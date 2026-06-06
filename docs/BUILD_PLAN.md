# Build Plan: Local Music Video Studio

This is the engineering build plan for the product described in
[`PRODUCT.md`](./PRODUCT.md). It translates the product roadmap into a concrete,
phased technical plan with architecture, data model, and per-phase deliverables.

---

## 0. Guiding Principles

These principles come straight out of the product constraints and shape every
decision below:

1. **The scene graph is the source of truth.** Models are fallible, swappable
   workers. The product is an orchestration + review layer around them, not the
   models themselves.
2. **Approval is a state transition.** Every generated asset has an explicit
   status (`pending → generating → generated → approved | rejected`). Because
   each scene's assets are independent rows, "regenerate one bad scene without
   restarting the project" falls out for free.
3. **Start GPU-free.** Prove the entire spine (project → lyrics → audio analysis
   → storyboard → manual clip upload → MP4 render) before touching ComfyUI.
4. **Never block HTTP on generation.** GPU work takes minutes; it runs in a
   background job queue with progress streamed to the UI.
5. **Never rely on a single video model.** Image and video backends sit behind a
   common interface so LTX-Video, Wan 2.2, and HunyuanVideo are drop-in.
6. **Pin everything in the model layer.** ComfyUI custom-node breakage is the
   top flagged risk; vendor pinned workflow JSON and smoke-test on startup.

---

## 1. Target Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       Frontend (Next.js / React)                   │
│  Dashboard · Project · Lyrics · Audio · Storyboard · Character ·   │
│  Keyframe · Clip · Final Render        (polling / SSE for jobs)    │
└───────────────────────────────┬──────────────────────────────────┘
                                 │ REST + SSE
┌───────────────────────────────▼──────────────────────────────────┐
│                      Backend API (FastAPI)                         │
│  Projects · Lyrics · Audio · Scenes · Characters · Jobs · Render   │
│  SQLite (metadata)  ·  Filesystem (assets, per-project folders)    │
└───────┬───────────────┬───────────────┬───────────────┬──────────┘
        │               │               │               │
        ▼               ▼               ▼               ▼
   Job Queue        LLM Adapter     Media Adapter    Render Adapter
  (RQ/Celery     (Ollama: lyrics,  (ComfyUI HTTP+WS: (FFmpeg: normalize,
   + Redis;       storyboard,       keyframes,        concat, mux audio)
   serializes     characters)       clips)
   GPU work)
```

### Components

| Component | Responsibility |
|---|---|
| **Frontend** | Card-based review UI; create projects; trigger generation; approve/regenerate/replace assets; poll job progress; download final MP4. |
| **Backend API** | CRUD over the scene graph; enqueue jobs; serve assets; orchestrate the pipeline state machine. |
| **Job Queue** | Single GPU worker serializing slow generation; progress + error reporting; one model loaded at a time. |
| **LLM Adapter** | Wraps Ollama for lyrics, storyboard, and character generation with structured JSON output + validation/retry. |
| **Media Adapter** | Wraps ComfyUI; clones parameterized workflow templates, injects prompts/seeds, listens on WebSocket for completion, pulls assets. |
| **Render Adapter** | Deterministic, re-runnable FFmpeg pipeline producing the final MP4. |

### Recommended Stack

- **Backend / orchestrator:** Python + FastAPI (local-AI ecosystem is Python-native).
- **LLM:** Ollama serving Llama 3.1 / Qwen2.5.
- **Image + video:** ComfyUI via HTTP + WebSocket API (SDXL/Flux for images;
  LTX-Video → Wan 2.2 / HunyuanVideo for clips).
- **Audio analysis:** librosa + ffprobe.
- **Final render:** FFmpeg (subprocess).
- **Job queue:** RQ or Celery + Redis (or DB-backed worker for zero extra deps).
- **DB:** SQLite. **Asset storage:** filesystem, per-project folders.
- **Frontend:** Next.js / React.

---

## 2. Data Model

```
Project(id, title, idea, genre, mood, visualStyle, targetDuration,
        aspectRatio, status, createdAt, updatedAt)

Audio(id, projectId, path, durationSeconds, bpm, beats[], sections[],
      waveform, source)            # source = "upload" | "generated"

Lyrics(id, projectId, title, structure, body, musicPrompt, emotionalArc)

Character(id, projectId, name, age, face, hair, clothing, personality,
          identityAnchors[], refImagePath, status)

Scene(id, projectId, number, startTime, endTime, durationSeconds,
      sectionName, visualDescription, cameraInstruction, motionInstruction,
      keyframePrompt, videoPrompt, negativePrompt,
      keyframePath, keyframeStatus, clipPath, clipStatus)

Job(id, projectId, sceneId?, type, status, progress, error, params,
    resultPath, createdAt)
    # type   = "lyrics" | "storyboard" | "character" | "keyframe" | "clip" | "render"
    # status = "queued" | "running" | "succeeded" | "failed"
```

The `*Status` fields plus the `Job` table drive the entire approval workflow and
make per-scene regeneration independent.

### Filesystem layout

```
projects/<projectId>/
  audio/song.wav
  characters/<characterId>.png
  scenes/<sceneId>/keyframe.png
  scenes/<sceneId>/clip.mp4
  scenes/<sceneId>/uploaded_clip.mp4
  renders/final.mp4
  workflows/                 # snapshot of the workflow JSON used
```

---

## 3. Phased Plan

Each phase ends in a **demoable, shippable increment**. Phases map 1:1 to the
product roadmap but are sequenced to de-risk GPU work as late as possible.

### Phase 1 — Pipeline Skeleton (no GPU)

**Goal:** End-to-end MP4 from a song idea + uploaded audio + *manually uploaded*
clips. Proves the data model and render pipeline before any image/video model.

**Backend**
- Project CRUD + SQLite schema + per-project filesystem layout.
- Lyrics generation via Ollama (structured JSON: title, structure, body,
  musicPrompt, emotionalArc) with originality system prompt + validation/retry.
- Audio upload (MP3/WAV) + analysis: `ffprobe` duration; librosa BPM, beat
  timestamps, rough sections; downsampled waveform envelope.
- Storyboard generation: LLM call fed lyrics + audio analysis + style + scene
  count (8–12); returns scene array; **post-process to snap start/end times to
  real section/beat boundaries.**
- Scene management endpoints (list, edit prompt, regenerate prompt).
- Manual clip upload per scene; mark scene final.
- FFmpeg final render: normalize res/fps/SAR, concat (hard cuts), mux audio,
  trim to audio length → `renders/final.mp4`.
- Job queue scaffolding (even if jobs are fast here).

**Frontend**
- Dashboard, Project Creation, Lyrics, Audio (waveform), Storyboard (scene
  cards), Clip upload, Final Render + download screens.

**Exit criteria** (maps to success metrics 1, 2, 4, 5)
- User creates a project, generates lyrics, uploads audio, gets a timed
  storyboard, uploads clips per scene, and downloads a final 40–60s MP4 — with
  no GPU and no paid APIs.

---

### Phase 2 — Local Image Generation

**Goal:** Replace imagination with pictures — character refs + scene keyframes
via ComfyUI.

- **Media Adapter v1:** ComfyUI client (HTTP `/prompt` + WebSocket progress);
  parameterized workflow templates committed to repo; smoke-test on startup.
- Character Bible generation (LLM) including `identityAnchors[]`.
- Character reference image generation (`character_workflow.json`).
- Keyframe generation per scene (`keyframe_workflow.json`); inject
  `keyframePrompt` + character identity anchors + `negativePrompt` + seed.
- **Consistency lever:** identity-anchor tokens injected verbatim into every
  keyframe prompt; add IP-Adapter referencing the approved character image.
- Approval UI: view / approve / regenerate / edit prompt / replace manually for
  both characters and keyframes.
- Jobs now genuinely async; UI shows queue position + progress + errors.

**Exit criteria:** Every scene has an approved keyframe; characters look
consistent across scenes.

---

### Phase 3 — Local Video Generation

**Goal:** Generate the 5-second clips instead of uploading them.

- **`VideoBackend` interface** with `LTXBackend` first implementation;
  contract = `(keyframe + videoPrompt + negativePrompt) → clip.mp4`.
- Scene clip generation from approved keyframes via ComfyUI (LTX-Video workflow).
- Per-scene: preview / approve / regenerate / upload replacement / mark final.
- Final render now consumes generated clips (Phase 1 render path unchanged).

**Exit criteria** (maps to success metric 3): ≥70% of scenes usable within 1–3
generations; full pipeline runs locally end to end.

---

### Phase 4 — Better Quality

**Goal:** More backends, more control, better consistency.

- Additional `VideoBackend` implementations: `WanBackend` (Wan 2.2),
  `HunyuanBackend` — selectable per project/scene.
- Prompt versioning (history of prompt edits + which version produced an asset).
- Character consistency checks (e.g., face-embedding similarity score) +
  optional per-character LoRA.
- Transition options in render (crossfades) beyond hard cuts.
- Beat-synced cut suggestions from audio analysis.

---

### Phase 5 — Productization

**Goal:** From single-creator tool toward shareable product.

- Project templates and export presets (resolution/format/platform).
- Multi-user support + auth; project export/import.
- Cloud fallback for difficult scenes (optional, opt-in).
- Usage tracking; optional SaaS layer + billing.
- Optional: local full-song generation (ACE-Step) to remove the upload step.

---

## 4. Cross-Cutting Concerns

| Concern | Approach |
|---|---|
| **Slow generation** | Async job queue; SSE/WebSocket progress; never block HTTP; show ETA + queue depth. |
| **GPU / VRAM limits** | Single serialized GPU worker; one model loaded at a time; configurable resolution. |
| **Character consistency** | Layered: identity-anchor tokens (P2) → IP-Adapter (P2) → consistency scoring + LoRA (P4). |
| **ComfyUI node breakage** | Pin ComfyUI + node versions; vendor workflow JSON in repo; startup smoke-test; never auto-update nodes. |
| **Timing drift** | Snap scene boundaries to real beats/sections from audio analysis; don't trust LLM timestamps. |
| **Originality** | System-prompt constraint forbidding real artists/songs/melodies/lyrics; keep generations original. |
| **Reproducibility** | Persist seeds, prompts, and the exact workflow JSON used per asset. |

---

## 5. Definition of Done (MVP)

The MVP is complete when, against [`PRODUCT.md`](./PRODUCT.md) §11, a single user
can locally and with no paid APIs:

1. Generate a complete 40–60 second video.
2. Export it successfully as an MP4.
3. Get ≥70% usable scenes within 1–3 generations.
4. Regenerate bad scenes without restarting the project.

That corresponds to completing **Phases 1–3**. Phases 4–5 are quality and
productization beyond the MVP.
