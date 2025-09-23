import os
import tempfile
import shutil
from typing import TypedDict, List, Optional, Dict, Any
from dotenv import load_dotenv
import httpx
from starlette.requests import Request as StarletteRequest
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.dependencies import get_access_token, AccessToken
from pydantic import BaseModel, Field
from fastmcp import FastMCP
from githubhelper import make_github_request, clone_repo_temp

from starlette.requests import Request as StarletteRequest
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from starlette.responses import JSONResponse
from fastmcp.server.auth import BearerAuthProvider
from fastmcp.server.dependencies import get_access_token, AccessToken
from starlette.types import ASGIApp, Receive, Scope, Send

from pydantic import BaseModel, Field
from fastmcp import FastMCP

load_dotenv()

auth = BearerAuthProvider(
    jwks_uri=f"{os.getenv('STYTCH_DOMAIN')}/.well-known/jwks.json",
    issuer=os.getenv("STYTCH_DOMAIN"),
    algorithm="RS256",
    audience=os.getenv("STYTCH_PROJECT_ID")
)

mcp = FastMCP(name="GitHub Tools Integration", auth=auth)

# Configuration
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_BASE = os.getenv('GITHUB_API_BASE')

print(f"Using GitHub API Base:", GITHUB_API_BASE)
print(f"Using GitHub Token:", GITHUB_TOKEN)

OPA_SERVER_URL = "http://localhost:8181/v1/data/policies/main"

# Custom middleware to enforce policies using OPA
class OPAMiddleware:
    """
    Middleware that sends tool call information to an OPA server for authorization.
    """
    def __init__(self, app: ASGIApp):
        self.app = app
        self.client = httpx.AsyncClient()

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        # Only process requests that have the required tool call header
        if scope["type"] == "http" and "x-mcp-tool-call" in scope.get("headers", {}):
            request = StarletteRequest(scope, receive)
            try:
                # Decode the tool call header to get the tool name and arguments
                # Note: headers are bytes, so we need to decode them
                tool_call_header = request.headers.get("x-mcp-tool-call")
                tool_call_data = self.decode_tool_call_header(tool_call_header)

                # Prepare the input for the OPA policy check
                opa_input = {"tool_call": tool_call_data}
                print("OPA Input:", opa_input)

                # Make a POST request to the OPA server
                response = await self.client.post(OPA_SERVER_URL, json={"input": opa_input})
                response.raise_for_status()
                
                # Check the OPA policy result
                opa_result = response.json().get("result", False)
                if not opa_result:
                    # Policy denied the request
                    response_body = {"error": "Request denied by policy."}
                    response = JSONResponse(response_body, status_code=403)
                    await response(scope, receive, send)
                    return

            except httpx.HTTPStatusError as e:
                # OPA server returned an error (e.g., 404, 500)
                response_body = {"error": f"OPA server error: {e.response.text}"}
                response = JSONResponse(response_body, status_code=500)
                await response(scope, receive, send)
                return
            except Exception as e:
                # Other errors (e.g., decoding header, invalid JSON)
                response_body = {"error": f"Policy check failed: {str(e)}"}
                response = JSONResponse(response_body, status_code=500)
                await response(scope, receive, send)
                return

        # If the check passes or the request is not a tool call, proceed
        await self.app(scope, receive, send)

    def decode_tool_call_header(self, header_value: str) -> Dict[str, Any]:
        """A simplified decoder for the tool call header."""
        # A more robust solution would handle complex JSON/URL encoding
        # For this example, we assume a simple JSON string.
        import json
        return json.loads(header_value)

# Pydantic Models for structured responses
class CommitInfo(BaseModel):
    """Commit information structure."""
    sha: str = Field(description="Commit SHA hash")
    message: str = Field(description="Commit message")
    author: str = Field(description="Commit author")
    date: str = Field(description="Commit date")
    url: str = Field(description="Commit URL")


class FileChange(BaseModel):
    """File change information."""
    filename: str = Field(description="Changed file path")
    status: str = Field(description="Change status (added/modified/deleted)")
    additions: int = Field(description="Lines added")
    deletions: int = Field(description="Lines deleted")
    patch: Optional[str] = Field(description="File diff patch", default=None)


class CommitDiff(BaseModel):
    """Complete commit diff information."""
    commit: CommitInfo
    files: List[FileChange]
    total_additions: int = Field(description="Total lines added")
    total_deletions: int = Field(description="Total lines deleted")


class RepoInfo(BaseModel):
    """Repository information."""
    name: str
    full_name: str
    description: Optional[str]
    default_branch: str
    clone_url: str
    updated_at: str


class BranchInfo(TypedDict):
    """Branch information structure."""
    name: str
    sha: str
    protected: bool

# MCP Tools
@mcp.tool()
def get_repo_info(owner: str, repo: str) -> RepoInfo:
    """Get repository information from GitHub."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}")
        return RepoInfo(
            name=data["name"],
            full_name=data["full_name"],
            description=data.get("description"),
            default_branch=data["default_branch"],
            clone_url=data["clone_url"],
            updated_at=data["updated_at"]
        )
    except Exception as e:
        raise Exception(f"Failed to get repo info: {str(e)}")


@mcp.tool()
def get_latest_commit(owner: str, repo: str, branch: str = "main") -> CommitInfo:
    """Get the latest commit from a repository branch."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}/commits/{branch}")
        return CommitInfo(
            sha=data["sha"],
            message=data["commit"]["message"],
            author=data["commit"]["author"]["name"],
            date=data["commit"]["author"]["date"],
            url=data["html_url"]
        )
    except Exception as e:
        raise Exception(f"Failed to get latest commit: {str(e)}")


# Additional MCP Tools for full GitHub access
@mcp.tool()
def get_commit_diff(owner: str, repo: str, commit_sha: str) -> CommitDiff:
    """Get detailed diff for a specific commit."""
    try:
        commit_data = make_github_request(f"repos/{owner}/{repo}/commits/{commit_sha}")
        commit_info = CommitInfo(
            sha=commit_data["sha"],
            message=commit_data["commit"]["message"],
            author=commit_data["commit"]["author"]["name"],
            date=commit_data["commit"]["author"]["date"],
            url=commit_data["html_url"]
        )
        files = []
        total_additions = 0
        total_deletions = 0
        for file_data in commit_data.get("files", []):
            file_change = FileChange(
                filename=file_data["filename"],
                status=file_data["status"],
                additions=file_data.get("additions", 0),
                deletions=file_data.get("deletions", 0),
                patch=file_data.get("patch", "")
            )
            files.append(file_change)
            total_additions += file_change.additions
            total_deletions += file_change.deletions
        return CommitDiff(
            commit=commit_info,
            files=files,
            total_additions=total_additions,
            total_deletions=total_deletions
        )
    except Exception as e:
        raise Exception(f"Failed to get commit diff: {str(e)}")


@mcp.tool()
def get_recent_commits(owner: str, repo: str, count: int = 10, branch: str = "main") -> List[CommitInfo]:
    """Get recent commits from a repository."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}/commits?sha={branch}&per_page={count}")
        commits = []
        for commit_data in data:
            commit = CommitInfo(
                sha=commit_data["sha"],
                message=commit_data["commit"]["message"],
                author=commit_data["commit"]["author"]["name"],
                date=commit_data["commit"]["author"]["date"],
                url=commit_data["html_url"]
            )
            commits.append(commit)
        return commits
    except Exception as e:
        raise Exception(f"Failed to get recent commits: {str(e)}")


@mcp.tool()
def get_file_content(owner: str, repo: str, file_path: str, branch: str = "main") -> dict:
    """Get content of a specific file from repository."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}/contents/{file_path}?ref={branch}")
        if data.get("type") != "file":
            raise Exception(f"Path {file_path} is not a file")
        import base64
        content = base64.b64decode(data["content"]).decode('utf-8')
        return {
            "path": file_path,
            "content": content,
            "sha": data["sha"],
            "size": data["size"],
            "download_url": data.get("download_url", "")
        }
    except Exception as e:
        raise Exception(f"Failed to get file content: {str(e)}")


@mcp.tool()
def get_branches(owner: str, repo: str) -> List[BranchInfo]:
    """Get all branches from a repository."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}/branches")
        branches = []
        for branch_data in data:
            branch = BranchInfo(
                name=branch_data["name"],
                sha=branch_data["commit"]["sha"],
                protected=branch_data.get("protected", False)
            )
            branches.append(branch)
        return branches
    except Exception as e:
        raise Exception(f"Failed to get branches: {str(e)}")


@mcp.tool()
def compare_commits(owner: str, repo: str, base: str, head: str) -> dict:
    """Compare two commits/branches and get the diff."""
    try:
        data = make_github_request(f"repos/{owner}/{repo}/compare/{base}...{head}")
        files_changed = []
        for file_data in data.get("files", []):
            files_changed.append({
                "filename": file_data["filename"],
                "status": file_data["status"],
                "additions": file_data.get("additions", 0),
                "deletions": file_data.get("deletions", 0),
                "changes": file_data.get("changes", 0),
                "patch": file_data.get("patch", "")
            })
        return {
            "base": base,
            "head": head,
            "ahead_by": data.get("ahead_by", 0),
            "behind_by": data.get("behind_by", 0),
            "total_commits": data.get("total_commits", 0),
            "files": files_changed,
            "status": data.get("status", ""),
            "permalink_url": data.get("permalink_url", "")
        }
    except Exception as e:
        raise Exception(f"Failed to compare commits: {str(e)}")


@mcp.tool()
def search_repositories(query: str, language: str = "", sort: str = "updated") -> List[dict]:
    """Search for repositories on GitHub."""
    try:
        search_query = query
        if language:
            search_query += f" language:{language}"
        params = f"q={search_query}&sort={sort}&order=desc&per_page=10"
        data = make_github_request(f"search/repositories?{params}")
        repos = []
        for repo in data.get("items", []):
            repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "updated_at": repo["updated_at"],
                "html_url": repo["html_url"]
            })
        return repos
    except Exception as e:
        raise Exception(f"Failed to search repositories: {str(e)}")


@mcp.tool()
def get_user_repos(username: str, type: str = "all") -> List[dict]:
    """Get repositories for a specific user."""
    try:
        data = make_github_request(f"users/{username}/repos?type={type}&sort=updated&per_page=20")
        repos = []
        for repo in data:
            repos.append({
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "updated_at": repo["updated_at"],
                "html_url": repo["html_url"],
                "clone_url": repo["clone_url"]
            })
        return repos
    except Exception as e:
        raise Exception(f"Failed to get user repositories: {str(e)}")


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET","OPTIONS"])
def oauth_metadata(request: StarletteRequest) -> JSONResponse:
    base_url = str(request.base_url).rstrip("/")

    return JSONResponse({
        "resource": base_url,
        "authorization_servers": [os.getenv("STYTCH_DOMAIN")],
        "scopes_supported": ["read","write"],
        "bearer_methods_supported": ["header","body"]
    })

    
if __name__ == "__main__":
    # Validate GitHub token on startup
    if not GITHUB_TOKEN:
        print("Warning: GITHUB_PERSONAL_ACCESS_TOKEN not set. Some features may not work.")
    else:
        print("GitHub MCP Server initialized with authentication.")
    
    mcp.run(
        transport="http",
        host="127.0.0.1",
        port=8000,
        middleware=[
            Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],allow_credentials=True),
            Middleware(OPAMiddleware)
        ]
    )