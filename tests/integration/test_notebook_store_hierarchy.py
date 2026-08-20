import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.models.notebook_cell import NotebookCell
from app.models.notebook_metadata import NotebookMetadata
from app.models.project import Project
from app.models.workspace import Workspace
from app.repositories.notebook import NotebookRepository
from app.repositories.notebook_cell import NotebookCellRepository
from app.repositories.notebook_metadata import NotebookMetadataRepository
from app.repositories.project import ProjectRepository
from app.repositories.workspace import WorkspaceRepository


@pytest.mark.asyncio
async def test_full_notebook_store_hierarchy_and_cascade_deletion(db_session: AsyncSession):
    """Integration test verifying complete Workspace -> Project -> Notebook -> Cell -> Metadata hierarchy and cascade deletion."""
    ws_repo = WorkspaceRepository(db_session)
    proj_repo = ProjectRepository(db_session)
    nb_repo = NotebookRepository(db_session)
    cell_repo = NotebookCellRepository(db_session)
    meta_repo = NotebookMetadataRepository(db_session)

    # 1. Build hierarchy: Workspace -> Project -> Notebook
    ws = await ws_repo.create(name="Production Workspace", description="Enterprise analytics")
    proj = await proj_repo.create(workspace_id=ws.id, name="Financial Modeling", description="Q4 Forecasts")
    nb = await nb_repo.create(project_id=proj.id, name="Revenue Prediction", language="python")

    # 2. Attach Cells (0, 1, 2)
    c0 = await cell_repo.create(notebook_id=nb.id, position=0, source="import pandas as pd", cell_type="code")
    c1 = await cell_repo.create(notebook_id=nb.id, position=1, source="df = pd.read_csv('data.csv')", cell_type="code")
    c2 = await cell_repo.create(notebook_id=nb.id, position=2, source="print(df.head())", cell_type="code")

    # 3. Attach Metadata
    meta = await meta_repo.create_or_update(
        notebook_id=nb.id,
        configuration={"timeout_seconds": 900, "dependencies": ["pandas", "scikit-learn"]},
    )

    # 4. Verify Eager Loading via Repository
    nb_loaded = await nb_repo.get_by_id(nb.id, include_cells=True, include_metadata=True)
    assert nb_loaded is not None
    assert nb_loaded.name == "Revenue Prediction"
    assert len(nb_loaded.cells) == 3
    assert [c.position for c in nb_loaded.cells] == [0, 1, 2]
    assert [c.source for c in nb_loaded.cells] == ["import pandas as pd", "df = pd.read_csv('data.csv')", "print(df.head())"]
    assert nb_loaded.metadata_rec is not None
    assert nb_loaded.metadata_rec.configuration["timeout_seconds"] == 900

    # 5. Verify Workspace Cascade Deletion
    # Deleting Workspace must cascade delete Project, Notebook, Cells, and Metadata
    deleted_ws = await ws_repo.delete(ws.id)
    assert deleted_ws is True

    # Verify no orphaned records remain in database
    res_ws = await db_session.execute(select(Workspace).where(Workspace.id == ws.id))
    assert res_ws.scalar_one_or_none() is None

    res_proj = await db_session.execute(select(Project).where(Project.id == proj.id))
    assert res_proj.scalar_one_or_none() is None

    res_nb = await db_session.execute(select(Notebook).where(Notebook.id == nb.id))
    assert res_nb.scalar_one_or_none() is None

    res_cells = await db_session.execute(select(NotebookCell).where(NotebookCell.notebook_id == nb.id))
    assert len(res_cells.scalars().all()) == 0

    res_meta = await db_session.execute(select(NotebookMetadata).where(NotebookMetadata.notebook_id == nb.id))
    assert res_meta.scalar_one_or_none() is None
