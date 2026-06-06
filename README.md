# Local Music Video Studio

A local-first, AI-assisted pipeline for producing animated music videos. A
creator enters a song idea, generates lyrics, uploads (or later generates)
audio, and the system builds a beat-timed storyboard, character references,
keyframes, and short video clips — then stitches a final MP4. The emphasis is
**organized creative control**: scene-based, reviewable, with approval at every
stage and manual replacement of any asset.

> Not a one-click generator — a local AI-assisted production pipeline for
> creators who want control, privacy, low API cost, and scene-level editing.

See [`docs/PRODUCT.md`](docs/PRODUCT.md) for the product spec,
[`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) for the architecture, and
[`docs/STORIES.md`](docs/STORIES.md) for the story-by-story build log.

## Status

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | No-GPU spine: projects, lyrics, audio + analysis, storyboard, scenes, clip upload, FFmpeg render | ✅ complete |
| 2 | ComfyUI adapter, character bible, references, keyframes, IP-Adapter consistency, job queue | ✅ complete |
| 3 | VideoBackend + LTX-Video, scene clip generation, clip review, render from generated clips | ✅ complete |
| 4 | Wan 2.2 / HunyuanVideo, prompt versioning, consistency scoring, transitions | ⬜ planned |
| 5 | Productization (templates, multi-user, cloud fallback, SaaS) | ⬜ planned |

**Phases 1–3 are the MVP.** Backend: 89 tests. Frontend: 7 tests. Built test-first.

## Architecture

```
Next.js review UI  ──REST──>  FastAPI backend  ──>  SQLite (metadata)
 (frontend/)                   (backend/)            filesystem (assets)
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                      ▼
        LLM (Ollama)         ComfyUI (images/video)   FFmpeg (render)
     lyrics, storyboard,     keyframes, char refs,    normalize + concat
        characters           LTX-Video clips             + mux audio
```

Every external dependency sits behind a **mockable adapter** injected via
FastAPI dependencies, so the full test suite runs with no GPU, Ollama, ComfyUI,
or ffmpeg. The **scene graph is the source of truth**; models are swappable
workers, and slow generation runs on a single-worker **job queue**.

## Repository layout

```
backend/    FastAPI app, adapters (llm, audio, render, comfyui, video), services, tests
frontend/   Next.js (App Router) review UI + typed API client, tests
docs/       PRODUCT.md, BUILD_PLAN.md, STORIES.md
docker-compose.yml   Local stack: backend, frontend, Ollama, (optional) ComfyUI
```

## Quick start (Docker)

```bash
# Core stack (backend + frontend + Ollama). ComfyUI is opt-in (needs a GPU).
docker compose up --build

# Pull a model for lyrics/storyboard/characters:
docker compose exec ollama ollama pull llama3.1

# With local image/video generation (requires NVIDIA GPU + nvidia-container-toolkit):
docker compose --profile gpu up --build
```

- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000/docs

## Local development (without Docker)

Backend:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # core/runtime + test deps
pip install -r requirements-ml.txt        # librosa/numpy for real audio analysis
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

External services for full functionality: [Ollama](https://ollama.com) on
`:11434`, [ComfyUI](https://github.com/comfyanonymous/ComfyUI) on `:8188`, and
`ffmpeg` on PATH. Configure via `OLLAMA_HOST`, `COMFYUI_HOST`, `STORAGE_DIR`,
`DATABASE_URL`, and `NEXT_PUBLIC_API_URL`.

## Tests

```bash
cd backend  && pytest                 # 89 tests, no GPU/ffmpeg/Ollama needed
cd frontend && npm run typecheck && npm run test
```

CI runs both suites on every push — see `.github/workflows/ci.yml`.
