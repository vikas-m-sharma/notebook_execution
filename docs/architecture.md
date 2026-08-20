# Precision Data Platform — Notebook Execution & Management Backend Architecture

## 1. Product Overview & Purpose
The **Notebook Execution & Management Backend** is a core module of the **Precision Data Platform**. It provides a robust, enterprise-grade platform for managing, executing, and orchestrating analytical notebooks. Inspired by modern data engineering platforms like Databricks and Google Colab, this backend offers stateful interactive execution, scheduled background execution, isolated code runtimes, and platform-managed data connector abstractions.

---

## 2. High-Level Architecture

```
                    PRECISION DATA PLATFORM
                              |
                              v
                  +-------------------------+
                  | Notebook Management API |
                  +------------+------------+
                               |
              +----------------+----------------+
              |                |                |
              v                v                v
       +-------------+  +---------------+  +-------------+
       |  Notebook   |  |  Execution     |  |    Job      |
       |    Store    |  |    Manager     |  |   Manager   |
       +-------------+  +-------+-------+  +------+------+
                               |                 |
                               v                 |
                       +---------------+         |
                       | Runtime       |         |
                       | Manager       |         |
                       +-------+-------+         |
                               |                 |
                         +-----+-----+           |
                         |           |           |
                         v           v           |
                  +-----------+ +-----------+    |
                  |  Python   | |    SQL    |    |
                  |  Runtime  | |  Runtime  |    |
                  +-----+-----+ +-----+-----+    |
                        |             |           |
                        +------+------+\----------+
                               |
                               v
                    +---------------------+
                    | Execution Session   |
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |    Output / Logs    |
                    +----------+----------+
                               |
                               v
                    +---------------------+
                    |   Data Connectors   |
                    +---------------------+
```

---

## 3. Control Plane vs. Execution Plane

To ensure stability, security, and scalability, the architecture strictly segregates the system into two distinct operational planes:

```
+-----------------------------------------------------------------------+
|                             CONTROL PLANE                             |
|                                                                       |
|  [ Notebook Management API ]  <--->  [ Notebook Store ]               |
|              |                                                        |
|              +---> [ Execution Manager ] <--- [ Job Manager ]         |
|                           |                                           |
|                           v                                           |
|                   [ Runtime Manager ]                                 |
+-----------------------------------------------------------------------+
                                   |
                             (Provisions &
                              Orchestrates)
                                   |
                                   v
+-----------------------------------------------------------------------+
|                            EXECUTION PLANE                            |
|                                                                       |
|  [ Python Runtime ]  /  [ SQL Runtime ] (Future)                       |
|           |                                                           |
|           v                                                           |
|  [ Isolated Python Execution Process / Container ]                        |
|           |                                                           |
|           v                                                           |
|  [ Execution Session (Stateful Memory, Vars, Imports) ]               |
|           |                                                           |
|           v                                                           |
|  [ Output / Logs Capture ] <---> [ Data Connectors ]                  |
+-----------------------------------------------------------------------+
```

### Control Plane
- **Scope**: HTTP endpoint processing, metadata persistence, job scheduling, execution request validation, and runtime provisioning/selection.
- **Technology**: FastAPI, PostgreSQL, SQLAlchemy, Alembic.
- **Rule**: The Control Plane **MUST NOT** directly execute user notebook Python/SQL code.

### Execution Plane
- **Scope**: User Python code compilation, execution, stateful variable retention, stdout/stderr capture, and external data querying via connectors.
- **Technology**: Isolated Python processes or containers.
- **Rule**: The Execution Plane is decoupled from FastAPI. A failure in user code execution does not impact Control Plane availability.

---

## 4. Component Responsibilities

### 4.1 Notebook Management API
- Entry point for all external interactions.
- Endpoints for notebook CRUD, cell operations, metadata, runtime/dependency configuration, execution triggers (interactive & cell level), execution status/logs inspection, session termination.
- **Boundary**: Validates requests and forwards instructions to backend services. Never runs user code.

### 4.2 Notebook Store
- Data access and persistence layer backed by PostgreSQL via SQLAlchemy ORM.
- Stores notebook metadata, cell contents, cell ordering, versioning, runtime configurations, dependency definitions, and execution records.
- **Boundary**: Focuses strictly on relational persistence and queries.

### 4.3 Execution Manager
- Central execution orchestrator.
- Responsibilities: Request validation, notebook & dependency verification, creating execution database records, requesting runtimes from Runtime Manager, initializing execution sessions, triggering execution, monitoring, timeout enforcement, cancellation, and execution finalization.
- **Boundary**: Orchestrates execution workflow without containing low-level runtime details or running Python code directly.

### 4.4 Job Manager
- Scheduling engine for automated and recurring notebook execution.
- Configures cron triggers, recurring schedules, and background job runs.
- **Boundary**: Delegates all notebook execution directly to the Execution Manager.

### 4.5 Runtime Manager
- Lifecycle manager and abstraction layer for execution runtimes.
- Handles runtime selection (Python vs. SQL), startup, health checks, shutdown, cleanup, and resource allocation.
- **Boundary**: Provides a unified interface to Execution Manager while encapsulating concrete runtime implementations.

### 4.6 Python Runtime
- Primary V1 execution engine.
- Spawns and manages isolated Python processes/containers for running user notebook code.
- **Boundary**: Executes code strictly outside the FastAPI server process.

### 4.7 SQL Runtime
- Approved future architecture extension point for executing SQL-native analytical workloads.
- **Boundary**: Placeholders/interfaces preserved in Phase 0; implementation deferred to future phases without API contract changes.

### 4.8 Execution Session
- Maintains stateful execution context across multiple cell runs within the same active session.
- Retains memory state: variables, module imports, functions, classes, DataFrames, and runtime state.
- **Boundary**: Completely isolated per notebook execution to prevent cross-notebook state contamination.

### 4.9 Output / Logs
- Subsystem for collecting, streaming, and persisting execution artifacts.
- Captures: `stdout`, `stderr`, cell outputs, Python tracebacks, status transitions, execution timestamps, duration, Execution ID, Session ID, and Trace/Correlation IDs.

### 4.10 Data Connectors
- Platform-managed connectors providing secure data access.
- Supported initial categories: MySQL, MSSQL, MongoDB, AWS S3.
- **Boundary**: Injects managed connections/credentials securely into the runtime environment without exposing raw platform secrets in user notebook code.

---

## 5. Execution Flows

### 5.1 Interactive Execution Flow
```
User
  |
  v
Notebook Management API
  |
  v
Execution Manager
  |
  v
Runtime Manager
  |
  v
Python Runtime
  |
  v
Isolated Execution Environment
  |
  v
Execution Session
  |
  v
Notebook Cell Execution
  |
  v
Output / Logs Capture
```

### 5.2 Scheduled Execution Flow
```
Schedule / Cron Trigger
  |
  v
Job Manager
  |
  v
Execution Manager
  |
  v
Runtime Manager
  |
  v
Python Runtime
  |
  v
Execution Session
  |
  v
Full Notebook Execution
  |
  v
Output / Logs Capture
```

---

## 6. Execution Lifecycle State Model

Notebook executions transition through a strict, deterministic lifecycle state machine:

```
     +---------+
     | QUEUED  |
     +----+----+
          |
          v
    +-----------+
    | STARTING  |
    +----+------+
          |
          v
    +-----------+
    |  RUNNING  |
    +----+------+
         |
         +-------------------+-------------------+-------------------+
         |                   |                   |                   |
         v                   v                   v                   v
   +-----------+       +-----------+       +-----------+       +-----------+
   |  SUCCESS  |       |  FAILED   |       | CANCELLED |       |  TIMEOUT  |
   +-----------+       +-----------+       +-----------+       +-----------+
```

State descriptions:
- `QUEUED`: Execution request accepted and placed in the processing queue.
- `STARTING`: Runtime resource allocation, container/process launch, and session setup in progress.
- `RUNNING`: Notebook cells currently executing in the isolated runtime environment.
- `SUCCESS`: All target cells executed cleanly without uncaught exceptions.
- `FAILED`: Execution halted due to user code exception, dependency error, or runtime failure.
- `CANCELLED`: Execution manually terminated by user request.
- `TIMEOUT`: Execution terminated due to exceeding maximum allowed execution duration.

---

## 7. Mandatory Architectural Principle

> **API controls. Store persists. Execution Manager orchestrates. Job Manager schedules. Runtime Manager provisions/selects. Runtime executes. Session maintains state. Output/Logs records execution. Connectors provide data access.**
