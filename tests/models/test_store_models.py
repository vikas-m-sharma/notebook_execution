import uuid

from app.models.notebook import Notebook
from app.models.notebook_cell import NotebookCell
from app.models.notebook_metadata import NotebookMetadata
from app.models.project import Project
from app.models.workspace import Workspace


def test_workspace_model_instantiation():
    """Verify Workspace model initialization and attributes."""
    ws = Workspace(name="Test Workspace", description="Analytics Workspace")
    assert ws.name == "Test Workspace"
    assert ws.description == "Analytics Workspace"
    assert "Workspace" in repr(ws)


def test_project_model_instantiation():
    """Verify Project model initialization and relationship parameters."""
    ws_id = uuid.uuid4()
    proj = Project(workspace_id=ws_id, name="Data Engineering", description="ETL Pipelines")
    assert proj.workspace_id == ws_id
    assert proj.name == "Data Engineering"
    assert "Project" in repr(proj)


def test_notebook_model_instantiation():
    """Verify Notebook model initialization with language parameter."""
    proj_id = uuid.uuid4()
    nb = Notebook(project_id=proj_id, name="EDA Notebook", language="python")
    assert nb.project_id == proj_id
    assert nb.name == "EDA Notebook"
    assert nb.language == "python"
    assert "Notebook" in repr(nb)


def test_notebook_cell_model_instantiation():
    """Verify NotebookCell model initialization with code source and position."""
    nb_id = uuid.uuid4()
    cell = NotebookCell(notebook_id=nb_id, position=0, source="print('Hello World')", cell_type="code")
    assert cell.notebook_id == nb_id
    assert cell.position == 0
    assert cell.source == "print('Hello World')"
    assert cell.cell_type == "code"
    assert "NotebookCell" in repr(cell)


def test_notebook_metadata_model_instantiation():
    """Verify NotebookMetadata model initialization with configuration dict."""
    nb_id = uuid.uuid4()
    meta = NotebookMetadata(notebook_id=nb_id, configuration={"timeout_seconds": 300, "packages": ["pandas"]})
    assert meta.notebook_id == nb_id
    assert meta.configuration == {"timeout_seconds": 300, "packages": ["pandas"]}
    assert "NotebookMetadata" in repr(meta)
