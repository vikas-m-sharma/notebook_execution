# Precision Data Platform — Development Rules & Standards

This document establishes the mandatory development rules, standards, architectural lock, phase boundaries, workspace hierarchy, and development discipline for the **Notebook Execution & Management Backend** of the **Precision Data Platform**.

---

## 1. Development Philosophy
1. **Architectural Integrity**: Architectural boundaries are non-negotiable. Control Plane components must never execute user notebook code directly.
2. **Production Quality**: Every phase must deliver clean, maintainable, tested, type-safe, and production-ready code.
3. **Incremental Phase Discipline**: Development strictly follows the defined phase roadmap. No feature leakage or premature infrastructure creation across phases.
4. **Explicit Verification**: Every implementation phase must be validated through automated tests (`pytest`) before completion.

---

## 2. Locked Application Architecture

The system architecture defined below is **FINAL** and **LOCKED**. Developers and AI coding agents must preserve these layer boundaries without alteration.

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

### Key V1 Architecture Principles:
- **Python Runtime**: Primary V1 isolated Python execution engine.
- **SQL Runtime**: Reserved and extensible architectural extension point for future SQL-native execution support.
- **Runtime Isolation**: Every notebook execution must run inside an isolated Python process or container environment.
- **Control Plane Isolation**: The FastAPI Control Plane application must **NEVER** execute user notebook code directly.

---

## 3. Control Plane vs. Execution Plane Isolation

The system strictly segregates operational responsibilities into two distinct planes:

### Control Plane
- **Components**: Notebook Management API, Notebook Store, Job Manager, Runtime Manager, Execution Manager.
- **Responsibilities**: Metadata management, HTTP request handling, persistence, job scheduling, execution orchestration, and runtime lifecycle control.
- **Technology**: FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic.

### Execution Plane
- **Components**: Isolated Python Runtime, future SQL Runtime, Execution Session, Output / Logs capture, Data Connectors.
- **Responsibilities**: Isolated code compilation, execution, in-memory state persistence across cells (variables, DataFrames, imports), stdout/stderr capture, and data source interaction.
- **Technology**: Isolated Python processes / containers.

### Mandatory Control Plane Rule:
> **The Control Plane MUST NEVER execute user notebook code directly inside the FastAPI application process, thread pool, or event loop.**

Prohibited patterns inside FastAPI endpoints, background tasks, or control plane handlers:
- `exec(user_code)`
- `eval(user_code)`
- `subprocess` execution of arbitrary notebook code directly from FastAPI request handlers.

FastAPI must exclusively delegate, coordinate, and orchestrate execution through the `Execution Manager` and `Runtime Manager`.

---

## 4. Workspace & Storage Hierarchy

Notebook organization follows a workspace-oriented hierarchy:

```
Workspace
└── Projects
    └── Notebooks
        ├── Notebook A
        ├── Notebook B
        └── Notebook C
```

Conceptually:
```
Workspace
    ↓
Project
    ↓
Notebook
    ↓
Cells / Metadata
```

### Hierarchy Principles:
- **Databricks Conceptual Reference**: Inspired by workspace-oriented notebook platforms (e.g., Databricks), users work inside a workspace, projects organize analytical work, notebooks belong to projects, notebook content and metadata are persisted, and notebooks execute via the platform runtime.
- **No Direct Copying**: This design provides a product/architectural reference; proprietary implementation details of external platforms must not be copied.
- **Phase Discipline**: Do **NOT** create models or tables for Workspaces, Projects, or Notebooks prior to their assigned phase (Phase 2).

---

## 5. Database & Schema Migration Principles

- **Primary Database**: PostgreSQL is the sole relational database.
- **ORM Foundation**: SQLAlchemy 2.x using `AsyncSession` and `asyncpg`.
- **Migration Engine**: Alembic manages all database schema migrations.
- **Migration Discipline**:
  - Schema changes must be version-controlled through Alembic scripts in `alembic/versions/`.
  - Production database schemas must never be modified manually.
  - Database migrations for future-phase models must **NOT** be generated early.
  - Domain models (`Workspace`, `Project`, `Notebook`, `NotebookCell`, `ExecutionRecord`) are introduced only in their assigned phase.

---

## 6. Technology Stack Policy

Technology introduction must be phase-specific and architectural-boundary compliant.

### Core Approved Tech Stack:
- **Core Backend**: Python 3.10+, FastAPI, PostgreSQL, SQLAlchemy 2.x, Alembic, Pydantic, `pydantic-settings`.
- **Execution & Isolation**: Isolated Python processes/containers, stateful execution sessions.
- **Testing**: `pytest`, `pytest-asyncio`, `httpx`.

### Policy on External Dependencies & Distributed Infrastructure:
Technologies such as Redis, Celery, Kafka, RabbitMQ, Kubernetes, Spark, Airflow, or Databricks SDK **MUST NOT** be introduced prematurely.

A technology may only be introduced when:
1. It is explicitly required by the approved architecture,
2. It belongs to the current active development phase,
3. Its introduction does not violate Control/Execution plane boundaries,
4. It receives explicit approval if it introduces a new infrastructure dependency.

---

## 7. Conceptual Product References

### Databricks Reference
Used as a conceptual reference for workspace-oriented organization, notebook lifecycle, runtime abstractions, isolated execution, persistent state, execution sessions, dependency management, and job-based scheduled execution.

### Google Colab Reference
Used as a conceptual reference for interactive cell execution, dynamic output capture, runtime dependency/package installation, persistent cell state, and interactive notebook sessions.

*Note: Both platforms serve strictly as architectural and workflow references. The implementation remains custom to the Precision Data Platform.*

---

## 8. Phase-by-Phase Development Roadmap

Development strictly proceeds in sequential phases. Developers and AI agents must work **ONLY** within the active phase.

| Phase | Phase Name | Description | Status |
|---|---|---|---|
| **Phase 0** | **Architecture & Development Contract** | Establish documentation, development rules, architectural lock, and AGENTS guidelines. | **COMPLETED** |
| **Phase 1** | **FastAPI + PostgreSQL Foundation** | Basic FastAPI app setup, PostgreSQL connection pool, SQLAlchemy base models, Alembic setup. | **COMPLETED** |
| **Phase 2** | **Notebook Store** | Database schemas, models, and repositories for Workspaces, Projects, Notebooks, Cells, and Metadata. | **COMPLETED** |
| **Phase 3** | **Notebook Management API** | FastAPI CRUD endpoints for notebooks, cells, configurations, and metadata management. | **COMPLETED** |
| **Phase 4** | **Runtime Manager** | Lifecycle management, runtime selection abstractions, startup/shutdown orchestration. | **COMPLETED** |
| **Phase 5** | **Python Runtime** | Isolated Python process/container execution worker implementation. | **COMPLETED** |
| **Phase 6** | **Execution Session** | Stateful in-memory execution context (variables, imports, namespace persistence across cells). | **COMPLETED** |
| **Phase 7** | **Execution Manager** | Execution orchestration, validation, monitoring, cancellation, and timeout management. | **COMPLETED** |
| **Phase 8** | **Output / Logs** | Capture, streaming, and storage of stdout, stderr, outputs, tracebacks, and execution metrics. | **COMPLETED** |
| **Phase 9** | **Dependency Management** | Environment dependency resolution and package installation in execution runtimes. | **COMPLETED** |
| **Phase 10** | **Data Connector Integration** | Platform-managed connector injection (MySQL, MSSQL, MongoDB, AWS S3). | **COMPLETED** |
| **Phase 11** | **Job Manager + Production Hardening** | Scheduled execution triggers, cron management, performance tuning, and production readiness. | **COMPLETED** |

---

## 9. Strict Scope & Feature Leakage Prevention

To prevent architectural drift and premature complexity, implementation agents **MUST NOT**:
- Implement future-phase features early.
- Create future-phase database tables or Alembic migrations.
- Create placeholder classes or fake/stub execution engines for future components.
- Create unused infrastructure "for future use".
- Install unapproved future-phase dependencies.
- Silently modify the phase roadmap or architectural boundaries.

> **Rule**: If a future feature is required to complete the current phase, **STOP** and report the dependency instead of implementing it early.

---

## 10. Locked Architectural Decision Control

The following 13 architectural decisions are **LOCKED**:
1. FastAPI is the Notebook Management API / Control Plane layer.
2. PostgreSQL is the application database.
3. SQLAlchemy 2.x Async (`asyncpg`, `AsyncSession`) is the database foundation.
4. Alembic manages database schema migrations.
5. Notebook storage follows: `Workspace` → `Projects` → `Notebooks` → `Cells`.
6. Notebook execution is isolated from the FastAPI server process.
7. Runtime Manager controls runtime lifecycle and provisioning.
8. Python Runtime is the mandatory V1 execution engine.
9. SQL Runtime remains an extensible architecture point for future implementation.
10. Execution Session maintains stateful memory context across cells within a session.
11. Execution Manager orchestrates execution requests and lifecycles.
12. Job Manager handles scheduled and background trigger delegation.
13. Data Connectors isolate platform credentials from notebook user code.

*Any modification to these responsibilities requires prior explicit user approval.*

---

## 11. Code Quality, Error Handling & Security

- **Type Safety**: Use Python standard type hints (`typing`) across all modules.
- **Validation**: Use Pydantic models for request validation, configuration management, and API serialization.
- **Async I/O**: Use `async`/`await` for database access and non-blocking I/O operations.
- **Logging**: Use standard Python `logging` with structured, informative log messages.
- **Security & Zero Secrets Leakage**: Never hard-code passwords, API keys, database credentials, or secret keys in source code. Retrieve credentials dynamically via `get_settings()`. Never expose internal tracebacks or connection credentials in API HTTP responses.
- **Git Discipline**: Commit changes incrementally per phase with clear, descriptive messages. Do not mix unrelated phase changes.

---

## 12. Automated Testing Rules

- Every implementation phase (Phase 1 onward) requires automated test coverage.
- Mandatory test execution command:
  ```bash
  pytest
  ```
- All test suites must pass cleanly before declaring phase completion.
- Tests must verify functionality of the current phase only. Do not write tests for unimplemented future phases.

---

## 13. Phase Completion Criteria

A phase is considered **COMPLETED** ONLY when:
1. All explicitly listed phase requirements are fully implemented.
2. No code, models, or migrations from future phases were created.
3. Architectural boundaries specified in [`docs/architecture.md`](architecture.md) remain intact.
4. Comprehensive unit and integration tests pass cleanly (`pytest`).
5. Code meets production standards without temporary stubs or mocks (unless explicitly requested).
6. Database migrations are generated and tested cleanly (where applicable).
7. Documentation accurately reflects implementation status.

---

## 14. AI & Agent Execution Directives

All AI coding agents (including Antigravity) operating on this repository must:
1. Read [`AGENTS.md`](../AGENTS.md) before making changes.
2. Read [`docs/architecture.md`](architecture.md) to respect component boundaries.
3. Read [`docs/development-rules.md`](development-rules.md) to understand current scope.
4. Identify the active development phase and work **ONLY** within its boundaries.
5. Inspect existing codebase before creating new files or abstractions.
6. Reuse existing core configurations, databases, and utilities.
7. Never silently modify architecture or layer boundaries.
8. Never implement future phases ahead of schedule.
9. Run `pytest` before reporting phase completion.
10. Report all files created, modified, dependencies added, and test execution results.
11. Report assumptions, conflicts, or blockers immediately.
12. **STOP** upon completing the assigned phase.
