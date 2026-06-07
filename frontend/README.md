# Local Music Video Studio — Frontend

Next.js (App Router) review UI for the pipeline. Talks to the FastAPI backend
via the typed client in `lib/api.ts`.

## Setup

```bash
npm install
```

Set the backend URL if it isn't the default `http://localhost:8000`:

```bash
export NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Run

```bash
npm run dev      # http://localhost:3000
```

## Checks

```bash
npm run typecheck   # tsc --noEmit
npm run test        # vitest
```

## Screens (P1-S9)

| Route | Screen |
|-------|--------|
| `/login` | Log in / create account (stores the JWT, attaches it to every request) |
| `/` | Dashboard — lists the signed-in user's projects |
| `/projects/new` | Project creation form |
| `/projects/[id]` | Pipeline: lyrics → audio → characters → storyboard → jobs → quality → render |

Auth (P5-S2): the token lives in `localStorage` (`lib/auth.ts`); `lib/api.ts`
adds it as a `Bearer` header; `RequireAuth` redirects signed-out visitors to
`/login`; `AuthControls` in the header handles login/logout.

The pipeline screen now exposes the full Phase 1–3 backend:

- **Lyrics / Audio** — generate lyrics, upload + analyze audio (Phase 1).
- **Characters** (`components/CharacterCard.tsx`) — generate the bible, then per
  character: generate / approve / upload a reference image (Phase 2).
- **Storyboard** (`components/SceneCard.tsx`) — per scene: regenerate prompt,
  generate / approve / upload **keyframe** (Phase 2), generate (job) / approve /
  upload **clip**, mark final (Phase 3).
- **Jobs** — live status / progress / queue position / errors for generation
  jobs (Phase 2 job queue).
- **Settings** — pick the video model (LTX / Wan 2.2 / HunyuanVideo) and the
  transition (hard cut / crossfade) per project (Phase 4).
- **Quality** — face-embedding character-consistency scores per keyframe and
  beat-synced cut suggestions; plus an optional per-character LoRA path on each
  `CharacterCard` (Phase 4).
- **Render** — stitch approved clips into the final MP4, with an optional
  **export preset** (YouTube / TikTok / Instagram) overriding the resolution
  (Phase 5).

Project creation supports **starting from a template** (Phase 5), and the Audio
step has a **Generate song** button that synthesizes audio locally from the
lyrics' music prompt (Phase 5).

Each control reads/writes its backend endpoint via the typed client in
`lib/api.ts`.
