import pytest

from app.output.enums import OutputType
from app.repositories.output import ExecutionOutputRepository
from app.schemas.output import OutputEventSchema


@pytest.mark.asyncio
async def test_output_repository_crud_and_sequence_ordering(db_session):
    """Test ExecutionOutputRepository bulk creation and sequence-ordered database retrieval."""
    repo = ExecutionOutputRepository(db_session)
    exec_id = "exec-db-123"
    cell_id = "cell-db-789"

    ev1 = OutputEventSchema(
        execution_id=exec_id,
        session_id="session-1",
        notebook_id=None,
        cell_id=cell_id,
        output_type=OutputType.STDOUT,
        content="First line\n",
        sequence=1,
    )
    ev2 = OutputEventSchema(
        execution_id=exec_id,
        session_id="session-1",
        notebook_id=None,
        cell_id=cell_id,
        output_type=OutputType.STDOUT,
        content="Second line\n",
        sequence=2,
    )

    # 1. Bulk create
    created = await repo.bulk_create([ev1, ev2])
    assert len(created) == 2
    assert created[0].sequence == 1
    assert created[1].sequence == 2

    # 2. Retrieve by execution_id
    by_exec = await repo.list_by_execution_id(exec_id)
    assert len(by_exec) == 2
    assert by_exec[0].content == "First line\n"
    assert by_exec[1].content == "Second line\n"

    # 3. Retrieve by cell_id
    by_cell = await repo.list_by_cell_id(cell_id)
    assert len(by_cell) == 2
    assert by_cell[0].sequence == 1
    assert by_cell[1].sequence == 2
