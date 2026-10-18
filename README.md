# Call Analyzer

Full-stack platform for turning recorded customer calls into searchable transcripts, structured evaluations, and team performance insights.

## Why It Exists

Reviewing calls manually is slow and inconsistent. Call Analyzer provides a repeatable workflow for uploading or synchronizing recordings, transcribing audio, evaluating conversations against configurable criteria, and presenting the results to managers and employees.

## Highlights

- Audio upload validation, preprocessing, cleanup, and transcription.
- AI-assisted call analysis using configurable company templates and criteria.
- Company-scoped authentication, roles, invitations, and manager assignments.
- Performance dashboards, daily reports, favorites, and report summaries.
- Mentor conversations and company-specific AI configuration.
- Optional Beeline synchronization for external call records.
- Defensive logging controls for sensitive payloads and transcripts.
- Backend tests covering permissions, integrations, processing, and failure cases.

## Code Guide

- [API and service lifecycle](backend/src/app/main.py): request handling and background worker startup and shutdown.
- [Transcription jobs](backend/src/app/services/transcription_jobs.py): queued processing, heartbeats, and stale-job recovery.
- [Upload validation tests](backend/tests/test_upload_validation.py): audio input validation.
- [Permission tests](backend/tests/test_admin_permissions.py): role and access checks.
- [Job logging tests](backend/tests/test_transcription_job_logging.py): processing and failure observability.
- [Frontend](frontend/src/): application pages, API clients, and interface components.

## Architecture

```text
Browser
  -> React + TypeScript frontend
  -> FastAPI application
      -> authentication and company-scoped APIs
      -> upload and transcription pipeline
      -> analysis and reporting services
      -> PostgreSQL through SQLAlchemy
      -> OpenAI, Whisper, and optional Beeline integration
```

### Backend

- Python, FastAPI, Pydantic
- SQLAlchemy 2 and Alembic
- PostgreSQL
- OpenAI and Whisper integrations
- pytest and pytest-asyncio

### Frontend

- React 19 and TypeScript
- Vite
- TanStack Query and TanStack Router
- React Hook Form and Zod
- Recharts and Tailwind CSS

## Local Development

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python run.py
```

Review and fill `backend/.env.example` before starting. Provision PostgreSQL separately. Audio conversion requires `ffmpeg`; local Whisper transcription also needs its model and runtime dependencies. Configure the selected transcription provider and OpenAI analysis integration before using those features. Beeline synchronization requires its own integration configuration.

### Frontend

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

The Vite development server runs on port `5173` by default.

## Verification

Run backend tests:

```bash
cd backend
pytest -q
```

Validate the frontend production build:

```bash
cd frontend
npm ci
npm run build
```

## Repository Layout

```text
backend/
  migrations/       database migrations
  src/app/          API modules and services
  src/analyzer/     model-driven analysis
  src/transcriber/  transcription pipeline
  tests/            backend test suite
frontend/
  src/api/          API clients
  src/pages/        product surfaces
  src/components/   reusable UI
```

## Security and Privacy

- Never commit `.env` files, recordings, transcripts, customer exports, or application logs.
- Use the logging flags in `backend/.env.example` conservatively in production.
- Rotate any credential that has previously appeared in Git history.
- Use synthetic or consented audio when demonstrating the project publicly.
