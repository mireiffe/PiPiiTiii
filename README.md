# PiPiiTiii

PiPiiTiii is a PowerPoint (PPT) Rebuilder and Parser application. It allows users to upload PowerPoint files, parse their content (slides, shapes, images), and view or reconstruct them in a web-based interface.

## Features

-   **PPT Parsing**: Extracts slides, shapes, and metadata from `.pptx` files.
-   **Web Viewer**: Interactive dashboard to view and manage parsed projects.
-   **Reconstruction**: (In progress) Capability to rebuild or modify presentations.

## Tech Stack

-   **Backend**: Python, FastAPI
-   **Frontend**: SvelteKit, TailwindCSS, TypeScript

## Installation & Usage

### Prerequisites

-   Python 3.8+
-   Node.js & npm

### Quick Start

You can use the provided helper scripts to start both backend and frontend:

**Windows (PowerShell):**
```powershell
./start_dev.ps1
```

**Linux/macOS:**
```bash
./start_dev.sh
```

### Manual Setup

**Backend:**
1.  Navigate to the `backend` directory.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the server:
    ```bash
    python main.py
    ```

**Frontend:**
1.  Navigate to the `frontend` directory.
2.  Install dependencies:
    ```bash
    npm install
    ```
3.  Run the development server:
    ```bash
    npm run dev
    ```
