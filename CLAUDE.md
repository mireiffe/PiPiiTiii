# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PiPiiTiii** is a PowerPoint parser and web viewer that extracts presentation content (slides, shapes, images, text, styles) and reconstructs them in a web-based interface. The system uses Windows COM automation (`pywin32`) to parse .pptx files and serves the parsed data via FastAPI, rendered by a SvelteKit frontend.

**Tech Stack:**

- Backend: Python 3.14, FastAPI 0.122, pywin32 311, Pillow 12.0
- Frontend: Svelte 5.43, SvelteKit 2.48, TailwindCSS 3.4, TypeScript 5.9
- Workflow: D3.js 7.9 (custom workflow graph visualization)
- Platform: **Windows only** (requires PowerPoint COM automation)

## Development Commands

### Backend (FastAPI Server)
```bash
python backend/main.py  # http://localhost:8000
```

### Frontend (SvelteKit Dev Server)
```bash
cd frontend
npm run dev  # http://localhost:5173
```

## Architecture

### Backend Structure

**Data Flow:**
```
Upload PPT → Background Task → COM Parser → JSON + Images → Frontend
```

**Key Modules:**
- `backend/main.py` - FastAPI server, endpoints, file upload
- `backend/ppt_parser/` - PowerPoint COM parsing (slides, shapes, styles, images, tables)
- `backend/llm_service.py` - LLM integration for workflow analysis

**Storage:**
```
uploads/              # Uploaded .pptx files
results/
  {project_id}/
    {project_id}.json # Parsed metadata
    images/           # Exported shape images (PNG)
```

### Frontend Structure

**Routes:**
- `/` - Project list
- `/upload` - Upload interface
- `/viewer/[id]` - Slide viewer with workflow editor

**Key Components:**
- `ViewerCanvas.svelte` - Main slide canvas with shape rendering
- `WorkflowSection.svelte` - Workflow tree UI container
- `workflow/D3WorkflowGraph.svelte` - Workflow graph editor using D3.js

**Node Types:**
- Phenomenon (red) - Root node with slide captures
- Sequence (blue) - Sequential child execution
- Selector (green) - First-success child selection
- Condition (yellow) - Branch logic
- Action (purple) - Executable operations

## Important Patterns

### Windows COM Automation

```python
powerpoint = win32.gencache.EnsureDispatch("PowerPoint.Application")
presentation = powerpoint.Presentations.Open(
    ppt_path,
    ReadOnly=False,
    Untitled=True,  # Avoid Protected View
    WithWindow=True
)
```

### RGB Color Conversion

PowerPoint COM uses BGR integer format (0xBBGGRR):
```python
r = rgb_val & 0xFF
g = (rgb_val >> 8) & 0xFF
b = (rgb_val >> 16) & 0xFF
```

### Error Handling

Individual shape failures don't stop parsing - log warnings and continue.

## API Endpoints

- `POST /api/upload` - Upload PPT, start background parsing
- `GET /api/projects` - List all projects
- `GET /api/project/{id}` - Get project JSON
- `POST /api/project/{id}/slides/{slide_index}/reparse` - Re-parse single slide
