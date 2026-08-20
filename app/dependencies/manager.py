import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.enums import DependencyStatus
from app.dependencies.exceptions import (
    DependencyError,
    DependencyInstallationError,
    DependencyResolutionError,
    DependencyTimeoutError,
    DependencyValidationError,
)
from app.dependencies.resolver import DependencyResolver
from app.dependencies.validator import DependencyValidator
from app.models.dependency import DependencyOperation, NotebookDependency
from app.output.enums import OutputType
from app.output.manager import OutputManager
from app.repositories.dependency import (
    DependencyOperationRepository,
    NotebookDependencyRepository,
)
from app.runtime.python_runtime import PythonRuntime


class DependencyManager:
    """Manager orchestrating dependency validation, resolution, installation, verification, and output capture."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.dep_repo = NotebookDependencyRepository(db)
        self.op_repo = DependencyOperationRepository(db)
        self.output_manager = OutputManager(db)

    async def declare_dependency(
        self,
        notebook_id: uuid.UUID,
        package_name: str,
        version_specifier: Optional[str] = None,
    ) -> NotebookDependency:
        """Validate and declare a package dependency for a notebook."""
        valid_name = DependencyValidator.validate_package_name(package_name)
        valid_spec = DependencyValidator.validate_version_specifier(version_specifier)

        existing = await self.dep_repo.get_by_notebook_and_package(notebook_id, valid_name)
        if existing:
            return await self.dep_repo.update(existing.id, valid_spec)  # type: ignore

        return await self.dep_repo.create(notebook_id, valid_name, valid_spec)

    async def list_dependencies(self, notebook_id: uuid.UUID) -> list[NotebookDependency]:
        """List declared dependencies for a notebook."""
        return list(await self.dep_repo.list_by_notebook_id(notebook_id))

    async def delete_dependency(self, dep_id: uuid.UUID) -> bool:
        """Delete a declared dependency."""
        return await self.dep_repo.delete(dep_id)

    async def install_notebook_dependencies(
        self,
        notebook_id: uuid.UUID,
        runtime: PythonRuntime,
        session_id: Optional[str] = None,
        timeout: float = 120.0,
    ) -> DependencyOperation:
        """Orchestrate full dependency lifecycle for a notebook inside the isolated Python runtime."""
        op_id = f"dep-op-{uuid.uuid4()}"
        declared_deps = await self.dep_repo.list_by_notebook_id(notebook_id)

        packages_payload = [
            {
                "package_name": dep.package_name,
                "version_specifier": dep.version_specifier or "",
            }
            for dep in declared_deps
        ]

        # 1. Create operation record with status REQUESTED
        op_rec = await self.op_repo.create(
            operation_id=op_id,
            notebook_id=notebook_id,
            packages=packages_payload,
            session_id=session_id,
            runtime_id=str(runtime.runtime_id),
            status=DependencyStatus.REQUESTED.value,
        )

        if not declared_deps:
            await self.op_repo.update_status(op_id, DependencyStatus.READY.value, resolved_versions={})
            return await self.op_repo.get_by_operation_id(op_id)  # type: ignore

        try:
            # 2. VALIDATING state
            await self.op_repo.update_status(op_id, DependencyStatus.VALIDATING.value)
            resolved_reqs = DependencyResolver.resolve_requirements(packages_payload)

            # 3. RESOLVING state
            await self.op_repo.update_status(op_id, DependencyStatus.RESOLVING.value)

            # Check if packages are already satisfied inside runtime
            verify_res = await runtime.verify_packages(packages_payload)
            if verify_res.get("satisfied"):
                await self.op_repo.update_status(
                    op_id,
                    DependencyStatus.READY.value,
                    resolved_versions=verify_res.get("resolved_versions", {}),
                )
                return await self.op_repo.get_by_operation_id(op_id)  # type: ignore

            # 4. INSTALLING state
            await self.op_repo.update_status(op_id, DependencyStatus.INSTALLING.value)
            requirements_strings = [req["requirement"] for req in resolved_reqs]

            install_res = await runtime.install_packages(requirements_strings, timeout=timeout)
            status_code = install_res.get("status")

            # Capture stdout / stderr logs into OutputManager
            stdout_content = install_res.get("stdout", "")
            stderr_content = install_res.get("stderr", "")

            if stdout_content:
                await self.output_manager.create_output_events(
                    execution_id=op_id,
                    session_id=session_id or "dep-session",
                    notebook_id=notebook_id,
                    output_type=OutputType.STDOUT,
                    content=stdout_content,
                )
            if stderr_content:
                await self.output_manager.create_output_events(
                    execution_id=op_id,
                    session_id=session_id or "dep-session",
                    notebook_id=notebook_id,
                    output_type=OutputType.STDERR,
                    content=stderr_content,
                )

            if status_code == "timeout":
                await self.op_repo.update_status(
                    op_id,
                    DependencyStatus.FAILED.value,
                    error_message=f"Installation timed out after {timeout} seconds.",
                )
                raise DependencyTimeoutError(op_id, timeout)

            if status_code != "ok":
                err_msg = stderr_content or "Pip installation returned non-zero exit status."
                await self.op_repo.update_status(
                    op_id,
                    DependencyStatus.FAILED.value,
                    error_message=err_msg,
                )
                raise DependencyInstallationError(op_id, err_msg)

            # 5. VERIFYING state
            await self.op_repo.update_status(op_id, DependencyStatus.VERIFYING.value)
            verify_res = await runtime.verify_packages(packages_payload)

            if not verify_res.get("satisfied"):
                missing = ", ".join(verify_res.get("missing_or_invalid", []))
                err_msg = f"Package verification failed: {missing}"
                await self.op_repo.update_status(
                    op_id,
                    DependencyStatus.FAILED.value,
                    error_message=err_msg,
                )
                raise DependencyInstallationError(op_id, err_msg)

            # 6. READY state
            await self.op_repo.update_status(
                op_id,
                DependencyStatus.READY.value,
                resolved_versions=verify_res.get("resolved_versions", {}),
            )
            return await self.op_repo.get_by_operation_id(op_id)  # type: ignore

        except (DependencyValidationError, DependencyResolutionError) as err:
            await self.op_repo.update_status(
                op_id, DependencyStatus.FAILED.value, error_message=str(err)
            )
            raise
        except Exception as exc:
            if not isinstance(exc, (DependencyTimeoutError, DependencyInstallationError)):
                await self.op_repo.update_status(
                    op_id, DependencyStatus.FAILED.value, error_message=str(exc)
                )
            raise

    async def cancel_operation(self, operation_id: str) -> Optional[DependencyOperation]:
        """Cancel an ongoing dependency installation operation."""
        op_rec = await self.op_repo.get_by_operation_id(operation_id)
        if not op_rec:
            return None
        if op_rec.status in (DependencyStatus.READY.value, DependencyStatus.FAILED.value, DependencyStatus.CANCELLED.value):
            return op_rec
        return await self.op_repo.update_status(operation_id, DependencyStatus.CANCELLED.value)
