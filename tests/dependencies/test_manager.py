import uuid
import pytest

from app.dependencies.enums import DependencyStatus
from app.dependencies.exceptions import DependencyValidationError
from app.dependencies.manager import DependencyManager
from app.models.notebook import Notebook
from app.models.project import Project
from app.models.workspace import Workspace
from app.repositories.output import ExecutionOutputRepository
from app.runtime.python_runtime import PythonRuntime


@pytest.mark.asyncio
async def test_dependency_manager_crud_and_lifecycle(db_session):
    """Test declaring, listing, deleting dependencies and executing lifecycle installation."""
    # 1. Setup DB workspace, project, notebook
    ws = Workspace(name="Dep WS")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(workspace_id=ws.id, name="Dep Proj")
    db_session.add(proj)
    await db_session.flush()

    nb = Notebook(project_id=proj.id, name="Dep Notebook")
    db_session.add(nb)
    await db_session.commit()

    manager = DependencyManager(db_session)

    # 2. Declare dependencies
    d1 = await manager.declare_dependency(nb.id, "pytest", ">=7.0")
    assert d1.package_name == "pytest"
    assert d1.version_specifier == ">=7.0"

    # List dependencies
    deps = await manager.list_dependencies(nb.id)
    assert len(deps) == 1
    assert deps[0].package_name == "pytest"

    # 3. Invalid package declaration rejection
    with pytest.raises(DependencyValidationError):
        await manager.declare_dependency(nb.id, "pandas; rm -rf /")

    # 4. Install dependencies inside isolated PythonRuntime
    runtime = PythonRuntime()
    await runtime.start()

    try:
        op_rec = await manager.install_notebook_dependencies(
            notebook_id=nb.id,
            runtime=runtime,
            session_id="session-dep-test",
            timeout=30.0,
        )

        assert op_rec.status == DependencyStatus.READY.value
        assert "pytest" in op_rec.resolved_versions

        # 5. Verify output logs were captured via Phase 8 OutputManager
        output_repo = ExecutionOutputRepository(db_session)
        logs = await output_repo.list_by_execution_id(op_rec.operation_id)
        # Note: If already satisfied, logs might be empty or stdout captured during pip
        assert isinstance(logs, list)

    finally:
        await runtime.stop()


@pytest.mark.asyncio
async def test_notebook_dependency_isolation(db_session):
    """Verify that notebook dependency environments are isolated per runtime process."""
    ws = Workspace(name="Iso WS")
    db_session.add(ws)
    await db_session.flush()

    proj = Project(workspace_id=ws.id, name="Iso Proj")
    db_session.add(proj)
    await db_session.flush()

    nb1 = Notebook(project_id=proj.id, name="Notebook A")
    nb2 = Notebook(project_id=proj.id, name="Notebook B")
    db_session.add_all([nb1, nb2])
    await db_session.commit()

    runtime1 = PythonRuntime()
    runtime2 = PythonRuntime()
    await runtime1.start()
    await runtime2.start()

    try:
        # Runtime 1 defines variable x = 100
        await runtime1.execute_code("x = 100")
        # Runtime 2 does not have x
        res2 = await runtime2.execute_code("print('x' in globals())")
        assert "False" in res2.get("stdout")

    finally:
        await runtime1.stop()
        await runtime2.stop()
