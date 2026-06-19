# AGENTS.md

Quick context for AI agents working on this repo.

## Stack
- Python 3.11+, Poetry, FastAPI, yt-dlp
- Chrome extension (Manifest V3) in `extension/`

## Layout
- `backend/app/main.py` — FastAPI server (port 8000) with `/download_single` and `/download_smart_batch` endpoints
- `backend/app/get_video.py` — yt-dlp wrapper (`download_video(url, opts)`)
- `backend/scripts/` — utility scripts (note: `run.py` is incomplete; `cli_to_api.py` is a yt-dlp helper)
- `extension/` — Chrome extension that posts to the FastAPI backend
- `data.json` — debug dump of yt-dlp format listing, not used by the app

## Run the standalone download
```bash
poetry run python backend/app/get_video.py
```
Edit the `URL` variable on line 53 before running for a different video. Output goes to current dir.

## Run the API server
```bash
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

## Hardcoded values (in `backend/app/main.py`)
- Download path: `~/projetos/yt_downloader/downloads` (line 25)
- Max concurrent downloads: `4` (line 32, via `ThreadPoolExecutor`)
- Default format: 360p (line 100)

## Gotchas
- Project uses `__initi__.py` (typo) in root and subfolders — keep this if refactoring
- `get_id()` in `backend/scripts/run.py` and `backend/app/utils.py` is dead code (never called)
- `backend/scripts/run.py` has no `if __name__ == '__main__'` block — does nothing on its own
- `ffmpeg` system binary is required (`sudo apt install ffmpeg`)
- No tests, no linter, no CI configured
