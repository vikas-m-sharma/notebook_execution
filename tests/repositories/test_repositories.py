import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.notebook import NotebookRepository
from app.repositories.notebook_cell import NotebookCellRepository
from app.repositories.notebook_metadata import NotebookMetadataRepository
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceRepository


@pytest.mark.asyncio
async def test_workspace_repository_crud(db_session: AsyncSession):
    """Verify WorkspaceRepository create, get_by_id, list_all, update, and delete."""
    repo = WorkspaceRepository(db_session)

    # 1. Create
    ws = await repo.create(name="Analytics WS", description="Main analytics workspace")
    assert ws.id is not None
    assert ws.name == "Analytics WS"
    assert ws.description == "Main analytics workspace"

    # 2. Get by ID
    retrieved = await repo.get_by_id(ws.id)
    assert retrieved is not None
    assert retrieved.name == "Analytics WS"

    # 3. List all
    all_ws = await repo.list_all()
    assert len(all_ws) == 1
    assert all_ws[0].id == ws.id

    # 4. Update
    updated = await repo.update(ws.id, name="Renamed WS", description="Updated description")
    assert updated is not None
    assert updated.name == "Renamed WS"
    assert updated.description == "Updated description"

    # 5. Delete
    deleted = await repo.delete(ws.id)
    assert deleted is True
    assert await repo.get_by_id(ws.id) is None


@pytest.mark.asyncio
async def test_project_repository_crud_and_uniqueness(db_session: AsyncSession):
    """Verify ProjectRepository operations and workspace/name uniqueness."""
    ws_repo = WorkspaceRepository(db_session)
    proj_repo = ProjectRepository(db_session)

    ws = await ws_repo.create(name="WS Alpha")

    # 1. Create Projects
    p1 = await proj_repo.create(workspace_id=ws.id, name="Project A", description="First Project")
    p2 = await proj_repo.create(workspace_id=ws.id, name="Project B")
    p1_id = p1.id
    assert p1.workspace_id == ws.id
    assert p2.workspace_id == ws.id

    # 2. List by Workspace
    projects = await proj_repo.list_by_workspace(ws.id)
    assert len(projects) == 2
    assert [p.name for p in projects] == ["Project A", "Project B"]

    # 3. Delete Project
    assert await proj_repo.delete(p1_id) is True
    assert await proj_repo.get_by_id(p1_id) is None

    # 4. Duplicate name in same workspace raises IntegrityError
    with pytest.raises(IntegrityError):
        await proj_repo.create(workspace_id=ws.id, name="Project B")
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_notebook_repository_crud(db_session: AsyncSession):
    """Verify NotebookRepository create, list_by_project, update, and delete."""
    ws_repo = WorkspaceRepository(db_session)
    proj_repo = ProjectRepository(db_session)
    nb_repo = NotebookRepository(db_session)

    ws = await ws_repo.create(name="WS Beta")
    proj = await proj_repo.create(workspace_id=ws.id, name="Data Science")

    # 1. Create Notebooks
    nb1 = await nb_repo.create(project_id=proj.id, name="Notebook 1", language="python")
    nb2 = await nb_repo.create(project_id=proj.id, name="Notebook 2", language="python")
    assert nb1.project_id == proj.id
    assert nb1.language == "python"

    # 2. List by Project
    notebooks = await nb_repo.list_by_project(proj.id)
    assert len(notebooks) == 2
    assert [nb.name for nb in notebooks] == ["Notebook 1", "Notebook 2"]

    # 3. Update
    updated = await nb_repo.update(nb1.id, name="Notebook 1 Updated", description="New description")
    assert updated is not None
    assert updated.name == "Notebook 1 Updated"

    # 4. Delete
    assert await nb_repo.delete(nb2.id) is True
    assert await nb_repo.get_by_id(nb2.id) is None


@pytest.mark.asyncio
async def test_notebook_cell_repository_ordering_and_reorder(db_session: AsyncSession):
    """Verify NotebookCellRepository ordering, reordering, and position constraints."""
    ws_repo = WorkspaceRepository(db_session)
    proj_repo = ProjectRepository(db_session)
    nb_repo = NotebookRepository(db_session)
    cell_repo = NotebookCellRepository(db_session)

    ws = await ws_repo.create(name="WS Gamma")
    proj = await proj_repo.create(workspace_id=ws.id, name="ML Project")
    nb = await nb_repo.create(project_id=proj.id, name="Model Training")

    # 1. Create cells out of position order
    c2 = await cell_repo.create(notebook_id=nb.id, position=2, source="print('Cell 2')")
    c0 = await cell_repo.create(notebook_id=nb.id, position=0, source="x = 10")
    c1 = await cell_repo.create(notebook_id=nb.id, position=1, source="y = 20")
    c0_id = c0.id

    # 2. List cells ordered by position
    cells = await cell_repo.list_by_notebook(nb.id)
    assert len(cells) == 3
    assert [c.position for c in cells] == [0, 1, 2]
    assert [c.source for c in cells] == ["x = 10", "y = 20", "print('Cell 2')"]

    # 3. Update cell source
    updated_c0 = await cell_repo.update(c0_id, source="x = 100")
    assert updated_c0 is not None
    assert updated_c0.source == "x = 100"

    # 4. Duplicate position in same notebook raises IntegrityError
    with pytest.raises(IntegrityError):
        await cell_repo.create(notebook_id=nb.id, position=0, source="duplicate")
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_notebook_metadata_repository(db_session: AsyncSession):
    """Verify NotebookMetadataRepository create_or_update, get_by_notebook_id, and delete."""
    ws_repo = WorkspaceRepository(db_session)
    proj_repo = ProjectRepository(db_session)
    nb_repo = NotebookRepository(db_session)
    meta_repo = NotebookMetadataRepository(db_session)

    ws = await ws_repo.create(name="WS Delta")
    proj = await proj_repo.create(workspace_id=ws.id, name="Metadata Test")
    nb = await nb_repo.create(project_id=proj.id, name="Configured Notebook")

    # 1. Create metadata
    meta = await meta_repo.create_or_update(
        notebook_id=nb.id,
        configuration={"timeout_seconds": 600, "environment": "py310"},
    )
    assert meta.notebook_id == nb.id
    assert meta.configuration["timeout_seconds"] == 600

    # 2. Update existing metadata
    meta_updated = await meta_repo.create_or_update(
        notebook_id=nb.id,
        configuration={"timeout_seconds": 1200, "environment": "py310", "gpu": True},
    )
    assert meta_updated.configuration["timeout_seconds"] == 1200
    assert meta_updated.configuration["gpu"] is True

    # 3. Retrieve
    retrieved = await meta_repo.get_by_notebook_id(nb.id)
    assert retrieved is not None
    assert retrieved.configuration["timeout_seconds"] == 1200

    # 4. Delete
    assert await meta_repo.delete(nb.id) is True
    assert await meta_repo.get_by_notebook_id(nb.id) is None
