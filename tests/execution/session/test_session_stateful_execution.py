import uuid
import pytest
from app.execution.session.manager import SessionManager


@pytest.mark.asyncio
async def test_stateful_variables_persistence():
    """Test that variables defined in previous cells remain available in subsequent cells."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1
        r1 = await session.execute_cell("a = 100")
        assert r1.status == "ok"

        # Cell 2
        r2 = await session.execute_cell("b = 200")
        assert r2.status == "ok"

        # Cell 3
        r3 = await session.execute_cell("c = a + b")
        assert r3.status == "ok"

        # Cell 4
        r4 = await session.execute_cell("print(c)")
        assert r4.status == "ok"
        assert r4.stdout.strip() == "300"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_stateful_imports_persistence():
    """Test that imports made in earlier cells remain available in subsequent cells."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Import module
        r1 = await session.execute_cell("import math")
        assert r1.status == "ok"

        # Cell 2: Use imported module
        r2 = await session.execute_cell("print(math.sqrt(25))")
        assert r2.status == "ok"
        assert r2.stdout.strip() == "5.0"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_stateful_functions_persistence():
    """Test that functions defined in earlier cells remain available in subsequent cells."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Define function
        r1 = await session.execute_cell("def multiply(x, y):\n    return x * y")
        assert r1.status == "ok"

        # Cell 2: Call function
        r2 = await session.execute_cell("print(multiply(6, 7))")
        assert r2.status == "ok"
        assert r2.stdout.strip() == "42"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_stateful_classes_persistence():
    """Test that classes defined in earlier cells remain available in subsequent cells."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Define class
        r1 = await session.execute_cell(
            "class Person:\n    def __init__(self, name):\n        self.name = name"
        )
        assert r1.status == "ok"

        # Cell 2: Instantiate class
        r2 = await session.execute_cell("p = Person('Precision')")
        assert r2.status == "ok"

        # Cell 3: Access class instance
        r3 = await session.execute_cell("print(p.name)")
        assert r3.status == "ok"
        assert r3.stdout.strip() == "Precision"
    finally:
        await manager.stop_session(session.session_id)


@pytest.mark.asyncio
async def test_stateful_mutable_objects():
    """Test that mutations on data structures persist across cell executions."""
    manager = SessionManager()
    session = await manager.create_session(notebook_id=uuid.uuid4())

    try:
        # Cell 1: Initialize list
        await session.execute_cell("items = []")

        # Cell 2: Append item 1
        await session.execute_cell("items.append('Python')")

        # Cell 3: Append item 2
        await session.execute_cell("items.append('FastAPI')")

        # Cell 4: Print list
        r4 = await session.execute_cell("print(items)")
        assert r4.status == "ok"
        assert "['Python', 'FastAPI']" in r4.stdout.strip()
    finally:
        await manager.stop_session(session.session_id)
