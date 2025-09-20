import os
import subprocess
import tempfile
import shutil
import requests
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_API_BASE = os.getenv('GITHUB_API_BASE')

print(GITHUB_TOKEN, GITHUB_API_BASE)

def make_github_request(endpoint: str, method: str = "GET") -> Dict[Any, Any]:
    """Make authenticated GitHub API request."""
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "MCP-Git-Tool"
    }
    url = f"{GITHUB_API_BASE}/{endpoint.lstrip('/')}"
    response = requests.request(method, url, headers=headers)
    response.raise_for_status()
    return response.json()

def clone_repo_temp(repo_url: str, branch: str = "main") -> str:
    """Clone repository to temporary directory."""
    temp_dir = tempfile.mkdtemp()
    try:
        cmd = ["git", "clone", "--depth", "50", "-b", branch, repo_url, temp_dir]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return temp_dir
    except subprocess.CalledProcessError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise Exception(f"Failed to clone repository: {e.stderr}")