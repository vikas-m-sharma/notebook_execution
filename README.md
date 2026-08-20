# Precision Data Platform — Notebook Execution & Management Backend

Backend engine for notebook management, stateful execution orchestration, runtime isolation, and scheduled analytical workflows within the **Precision Data Platform**.

---

## Purpose
The Notebook Execution & Management Backend provides an enterprise-grade execution platform designed for high-reliability notebook management. Inspired by modern cloud data notebook platforms (such as Databricks and Google Colab), it separates control plane management from isolated execution plane runtimes, enabling stateful cell execution, background job scheduling, and secure data access.

---

## Technology Stack
- **Language**: Python (3.10+)
- **API Framework**: FastAPI
- **Database**: PostgreSQL
- **Database Driver**: `asyncpg` (Async)
- **ORM**: SQLAlchemy 2.x Async (`AsyncSession`)
- **Database Migrations**: Alembic
- **Data Validation & Settings**: Pydantic & Pydantic Settings
- **Testing**: `pytest`, `pytest-asyncio`, `httpx`, `aiosqlite`

---

## Domain & Persistence Hierarchy (Notebook Store)
Notebook persistence is organized in a workspace-oriented hierarchy:
```
Workspace
    ↓
Project
    ↓
Notebook
    │   ├── Metadata (JSONB Configuration)
    │   ├── NotebookCells (Ordered by Position)
    │   ├── ExecutionOutputs (Sequence Ordered Records)
    │   ├── NotebookDependencies (Declared Package Constraints)
    │   ├── DependencyOperations (Lifecycle Installation Records)
    │   └── DataConnectors (Platform-Managed External Resource Definitions)
```

---

## Architecture & Layer Boundaries

```
Precision Data Platform
        │
        ▼
Notebook Management API
        │
 ┌──────┼──────────────┐
 ▼      ▼              ▼
Notebook Execution   Job
Store    Manager     Manager
          │            │
          ▼            │
     Runtime Manager   │
          │            │
     ┌────┴─────┐      │
     ▼          ▼      │
 Python       SQL      │
 Runtime     Runtime   │
     │          │      │
     └────┬─────┘      │
          ▼            │
    Execution Session ◄┘
          │
          ▼
    Output / Logs
          │
          ▼
    Data Connectors
```

---

## Control Plane vs Execution Plane Isolation

```
CONTROL PLANE                                EXECUTION PLANE
FastAPI / Control Process                     Isolated Python Worker
┌────────────────────────┐                    ┌────────────────────────┐
│  Workspace / Project   │                    │  Isolated Python       │
│  Notebook / Cells API  │                    │  Worker Process        │
│  Dependency Manager    │ ─── IPC Pipe ────► │  (executes code &      │
│  Execution Session     │                    │   pip install inside)  │
│  Output Manager        │ ◄── Streams ────── │                        │
│  Connector Manager     │                    │                        │
│  Runtime Manager       │                    │                        │
└────────────────────────┘                    └────────────────────────┘
```
- **Zero Control Plane Execution**: Notebook Python code, `pip install` operations, and data source connection handle executions belong strictly to isolated execution runtimes (no host-level `pip install`, `exec()`, `eval()`, or raw credentials in control plane responses/logs).
- **Dedicated Worker Process**: Each `PythonRuntime` instance spawns a dedicated, isolated Python worker process using `multiprocessing.get_context("spawn")`.

---

## API Endpoints (Control Plane)

The FastAPI Control Plane exposes RESTful JSON endpoints for resource management:

### Workspaces
- `POST /api/v1/workspaces` — Create workspace
- `GET /api/v1/workspaces` — List workspaces
- `GET /api/v1/workspaces/{workspace_id}` — Get workspace details
- `PATCH /api/v1/workspaces/{workspace_id}` — Update workspace
- `DELETE /api/v1/workspaces/{workspace_id}` — Delete workspace (cascades)

### Projects
- `POST /api/v1/workspaces/{workspace_id}/projects` — Create project in workspace
- `GET /api/v1/workspaces/{workspace_id}/projects` — List projects in workspace
- `GET /api/v1/projects/{project_id}` — Get project details
- `PATCH /api/v1/projects/{project_id}` — Update project
- `DELETE /api/v1/projects/{project_id}` — Delete project (cascades)

### Notebooks
- `POST /api/v1/projects/{project_id}/notebooks` — Create notebook (`python`)
- `GET /api/v1/projects/{project_id}/notebooks` — List notebooks in project
- `GET /api/v1/notebooks/{notebook_id}` — Get notebook details (ordered cells & metadata)
- `PATCH /api/v1/notebooks/{notebook_id}` — Update notebook
- `DELETE /api/v1/notebooks/{notebook_id}` — Delete notebook (cascades)

### Notebook Cells
- `POST /api/v1/notebooks/{notebook_id}/cells` — Create cell (`code`, `markdown`)
- `GET /api/v1/notebooks/{notebook_id}/cells` — List cells in notebook (ordered by position)
- `GET /api/v1/notebooks/{notebook_id}/cells/{cell_id}` — Get cell details
- `PATCH /api/v1/notebooks/{notebook_id}/cells/{cell_id}` — Update cell
- `DELETE /api/v1/notebooks/{notebook_id}/cells/{cell_id}` — Delete cell

### Notebook Metadata
- `GET /api/v1/notebooks/{notebook_id}/metadata` — Get notebook configuration metadata
- `PATCH /api/v1/notebooks/{notebook_id}/metadata` — Create/Update notebook configuration metadata

### Execution Outputs
- `GET /api/v1/executions/{execution_id}/outputs` — Retrieve sequence-ordered outputs for an execution
- `GET /api/v1/notebooks/{notebook_id}/cells/{cell_id}/outputs` — Retrieve sequence-ordered outputs for a notebook cell

### Dependencies
- `POST /api/v1/notebooks/{notebook_id}/dependencies` — Declare package dependency
- `GET /api/v1/notebooks/{notebook_id}/dependencies` — List dependencies declared for a notebook
- `PATCH /api/v1/notebooks/{notebook_id}/dependencies/{dependency_id}` — Update dependency version specifier constraint
- `DELETE /api/v1/notebooks/{notebook_id}/dependencies/{dependency_id}` — Delete dependency
- `GET /api/v1/dependency-operations/{operation_id}` — Get status & details of a dependency operation

### Data Connectors
- `POST /api/v1/connectors` — Create platform data connector definition with optional credentials
- `GET /api/v1/connectors` — List platform data connectors (sanitized, zero secrets)
- `GET /api/v1/connectors/{connector_id}` — Get connector details
- `PATCH /api/v1/connectors/{connector_id}` — Update connector configuration or credentials
- `DELETE /api/v1/connectors/{connector_id}` — Delete connector definition and credential reference
- `POST /api/v1/connectors/{connector_id}/test` — Test connection to external data target (`AVAILABLE` / `UNAVAILABLE`)

### Jobs
- `POST /api/v1/jobs` — Create scheduled or manual job definition
- `GET /api/v1/jobs` — List jobs (filtered by workspace, project, or notebook)
- `GET /api/v1/jobs/{job_id}` — Get job definition details
- `PATCH /api/v1/jobs/{job_id}` — Update job configuration or schedule
- `DELETE /api/v1/jobs/{job_id}` — Delete job definition
- `POST /api/v1/jobs/{job_id}/run` — Trigger manual notebook job execution
- `POST /api/v1/jobs/{job_id}/pause` — Pause job schedule evaluation
- `POST /api/v1/jobs/{job_id}/resume` — Resume job schedule evaluation
- `POST /api/v1/jobs/{job_id}/cancel/{execution_id}` — Cancel active job execution
- `GET /api/v1/jobs/{job_id}/executions` — List execution history for a job

---

## Data Connector Integration (`app/connectors/`)

- **Generic Connector Framework**: Extensible `BaseConnector` abstraction with `ConnectorCapabilities` (`can_read`, `can_write`, `supports_transactions`, `supports_query`, `supports_object_storage`).
- **V1 Implementations**:
  1. PostgreSQL (`postgresql`)
  2. MySQL (`mysql`)
  3. Microsoft SQL Server (`mssql`)
  4. MongoDB (`mongodb`)
  5. AWS S3 (`s3`)
- **Credential Protection**: Raw passwords, access keys, or tokens are securely stored under `credential_id` references via `CredentialManager` and NEVER exposed in API models or log outputs.
- **Phase 8 & 9 Integration**: Sanitized test connection events logged to `OutputManager`. Driver packages resolved via `DependencyManager`.

---

## Job Manager & Background Scheduler (`app/jobs/`)

- **Job Manager Framework**: Orchestrates job CRUD, notebook hierarchy validation, schedule evaluation, and notebook execution delegation through `ExecutionManager`.
- **Databricks-Inspired Cron & Timezones**: Supports `ONE_TIME` and `CRON` schedule types, 5-part cron syntax validation, and timezone-aware schedule calculation (`zoneinfo.ZoneInfo`).
- **Concurrency & Overlap Control**: `ConcurrencyPolicy.PREVENT_OVERLAP` prevents duplicate concurrent runs for the same job definition.
- **Background Scheduler Task Loop**: `JobScheduler` background task loop evaluates due active jobs periodically and updates `next_run_at` and `last_run_at` timestamps.
- **Execution History Tracking**: `JobExecution` ORM model records detailed run status (`QUEUED`, `RUNNING`, `SUCCESS`, `FAILED`, `CANCELLED`, `TIMED_OUT`), duration, and error messages.

---

## Getting Started & Development Commands

### 1. Environment Setup
Copy the example environment file:
```bash
cp .env.example .env
```

Configure your PostgreSQL database connection in `.env`:
```env
DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/precision_notebook"
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run Database Migrations
```bash
alembic upgrade head
```

### 4. Start the Application Server
```bash
uvicorn app.main:app --reload --port 8000
```
Open interactive API documentation in browser:
- Swagger UI: `http://localhost:8000/docs`
- OpenAPI Spec: `http://localhost:8000/openapi.json`

### 5. Run Test Suite
```bash
pytest -v
```

---

## Production Probes & Health Checks

- **Liveness Probe**: `GET /api/v1/health/live`
  ```json
  {
      "status": "alive"
  }
  ```
- **Readiness Probe**: `GET /api/v1/health/ready`
  ```json
  {
      "status": "ready",
      "database": "connected"
  }
  ```
- **API Control Plane Health**: `GET /health` or `GET /api/v1/health`
- **Database Connection Health**: `GET /health/db` or `GET /api/v1/health/db`

---

## Development Roadmap & Phases

- [x] **Phase 0**: Architecture & Development Contract
- [x] **Phase 1**: FastAPI + PostgreSQL Foundation
- [x] **Phase 2**: Notebook Store
- [x] **Phase 3**: Notebook Management API
- [x] **Phase 4**: Runtime Manager
- [x] **Phase 5**: Python Runtime
- [x] **Phase 6**: Execution Session
- [x] **Phase 7**: Execution Manager
- [x] **Phase 8**: Output / Logs
- [x] **Phase 9**: Dependency Management
- [x] **Phase 10**: Data Connector Integration
- [x] **Phase 11**: Job Manager + Production Hardening

---

## Current Project Status

**ALL PHASES (0 THROUGH 11) — COMPLETED** (Full 10-layer architecture implemented and verified, Job Manager, Cron & Timezone Background Scheduler, `PREVENT_OVERLAP` Concurrency Control, Job Execution History, `/health/live` Liveness Probe, `/health/ready` Readiness Probe, Lifespan Scheduler Lifecycle, and 99/99 unit & integration tests passing cleanly)
