# Compute & Model-Backend Plan

How the AI workloads get their GPU/compute. Written as **accepted decisions**
(this is a SaaS-hosted, balanced-hybrid posture with a quality hosted LLM), plus
a rollout broken into test-driven stories. Everything slots behind the adapters
that already exist (`LLMClient`, `ImageGenerator`, `VideoBackend` registry +
`cloud` slot, `SongGenerator`) — no core rewrites.

## Context

- **Posture:** Hosted SaaS — we run the GPU; users just log in (auth already shipped).
- **Priority:** Balanced hybrid — managed API for cheap text, our own serverless
  GPU for image/video so we keep pinned ComfyUI workflows + per-character LoRA +
  IP-Adapter consistency (the product's moat).
- **Four distinct workloads**, decided independently: LLM (light), image (medium,
  custom), video (heavy, custom — the cost driver), audio (medium, niche).
- **Key enabler already built:** the async **job worker** (PR0-5). All GPU/remote
  calls run there, never in the request — so cold starts and minute-long runtimes
  are fine.

---

## Decisions

### D1 — Posture: Hosted SaaS, GPU in our infra · `accepted`
We operate the compute. Local Docker + Ollama/ComfyUI stays as the **dev** path,
not the product. Adapters make "local vs hosted" a config switch.

### D2 — LLM: managed quality API (Anthropic primary, OpenAI swappable) · `accepted`
Lyrics/storyboard/characters call a hosted model — no GPU, no cold start, ~cents
per project. **Default: Claude (Sonnet-class for quality, Haiku-class to cut
cost); OpenAI GPT-4o-class as the swappable alternative.** Use the provider's
structured-output / tool-use mode for reliable JSON (replaces our prompt-only
"respond with JSON"). Keep Ollama as a local/dev + emergency-fallback backend.
*(Confirm exact model IDs + pricing via the `claude-api` reference at build time.)*

### D3 — Image (keyframes, char refs): serverless ComfyUI on RunPod · `accepted`
Run **our** ComfyUI (pinned graphs, models on a network volume, LoRAs, IP-Adapter)
on RunPod **Serverless** (scale-to-zero). A managed image API can't run our exact
workflow, so we keep ComfyUI but make it elastic.

### D4 — Video (clips): serverless ComfyUI on RunPod; managed video API as fallback · `accepted`
Same RunPod-serverless-ComfyUI for LTX/Wan/Hunyuan. The existing **`cloud`
VideoBackend slot** holds a managed video API (Fal.ai / Replicate) as
overflow/fallback, selectable per project/scene (already supported).

### D5 — Audio (ACE-Step): RunPod serverless · `accepted`
No clean managed API exists; self-host on the same serverless GPU platform.

### D6 — Execution: async-only in production · `accepted`
`ASYNC_JOBS=true` in prod; every generation endpoint **enqueues** and the worker
calls the backend, polls, and writes the asset. Nothing GPU-bound runs in-request.
(Today only clip generation is async — extend to keyframe, char-ref, and song.)

### D7 — Selection is config-driven · `accepted`
Provider chosen via env behind the adapters; per-project `video_backend` +
per-scene override already exist. Adding a provider = a new adapter + a registry
entry, not a rewrite.

### D8 — Reliability / cold starts · `accepted`
RunPod Serverless with FlashBoot + a **network volume** for model weights;
optionally **1 warm worker** for latency-sensitive image. Worker uses generous
timeouts, bounded retries, idempotent jobs, and a **circuit-breaker → managed
fallback** on repeated failure. `/ready` gates on backend reachability.

### D9 — Cost control · `accepted`
Scale-to-zero ⇒ ~0 idle cost. Per-user quotas already enforced (PR1-5); add
**GPU-second metering** to usage and budget caps. **Video is the line item** —
benchmark RunPod GPU-seconds vs a managed video API before committing volume.

### D10 — Data / privacy · `accepted`
Hosted tier ⇒ prompts/assets transit our infra + chosen providers (Anthropic/
OpenAI for text; our infra for image/video/audio). Document the data-flow + a DPA.
A future "no third-party" enterprise tier routes the LLM to a self-hosted model on
RunPod too — same adapter.

---

## Configuration surface (target)

| Key | Purpose |
|-----|---------|
| `LLM_PROVIDER` | `anthropic` \| `openai` \| `ollama` |
| `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL` | hosted LLM credentials/model |
| `COMFYUI_PROVIDER` | `local` \| `runpod` |
| `RUNPOD_API_KEY`, `RUNPOD_IMAGE_ENDPOINT`, `RUNPOD_VIDEO_ENDPOINT`, `RUNPOD_AUDIO_ENDPOINT` | serverless endpoints |
| `CLOUD_VIDEO_URL`, `CLOUD_VIDEO_API_KEY` | managed video fallback (exists) |
| `ASYNC_JOBS=true` | run generation in the worker (exists) |

---

## Rollout (test-driven stories, in order)

### CB-1 — Hosted LLM client · `todo` — *do first (unblocks today's Ollama pain)*
- `HostedLLMClient` implementing `LLMClient` (Anthropic + OpenAI), structured JSON.
- `get_llm_client()` selects by `LLM_PROVIDER`; Ollama stays for local.
- Tests mock the HTTP; transport errors already map to 502 (just shipped).

### CB-2 — RunPod serverless image/video backend · `todo`
- `RunPodImageGenerator` (`ImageGenerator`) + `RunPodVideoBackend` (`VideoBackend`):
  submit job (our pinned workflow JSON as payload) → poll status → fetch output.
- Register under `comfyui_provider=runpod` / video registry; reuse the committed
  workflow templates. Tests mock RunPod's submit/poll API.

### CB-3 — Async for all GPU work · `todo`
- Add `keyframe`, `character_ref`, and `song` handlers to the worker registry
  (clip already there); those endpoints enqueue when `ASYNC_JOBS=true`.

### CB-4 — Fallback / circuit-breaker · `todo`
- On repeated RunPod failure, fall back to the managed video API (`cloud` slot);
  record the switch; clear user-facing status.

### CB-5 — GPU-second metering + budget caps · `todo`
- Extend usage metering with per-job GPU seconds + cost; enforce budget caps (429).

### CB-6 — Cold-start & readiness tuning · `todo`
- Warm-pool config, network-volume weights, `/ready` checks model endpoints.

---

## Decision summary

| Workload | Backend | Why | Fallback |
|----------|---------|-----|----------|
| LLM | **Anthropic/OpenAI API** | cheap, no cold start, reliable JSON | Ollama |
| Image | **RunPod serverless ComfyUI** | keep pinned graphs + LoRA + consistency | — |
| Video | **RunPod serverless ComfyUI** | same; heavy = the cost driver | managed video API (`cloud`) |
| Audio | **RunPod serverless** | no managed API | — |
| Execution | **async worker** | cold starts/long runs off the request path | — |

**Start with CB-1.**
