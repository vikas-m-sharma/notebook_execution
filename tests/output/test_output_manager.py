import asyncio
import uuid
import pytest

from app.output.enums import OutputType
from app.output.manager import OutputManager
from app.output.publisher import OutputPublisher


def test_output_manager_create_events_stdout_and_stderr():
    """Test OutputManager creating normalized sequence-ordered events for stdout and stderr."""
    mgr = OutputManager()
    events, metrics = mgr.create_output_events(
        execution_id="exec-123",
        session_id="session-456",
        cell_id="cell-789",
        stdout="Hello World\n",
        stderr="Warning message\n",
        status="ok",
        execution_time_ms=12.5,
    )

    assert len(events) == 2
    assert events[0].output_type == OutputType.STDOUT
    assert events[0].sequence == 1
    assert events[0].content == "Hello World\n"

    assert events[1].output_type == OutputType.STDERR
    assert events[1].sequence == 2
    assert events[1].content == "Warning message\n"

    assert metrics.total_events == 2
    assert metrics.stdout_count == 1
    assert metrics.stderr_count == 1
    assert metrics.result_present is False
    assert metrics.traceback_present is False
    assert metrics.truncated is False


def test_output_manager_create_events_traceback():
    """Test OutputManager capturing traceback events when execution fails."""
    mgr = OutputManager()
    tb_text = "Traceback (most recent call last):\n  File '<string>', line 1, in <module>\nZeroDivisionError: division by zero"
    events, metrics = mgr.create_output_events(
        execution_id="exec-tb-123",
        session_id="session-456",
        cell_id="cell-789",
        traceback=tb_text,
        status="error",
        execution_time_ms=5.0,
    )

    assert len(events) == 1
    assert events[0].output_type == OutputType.TRACEBACK
    assert events[0].sequence == 1
    assert "ZeroDivisionError" in events[0].content

    assert metrics.traceback_present is True
    assert metrics.result_present is False


def test_output_manager_result_event():
    """Test OutputManager emitting a RESULT event when execution succeeds with no stdout."""
    mgr = OutputManager()
    events, metrics = mgr.create_output_events(
        execution_id="exec-res-123",
        session_id="session-456",
        cell_id="cell-789",
        status="ok",
    )

    assert len(events) == 1
    assert events[0].output_type == OutputType.RESULT
    assert events[0].content == "Success"
    assert metrics.result_present is True


def test_output_manager_truncation_protection():
    """Test OutputManager safely truncating outputs exceeding maximum size limit."""
    mgr = OutputManager(max_output_size=50)
    huge_stdout = "A" * 200

    events, metrics = mgr.create_output_events(
        execution_id="exec-trunc-123",
        session_id="session-456",
        stdout=huge_stdout,
    )

    assert len(events) == 1
    assert "[OUTPUT TRUNCATED - SIZE LIMIT EXCEEDED]" in events[0].content
    assert events[0].output_metadata["truncated"] is True
    assert metrics.truncated is True


@pytest.mark.asyncio
async def test_output_publisher_pub_sub():
    """Test OutputPublisher in-memory live streaming pub/sub."""
    publisher = OutputPublisher()

    async def _subscriber_task():
        events_received = []
        async for event in publisher.subscribe("exec-stream-123"):
            events_received.append(event)
            if len(events_received) == 2:
                break
        return events_received

    sub_task = asyncio.create_task(_subscriber_task())
    await asyncio.sleep(0.05)

    # Create dummy events
    mgr = OutputManager(publisher=publisher)
    evs, _ = mgr.create_output_events(
        execution_id="exec-stream-123",
        session_id="session-stream",
        stdout="Stream 1\n",
        stderr="Stream 2\n",
    )

    for ev in evs:
        await publisher.publish(ev)

    received = await asyncio.wait_for(sub_task, timeout=2.0)
    assert len(received) == 2
    assert received[0].content == "Stream 1\n"
    assert received[1].content == "Stream 2\n"
