# AGENTS.md — AI Agent Development Rules & Guidelines

This document contains strict instructions and constraints for any AI agent or automated developer operating on the **Precision Data Platform — Notebook Execution & Management Backend** repository. All future development phases must adhere strictly to these rules.

---

## MANDATORY AGENT DIRECTIVES & CONSTRAINTS

### 1. Architecture is Locked
The architecture defined in [`docs/architecture.md`](docs/architecture.md) is **FINAL** and **LOCKED**. You must not alter, simplify, merge, redesign, or replace any architectural component without explicit, prior user approval.

### 2. No Architecture Changes Without Explicit Approval
Do not re-architect the application, combine layers, or alter component responsibilities. Every component (API, Store, Execution Manager, Job Manager, Runtime Manager, Runtime, Session, Logs, Connectors) must maintain its isolated boundary.

### 3. No Notebook Execution Inside FastAPI
FastAPI belongs strictly to the **Control Plane**. Notebook Python/SQL code belongs strictly to the **Execution Plane**. Under no circumstances should notebook code be executed inside the FastAPI main process, thread pool, or event loop.

### 4. No Execution Logic Inside API Routes
API endpoints must strictly handle HTTP request validation, authentication/authorization (when added), and delegate orchestration directly to backend services (such as Execution Manager or Notebook Store). API handlers must not contain low-level execution or runtime logic.

### 5. Enforce Strict Separation of Responsibilities
Maintain strict separation across all ten architectural layers:
- **Notebook Management API**: Entry point for management & control requests.
- **Notebook Store**: Data persistence (PostgreSQL).
- **Execution Manager**: Notebook execution orchestration.
- **Job Manager**: Job scheduling and background trigger delegation.
- **Runtime Manager**: Provisioning, selection, and lifecycle management of execution runtimes.
- **Python Runtime**: Primary V1 isolated Python execution engine.
- **SQL Runtime**: Future runtime extension point.
- **Execution Session**: Stateful execution environment maintaining variables, imports, and context.
- **Output / Logs**: Capture of stdout, stderr, execution status, and metadata.
- **Data Connectors**: Platform-managed credentials and data source access.

### 6. Python is the V1 Runtime
Python is the mandatory primary runtime for V1. Implementation must focus on isolated Python execution processes/containers.

### 7. SQL is Future Runtime
SQL Runtime is part of the approved future architecture. Preserving the architectural extension point in Runtime Manager is required, but SQL execution must NOT be implemented until explicit phase assignment.

### 8. Notebook Execution Must Be Isolated
Notebook code must execute in an isolated environment (process/container) separate from the main application server. A crash or memory leak in a user notebook must never impact the FastAPI Control Plane or other notebook sessions.

### 9. Do Not Introduce Unapproved Infrastructure
Do not introduce unapproved third-party dependencies, frameworks, or infrastructure automatically. Approved tech stack: Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Pydantic, pytest. Unapproved without explicit consent: Django, Celery, Redis, Kafka, RabbitMQ, Kubernetes, Spark, Airflow, Databricks SDK.

### 10. Development Must Be Phase-by-Phase
Development proceeds strictly in sequential phases (Phase 0 through Phase 11). Focus exclusively on the requirements of the currently assigned phase.

### 11. Do Not Implement Future Phases Early
Never jump ahead to build features, endpoints, data models, or infrastructure intended for future phases.

### 12. No Unrelated Refactoring
When working on a phase task, modify only the relevant files needed for that phase. Do not perform global refactoring, style changes, or unrequested rewrites of existing working code.

### 13. Tests Are Mandatory for Implementation Phases
Every implementation phase (Phase 1 onwards) requires comprehensive test coverage using `pytest`. Unit tests and integration tests must pass cleanly before declaring phase completion.

### 14. Maintain Production-Level Design & Code Quality
All code must adhere to production-grade standards: type hints, clean error handling, standard logging, defensive validations, proper separation of concerns, and clean documentation.

### 15. Mandatory Async Database Pattern
All database operations must use SQLAlchemy 2.x AsyncEngine, `asyncpg`, and `AsyncSession`. Synchronous database calls, `psycopg2`, or blocking I/O inside FastAPI handlers are strictly prohibited.

### 16. Zero Hard-Coded Credentials
All credentials, database URLs, secret keys, and connection strings must be retrieved dynamically via `app.core.config.get_settings()`. Never commit secrets, real passwords, or production connection strings to source control.

---

## Summary of Architectural Principle

> **API controls. Store persists. Execution Manager orchestrates. Job Manager schedules. Runtime Manager provisions/selects. Runtime executes. Session maintains state. Output/Logs records execution. Connectors provide data access.**
