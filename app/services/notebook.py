import uuid
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notebook import Notebook
from app.repositories.notebook import NotebookRepository
from app.repositories.project import ProjectRepository
from app.schemas.notebook import NotebookCreate, NotebookUpdate

SUPPORTED_LANGUAGES = {"python"}


class NotebookService:
    """Service encapsulating business logic for Notebook operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.project_repository = ProjectRepository(session)
        self.notebook_repository = NotebookRepository(session)

    def _validate_language(self, language: str) -> str:
        """Validate supported notebook programming language."""
        lang_normalized = language.lower()
        if lang_normalized not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=422,
                detail=f"Unsupported notebook language '{language}'. Supported languages: {sorted(list(SUPPORTED_LANGUAGES))}.",
            )
        return lang_normalized

    async def create_notebook(
        self, project_id: uuid.UUID, data: NotebookCreate
    ) -> Notebook:
        """Create a new Notebook in a Project, verifying Project existence and language support."""
        project = await self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )

        language = self._validate_language(data.language)

        notebooks = await self.notebook_repository.list_by_project(project_id)
        if any(n.name == data.name for n in notebooks):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Notebook with name '{data.name}' already exists in project '{project_id}'.",
            )

        try:
            return await self.notebook_repository.create(
                project_id=project_id,
                name=data.name,
                description=data.description,
                language=language,
            )
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Notebook with name '{data.name}' already exists in project '{project_id}'.",
            ) from exc

    async def get_notebook(
        self,
        notebook_id: uuid.UUID,
        include_cells: bool = False,
        include_metadata: bool = False,
    ) -> Notebook:
        """Retrieve a Notebook by ID or raise HTTP 404."""
        notebook = await self.notebook_repository.get_by_id(
            notebook_id,
            include_cells=include_cells,
            include_metadata=include_metadata,
        )
        if notebook is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
        return notebook

    async def list_notebooks_by_project(
        self, project_id: uuid.UUID
    ) -> Sequence[Notebook]:
        """List all Notebooks in a Project, verifying Project existence."""
        project = await self.project_repository.get_by_id(project_id)
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project '{project_id}' not found.",
            )
        return await self.notebook_repository.list_by_project(project_id)

    async def update_notebook(
        self, notebook_id: uuid.UUID, data: NotebookUpdate
    ) -> Notebook:
        """Update an existing Notebook or raise HTTP 404/409/422."""
        notebook = await self.get_notebook(notebook_id)
        language = (
            self._validate_language(data.language)
            if data.language is not None
            else None
        )

        if data.name is not None:
            notebooks = await self.notebook_repository.list_by_project(notebook.project_id)
            if any(n.name == data.name and n.id != notebook_id for n in notebooks):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Notebook with name '{data.name}' already exists in this project.",
                )

        try:
            updated = await self.notebook_repository.update(
                notebook_id=notebook_id,
                name=data.name,
                description=data.description,
                language=language,
            )
            if updated is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Notebook '{notebook_id}' not found.",
                )
            return updated
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Notebook with name '{data.name}' already exists in this project.",
            ) from exc

    async def delete_notebook(self, notebook_id: uuid.UUID) -> None:
        """Delete a Notebook by ID or raise HTTP 404."""
        await self.get_notebook(notebook_id)
        deleted = await self.notebook_repository.delete(notebook_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notebook '{notebook_id}' not found.",
            )
