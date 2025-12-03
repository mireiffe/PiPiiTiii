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

```powershell
npm list
frontend@0.0.1 PiPiiTiii\frontend
├── @sveltejs/adapter-auto@7.0.0
├── @sveltejs/kit@2.49.0
├── @sveltejs/vite-plugin-svelte@6.2.1
├── autoprefixer@10.4.22
├── detect-libc@2.1.2 extraneous
├── lightningcss-win32-x64-msvc@1.30.2 extraneous
├── postcss@8.5.6
├── svelte-check@4.3.4
├── svelte@5.45.2
├── tailwindcss@3.4.17
├── typescript@5.9.3
└── vite@7.2.4
```