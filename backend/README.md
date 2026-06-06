# Local Music Video Studio — Backend

FastAPI backend for the local-first AI music video pipeline. See
[`../docs/BUILD_PLAN.md`](../docs/BUILD_PLAN.md) for architecture and
[`../docs/STORIES.md`](../docs/STORIES.md) for the story breakdown driving TDD.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs at <http://localhost:8000/docs>.

## Test (TDD)

```bash
pytest
```

We follow red → green → refactor. Each story in `docs/STORIES.md` becomes a test
module under `tests/` before its implementation lands under `app/`.

## Status

| Story | Description | Status |
|-------|-------------|--------|
| P1-S1 | Create and manage projects | ✅ done |
| P1-S2 | Generate lyrics and music prompt | ✅ done |
| P1-S3 | Upload project audio | ✅ done |
| P1-S4 | Analyze audio | ✅ done |
| P1-S5 | Generate storyboard | ✅ done |
| P1-S6 | Manage scenes | ✅ done |
| P1-S7 | Upload clip per scene | ✅ done |
| P1-S8 | Render final MP4 | ✅ done |

> Frontend (P1-S9) lives in `../frontend` (Next.js). **Phase 1 is complete.**

## Phase 2

| Story | Description | Status |
|-------|-------------|--------|
| P2-S1 | ComfyUI media adapter | ✅ done |
| P2-S2 | Character bible | ⬜ next |
