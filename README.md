
## Project Setup & Usage Guide

Follow these steps to set up and run the project:

---

### 1. Prerequisites

#### Install Required Tools

- **Gemini CLI**: Download and install from [Gemini CLI GitHub].
- **ngrok**: Download from [ngrok.com](https://ngrok.com/download).
- **uv**: pip install uv
- **Python dependencies**: Install using `uv` (see below).
- **Stytch Project**: Set up a Stytch project at [Stytch Dashboard](https://stytch.com/dashboard).

---

### 2. Backend Setup (Custom MCP Tool)

1. Clone or download this repository.
2. Install Python dependencies for fastmcp with uv.
    uv add "mcp[cli]"

3. Run the MCP tool (replace `<filename>` with your Python entry file, e.g., `main.py`):
	uv run <filename>

### 3. Expose Local Server with ngrok

1. In a new terminal, run:
	```powershell
	ngrok http <portnumber>
	```
	Replace `<portnumber>` with the port your MCP tool is running on (e.g., 8000).
2. Copy the generated public HTTP link from ngrok.


### 4. Configure Gemini CLI

1. After successful Gemini CLI setup, locate the `settings.json` file (usually in the Gemini CLI directory).
2. Add the ngrok public HTTP link to the appropriate field in `settings.json`.


### 5. Frontend Setup (Vite + Stytch)

1. Navigate to the `frontend` directory:
	```powershell
	cd frontend
	```
2. Install dependencies:
	```powershell
	npm install
	```
3. Start the development server:
	```powershell
	npm run dev
	```
4. Open the authentication tab in your browser (usually at [http://localhost:5173](http://localhost:5173)).

---

### 6. Start Gemini CLI

1. Run Gemini CLI by "gemini" command in terminal.
2. Ensure the settings include the ngrok link for proper backend communication.

### 7. OPA Setup

1. Download opa_windows_amd64.exe from [https://github.com/open-policy-agent/opa/releases](https://github.com/open-policy-agent/opa/releases).
2. Rename it as opa.exe and add it in opa/

## Notes

- Ensure all environment variables and API keys (Stytch, Gemini, etc.) are set up as required.
- For troubleshooting, refer to the documentation of each tool.

