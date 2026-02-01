# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**PiPiiTiii** is a PowerPoint parser and web viewer that extracts presentation content (slides, shapes, images, text, styles) and reconstructs them in a web-based interface. The system uses Windows COM automation (`pywin32`) to parse .pptx files and serves the parsed data via FastAPI, rendered by a SvelteKit frontend.

**Tech Stack:**

- Backend: Python 3.14, FastAPI 0.122, pywin32 311, Pillow 12.0
- Frontend: Svelte 5.43, SvelteKit 2.48, TailwindCSS 3.4, TypeScript 5.9
- Testing: Vitest (Frontend), Pytest (Backend)
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

### Test & Lint

```bash
# Run all tests and lints
uv run pytest tests/                    # Backend tests (pytest)
cd frontend && npm run test -- --run    # Frontend tests (vitest)
cd frontend && npm run lint             # Frontend lint (svelte-check)
uv run ruff check .                     # Backend lint (ruff)
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
- `backend/database.py` - SQLite database operations
- `backend/llm_service.py` - LLM integration for summary generation

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
- `/viewer/[id]` - Slide viewer with KeyInfo editor
- `/settings` - Application settings

**Key Components:**
- `ViewerCanvas.svelte` - Main slide canvas with shape rendering
- `KeyInfoSection.svelte` - KeyInfo (핵심정보) management UI
- `KeyInfoSettingsSection.svelte` - KeyInfo category/item definition settings

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

### Backend-Frontend Type Sync (IMPORTANT)

When adding new fields to frontend TypeScript types (e.g., in `keyInfo.ts`), **always check and update the corresponding Pydantic models in the backend**. Otherwise, the backend will silently drop unknown fields during validation, causing data to not be saved.

Example: Adding `imageCaptions` to `KeyInfoInstance` in TypeScript requires also adding it to the Pydantic model in `backend/main.py`.

### KeyInfo System (핵심정보)

프로젝트별 핵심 정보를 관리하는 시스템:
- **Category**: 핵심정보 분류 (예: "현상", "원인", "대책")
- **Item**: 각 카테고리 내 항목 정의
- **Instance**: 프로젝트별 실제 데이터 (텍스트, 캡처, 이미지)

**핵심 파일:**
- `frontend/src/lib/types/keyInfo.ts` - 타입 정의
- `frontend/src/lib/stores/keyInfo.ts` - 상태 관리
- `frontend/src/lib/components/viewer/right-pane/KeyInfoSection.svelte` - 메인 UI

**다중 캡처/이미지 지원:**
```typescript
interface KeyInfoInstance {
    categoryId: string;
    itemId: string;
    textValue?: string;
    captureValues?: KeyInfoCaptureValue[];  // 다중 캡처
    imageIds?: string[];                     // 다중 이미지
}
```

### Testing Infrastructure

**Frontend (Vitest):**
- 설정: `frontend/vitest.config.ts`
- 셋업: `frontend/src/setupTest.ts`
- SvelteKit 모킹: `frontend/src/mocks/app/`

**Backend (Pytest):**
- 테스트: `tests/backend/`

## API Endpoints

- `POST /api/upload` - Upload PPT, start background parsing
- `GET /api/projects` - List all projects
- `GET /api/project/{id}` - Get project JSON
- `POST /api/project/{id}/slides/{slide_index}/reparse` - Re-parse single slide
- `GET /api/project/{id}/keyinfo` - Get KeyInfo data
- `POST /api/project/{id}/keyinfo` - Update KeyInfo data
- `POST /api/project/{id}/keep` - Archive/unarchive project
