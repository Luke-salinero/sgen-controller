# sgen-controller

Control plane for SGen job scheduling and lifecycle. Postgres is the
authoritative job store and doubles as the work queue between this service
and `sgen-worker`. Not exposed to the internet directly — `sgen-gateway` is
the only intended caller.

## What this service does

- Creates jobs (`created` status) on behalf of `sgen-gateway`
- Owns the job lifecycle: `created → pending → running → completed|failed|cancelled`
- In **mock mode** (`SGEN_MODE=mock`, the default), runs an in-process
  `AsyncJobRunner` that promotes `created → pending` jobs and executes them
  with a stub result — no `sgen-worker` needed.
- In **live mode**, does not execute anything itself; `sgen-worker`
  instances claim `pending` jobs directly from Postgres
  (`SELECT ... FOR UPDATE SKIP LOCKED`) and run the real compute engine.

## Repository structure

- `app/api/v1/jobs.py` — `POST /api/v1/jobs`, `GET /api/v1/jobs/{job_id}`
- `app/services/postgres_job_store.py` — all job reads/writes (parameterized
  SQL via SQLAlchemy `text()`); creates the `jobs` table if missing
- `app/services/async_runner.py` — mock-mode execution loop
- `app/models/` — `Job`/`JobStatus` (job_id is a server-generated UUID4)
  and request/response schemas
- `app/db/session.py` — SQLAlchemy engine/session from `DATABASE_URL`

## API endpoints

| Method | Path | Description |
| ------ | ---- | ----------- |
| `GET`  | `/health` | Liveness check. |
| `POST` | `/api/v1/jobs` | Creates a job from a config + `api_key_owner`; returns `job_id`/`status`/`mode`. |
| `GET`  | `/api/v1/jobs/{job_id}` | Returns a job's full status/result/error by id. |

This service has no authentication or per-owner authorization of its own —
it trusts its caller (`sgen-gateway`) to have already authenticated the
request and to only ask for jobs it's entitled to see. It should not be
reachable from outside the private network `sgen-gateway` runs in.

## Configuration

| Variable | Required | Purpose |
| -------- | -------- | ------- |
| `DATABASE_URL` | yes | Postgres connection string; startup fails immediately if unset. |
| `SGEN_MODE` | no (default `mock`) | `mock` runs `AsyncJobRunner` in-process; `live` leaves execution to `sgen-worker`. |
| `CONTROLLER_WORKER_ID` | no | Identifier used by the mock-mode runner when claiming jobs. |

## Running locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost:5432/sgen
uvicorn app.main:app --reload
```

Available at `http://127.0.0.1:8000`, docs at `/docs`.
