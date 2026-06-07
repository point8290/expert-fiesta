# Running Local Music Video Studio on your machine

This gets the app running end to end. It works **without a GPU** — you can drive
the whole pipeline using manual audio + clip uploads. Local AI generation
(images, video, song, LLM) needs the optional model servers in the last section.

## What you need

- **Python 3.11+** and **Node 20+**
- **ffmpeg** on your PATH (for the final render)
- *(optional, for AI generation)* an NVIDIA GPU + [Ollama](https://ollama.com)
  and [ComfyUI](https://github.com/comfyanonymous/ComfyUI)

---

## Option A — Docker (simplest)

```bash
# from the repo root
docker compose up --build
```

This starts the backend (`:8000`), frontend (`:3000`), and Ollama (`:11434`).

```bash
# pull an LLM for lyrics/storyboard/characters
docker compose exec ollama ollama pull llama3.1

# (optional) also start ComfyUI for local image/video — needs an NVIDIA GPU
docker compose --profile gpu up --build
```

Then open **http://localhost:3000**, create an account, and go.

> Note: the frontend image currently runs Next.js in dev mode (fine for local;
> see `docs/PRODUCTION_READINESS.md` for the production build).

---

## Option B — Run the services directly

### 1. Backend (FastAPI, `:8000`)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt          # core + test deps (no GPU/ML needed)
pip install -r requirements-ml.txt        # librosa/numpy — only for real audio analysis
alembic upgrade head                      # create/upgrade the database schema
uvicorn app.main:app --reload
```

The schema is managed by Alembic (run `alembic upgrade head` after pulling
changes). An asset folder (`projects/`) is created on first upload. Interactive
API docs: **http://localhost:8000/docs**.

> Postgres: set `DATABASE_URL=postgresql+psycopg://user:pw@localhost:5432/lmvs`
> (the driver is bundled) and re-run `alembic upgrade head`.

Useful environment variables (all optional, sensible defaults):

| Var | Default | Purpose |
|-----|---------|---------|
| `DATABASE_URL` | `sqlite:///./localmv.db` | Database |
| `STORAGE_DIR` | `projects` | Where uploaded/generated assets are stored |
| `AUTH_SECRET` | dev placeholder | JWT signing key — **set this for anything real** |
| `CORS_ORIGINS` | `http://localhost:3000` | Allowed browser origins (comma-separated) |
| `OLLAMA_HOST` | `http://localhost:11434` | Local LLM server |
| `COMFYUI_HOST` | `http://localhost:8188` | ComfyUI server (images/video) |

### 2. Frontend (Next.js, `:3000`)

```bash
cd frontend
npm install
# point at the backend if it isn't the default:
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open **http://localhost:3000**.

---

## First run, step by step

1. **Create an account** — you'll be redirected to `/login`; register with an
   email + password (every project is scoped to your account).
2. **New Project** — fill the form, or pick a **template** to prefill it.
3. **Lyrics** — *Generate* (needs Ollama; otherwise skip).
4. **Audio** — *Upload* an MP3/WAV, or *Generate song* (needs the local song
   model). Then *Analyze* to extract beats/sections (needs `requirements-ml.txt`).
5. **Characters** — generate the bible, then per character generate/approve a
   reference image (needs ComfyUI).
6. **Storyboard** — *Generate* an 8–12 scene, beat-timed storyboard.
7. **Per scene** — generate/approve a **keyframe**, then generate/approve a
   **clip** (or just **upload** your own clip — no GPU needed).
8. **Quality** — score character consistency, suggest beat-synced cuts.
9. **Render** — pick an export preset (or aspect-ratio default) and *Render MP4*
   (needs ffmpeg).

### The no-GPU path
You can produce a finished MP4 with **zero** AI servers: create a project,
*upload* audio, generate a storyboard is LLM-backed (skip if no Ollama) — but you
can also just *upload a clip per scene* and **Render**. Lyrics/storyboard/
characters/keyframes/clips/song all degrade gracefully to manual upload.

---

## Running the tests

```bash
cd backend  && pytest                 # 147 tests, no GPU/ffmpeg/Ollama needed
cd frontend && npm run typecheck && npm run test
```

---

## Local AI generation (optional)

| Capability | Server | Notes |
|------------|--------|-------|
| Lyrics, storyboard, characters | **Ollama** `:11434` | `ollama pull llama3.1` |
| Keyframes, character refs, clips | **ComfyUI** `:8188` | Needs an NVIDIA GPU + the models referenced in `backend/app/comfyui/templates/*.json` |
| Local song generation | ACE-Step | Set `ACESTEP_MODEL`; heavy, GPU |
| Cloud fallback (per scene) | hosted API | Set `CLOUD_VIDEO_URL` / `CLOUD_VIDEO_API_KEY` |

Without these, the corresponding "Generate" buttons return an error and you fall
back to manual upload — the pipeline still completes.
