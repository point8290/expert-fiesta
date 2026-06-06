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
| `/` | Dashboard — lists projects |
| `/projects/new` | Project creation form |
| `/projects/[id]` | Pipeline: lyrics → audio → storyboard → render |

Per-scene review (regenerate prompt, upload clip, mark final) lives in
`components/SceneCard.tsx`. Each pipeline step reads/writes its backend endpoint.
