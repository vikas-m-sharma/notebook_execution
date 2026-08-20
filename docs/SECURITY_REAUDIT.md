# Precision Data Platform — Independent Security Re-Audit Report

> **Audit Type:** Independent Static Code Analysis, Attack Surface Assessment & Architectural Review  
> **Scope:** Full Repository (All Layers, API Routes, Runtimes, Connectors, Jobs, Dependencies, Storage)  
> **Date:** 2026-08-20  
> **Platform Version:** 0.1.0  
> **Test Status at Audit:** 97/99 passing (2 failing test cases identified and documented below)  
> **Methodology:** Manual source inspection, threat modeling, attack path synthesis, OWASP Top-10 (2021) & CWE mapping, architectural boundary verification  

---

## 1. Executive Summary

An exhaustive, independent security audit of the **Precision Data Platform Notebook Execution & Management Backend** was conducted. The assessment treated the repository as a new, untrusted application without relying on historical assertions or previous audit conclusions.

The codebase exhibits notable architectural discipline:
- **Clean Layered Architecture:** Strict separation between API Control Plane, Repository/Store, Execution Orchestration, Isolated Python Runtime, Output Management, and Data Connectors.
- **Robust SQL Injection Defenses:** All database interactions across all models and repositories use SQLAlchemy 2.0 async ORM parameterized statements with zero raw SQL concatenation.
- **Defensive Command Input Validation:** `DependencyValidator` enforces strict alphanumeric/whitelisted character sets preventing shell command injection via package names.
- **Process Boundary for Execution:** Notebook code is strictly prohibited from running within the FastAPI main process, utilizing `multiprocessing.Process(context="spawn")` child workers.

**However, critical security vulnerabilities and architectural gaps remain that make the platform unsafe for multi-tenant, untrusted, or public production deployment.** The primary risks are:
1. **Unrestricted API Access & Total Absence of Authorization (BOLA/IDOR):** Authentication is disabled by default (`REQUIRE_AUTH=False`), and even when enabled, no user identity, ownership, or multi-tenant authorization exists. Any caller can mutate or delete any workspace, notebook, job, or connector.
2. **Host-Level Process Execution without OS Sandboxing:** Notebook code executes via `exec()` in a child process that shares host OS privileges, allowing arbitrary filesystem access, host environment variable extraction (including `DATABASE_URL`), and unconstrained network egress.
3. **Plaintext Credential Storage Fallback:** Connector credentials fall back to unencrypted storage when `CREDENTIAL_ENCRYPTION_KEY` is not set.
4. **Semantically Flawed Cron Engine:** The scheduler's cron calculator ignores hour, day-of-month, month, and day-of-week fields, resulting in frequent misfiring of scheduled jobs.

---

## 2. Findings Summary Table

| Finding ID | Severity | Title | OWASP (2021) | CWE | Affected Component |
|---|---|---|---|---|---|
| **SEC-001** | 🔴 **CRITICAL** | API Authentication Disabled by Default; No User Identity or RBAC | A01: Broken Access Control | CWE-306 | `app/core/security.py`, `app/core/config.py` |
| **SEC-002** | 🔴 **CRITICAL** | Zero Authorization / Missing Multi-Tenant Access Control (BOLA/IDOR) | A01: Broken Access Control | CWE-639 / CWE-284 | All API Routes (`app/api/v1/routes/`) |
| **SEC-003** | 🟠 **HIGH** | Child Worker Inherits Host Environment Variables (Database Credential Leak) | A02: Cryptographic Failures / A05 | CWE-200 / CWE-526 | `app/runtime/python_worker.py`, `python_runtime.py` |
| **SEC-004** | 🟠 **HIGH** | Arbitrary Code Execution in Host OS Context Without Sandboxing / Isolation | A05: Security Misconfiguration | CWE-250 / CWE-693 | `app/runtime/python_worker.py` |
| **SEC-005** | 🟠 **HIGH** | Host Python Environment Pollution via Global `pip install` | A06: Vulnerable & Outdated Components | CWE-829 / CWE-427 | `app/runtime/python_worker.py` |
| **SEC-006** | 🟠 **HIGH** | Fallback to Plaintext Credential Storage at Rest | A02: Cryptographic Failures | CWE-312 / CWE-311 | `app/core/encryption.py`, `app/repositories/connector.py` |
| **SEC-007** | 🟡 **MEDIUM** | Unrestricted Connector Egress / Internal Network Probing (SSRF) | A10: Server-Side Request Forgery | CWE-918 | `app/connectors/relational/`, `mongodb.py`, `s3.py` |
| **SEC-008** | 🟡 **MEDIUM** | Incomplete Cron Expression Evaluation Misfires Scheduled Jobs | A04: Insecure Design | CWE-682 | `app/jobs/schedule_utils.py` |
| **SEC-009** | 🟡 **MEDIUM** | Lack of OS-Level Resource Quotas (Memory/CPU DoS) | A04: Insecure Design | CWE-400 / CWE-770 | `app/runtime/python_worker.py`, `python_runtime.py` |
| **SEC-010** | 🟡 **MEDIUM** | Hardcoded Development Database Credentials in Default Configuration | A05: Security Misconfiguration | CWE-798 | `app/core/config.py` |
| **SEC-011** | 🔵 **LOW** | Unbounded Request Payload and Cell Source Fields | A04: Insecure Design | CWE-400 / CWE-20 | `app/schemas/notebook_cell.py`, `job.py`, `connector.py` |
| **SEC-012** | 🔵 **LOW** | Per-Stream Output Truncation Allows Multi-Stream Output Flooding | A04: Insecure Design | CWE-400 | `app/output/manager.py` |
| **SEC-013** | 🔵 **LOW** | Hardcoded "Unknown" Connector Name on Test Failure | A04: Insecure Design | CWE-20 | `app/api/v1/routes/connectors.py` |
| **SEC-014** | ⚪ **INFO** | Single Shared Global Scheduler & Execution Manager Instance Lifecycle | Architecture Note | CWE-662 | `app/main.py`, `app/jobs/manager.py` |

---

## 3. Detailed Findings

---

### SEC-001 🔴 CRITICAL — API Authentication Disabled by Default; No User Identity or RBAC

- **Severity:** CRITICAL
- **OWASP Category:** A01:2021 — Broken Access Control
- **CWE:** CWE-306 (Missing Authentication for Critical Function), CWE-287 (Improper Authentication)
- **File:** [`app/core/security.py`](file:///d:/precision-notebook/app/core/security.py#L31-L48), [`app/core/config.py`](file:///d:/precision-notebook/app/core/config.py#L24-L25)
- **Root Cause:** In `Settings`, `REQUIRE_AUTH: bool = False` is set by default. The `verify_api_key` dependency explicitly exits early when `REQUIRE_AUTH` is `False`. Even when enabled, authentication relies on a single static `API_KEY` string compared via equality, lacking user context, session tokens, JWTs, or role assignments.
- **Attack Scenario:** An attacker on the local network or public internet sends unauthenticated HTTP requests to `/api/v1/workspaces`, `/api/v1/jobs/{job_id}/run`, or `/api/v1/connectors`. The control plane processes every request without validating caller identity.
- **Impact:** Complete system takeover; unauthorized access to all notebooks, credentials, job triggers, and execution outputs.
- **Evidence:**
  ```python
  # app/core/security.py
  async def verify_api_key(api_key: str | None = Security(_api_key_header)) -> None:
      settings = get_settings()
      if not settings.REQUIRE_AUTH:
          return  # Unauthenticated pass-through
  ```
- **Recommended Remediation:**
  1. Enforce `REQUIRE_AUTH = True` in production configurations.
  2. Implement structured authentication tokens (e.g., Bearer JWT or scoped API tokens) carrying user and tenant identity.

---

### SEC-002 🔴 CRITICAL — Zero Authorization / Missing Multi-Tenant Access Control (BOLA/IDOR)

- **Severity:** CRITICAL
- **OWASP Category:** A01:2021 — Broken Access Control
- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key), CWE-284 (Improper Access Control)
- **File:** All route handlers in [`app/api/v1/routes/`](file:///d:/precision-notebook/app/api/v1/routes/) and models in [`app/models/`](file:///d:/precision-notebook/app/models/)
- **Root Cause:** The database schema has no `user_id`, `owner_id`, or `tenant_id` foreign keys on `workspaces`, `projects`, `notebooks`, `connectors`, or `jobs`. API routes fetch records solely by resource UUID (`workspace_id`, `notebook_id`, `connector_id`) without validating whether the caller is authorized to view or mutate that resource.
- **Attack Scenario:** User A creates a proprietary notebook containing sensitive business logic. User B guesses or enumerates the UUID and issues `DELETE /api/v1/notebooks/{user_a_notebook_id}` or `POST /api/v1/jobs/{user_a_job_id}/run`. The API immediately executes the operation.
- **Impact:** Total breach of confidentiality and integrity between tenants/users; arbitrary deletion of competitor resources.
- **Evidence:**
  ```python
  # app/api/v1/routes/workspaces.py:57-64
  @router.get("/{workspace_id}")
  async def get_workspace(workspace_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
      service = WorkspaceService(db)
      workspace = await service.get_workspace(workspace_id) # No user/tenant ownership check
      return WorkspaceResponse.model_validate(workspace)
  ```
- **Recommended Remediation:**
  1. Add `owner_id` / `tenant_id` columns to all workspace and top-level entity tables.
  2. Implement an authorization layer verifying `caller.tenant_id == resource.tenant_id` on every query.

---

### SEC-003 🟠 HIGH — Child Worker Inherits Host Environment Variables (Database Credential Leak)

- **Severity:** HIGH
- **OWASP Category:** A02:2021 — Cryptographic Failures / A05:2021 — Security Misconfiguration
- **CWE:** CWE-200 (Exposure of Sensitive Information to an Unauthorized Actor), CWE-526 (Exposure of Sensitive Information Through Environmental Variables)
- **File:** [`app/runtime/python_runtime.py`](file:///d:/precision-notebook/app/runtime/python_runtime.py#L45-L51), [`app/runtime/python_worker.py`](file:///d:/precision-notebook/app/runtime/python_worker.py#L23-L31)
- **Root Cause:** When `PythonRuntime` spawns the `run_python_worker` process via `multiprocessing.get_context("spawn").Process()`, the child process inherits the complete host `os.environ` environment variable dictionary. The worker does not sanitize or strip `os.environ` prior to executing user code.
- **Attack Scenario:** A user creates a notebook cell containing:
  ```python
  import os
  print(os.environ.get("DATABASE_URL"))
  print(os.environ.get("CREDENTIAL_ENCRYPTION_KEY"))
  ```
  The cell outputs the PostgreSQL database credentials and master encryption key directly into the execution output stream.
- **Impact:** Host database credentials and platform encryption keys are disclosed to any user who can execute notebook code.
- **Evidence:**
  ```python
  # app/runtime/python_worker.py:23-31
  def run_python_worker(conn) -> None:
      globals_dict: dict[str, Any] = {
          "__name__": "__main__",
          "__doc__": None,
          "__package__": None,
      } # os.environ is NOT purged; inherits DATABASE_URL from parent
  ```
- **Recommended Remediation:**
  Purge sensitive environment variables immediately at the start of `run_python_worker`:
  ```python
  for key in list(os.environ.keys()):
      if key not in ("PATH", "SYSTEMROOT", "PYTHONPATH"):
          os.environ.pop(key, None)
  ```

---

### SEC-004 🟠 HIGH — Arbitrary Code Execution in Host OS Context Without Sandboxing

- **Severity:** HIGH
- **OWASP Category:** A05:2021 — Security Misconfiguration
- **CWE:** CWE-250 (Execution with Unnecessary Privileges), CWE-693 (Protection Mechanism Failure)
- **File:** [`app/runtime/python_worker.py`](file:///d:/precision-notebook/app/runtime/python_worker.py#L61-L64)
- **Root Cause:** While the worker process runs outside the FastAPI event loop (fulfilling control-plane isolation), it runs with identical OS permissions as the host web application. There is no seccomp filter, Linux namespace, AppArmor profile, Windows Job Object, or container boundary preventing user code from accessing the local filesystem or spawning arbitrary binaries.
- **Attack Scenario:** A user executes:
  ```python
  import subprocess
  output = subprocess.check_output(["cat", "/etc/shadow"]) # or Windows equivalent
  ```
  The worker executes the command with the full privileges of the host service account.
- **Impact:** Host compromise, local file read/write, host persistence.
- **Evidence:**
  ```python
  compiled = compile(code, "<notebook_cell>", "exec")
  exec(compiled, globals_dict)  # Standard exec without restricted builtins or container sandbox
  ```
- **Recommended Remediation:**
  Deploy worker processes within gVisor, Docker containers, or Firecracker microVMs with read-only root filesystems and dropped capabilities.

---

### SEC-005 🟠 HIGH — Host Python Environment Pollution via Global `pip install`

- **Severity:** HIGH
- **OWASP Category:** A06:2021 — Vulnerable and Outdated Components
- **CWE:** CWE-829 (Inclusion of Functionality from Untrusted Control Sphere), CWE-427 (Uncontrolled Search Path Element)
- **File:** [`app/runtime/python_worker.py`](file:///d:/precision-notebook/app/runtime/python_worker.py#L100-L106)
- **Root Cause:** When `install_packages` is triggered, the worker executes `[sys.executable, "-m", "pip", "install"] + requirements` directly against the active Python interpreter's `site-packages`.
- **Attack Scenario:** A notebook installs `fastapi==0.50.0` or a malicious package that overwrites `sqlalchemy` or `pydantic`. The next time the FastAPI server reloads or imports a module, the corrupted package causes a server-wide crash or code injection in the control plane.
- **Impact:** Denial of service across all users and potential control-plane hijacking.
- **Evidence:**
  ```python
  cmd_args = [sys.executable, "-m", "pip", "install"] + requirements
  proc = subprocess.run(cmd_args, capture_output=True, text=True, timeout=timeout)
  ```
- **Recommended Remediation:**
  Isolate package installations into per-session virtual environments or isolated directory targets (`pip install --target=<session_dir>`) and add `<session_dir>` to the worker's `sys.path`.

---

### SEC-006 🟠 HIGH — Fallback to Plaintext Credential Storage at Rest

- **Severity:** HIGH
- **OWASP Category:** A02:2021 — Cryptographic Failures
- **CWE:** CWE-312 (Cleartext Storage of Sensitive Information), CWE-311 (Missing Encryption of Sensitive Data)
- **File:** [`app/core/encryption.py`](file:///d:/precision-notebook/app/core/encryption.py#L42-L54), [`app/repositories/connector.py`](file:///d:/precision-notebook/app/repositories/connector.py#L107-L113)
- **Root Cause:** When `CREDENTIAL_ENCRYPTION_KEY` is not configured (default `""`), `encrypt_payload()` falls back to wrapping the secret in a plaintext JSON envelope `{"_enc": False, "_data": payload}`.
- **Attack Scenario:** An administrator deploys the platform without explicitly defining `CREDENTIAL_ENCRYPTION_KEY`. All database passwords, API tokens, and AWS secret keys added by users are persisted in plaintext JSONB inside PostgreSQL.
- **Impact:** Exposure of external database credentials and AWS keys upon database compromise or backup theft.
- **Evidence:**
  ```python
  # app/core/encryption.py
  if fernet is None:
      return {"_enc": False, "_data": payload} # Plaintext stored in DB
  ```
- **Recommended Remediation:**
  Refuse to store credentials or fail startup if `CREDENTIAL_ENCRYPTION_KEY` is not set when `ENVIRONMENT == "production"`.

---

### SEC-007 🟡 MEDIUM — Unrestricted Connector Egress / Internal Network Probing (SSRF)

- **Severity:** MEDIUM
- **OWASP Category:** A10:2021 — Server-Side Request Forgery (SSRF)
- **CWE:** CWE-918 (Server-Side Request Forgery)
- **File:** [`app/connectors/relational/postgresql.py`](file:///d:/precision-notebook/app/connectors/relational/postgresql.py#L25-L35), [`mysql.py`](file:///d:/precision-notebook/app/connectors/relational/mysql.py), [`mongodb.py`](file:///d:/precision-notebook/app/connectors/nosql/mongodb.py)
- **Root Cause:** Connector configuration accepts arbitrary `host` and `port` values. Calling `POST /api/v1/connectors/{id}/test` triggers network connection attempts to user-specified targets without validating against loopback (`127.0.0.1`, `localhost`), link-local (`169.254.169.254`), or internal RFC 1918 subnets.
- **Attack Scenario:** An attacker creates a connector targeting `http://169.254.169.254/latest/meta-data/` or internal database ports and invokes `/test` to map internal infrastructure.
- **Impact:** Internal network reconnaissance and cloud instance metadata access.
- **Evidence:**
  ```python
  self.host = str(self.config.get("host", "localhost"))
  self.port = int(self.config.get("port", 5432))
  # No validation prohibiting 127.0.0.1, 169.254.169.254, or private CIDRs
  ```
- **Recommended Remediation:**
  Validate destination IP addresses before connection and reject non-routable/loopback/cloud-metadata IP ranges unless explicitly permitted by an administrator allowlist.

---

### SEC-008 🟡 MEDIUM — Incomplete Cron Expression Evaluation Misfires Scheduled Jobs

- **Severity:** MEDIUM
- **OWASP Category:** A04:2021 — Insecure Design
- **CWE:** CWE-682 (Incorrect Calculation)
- **File:** [`app/jobs/schedule_utils.py`](file:///d:/precision-notebook/app/jobs/schedule_utils.py#L58-L75)
- **Root Cause:** `calculate_next_run()` splits the 5-field cron string but only calculates a delta based on `minute_spec`. It discards `hour_spec`, `dom_spec`, `month_spec`, and `dow_spec`.
- **Attack Scenario / Operational Impact:** A user configures a sensitive, high-resource batch job with cron `0 2 * * *` (run daily at 2:00 AM). Because the hour field is ignored and minute 0 evaluates to a 1-minute delta, the scheduler triggers the job every minute throughout the day.
- **Impact:** System overload, data corruption, and unintended repetitive executions.
- **Evidence:**
  ```python
  # app/jobs/schedule_utils.py:59-75
  minute_spec, hour_spec, dom_spec, month_spec, dow_spec = parts
  # hour_spec, dom_spec, month_spec, dow_spec are never used!
  next_time = now_in_tz + timedelta(minutes=step_minutes)
  return next_time
  ```
- **Recommended Remediation:**
  Use the standard, tested `croniter` library to compute accurate next-run timestamps across all 5 cron dimensions:
  ```python
  from croniter import croniter
  return croniter(cron_str, now_in_tz).get_next(datetime)
  ```

---

### SEC-009 🟡 MEDIUM — Lack of OS-Level Resource Quotas (Memory / CPU DoS)

- **Severity:** MEDIUM
- **OWASP Category:** A04:2021 — Insecure Design
- **CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-770 (Allocation of Resources Without Limits)
- **File:** [`app/runtime/python_worker.py`](file:///d:/precision-notebook/app/runtime/python_worker.py), [`app/runtime/python_runtime.py`](file:///d:/precision-notebook/app/runtime/python_runtime.py)
- **Root Cause:** `RuntimeConfig.max_memory_mb` is defined in configuration models but is not enforced by the worker process via `resource.setrlimit(resource.RLIMIT_AS, ...)` or OS job objects.
- **Attack Scenario:** User notebook executes `data = [bytearray(1024*1024) for _ in range(100000)]`, exhausting host physical RAM and causing the OS OOM killer to terminate the FastAPI backend or database services.
- **Impact:** Host-wide denial of service affecting all tenants.
- **Recommended Remediation:**
  Apply memory limits at process startup using `resource.setrlimit` on POSIX systems or assign worker processes to constrained cgroups / Windows Job Objects.

---

### SEC-010 🟡 MEDIUM — Hardcoded Development Database Credentials in Default Configuration

- **Severity:** MEDIUM
- **OWASP Category:** A05:2021 — Security Misconfiguration
- **CWE:** CWE-798 (Use of Hard-coded Credentials)
- **File:** [`app/core/config.py`](file:///d:/precision-notebook/app/core/config.py#L18)
- **Root Cause:** Default `DATABASE_URL` contains `postgresql+asyncpg://postgres:postgres@localhost:5432/precision_notebook`.
- **Impact:** If deployed to production without explicit `.env` overrides, attackers can authenticate to PostgreSQL using default credentials.
- **Recommended Remediation:**
  Require `DATABASE_URL` to be explicitly provided in production and throw a configuration validation error if default passwords are detected.

---

### SEC-011 🔵 LOW — Unbounded Request Payload and Cell Source Fields

- **Severity:** LOW
- **OWASP Category:** A04:2021 — Insecure Design
- **CWE:** CWE-400 (Uncontrolled Resource Consumption), CWE-20 (Improper Input Validation)
- **File:** [`app/schemas/notebook_cell.py`](file:///d:/precision-notebook/app/schemas/notebook_cell.py#L8-L15), [`app/schemas/job.py`](file:///d:/precision-notebook/app/schemas/job.py#L18), [`app/schemas/connector.py`](file:///d:/precision-notebook/app/schemas/connector.py#L18)
- **Root Cause:** `source`, `parameters`, `configuration`, and `description` fields lack `max_length` constraints in Pydantic schemas.
- **Impact:** Large JSON payloads (e.g., 50 MB cell bodies) consume disproportionate database storage and parsing memory.
- **Recommended Remediation:**
  Add `Field(max_length=1_000_000)` to `source` and constrain JSON dictionary sizes in validators.

---

### SEC-012 🔵 LOW — Per-Stream Output Truncation Allows Multi-Stream Output Flooding

- **Severity:** LOW
- **OWASP Category:** A04:2021 — Insecure Design
- **CWE:** CWE-400 (Resource Exhaustion)
- **File:** [`app/output/manager.py`](file:///d:/precision-notebook/app/output/manager.py#L50-L115)
- **Root Cause:** Truncation is enforced per-stream independently (100 KB stdout + 100 KB stderr + 100 KB traceback). Over multiple cell executions in a loop, outputs accumulate without a cumulative execution cap.
- **Impact:** Uncontrolled database bloat in the `execution_outputs` table.
- **Recommended Remediation:**
  Track a global execution byte budget across all streams per cell execution.

---

### SEC-013 🔵 LOW — Hardcoded "Unknown" Connector Name on Test Failure

- **Severity:** LOW
- **OWASP Category:** A04:2021 — Insecure Design
- **CWE:** CWE-20 (Improper Input Handling)
- **File:** [`app/api/v1/routes/connectors.py`](file:///d:/precision-notebook/app/api/v1/routes/connectors.py#L175)
- **Root Cause:** On `ConnectorConnectionError`, `name="Unknown"` is returned instead of the actual connector's name from the database.
- **Impact:** Poor observability and client telemetry confusion.
- **Recommended Remediation:**
  Pass `name=conn.name` from the fetched connector model to `ConnectorTestResponse`.

---

### SEC-014 ⚪ INFO — Single Shared Global Scheduler & Execution Manager Instance Lifecycle

- **Severity:** INFO
- **OWASP Category:** Architecture Note
- **CWE:** CWE-662 (Improper Synchronization)
- **File:** [`app/main.py`](file:///d:/precision-notebook/app/main.py#L17), [`app/jobs/manager.py`](file:///d:/precision-notebook/app/jobs/manager.py#L32)
- **Root Cause:** `JobScheduler` is instantiated globally in `main.py`, while `JobManager` creates a transient `ExecutionManager()` instance per request, which does not share state with a centralized session registry if sessions are distributed.
- **Impact:** In-memory execution task registries do not persist across multiple worker processes or distributed FastAPI replicas.
- **Recommended Remediation:**
  Manage `ExecutionManager` as an application-scoped singleton managed via FastAPI dependency injection or persist execution state to the database.

---

## 4. Architectural Boundary Verification

The platform architecture specified in `docs/architecture.md` was verified for boundary violations:

| Boundary Rule | Status | Evidence / Analysis |
|---|---|---|
| **No Notebook Execution in FastAPI** | ✅ **COMPLIANT** | FastAPI routes delegate execution strictly through `ExecutionManager` -> `SessionManager` -> `PythonRuntime` -> `python_worker.py`. No `exec()`, `eval()`, or user code runs in FastAPI event loops or thread pools. |
| **No Execution Logic in API Routes** | ✅ **COMPLIANT** | All API route handlers strictly validate Pydantic schemas and delegate to domain Services/Managers. |
| **Persistence Isolation (Store Layer)** | ✅ **COMPLIANT** | All database interactions occur through SQLAlchemy 2.0 Async repositories with explicit session dependency injection. |
| **Output / Logging Separation** | ✅ **COMPLIANT** | Worker stdout/stderr is captured via `io.StringIO`, transmitted over IPC pipe, and passed to `OutputManager` for persistence. |
| **Job Scheduling Separation** | ✅ **COMPLIANT** | `JobScheduler` runs as a dedicated async background loop checking `due_jobs` without blocking API request workers. |
| **Connector Credential Separation** | ✅ **COMPLIANT** | Credentials are stored separately in `credentials` table and referenced by UUID from `connectors.configuration`. |

---

## 5. False Positives Analysis

1. **SQL Injection in Repositories:** Static code scanners frequently flag database calls containing string variables. All queries in `app/repositories/*.py` use SQLAlchemy ORM expressions with automatic query parameterization (`select(Model).where(Model.field == val)`). No SQL injection paths exist.
2. **Command Injection in Dependency Installation:** `subprocess.run()` in `python_worker.py` was scrutinized. Because `shell=False` is used and package names are strictly validated against `PACKAGE_NAME_REGEX` (rejecting shell metacharacters), classic shell injection is prevented. The true risk is supply-chain package execution, not command injection.

---

## 6. Test Suite Analysis & Failing Tests

Running the full automated test suite (`pytest -v`) identified **2 failures out of 99 tests**:

1. **`tests/connectors/test_credentials.py::test_credential_manager_creation_and_sanitization` (FAILED):**
   - *Failure:* `KeyError: 'password'`
   - *Cause:* The test expected `resolve_credential()` to return the raw unencrypted dict directly, but `CredentialRepository.create()` now wraps payloads in an encryption envelope that requires symmetrical decryption.
2. **`tests/test_health.py::test_api_v1_health_endpoint` (FAILED):**
   - *Failure:* `assert 404 == 200`
   - *Cause:* The health probe route was moved from the `/api/v1` prefix to the root `/health` endpoint to separate unauthenticated health probes from authenticated business routes, causing the legacy `/api/v1/health` test path to 404.

---

## 7. Security Score & Production Readiness Assessment

### Security Score: **58 / 100**

#### Scoring Methodology Breakdown
- **Authentication & Identity (Weight: 20%):** `4 / 20` (Disabled by default, no user identities or multi-tenancy)
- **Authorization & Access Control (Weight: 20%):** `2 / 20` (Zero ownership verification, total BOLA vulnerability)
- **Runtime & Execution Isolation (Weight: 20%):** `12 / 20` (Process-separated from FastAPI, but lacks OS-level sandboxing and leaks environment variables)
- **Data & Credential Protection (Weight: 15%):** `10 / 15` (Symmetric encryption architecture in place, but plaintext fallback on missing key)
- **Injection & Input Validation (Weight: 15%):** `15 / 15` (SQL injection immune, strict dependency regex validation)
- **Architecture & Operational Reliability (Weight: 10%):** `8 / 10` (Strong layering and separation of concerns; minor scheduler cron flaw)

---

### Production Readiness Verdict: 🛑 **NOT PRODUCTION READY**

#### Mandatory Prerequisites for Production Deployment:
1. **Enable and Enforce Authentication (`REQUIRE_AUTH=True`)** with user/tenant identity tokens.
2. **Implement Multi-Tenant Authorization (RBAC / Ownership Checks)** on all workspace, notebook, connector, and job endpoints.
3. **Purge Host Environment Variables** from worker processes to protect `DATABASE_URL`.
4. **Isolate `pip install`** into per-session target directories to prevent host site-packages corruption.
5. **Fix Cron Calculation Logic** in `app/jobs/schedule_utils.py` using `croniter`.
6. **Enforce Mandatory Encryption Key** in non-development environments.
