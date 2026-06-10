# Running the project & configuring RunPod Serverless

This guide takes you from a clean checkout to a running system, maps every
dependency the pipeline can use, and explains how to wire image/video generation
to **RunPod Serverless** (the CB-2 compute backend).

The system is built so that **every external dependency is optional and behind a
config switch**. You can run it three ways:

| Mode | LLM | Image/Video | When to use |
|------|-----|-------------|-------------|
| **A. Fully local** | Ollama | Local ComfyUI (needs NVIDIA GPU) | You have a GPU box |
| **B. Hybrid (recommended)** | Hosted API (Anthropic/OpenAI) | RunPod Serverless | No local GPU; pay per second |
| **C. Manual / no-AI** | — | Upload your own clips | Demo / no servers at all |

---

## 1. Dependency map

### 1.1 Always required (the app itself)

| Dependency | Version | Used for | Install |
|------------|---------|----------|---------|
| **Python** | 3.11+ | Backend (FastAPI) | system / pyenv |
| **Node** | 20+ | Frontend (Next.js) | system / nvm |
| **ffmpeg** | any recent | Final MP4 render + transitions | `apt install ffmpeg` / `brew install ffmpeg` |
| Python: `requirements.txt` | — | FastAPI, SQLAlchemy, Alembic, httpx, JWT, bcrypt | `pip install -r backend/requirements.txt` |
| Node deps | — | React/Next UI | `npm install` in `frontend/` |

The database defaults to **SQLite** (zero setup). For multi-user / production use
**Postgres** via `DATABASE_URL` (the `psycopg` driver is already bundled).

### 1.2 Optional — only for *real audio analysis*

| Dependency | Used for | Install |
|------------|----------|---------|
| `requirements-ml.txt` (`librosa`, `numpy`, `soundfile`) | Extracting BPM/beats/sections from an uploaded track | `pip install -r backend/requirements-ml.txt` |

These are **lazily imported** — you don't need them for the test suite or for the
no-AI path. Without them, upload audio and set timing manually.

### 1.3 Optional — AI generation backends (pick per capability)

| Capability | Local option | Hosted option | Config switch |
|------------|--------------|---------------|---------------|
| Lyrics / storyboard / characters (LLM) | **Ollama** `:11434` | **Anthropic** or **OpenAI** API | `LLM_PROVIDER` |
| Keyframes / character refs (image) | **ComfyUI** `:8188` (GPU) | **RunPod Serverless** | `COMFYUI_PROVIDER` |
| Clips (video) | ComfyUI (LTX/Wan/Hunyuan, GPU) | **RunPod Serverless** | `COMFYUI_PROVIDER` |
| Per-scene fallback video | — | hosted video API | `CLOUD_VIDEO_URL` |
| Local song generation | ACE-Step (GPU) | — | `ACESTEP_MODEL` |

**Key idea:** nothing here is wired at import time. The backend reads config at
startup and selects the adapter. If a backend isn't configured, the matching
"Generate" button returns a clean error and you fall back to manual upload — the
pipeline still completes.

---

## 2. Step-by-step: run the project

### Step 0 — clone & pick a mode

```bash
git clone <repo> && cd expert-fiesta
```

Decide which mode (A/B/C) from the table above. Mode **B (hybrid)** is the path
this guide leads to, since it needs no local GPU.

### Step 1 — Backend (FastAPI, `:8000`)

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt        # core app
pip install -r requirements-ml.txt     # optional: real audio analysis
alembic upgrade head                   # create/upgrade the DB schema
```

Create `backend/.env` (or export the vars). Minimal hybrid example:

```bash
# --- security (set this for anything real) ---
AUTH_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# --- hosted LLM (Mode B) ---
LLM_PROVIDER=anthropic            # ollama | anthropic | openai
LLM_API_KEY=sk-ant-...            # your provider key
LLM_MODEL=claude-sonnet-4-6       # optional; empty = provider default

# --- RunPod Serverless for image+video (Mode B) ---
COMFYUI_PROVIDER=runpod           # local | runpod
RUNPOD_API_KEY=rpa_...
RUNPOD_IMAGE_ENDPOINT=https://api.runpod.ai/v2/<image-endpoint-id>
RUNPOD_VIDEO_ENDPOINT=https://api.runpod.ai/v2/<video-endpoint-id>

# --- optional cost guardrails (CB-5) ---
MAX_GPU_SECONDS_PER_USER=0        # 0 = unlimited
GPU_COST_PER_SECOND=0.00044       # for the usage/cost readout

# --- optional readiness gating (CB-6) ---
READY_CHECK_BACKENDS=false        # true = /ready probes LLM + RunPod before traffic
```

Start it:

```bash
uvicorn app.main:app --reload
```

API docs at **http://localhost:8000/docs**. If `ASYNC_JOBS=true`, also run the
worker (next step); otherwise generation runs inline in the request.

### Step 2 — (optional) async job worker

Image/video/clip generation is slow, so it can run through a DB-backed job queue
instead of blocking the request:

```bash
# same .venv
ASYNC_JOBS=true python -m app.worker     # processes queued jobs FIFO
```

Set `ASYNC_JOBS=true` for the backend too so endpoints enqueue rather than run
inline. Leave it off (default) for the simplest setup.

### Step 3 — Frontend (Next.js, `:3000`)

```bash
cd frontend
npm install
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

Open **http://localhost:3000**, register an account, and start a project.

### Step 4 — Docker alternative

```bash
docker compose up --build          # backend :8000, frontend :3000, ollama :11434
docker compose exec ollama ollama pull llama3.1   # if using local LLM
```

(For RunPod, set the `LLM_*` / `RUNPOD_*` / `COMFYUI_PROVIDER` vars in the compose
environment instead of running Ollama.)

### Step 5 — verify

```bash
curl http://localhost:8000/health        # {"status":"ok"}
curl http://localhost:8000/ready         # {"status":"ready","checks":{...}}
cd backend && pytest                      # full suite, no GPU/servers needed
```

---

## 3. Configuring RunPod Serverless

RunPod Serverless runs **our pinned ComfyUI workflow** on elastic GPUs. The
backend builds the workflow graph locally, submits it, polls for completion, and
writes the returned asset. You create **two endpoints** (image + video) — they
can share one worker image.

### 3.1 The contract the backend expects

The backend calls the standard RunPod Serverless REST API:

```
POST {ENDPOINT}/run          body: {"input": {"workflow": <ComfyUI graph JSON>}}
                             ->   {"id": "<job-id>"}
GET  {ENDPOINT}/status/{id}  ->   {"status": "COMPLETED", "output": {...}}
```

- Auth header: `Authorization: Bearer $RUNPOD_API_KEY`.
- Statuses `FAILED` / `CANCELLED` / `TIMED_OUT` raise a `RunPodError`.
- Your handler's `output` **must** contain the asset in one of:
  - `{"image_base64": "<b64>"}`  (or `{"base64": "<b64>"}`), **or**
  - `{"url": "https://.../asset"}` (the backend downloads it).

Source of truth: `backend/app/adapters/runpod.py` (`RunPodClient.run` and
`_write_output`).

### 3.2 What your RunPod worker handler must do

The handler receives `event["input"]["workflow"]` — a complete ComfyUI API-format
graph (prompts/seed/resolution already substituted). It should:

1. Boot ComfyUI (with the models below baked into the image or on a network volume).
2. Queue the provided graph, wait for it to finish.
3. Read the produced image (for image endpoints) or video file (for video
   endpoints).
4. Return it base64-encoded (`image_base64`/`base64`) or upload it and return `url`.

A minimal handler shape (Python, `runpod` SDK):

```python
import base64, runpod
from comfy_runner import run_graph   # your ComfyUI driver

def handler(event):
    graph = event["input"]["workflow"]
    asset_path = run_graph(graph)              # runs ComfyUI, returns output file
    data = base64.b64encode(open(asset_path, "rb").read()).decode()
    key = "image_base64" if asset_path.endswith((".png", ".jpg")) else "base64"
    return {key: data}

runpod.serverless.start({"handler": handler})
```

### 3.3 Models the workflows reference

The workflow JSONs the backend ships (`backend/app/comfyui/templates/`) reference
these — bake them into the worker image or mount a RunPod **network volume**:

| Endpoint | Workflow templates | Models needed |
|----------|--------------------|---------------|
| **Image** | `keyframe.json`, `keyframe_ipadapter.json`, `character.json` | SDXL (or your chosen checkpoint) + IP-Adapter for character consistency |
| **Video** | `ltx_video.json`, `wan_video.json`, `hunyuan_video.json` | LTX-Video, Wan, and/or HunyuanVideo checkpoints (only those you enable) |

The video model is chosen per project/scene by name (`ltx` / `wan` / `hunyuan`),
mapped to its workflow in `backend/app/video/registry.py` (`_RUNPOD_WORKFLOWS`).
You only need the model for the backend(s) you actually use; `ltx` is the default
and the lightest.

### 3.4 Create the endpoints (RunPod console)

1. **Build/choose a worker image** that runs ComfyUI + the handler above. Either
   bake models in, or attach a **Network Volume** with the models and point
   ComfyUI's model dirs at it (cheaper, faster cold starts to update).
2. In **Serverless → New Endpoint**, create one endpoint for **image** and one for
   **video** (video needs more VRAM — e.g. A100/L40S; image can run on a 24 GB
   card).
3. **Workers:** set **Min = 0** for cheapest (pure pay-per-use) or **Min = 1** to
   keep one warm and avoid cold starts. Set Max for your concurrency.
4. Copy each endpoint's URL — it looks like
   `https://api.runpod.ai/v2/<endpoint-id>` — into `RUNPOD_IMAGE_ENDPOINT` /
   `RUNPOD_VIDEO_ENDPOINT`.
5. Create an API key under **Settings → API Keys** → `RUNPOD_API_KEY`.

### 3.5 Wire it into the backend

```bash
COMFYUI_PROVIDER=runpod
RUNPOD_API_KEY=rpa_...
RUNPOD_IMAGE_ENDPOINT=https://api.runpod.ai/v2/<image-endpoint-id>
RUNPOD_VIDEO_ENDPOINT=https://api.runpod.ai/v2/<video-endpoint-id>
# optional: an audio endpoint for hosted song gen
RUNPOD_AUDIO_ENDPOINT=https://api.runpod.ai/v2/<audio-endpoint-id>
```

Restart the backend. `build_registry()` now builds RunPod-backed video backends
and `get_image_generator()` returns the RunPod image generator automatically.

### 3.6 Optional: cloud fallback + circuit breaker (CB-4)

If you also set a managed video API:

```bash
CLOUD_VIDEO_URL=https://your-video-api/generate
CLOUD_VIDEO_API_KEY=...
```

each RunPod video backend is wrapped in a `FallbackVideoBackend` with a circuit
breaker (3 failures → 60s cooldown). If RunPod errors or trips the breaker, clips
are generated via the cloud API instead — so a RunPod outage degrades instead of
failing.

### 3.7 Cost control & warm-up (CB-5 / CB-6)

- **Budget caps:** set `MAX_GPU_SECONDS_PER_USER` to return **429** once a user
  burns through their GPU-second budget. `GPU_COST_PER_SECOND` powers the
  `totalGpuSeconds` / `estimatedCost` figures in each project's usage summary.
- **Readiness gating:** set `READY_CHECK_BACKENDS=true` so `/ready` probes the
  RunPod (and hosted LLM) endpoints and returns **503** until they answer — useful
  behind a load balancer so a cold node doesn't take traffic. Tune the probe with
  `READY_PROBE_TIMEOUT_SECONDS`.

### 3.8 Verify the RunPod path

```bash
# with the RunPod vars set, in the app:
# 1. create a project, generate a storyboard (LLM)
# 2. on a scene: generate a keyframe   -> hits RUNPOD_IMAGE_ENDPOINT
# 3. approve it, then generate a clip   -> hits RUNPOD_VIDEO_ENDPOINT
# watch the RunPod console: a job appears, runs, completes
curl http://localhost:8000/ready        # with READY_CHECK_BACKENDS=true, confirms RunPod reachable
```

If a generation returns an error, check: API key valid, endpoint URL correct
(includes the endpoint id), the worker handler returns `image_base64`/`base64`/
`url`, and the required models are present on the worker.

---

## 4. Full config reference (compute backends)

| Var | Default | Purpose |
|-----|---------|---------|
| `LLM_PROVIDER` | `ollama` | `ollama` \| `anthropic` \| `openai` |
| `LLM_API_KEY` | — | Hosted LLM key |
| `LLM_MODEL` | provider default | Override model name |
| `LLM_BASE_URL` | provider default | Override API base URL |
| `LLM_TIMEOUT_SECONDS` | `120` | LLM + RunPod HTTP timeout |
| `COMFYUI_PROVIDER` | `local` | `local` \| `runpod` |
| `RUNPOD_API_KEY` | — | RunPod bearer token |
| `RUNPOD_IMAGE_ENDPOINT` | — | Serverless endpoint for keyframes/refs |
| `RUNPOD_VIDEO_ENDPOINT` | — | Serverless endpoint for clips |
| `RUNPOD_AUDIO_ENDPOINT` | — | Serverless endpoint for song gen |
| `CLOUD_VIDEO_URL` / `CLOUD_VIDEO_API_KEY` | — | Managed video fallback (CB-4) |
| `MAX_GPU_SECONDS_PER_USER` | `0` | Per-user GPU budget; 0 = unlimited (CB-5) |
| `GPU_COST_PER_SECOND` | `0.0` | Cost estimate in usage summary (CB-5) |
| `READY_CHECK_BACKENDS` | `false` | `/ready` probes remote backends (CB-6) |
| `READY_PROBE_TIMEOUT_SECONDS` | `3.0` | Per-probe timeout (CB-6) |
| `ASYNC_JOBS` | `false` | Enqueue generation to the worker vs. run inline |

See also `docs/RUNNING_LOCALLY.md` (local-first walkthrough) and
`docs/COMPUTE_BACKEND_PLAN.md` (the design decisions behind these switches).
