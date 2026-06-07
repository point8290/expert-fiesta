# User Stories: Local Music Video Studio

Each phase from [`BUILD_PLAN.md`](./BUILD_PLAN.md) broken into independently
testable stories. Format: **ID — Title**, a user-value statement, and acceptance
criteria (AC) written so they can be turned directly into tests (TDD).

Status legend: `todo` · `in-progress` · `done`

---

## Phase 1 — Pipeline Skeleton (no GPU)

### P1-S1 — Create and manage projects · `done`
*As a creator, I want to create, view, update, and delete music-video projects
so that each video has its own workspace.*

- AC1: `POST /projects` with a valid body creates a project and returns it with a
  generated `id`, `status="draft"`, and `createdAt`/`updatedAt` timestamps.
- AC2: `POST /projects` with missing/invalid required fields returns `422`.
- AC3: `GET /projects` returns all projects (newest first).
- AC4: `GET /projects/{id}` returns the project; unknown id returns `404`.
- AC5: `PATCH /projects/{id}` updates editable fields and bumps `updatedAt`.
- AC6: `DELETE /projects/{id}` removes the project; subsequent `GET` returns `404`.
- AC7: Required fields: `title`, `idea`, `genre`, `mood`, `visualStyle`,
  `targetDuration`, `aspectRatio`.

### P1-S2 — Generate lyrics and music prompt · `done`
*As a creator, I want the system to generate a title, lyrics, structure, music
prompt, and emotional arc from my idea.*

- AC1: `POST /projects/{id}/lyrics` returns `title`, `structure[]`, `body`,
  `musicPrompt`, `emotionalArc`.
- AC2: The LLM call goes through an adapter that can be mocked in tests.
- AC3: Malformed LLM JSON triggers a bounded retry; persistent failure → `502`.
- AC4: A system prompt forbids referencing real artists/songs/lyrics/melodies.
- AC5: Generated lyrics are persisted and re-fetchable via `GET`.

### P1-S3 — Upload project audio · `done`
*As a creator, I want to upload an MP3/WAV so the video can be timed to my song.*

- AC1: `POST /projects/{id}/audio` accepts MP3/WAV multipart upload, stores it
  under the project folder, and records `source="upload"`.
- AC2: Non-audio mime types are rejected with `415`.
- AC3: `GET /projects/{id}/audio` returns stored audio metadata.

### P1-S4 — Analyze audio · `done`
*As a creator, I want the system to extract duration, BPM, beats, sections, and
waveform so scenes can be timed.*

- AC1: Analysis returns `durationSeconds`, `bpm`, `beats[]`, `sections[]`,
  `waveform[]`.
- AC2: Analysis runs behind an adapter (librosa/ffprobe) that is mockable.
- AC3: Results persist on the `Audio` record.

### P1-S5 — Generate storyboard · `done`
*As a creator, I want an 8–12 scene storyboard timed to my audio.*

- AC1: `POST /projects/{id}/storyboard` creates `Scene` rows with all spec
  fields (number, start/end/duration, sectionName, descriptions, prompts).
- AC2: Scene boundaries snap to real section/beat boundaries from audio analysis.
- AC3: Scene count is within 8–12 and total duration ≈ target duration.

### P1-S6 — Manage scenes · `done`
*As a creator, I want to view and edit individual scenes.*

- AC1: `GET /projects/{id}/scenes` lists scenes in order.
- AC2: `PATCH /scenes/{id}` edits prompt fields.
- AC3: `POST /scenes/{id}/regenerate-prompt` re-generates prompts for one scene.

### P1-S7 — Upload clip per scene · `done`
*As a creator, I want to upload a video clip for a scene and mark it final.*

- AC1: `POST /scenes/{id}/clip` stores an uploaded clip and sets
  `clipStatus="approved"`.
- AC2: Non-video uploads are rejected with `415`.
- AC3: `POST /scenes/{id}/finalize` marks the scene final.

### P1-S8 — Render final MP4 · `done`
*As a creator, I want all approved clips stitched with my audio into one MP4.*

- AC1: `POST /projects/{id}/render` enqueues a render job over approved clips.
- AC2: Render normalizes resolution/fps/SAR, concatenates (hard cuts), muxes
  audio, trims to audio length, writes `renders/final.mp4`.
- AC3: Render runs behind a mockable FFmpeg adapter (no ffmpeg needed in tests).
- AC4: Rendering with missing/unapproved clips returns a clear error.

### P1-S9 — Frontend review screens · `done`
*As a creator, I want screens for dashboard, project, lyrics, audio, storyboard,
clips, and final render.*

- AC1: Dashboard lists projects with title/status/duration/thumbnail.
- AC2: Each pipeline screen reads/writes its corresponding API.
- AC3: Long-running actions show progress via polling/SSE.

---

## Phase 2 — Local Image Generation

### P2-S1 — ComfyUI media adapter · `done`
*As the system, I want a client that runs parameterized ComfyUI workflows.*

- AC1: Adapter clones a workflow template, injects prompt/seed/resolution, POSTs
  to `/prompt`, and tracks completion via WebSocket.
- AC2: Workflow templates are committed to the repo and version-pinned.
- AC3: A startup smoke-test validates each workflow loads.

### P2-S2 — Generate character bible · `done`
*As a creator, I want characters with identity anchors for consistency.*

- AC1: Characters include name, age, face, hair, clothing, personality,
  `identityAnchors[]`.
- AC2: Characters persist and are editable.

### P2-S3 — Generate character reference images · `done`
- AC1: One reference image per character via ComfyUI.
- AC2: View / approve / regenerate / replace manually.

### P2-S4 — Generate scene keyframes · `done`
- AC1: One keyframe per scene; prompt = keyframePrompt + identity anchors +
  negative prompt + seed.
- AC2: View / approve / regenerate / edit prompt / replace manually.

### P2-S5 — Character consistency · `done`
- AC1: Identity-anchor tokens injected verbatim into every keyframe prompt.
- AC2: IP-Adapter references the approved character image.

### P2-S6 — Async jobs + progress · `done`
- AC1: Generation runs in the job queue; UI shows queue position/progress/errors.

---

## Phase 3 — Local Video Generation

### P3-S1 — VideoBackend interface + LTX-Video · `done`
- AC1: `VideoBackend` contract: `(keyframe, videoPrompt, negativePrompt) → clip.mp4`.
- AC2: `LTXBackend` implements it via a ComfyUI workflow.

### P3-S2 — Generate scene clips · `done`
- AC1: Each approved keyframe produces a ~5s clip.
- AC2: Clips persist with `clipStatus`.

### P3-S3 — Review clips · `done`
- AC1: Preview / approve / regenerate / upload replacement / mark final per scene.

### P3-S4 — Render with generated clips · `done`
- AC1: Final render consumes generated clips through the unchanged Phase 1 path.
- AC2: ≥70% of scenes usable within 1–3 generations (tracked metric).

---

## Phase 4 — Better Quality

### P4-S1 — Wan 2.2 backend · `done`
- AC1: `WanBackend` implements `VideoBackend`; selectable per project/scene.

### P4-S2 — HunyuanVideo backend · `done`
- AC1: `HunyuanBackend` implements `VideoBackend`; selectable per project/scene.

### P4-S3 — Prompt versioning · `done`
- AC1: Prompt edits are versioned; each asset records the prompt version used.

### P4-S4 — Consistency scoring + LoRA · `done`
- AC1: Face-embedding similarity score per character across scenes.
- AC2: Optional per-character LoRA path.

### P4-S5 — Transitions · `done`
- AC1: Render supports crossfades in addition to hard cuts.

### P4-S6 — Beat-synced cuts · `done`
- AC1: Suggest cut points aligned to detected beats.

---

## Phase 5 — Productization

### P5-S1 — Templates + export presets · `todo`
- AC1: Project templates; export presets per resolution/format/platform.

### P5-S2 — Multi-user + auth · `todo`
- AC1: Users authenticate; projects are scoped per user.

### P5-S3 — Project export/import · `todo`
- AC1: A project (metadata + assets) can be exported and re-imported.

### P5-S4 — Cloud fallback · `todo`
- AC1: Opt-in cloud generation for difficult scenes behind the same backend interface.

### P5-S5 — Usage tracking + SaaS · `todo`
- AC1: Usage metering; optional billing layer.

### P5-S6 — Local song generation · `todo`
- AC1: ACE-Step (or similar) generates audio locally, removing the upload step
  (`source="generated"`).
