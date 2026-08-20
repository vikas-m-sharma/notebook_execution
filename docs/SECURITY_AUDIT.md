# Precision Data Platform — Security & Code Quality Audit

> **Audit Type:** Static Code Analysis & Architectural Review
> **Scope:** Full Repository (All 27 Audit Areas)
> **Date:** 2026-08-20
> **Phases Covered:** Phase 0 – Phase 11 (Complete)
> **Test Status at Time of Audit:** 99/99 tests passing
> **Methodology:** Manual code inspection, pattern search, OWASP Top-10 mapping, CWE classification

---

## Audit Classification

| Severity | Label | Definition |
|----------|-------|-----------|
| 🔴 **Critical** | C | Immediate exploitation risk or data loss possible |
| 🟠 **High** | H | Significant security risk requiring prompt remediation |
| 🟡 **Medium** | M | Material weakness with a plausible attack surface |
| 🔵 **Low** | L | Minor issue or defense-in-depth gap |
| ⚪ **Info** | I | Observation, best-practice deviation, or architectural note |

---

## Executive Summary

The Precision Data Platform is a well-structured, multi-layered backend API built with FastAPI, SQLAlchemy 2.x async, and a spawn-isolated Python execution engine. The codebase demonstrates strong separation of concerns, consistent ORM-parameterized queries, output size limiting, and deliberate credential separation from connector configuration data.

**However, the audit surfaces several findings that must be addressed before the platform is considered production-safe.** The most impactful cluster around three themes:

1. **Complete absence of authentication and authorization** across all API endpoints.
2. **Credentials stored in plaintext JSONB** — the `encrypted_payload` field name is misleading; no encryption is applied.
3. **Unbounded `exec()` of arbitrary user code** in an isolated process, but without OS-level sandboxing, system-call filtering, or file-system restrictions.

These findings are detailed below, ordered by severity.

---

## Findings Index

| ID | Severity | Title | OWASP / CWE | Component |
|----|----------|-------|-------------|-----------|
| SEC-001 | 🔴 Critical | No Authentication or Authorization on Any Endpoint | A01:2021 | All API Routes |
| SEC-002 | 🔴 Critical | Credentials Stored Unencrypted Despite `encrypted_payload` Field Name | A02:2021 / CWE-312 | Credential Store |
| SEC-003 | 🟠 High | No OS-Level Sandboxing for Worker Processes | A05:2021 / CWE-250 | Python Runtime |
| SEC-004 | 🟠 High | No Memory or CPU Limits Enforced at OS Level | CWE-400 | Python Runtime |
| SEC-005 | 🟠 High | Default Hardcoded Database Credentials in Source Code | A02:2021 / CWE-798 | Configuration |
| SEC-006 | 🟠 High | Arbitrary pip Install from Worker Process on Host System | CWE-829 | Dependency Manager |
| SEC-007 | 🟡 Medium | No CORS Policy Configured | A05:2021 | FastAPI App |
| SEC-008 | 🟡 Medium | No Rate Limiting or Request Throttling | A04:2021 / CWE-770 | FastAPI App |
| SEC-009 | 🟡 Medium | Scheduler Logs Exception Stack Traces at ERROR Level | CWE-209 | Job Scheduler |
| SEC-010 | 🟡 Medium | Cron Next-Run Calculation Is Semantically Incorrect | CWE-682 | schedule_utils.py |
| SEC-011 | 🟡 Medium | Global Exception Handler Logs Full URL and Exc Details | CWE-209 | main.py |
| SEC-012 | 🟡 Medium | No .gitignore Preventing .env Commit | A02:2021 / CWE-540 | Repository |
| SEC-013 | 🔵 Low | `source` Field in `NotebookCellCreate` Has No Size Limit | CWE-400 | Notebook Cell Schema |
| SEC-014 | 🔵 Low | Job `parameters` / Connector `configuration` Fields Unbounded | CWE-400 | Schemas |
| SEC-015 | 🔵 Low | Dependency Installation Timeout Passed Through User Input Without Cap | CWE-400 | Dependency Schema |
| SEC-016 | 🔵 Low | `description` and Free-Text Fields Have No Max Length | CWE-20 | Multiple Schemas |
| SEC-017 | 🔵 Low | Daemonic Worker Processes Cannot Spawn Sub-Children | CWE-400 | Python Runtime |
| SEC-018 | 🔵 Low | `ConnectorTestResponse.name` Hard-Coded to "Unknown" on Error | CWE-20 | Connector Route |
| SEC-019 | ⚪ Info | `/docs` / `/redoc` Only Disabled in `production` ENVIRONMENT | I | FastAPI App |
| SEC-020 | ⚪ Info | Duplicate Router Prefix Registration (`/` and `/api/v1`) | I | main.py |
| SEC-021 | ⚪ Info | `lru_cache` on `get_settings()` Cannot Refresh at Runtime | I | config.py |
| SEC-022 | ⚪ Info | No Structured Audit Log for Credential Access / Mutation | I | Credential Manager |
| SEC-023 | ⚪ Info | `calculate_next_run()` Ignores hour/dom/month/dow Cron Fields | I | schedule_utils.py |
| CQ-001 | 🟡 Medium | `OutputManager` Truncation Applies Per-Stream, Not Per-Execution | Code Quality | Output Manager |
| CQ-002 | 🔵 Low | `DependencyManager.output_manager.create_output_events()` Signature Mismatch | Code Quality | Dependency Manager |
| CQ-003 | 🔵 Low | `JobManager` Creates a New `ExecutionManager` Per Request | Code Quality | Job Manager |
| CQ-004 | 🔵 Low | `CredentialManager.sanitize_credential_payload()` Never Called in API Responses | Code Quality | Credential Manager |
| CQ-005 | ⚪ Info | `pytest` Listed in `requirements.txt` Alongside Production Dependencies | Code Quality | requirements.txt |
| CQ-006 | ⚪ Info | SQLAlchemy Engine Created with `echo=settings.DEBUG` | Code Quality | database.py |

---

## Detailed Findings

---

### SEC-001 🔴 Critical — No Authentication or Authorization on Any Endpoint

**File(s):** `app/main.py`, all files in `app/api/v1/routes/`
**OWASP:** A01:2021 – Broken Access Control
**CWE:** CWE-306 – Missing Authentication for Critical Function

**Observation:**
Every API endpoint in the platform (workspaces, projects, notebooks, cells, jobs, connectors, credentials, dependencies, execution outputs) is completely unauthenticated. A grep across the entire `app/` directory finds **zero occurrences** of `current_user`, `Bearer`, `JWT`, `APIKey`, or any OAuth2 dependency injection. The only dependency injected into route handlers is `get_db` (the database session).

Any actor with network access to the FastAPI server can:
- Read, create, update, and delete all workspaces, projects, notebooks, and cells.
- Create and list all connector definitions and their `credential_id` references.
- Trigger arbitrary notebook executions via the Job Manager.
- Install arbitrary Python packages into the worker process's host environment.

**Evidence (`app/api/v1/routes/connectors.py`, line 31):**
```python
async def create_connector(
    data: CreateConnectorRequest,
    db: AsyncSession = Depends(get_db),  # No auth dependency
) -> ConnectorResponse:
```

**Recommendation:**
Implement API key or JWT bearer token authentication via a FastAPI `Security` dependency. Apply a global dependency at the `APIRouter` level so all routes inherit the constraint. Authorization checks (workspace/project ownership scoping) should be layered on top.

---

### SEC-002 🔴 Critical — Credentials Stored Unencrypted Despite `encrypted_payload` Field Name

**File(s):** `app/models/connector.py` (line 92), `app/repositories/connector.py` (line 111), `app/connectors/credentials/manager.py` (line 33)
**OWASP:** A02:2021 – Cryptographic Failures
**CWE:** CWE-312 – Cleartext Storage of Sensitive Information

**Observation:**
The `Credential` database model contains a column named `encrypted_payload`. Inspection of the full data flow — from `CredentialRepository.create()` through to `CredentialManager.resolve_credential()` — reveals that the raw `secret_payload` dict received from the API request is stored directly into this column **without any encryption**. There is **no import or usage** of `cryptography`, `fernet`, `AES`, or any other encryption library anywhere in the codebase.

This means database passwords, access keys, and private keys for all registered connectors are stored as plaintext JSONB in the PostgreSQL `credentials` table. A single database read by any privileged or unauthorized actor exposes all secrets.

**Evidence (`app/repositories/connector.py`, lines 107-111):**
```python
cred = Credential(
    credential_id=credential_id,
    credential_type=credential_type,
    encrypted_payload=payload,   # plaintext dict stored directly
)
```

**Evidence (`app/connectors/credentials/manager.py`, line 33):**
```python
return cred.encrypted_payload   # raw plaintext returned
```

**Recommendation:**
Rename `encrypted_payload` to `payload` or `secret_payload` to eliminate the misleading name. Implement field-level encryption using `cryptography.fernet.Fernet` or a KMS-backed envelope encryption scheme before persisting secrets. The encryption key must not be stored in the same database and must be retrieved from a secure secret store (environment variable, vault, or HSM).

---

### SEC-003 🟠 High — No OS-Level Sandboxing for Worker Processes

**File(s):** `app/runtime/python_runtime.py` (lines 42–50), `app/runtime/python_worker.py` (line 63)
**OWASP:** A05:2021 – Security Misconfiguration
**CWE:** CWE-250 – Execution with Unnecessary Privileges

**Observation:**
The Python worker is spawned as a child process of the FastAPI application using `mp.get_context("spawn")`. The worker executes arbitrary user-submitted notebook code via `exec(compiled, globals_dict)` with no OS-level constraints beyond the Python process boundary. Specifically:

- No `seccomp` profile filtering dangerous system calls (e.g., `fork`, `ptrace`, network socket creation).
- No `cgroup` memory or CPU hard limits applied to the child process.
- No chroot, namespace isolation, or container boundary.
- No AppArmor/SELinux policy.
- The worker inherits the parent process's environment variables (including `DATABASE_URL`) via the OS environment block at spawn time.

A malicious notebook cell can read `/etc/passwd`, make outbound network connections to exfiltrate data, or access the `DATABASE_URL` via `import os; os.environ`.

**Evidence (`app/runtime/python_runtime.py`, lines 45-50):**
```python
self._process = ctx.Process(
    target=run_python_worker,
    args=(self._child_conn,),
    name=f"python_worker_{self.runtime_id}",
    daemon=True,
    # No preexec_fn, no cgroup, no seccomp
)
```

**Recommendation:**
On Linux deployment targets, use `multiprocessing`'s `preexec_fn` to apply a `libseccomp` or `bubblewrap` profile. Consider running worker processes inside a minimal container or using `nsjail`/`gVisor` for kernel-level syscall isolation. At minimum, strip environment variables from the worker process before spawn by clearing `os.environ` inside the worker's initialization before accepting any code.

---

### SEC-004 🟠 High — No Memory or CPU Limits Enforced at OS Level

**File(s):** `app/runtime/config.py` (line 10), `app/runtime/python_runtime.py`
**OWASP:** A05:2021
**CWE:** CWE-400 – Uncontrolled Resource Consumption

**Observation:**
`RuntimeConfig` declares `max_memory_mb: int = Field(2048, ...)`. A search for `max_memory_mb` and `resource.setrlimit`/`RLIMIT` across the entire codebase finds **zero enforcement sites**. The field is defined and accepted but never applied. A notebook cell executing `x = [0] * (10**10)` will consume all available RAM on the host, potentially causing an OOM-kill cascade that terminates the FastAPI server process itself.

**Recommendation:**
In `python_runtime.py`, pass a `preexec_fn` (Linux) that applies the `max_memory_mb` constraint using `resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))` applied inside the child before `run_python_worker` begins.

---

### SEC-005 🟠 High — Default Hardcoded Database Credentials in Source Code

**File(s):** `app/core/config.py` (line 14)
**OWASP:** A02:2021 – Cryptographic Failures
**CWE:** CWE-798 – Use of Hard-coded Credentials

**Observation:**
The `Settings` class defines a default value for `DATABASE_URL` that embeds literal credentials `postgres:postgres`:

```python
DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/precision_notebook"
```

While `pydantic-settings` allows overriding via `.env` or environment variables, this default will be used whenever no override is present — including in CI/CD pipelines, staging environments, or developer machines where an environment file is not provisioned. The same value appears in committed `README.md` and `docs/IMPLEMENTATION_SUMMARY.md`, normalizing default credential reuse.

**Recommendation:**
Remove the default value from `DATABASE_URL` and mark it as required: `DATABASE_URL: str`. If no value is set, Pydantic will raise a `ValidationError` at startup, making misconfiguration explicit rather than silently dangerous.

---

### SEC-006 🟠 High — Arbitrary pip Install from Worker Process on Host Python Environment

**File(s):** `app/runtime/python_worker.py` (lines 100–106)
**OWASP:** A08:2021 – Software and Data Integrity Failures
**CWE:** CWE-829 – Inclusion of Functionality from Untrusted Control Sphere

**Observation:**
The `install_packages` command executes:

```python
cmd_args = [sys.executable, "-m", "pip", "install"] + requirements
proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
```

`sys.executable` inside the spawned child process refers to the **same Python interpreter** that runs the FastAPI server. Therefore, packages are installed into the **host-wide or virtualenv-wide** site-packages shared by the control plane. This means:

1. A user-declared dependency can overwrite or shadow a platform dependency (e.g., `fastapi`, `sqlalchemy`, `pydantic`) with a malicious version.
2. There is no per-session or per-notebook isolation of installed packages.
3. The `DependencyValidator` correctly blocks shell metacharacters in package names but cannot prevent installation of a legitimately named PyPI package that contains malicious code in its wheel entry points.

**Recommendation:**
Each notebook session should install dependencies into an isolated virtual environment created per-session (using `venv` or `uv`) with `sys.executable` pointed at the venv's Python. At minimum, use `pip install --target=<isolated_dir>` and configure `sys.path` inside the worker to prefer the isolated directory.

---

### SEC-007 🟡 Medium — No CORS Policy Configured

**File(s):** `app/main.py`
**OWASP:** A05:2021 – Security Misconfiguration

**Observation:**
A search for `CORSMiddleware`, `allow_origins`, and `add_middleware` across the full codebase yields **zero results**. FastAPI's default behavior when no CORS middleware is registered means that if CORS headers are ever needed (e.g., for an internal dashboard), a wildcard `*` may be added incorrectly under time pressure.

**Recommendation:**
Explicitly configure `CORSMiddleware` with an allowlist of trusted origins. Set `allow_credentials=False` unless session cookies are specifically required.

---

### SEC-008 🟡 Medium — No Rate Limiting or Request Throttling

**File(s):** `app/main.py`, all route files
**OWASP:** A04:2021 – Insecure Design
**CWE:** CWE-770 – Allocation of Resources Without Limits or Throttling

**Observation:**
No rate-limiting middleware is registered. Combined with the complete absence of authentication (SEC-001), any unauthenticated actor can flood the execution endpoint to exhaust database connections and worker processes, trigger thousands of scheduled job creations, or submit megabyte-sized notebook cell `source` fields repeatedly.

**Recommendation:**
Add `slowapi` or an NGINX upstream rate limiter. Particularly sensitive endpoints: `POST /executions`, `POST /jobs/{id}/trigger`, `POST /dependencies/{id}/install`.

---

### SEC-009 🟡 Medium — Scheduler Logs Full Stack Traces at ERROR Level

**File(s):** `app/jobs/scheduler.py` (line 49)
**CWE:** CWE-209 – Generation of Error Message Containing Sensitive Information

**Observation:**
```python
logger.error(f"Error during JobScheduler evaluation: {exc}", exc_info=True)
```

`exc_info=True` causes Python's logging framework to append the full exception traceback to the log record. Scheduler errors may contain database query text, internal table and column names, and file system paths. If logs are forwarded to a third-party aggregator without masking, this constitutes information disclosure.

**Recommendation:**
In production (`settings.ENVIRONMENT == "production"`), log a sanitized error reference (e.g., a correlation ID) and suppress the full traceback from externally visible logs.

---

### SEC-010 🟡 Medium — Cron next_run Calculation Is Semantically Incorrect

**File(s):** `app/jobs/schedule_utils.py` (lines 61–75)
**CWE:** CWE-682 – Incorrect Calculation

**Observation:**
`calculate_next_run()` only interprets the **minute** field of the cron expression and ignores hour, day-of-month, month, and day-of-week entirely. The implementation computes `now + timedelta(minutes=step_minutes)` regardless of the actual cron schedule:

- `0 2 * * *` (daily at 02:00) calculates a next run **1 minute** from now instead of the next occurrence of 02:00.
- `0 0 1 * *` (monthly) will trigger every minute.

Because the scheduler queries for jobs `WHERE next_run_at <= NOW()`, an incorrect next-run time causes jobs set to run daily to fire every scheduler tick (every 5 seconds), flooding the database with repeated execution records.

**Recommendation:**
Replace the custom implementation with `croniter` or `python-crontab`, which correctly handle all 5-field cron semantics including DST boundary transitions.

---

### SEC-011 🟡 Medium — Global Exception Handler Logs Full URL and Exception String

**File(s):** `app/main.py` (line 55)
**CWE:** CWE-209

**Observation:**
```python
logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
```

If a URL path contains user-supplied data or if the exception message includes an internal connection string, these values will appear in log records. This is low-severity in isolation but compounds with insecure log storage.

---

### SEC-012 🟡 Medium — No .gitignore Preventing .env File Commit

**File(s):** Repository root
**OWASP:** A02:2021
**CWE:** CWE-540 – Inclusion of Sensitive Information in Source Code

**Observation:**
The repository contains no `.gitignore` file. `pydantic-settings` is configured to read from `.env` (via `env_file=".env"`). Without a `.gitignore` entry, developers may accidentally commit a `.env` file containing real database passwords, connection strings, or encryption keys.

**Recommendation:**
Add a `.gitignore` with at minimum: `.env`, `.env.*`, `*.pem`, `*.key`, `__pycache__/`, `*.pyc`, `.pytest_cache/`.

---

### SEC-013 🔵 Low — `source` Field in `NotebookCellCreate` Has No Size Limit

**File(s):** `app/schemas/notebook_cell.py` (line 11)
**CWE:** CWE-400 – Uncontrolled Resource Consumption

**Observation:**
```python
source: str = Field("", json_schema_extra={"example": "import pandas as pd"})
```

No `max_length` constraint exists. A client can POST a cell with hundreds of megabytes of code content, which will be persisted to the database `TEXT` column and subsequently sent to the worker process via an IPC pipe for execution.

**Recommendation:**
Add `max_length=1_000_000` (1 MB) or a configurable `MAX_CELL_SOURCE_BYTES` setting to `NotebookCellCreate.source` and `NotebookCellUpdate.source`.

---

### SEC-014 🔵 Low — Job `parameters` and Connector `configuration` Fields Are Unbounded

**File(s):** `app/schemas/job.py` (line 22), `app/schemas/connector.py` (line 14)
**CWE:** CWE-400

**Observation:**
`parameters: Optional[dict[str, Any]]` and `configuration: dict[str, Any]` fields accept arbitrary JSON objects with no depth limit, key count limit, or value size limit. A deeply nested JSON object can cause stack overflows during parsing or excessive memory consumption.

**Recommendation:**
Apply a `max_length` to string values within these dictionaries using a custom Pydantic validator, and limit the total serialized byte size of these fields.

---

### SEC-015 🔵 Low — Dependency Installation Timeout Passes User Input Without Upper Cap

**File(s):** `app/schemas/dependency.py` (line 44)
**CWE:** CWE-400

**Observation:**
```python
timeout_seconds: Optional[float] = Field(120.0, description="Optional installation timeout in seconds.")
```

No upper bound is set. A user can supply `timeout_seconds=86400` (24 hours), causing the worker process to block a worker slot indefinitely.

**Recommendation:**
Add `le=600.0` (10 minutes maximum) or enforce a platform-wide cap in `DependencyManager`.

---

### SEC-016 🔵 Low — `description` and Free-Text Fields Have No `max_length`

**File(s):** `app/schemas/notebook.py`, `app/schemas/job.py`, `app/schemas/workspace.py`, `app/schemas/project.py`
**CWE:** CWE-20 – Improper Input Validation

**Observation:**
`description: Optional[str]` fields across all entity schemas have no `max_length` constraint. While stored in `TEXT` database columns, excessively large values are returned in list responses, multiplying bandwidth consumption.

**Recommendation:**
Apply `max_length=2048` to all `description` fields.

---

### SEC-017 🔵 Low — Daemonic Worker Processes Cannot Spawn Sub-Children

**File(s):** `app/runtime/python_runtime.py` (line 49)
**CWE:** CWE-400 – Unexpected behavioral restriction

**Observation:**
Worker processes are created with `daemon=True`. Python daemon processes cannot themselves spawn child processes. This means notebook code that attempts to use `multiprocessing`, `concurrent.futures.ProcessPoolExecutor`, or `subprocess` in a way that spawns OS-level children will receive a `DaemonError` or silently fail.

**Note:** From a security perspective, `daemon=True` is beneficial as it prevents detached child processes from surviving the parent's termination. The issue is that this constraint is invisible to notebook authors.

**Recommendation:**
Document the limitation clearly. If parallel execution within notebooks is required, consider using `asyncio`-based concurrency or thread pools instead.

---

### SEC-018 🔵 Low — `ConnectorTestResponse.name` Hard-Coded to "Unknown" on Error Path

**File(s):** `app/api/v1/routes/connectors.py` (lines 172–178)
**CWE:** CWE-20

**Observation:**
```python
except ConnectorConnectionError as err:
    await db.commit()
    return ConnectorTestResponse(
        connector_id=str(connector_id),
        name="Unknown",   # actual name available from conn object resolved earlier
        status="ERROR",
        capabilities={},
    )
```

The connector name is available in the `conn` object retrieved earlier in the function. Returning `"Unknown"` can confuse monitoring systems and audit trails.

---

### SEC-019 ⚪ Info — `/docs` and `/redoc` Only Disabled in `production` ENVIRONMENT

**File(s):** `app/main.py` (lines 42–43)

**Observation:**
```python
docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
```

This is a good practice. However, if staging or pre-prod environments use `ENVIRONMENT=development` (the default), OpenAPI documentation remains publicly accessible.

**Recommendation:**
Consider defaulting `ENVIRONMENT` to `"production"` so that documentation is hidden unless explicitly enabled.

---

### SEC-020 ⚪ Info — Duplicate Router Registration at `/` and `/api/v1`

**File(s):** `app/main.py` (lines 47–49)

**Observation:**
```python
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(v1_router, prefix="", tags=["health"])
```

The `v1_router` is registered twice. Every endpoint is reachable at both `/api/v1/workspaces` **and** `/workspaces`. Any future authentication middleware applied only to the `/api/v1` prefix will leave root-prefix routes unprotected.

**Recommendation:**
Extract the health check routes into a dedicated `health_router` and include only that at `/`. Do not double-register the full application router.

---

### SEC-021 ⚪ Info — `lru_cache` on `get_settings()` Cannot Refresh at Runtime

**File(s):** `app/core/config.py` (lines 28–31)

**Observation:**
`@lru_cache` caches the `Settings` instance for the lifetime of the process. If environment variables are rotated (e.g., database password rotation) without a process restart, the application continues using the stale cached credentials.

---

### SEC-022 ⚪ Info — No Structured Audit Log for Credential Access or Mutation

**File(s):** `app/connectors/credentials/manager.py`

**Observation:**
Credential creation, resolution, and deletion occur without any structured audit event being emitted. There is no way to reconstruct "who accessed credential X at time Y" from application logs.

**Recommendation:**
Emit a structured audit log event (at `INFO` level) for every credential create, resolve, and delete operation, including the `credential_id`, timestamp, and (once auth is added) the actor identity.

---

### SEC-023 ⚪ Info — `calculate_next_run()` Ignores Four of Five Cron Fields

**File(s):** `app/jobs/schedule_utils.py` (lines 58–75)

**Observation:**
See SEC-010. The function parses all five cron fields but only acts on the minute field. Variables `hour_spec`, `dom_spec`, `month_spec`, and `dow_spec` are unpacked but never used.

---

## Code Quality Findings

---

### CQ-001 🟡 Medium — `OutputManager` Truncation Applies Per-Stream, Not Per-Execution

**File(s):** `app/output/manager.py` (lines 19–54)

**Observation:**
`DEFAULT_MAX_OUTPUT_SIZE = 100_000` (100 KB) is applied independently to each of stdout, stderr, and traceback. A single cell execution can therefore persist up to **300 KB** of output before any truncation occurs. For a job that executes many cells sequentially, total output may grow unboundedly across cell boundaries.

**Recommendation:**
Implement an execution-level budget that tracks cumulative output size across all events for a single `execution_id` and stops appending once the budget is exhausted.

---

### CQ-002 🔵 Low — `DependencyManager` Calls `create_output_events()` With Wrong Keyword Arguments

**File(s):** `app/dependencies/manager.py` (lines 122–136)

**Observation:**
`DependencyManager.install_notebook_dependencies()` calls:
```python
await self.output_manager.create_output_events(
    execution_id=op_id,
    session_id=session_id or "dep-session",
    notebook_id=notebook_id,
    output_type=OutputType.STDOUT,   # not a parameter of create_output_events()
    content=stdout_content,          # not a parameter of create_output_events()
)
```

The actual signature of `OutputManager.create_output_events()` accepts `stdout: str`, `stderr: str`, and `traceback: Optional[str]` — not `output_type` and `content`. This call pattern will raise a `TypeError` or silently discard data at runtime. Because this code path is only reached during dependency installation, this mismatch may not be caught by existing tests.

**Recommendation:**
Align the call to use `stdout=stdout_content` and `stderr=stderr_content` keyword arguments matching the actual method signature.

---

### CQ-003 🔵 Low — `JobManager` Creates a New `ExecutionManager` Per Request

**File(s):** `app/jobs/manager.py` (line 40)

**Observation:**
```python
self.exec_manager = ExecutionManager()
```

`JobManager` is instantiated fresh per API request. Each instantiation creates a new `ExecutionManager()`, which in turn creates a new `SessionManager()` and `ExecutionRegistry()`. Session state (active runtime processes, in-flight execution tasks) stored in these instances is therefore lost between requests, making job-level session reuse based on `session_id = f"job-{job.id}"` ineffective in practice.

**Recommendation:**
`ExecutionManager`, `SessionManager`, and `ExecutionRegistry` should be singletons at application scope, injected as FastAPI dependencies rather than instantiated inside `JobManager.__init__`.

---

### CQ-004 🔵 Low — `sanitize_credential_payload()` Is Defined But Never Applied in API Responses

**File(s):** `app/connectors/credentials/manager.py` (lines 35–48)

**Observation:**
`sanitize_credential_payload()` is a class method that masks sensitive keys in a credential payload dict. However, `resolve_credential()` returns the raw `encrypted_payload` directly. The sanitization method is defined but not applied in any API response serialization path.

**Recommendation:**
If `sanitize_credential_payload()` is intended for internal audit logging, document its intended use explicitly and add a call in `ConnectorManager.test_connector()` when logging connector test events.

---

### CQ-005 ⚪ Info — `pytest` and Test-Only Dependencies Mixed into `requirements.txt`

**File(s):** `requirements.txt`

**Observation:**
`pytest>=7.0.0`, `pytest-asyncio>=0.21.0`, `httpx`, and `aiosqlite` are all test-only dependencies listed in the same `requirements.txt` as production dependencies. A production Docker image built from `pip install -r requirements.txt` will include test tooling, increasing the attack surface and image size.

**Recommendation:**
Split into `requirements.txt` (production) and `requirements-dev.txt`, or use a `pyproject.toml` with `[dev]` extras.

---

### CQ-006 ⚪ Info — SQLAlchemy Engine Logs All Queries When `DEBUG=True`

**File(s):** `app/core/database.py` (line 30)

**Observation:**
```python
echo=settings.DEBUG
```

When `DEBUG=True`, SQLAlchemy logs every SQL statement including all bound parameter values. If `DEBUG` is inadvertently set to `True` in a staging environment, full SQL logs (including values from `INSERT INTO credentials` statements) will be written to stdout.

**Recommendation:**
Keep `echo=False` in all environments. Use SQLAlchemy's event system with explicit opt-in filtering rather than `echo=True`.

---

## Architectural Security Observations

| # | Observation |
|---|-------------|
| A1 | **Process boundary isolation is the primary defense.** The `spawn` context with daemonic workers correctly prevents notebook crashes from bringing down the FastAPI process. This is a sound architectural decision. |
| A2 | **All SQL queries use ORM parameterization.** No raw string concatenation was found in query construction. The one use of `text("SELECT 1")` in the health check is safe. |
| A3 | **Credential references (`credential_id`) are correctly decoupled** from connector configuration in the data model. The `ConnectorResponse` schema correctly excludes the raw `secret_payload` from API responses. |
| A4 | **Output truncation exists** at the `OutputManager` level (100 KB per stream). This prevents unbounded storage growth from verbose notebook outputs. |
| A5 | **The `DependencyValidator`** correctly applies PEP 508 regex and forbidden character checks before constructing pip arguments, preventing shell injection via package names. `shell=True` is never used in any subprocess call. |
| A6 | **The Job Scheduler runs entirely within the FastAPI async event loop** and does not spawn additional threads, avoiding threading-related race conditions on the scheduler state. |
| A7 | **The global exception handler returns a generic `500` body** to clients, preventing internal error detail leakage via HTTP responses. |
| A8 | **The `lru_cache` on `get_settings()`** ensures `DATABASE_URL` is read only once at startup, reducing repeated environment access but requiring a process restart for credential rotation. |

---

## Risk Heat Map

```
                    LIKELIHOOD
              Low     Medium      High
            +--------+-----------+-----------+
   High     |        | SEC-006   | SEC-001   |
   IMPACT   |        | SEC-003   | SEC-002   |
            |        | SEC-004   |           |
            +--------+-----------+-----------+
   Medium   |SEC-017 | SEC-010   | SEC-005   |
            |CQ-003  | SEC-008   | SEC-012   |
            |        | SEC-007   |           |
            +--------+-----------+-----------+
   Low      |CQ-005  | SEC-013   | SEC-009   |
            |CQ-006  | SEC-014   | SEC-016   |
            |        | SEC-015   |           |
            +--------+-----------+-----------+
```

---

## Remediation Priority

| Priority | Finding IDs | Suggested Action |
|----------|-------------|-----------------|
| **P0 — Block deployment** | SEC-001, SEC-002 | Implement authentication. Implement credential encryption. |
| **P1 — Before public access** | SEC-003, SEC-004, SEC-005, SEC-006 | Apply process sandboxing. Enforce memory limits. Remove default credentials. Isolate pip environments. |
| **P2 — Sprint** | SEC-007, SEC-008, SEC-010, SEC-012, CQ-002 | Add CORS policy. Add rate limiting. Fix cron calculator. Add `.gitignore`. Fix `OutputManager` call signature. |
| **P3 — Backlog** | SEC-013–SEC-018, CQ-001, CQ-003, CQ-004 | Input size limits. Fix session singleton. Document sanitization. Audit logging. |
| **P4 — Low urgency** | SEC-019–SEC-023, CQ-005, CQ-006 | Environment defaults. Router deduplication. Settings cache documentation. Dev dependency split. |

---

## Appendix: Files Inspected

| File | Inspection Coverage |
|------|---------------------|
| `app/main.py` | Full |
| `app/core/config.py` | Full |
| `app/core/database.py` | Full |
| `app/core/logging.py` | Full |
| `app/runtime/python_worker.py` | Full |
| `app/runtime/python_runtime.py` | Full |
| `app/runtime/config.py` | Full |
| `app/execution/manager.py` | Full |
| `app/execution/session/session.py` | Full |
| `app/dependencies/manager.py` | Full |
| `app/dependencies/validator.py` | Full |
| `app/connectors/manager.py` | Full |
| `app/connectors/credentials/manager.py` | Full |
| `app/models/connector.py` | Full |
| `app/repositories/connector.py` | Full |
| `app/jobs/manager.py` | Full |
| `app/jobs/scheduler.py` | Full |
| `app/jobs/schedule_utils.py` | Full |
| `app/output/manager.py` | Full |
| `app/schemas/*.py` | Full (all 10 schema files) |
| `app/api/v1/routes/*.py` | Full (all 9 route files) |
| `requirements.txt` | Full |
| `pytest.ini` | Reviewed |

**Pattern Scans Performed:**

| Pattern | Matches | Assessment |
|---------|---------|------------|
| `exec(` | 1 | Controlled — inside isolated worker only |
| `shell=True` | 0 | PASS |
| `os.system` / `os.popen` | 0 | PASS |
| `pickle` / `marshal` / `yaml.load` | 0 | PASS |
| `text()` raw SQL | 1 | PASS — safe `SELECT 1` health check only |
| `fernet` / `AES` / `encrypt` | 0 | FAIL — SEC-002 |
| `current_user` / `Bearer` / `JWT` / `APIKey` | 0 | FAIL — SEC-001 |
| `CORSMiddleware` | 0 | FAIL — SEC-007 |
| `rate.limit` / `throttle` | 0 | FAIL — SEC-008 |
| `resource.setrlimit` / `RLIMIT` | 0 | FAIL — SEC-003, SEC-004 |
| `seccomp` / `docker` / `container` | 0 | FAIL — SEC-003 |
| `postgres:postgres` hardcoded | 3 | FAIL — SEC-005 |

---

*End of Precision Data Platform Security & Code Quality Audit — v1.0*
