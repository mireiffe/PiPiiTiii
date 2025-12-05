# PiPiiTiii

PiPiiTiii is a presentation rebuilder and parser that automates Microsoft PowerPoint through Python's `win32com` library. It opens `.pptx` files, extracts slide contents (shapes, images, metadata), and surfaces them in a web interface for inspection and reconstruction.

## Features
- **PowerPoint-native parsing**: Uses `pywin32` (`win32com`) to drive Microsoft PowerPoint for high-fidelity reads of presentations.
- **Project dashboard**: Upload PowerPoint files, monitor parsing progress, and browse slide data from the backend API.
- **Web viewer & reconstruction**: SvelteKit UI for visualizing parsed slides and iterating on rebuilt presentations.

## Tech Stack
- **Backend**: Python, FastAPI, PowerPoint COM automation
- **Frontend**: SvelteKit, TailwindCSS, TypeScript

## Prerequisites
- Windows environment with Microsoft PowerPoint installed (required for COM automation).
- Python 3.10+ with [`uv`](https://docs.astral.sh/uv/) available in your PATH.
- Node.js and npm for the frontend.

## Setup & Usage
### 1) Backend environment
Install Python dependencies with `uv` (this creates or updates `.venv` automatically):
```bash
uv sync
```

### 2) Run the backend API
Start the FastAPI server (default port `8000`). Ensure PowerPoint is installed and available on the host:
```bash
uv run python backend/main.py
```
To change the port, set `BACKEND_PORT` (e.g., `BACKEND_PORT=9000 uv run python backend/main.py`).

### 3) Frontend
Install and run the SvelteKit app:
```bash
cd frontend
npm install
npm run dev
```
If you customized the backend port, set `VITE_API_PORT` to match when starting the frontend (e.g., `VITE_API_PORT=9000 npm run dev`).

### 4) Combined dev helper
The repo includes helper scripts that start both services after dependencies are installed with `uv sync`:
- **Windows (PowerShell):**
  ```powershell
  ./start_dev.ps1
  ```
- **Linux/macOS:**
  ```bash
  ./start_dev.sh
  ```

## Usage
1. Open the frontend (default `http://localhost:5173`).
2. Upload a `.pptx` file. The backend drives Microsoft PowerPoint to parse slides and stores results in `results/`.
3. Monitor progress, review parsed slide data, and iterate on reconstructions through the web UI.
