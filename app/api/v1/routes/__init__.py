from app.api.v1.routes.connectors import router as connectors_router
from app.api.v1.routes.dependencies import router as dependencies_router
from app.api.v1.routes.execution_outputs import router as execution_outputs_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.jobs import router as jobs_router
from app.api.v1.routes.notebook_cells import router as notebook_cells_router
from app.api.v1.routes.notebook_metadata import router as notebook_metadata_router
from app.api.v1.routes.notebooks import router as notebooks_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.workspaces import router as workspaces_router

__all__ = [
    "workspaces_router",
    "projects_router",
    "notebooks_router",
    "notebook_cells_router",
    "notebook_metadata_router",
    "execution_outputs_router",
    "dependencies_router",
    "connectors_router",
    "jobs_router",
    "health_router",
]
