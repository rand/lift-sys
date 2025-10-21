"""
Tests for State Persistence (H2)

Test suite validating:
1. Round-trip serialization (save → load → save)
2. Pydantic model handling (RunContext, StateT, provenance)
3. Atomicity (no partial states)
4. Performance (<100ms for save/load)
5. 100 consecutive save/load cycles
"""

import asyncio
import time
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import BaseModel

from lift_sys.dspy_signatures.node_interface import RunContext
from lift_sys.dspy_signatures.state_persistence import (
    GraphState,
    NodeOutput,
    StatePersistence,
    deserialize_run_context,
    serialize_run_context,
)

# Test state models


class SimpleTestState(BaseModel):
    """Simple state for testing."""

    user_input: str = ""
    processed_output: str = ""
    counter: int = 0
    is_complete: bool = False
    metadata: dict[str, str] = {}


class ComplexState(BaseModel):
    """Complex state with nested structures."""

    id: str
    nested_data: dict[str, list[int]]
    optional_field: str | None = None
    timestamp: str


# Fixtures


@pytest.fixture
def simple_state() -> SimpleTestState:
    """Create a simple test state."""
    return SimpleTestState(
        user_input="test input",
        processed_output="test output",
        counter=42,
        is_complete=False,
        metadata={"key": "value"},
    )


@pytest.fixture
def complex_state() -> ComplexState:
    """Create a complex test state."""
    return ComplexState(
        id="test-123",
        nested_data={"numbers": [1, 2, 3], "more": [4, 5, 6]},
        optional_field="present",
        timestamp=datetime.now(UTC).isoformat(),
    )


@pytest.fixture
def run_context(simple_state: SimpleTestState) -> RunContext[SimpleTestState]:
    """Create a RunContext for testing."""
    ctx = RunContext(
        state=simple_state,
        execution_id=str(uuid4()),
        user_id="test-user-123",
        metadata={"test": "metadata"},
    )
    ctx.add_provenance(
        node_name="TestNode", signature_name="TestSignature", inputs={"prompt": "test"}
    )
    return ctx


@pytest.fixture
def graph_state(simple_state: SimpleTestState) -> GraphState:
    """Create a GraphState for testing."""
    return GraphState(
        execution_id=str(uuid4()),
        state_snapshot=simple_state.model_dump(),
        state_type=f"{simple_state.__class__.__module__}.{simple_state.__class__.__name__}",
        provenance=[
            {
                "node": "TestNode",
                "signature": "TestSignature",
                "inputs": {"prompt": "test"},
            }
        ],
        metadata={"test": "data"},
        user_id="test-user-123",
    )


# Test GraphState model


def test_graph_state_creation(simple_state: SimpleTestState):
    """Test GraphState can be created with valid data."""
    state = GraphState(
        execution_id="exec-123",
        state_snapshot=simple_state.model_dump(),
        state_type="test.SimpleTestState",
    )

    assert state.execution_id == "exec-123"
    assert state.state_snapshot["user_input"] == "test input"
    assert state.state_type == "test.SimpleTestState"
    assert state.provenance == []
    assert state.metadata == {}


def test_graph_state_with_provenance(simple_state: SimpleTestState):
    """Test GraphState preserves provenance chain."""
    provenance = [
        {"node": "Node1", "signature": "Sig1"},
        {"node": "Node2", "signature": "Sig2"},
    ]

    state = GraphState(
        execution_id="exec-123",
        state_snapshot=simple_state.model_dump(),
        state_type="test.SimpleTestState",
        provenance=provenance,
    )

    assert len(state.provenance) == 2
    assert state.provenance[0]["node"] == "Node1"
    assert state.provenance[1]["signature"] == "Sig2"


# Test NodeOutput model


def test_node_output_creation():
    """Test NodeOutput can be created with valid data."""
    output = NodeOutput(
        node_name="ExtractIntent",
        signature_name="NLToIntent",
        inputs={"prompt": "test"},
        outputs={"intent": "extracted"},
        execution_time_ms=15.5,
    )

    assert output.node_name == "ExtractIntent"
    assert output.signature_name == "NLToIntent"
    assert output.inputs == {"prompt": "test"}
    assert output.outputs == {"intent": "extracted"}
    assert output.execution_time_ms == 15.5
    assert output.timestamp is not None


# Test serialization helpers


def test_serialize_run_context(run_context: RunContext[SimpleTestState]):
    """Test RunContext serialization to GraphState."""
    graph_state = serialize_run_context(run_context)

    assert graph_state.execution_id == run_context.execution_id
    assert graph_state.user_id == run_context.user_id
    assert graph_state.state_snapshot == run_context.state.model_dump()
    assert len(graph_state.provenance) == 1
    assert graph_state.metadata == run_context.metadata


def test_deserialize_run_context(graph_state: GraphState):
    """Test GraphState deserialization to RunContext."""
    ctx = deserialize_run_context(graph_state, SimpleTestState)

    assert ctx.execution_id == graph_state.execution_id
    assert ctx.user_id == graph_state.user_id
    assert ctx.state.user_input == "test input"
    assert ctx.state.counter == 42
    assert len(ctx.provenance) == 1
    assert ctx.metadata == graph_state.metadata


def test_round_trip_serialization(run_context: RunContext[SimpleTestState]):
    """Test RunContext → GraphState → RunContext preserves data."""
    # Serialize
    graph_state = serialize_run_context(run_context)

    # Deserialize
    restored_ctx = deserialize_run_context(graph_state, SimpleTestState)

    # Verify all fields preserved
    assert restored_ctx.execution_id == run_context.execution_id
    assert restored_ctx.user_id == run_context.user_id
    assert restored_ctx.state.model_dump() == run_context.state.model_dump()
    assert restored_ctx.provenance == run_context.provenance
    assert restored_ctx.metadata == run_context.metadata


# Test StatePersistence (mock mode - no Supabase)


class MockSupabaseClient:
    """Mock Supabase client for testing without database."""

    def __init__(self):
        self.storage = {}
        self._last_operation = None

    def table(self, name: str):
        return self

    def insert(self, data: dict):
        # Enforce unique execution_id constraint
        if data["execution_id"] in self.storage:
            raise Exception("duplicate key value violates unique constraint")
        self.storage[data["execution_id"]] = data
        self._last_operation = "insert"
        return self

    def select(self, fields: str):
        return self

    def eq(self, field: str, value: str):
        self._query_value = value
        return self

    def order(self, field: str, desc: bool = False):
        return self

    def limit(self, n: int):
        return self

    def update(self, data: dict):
        if self._query_value in self.storage:
            self.storage[self._query_value].update(data)
        self._last_operation = "update"
        return self

    def delete(self):
        self._last_operation = "delete"
        return self

    def execute(self):
        if self._last_operation == "delete" and hasattr(self, "_query_value"):
            # Delete the item if it exists
            if self._query_value in self.storage:
                del self.storage[self._query_value]

        if hasattr(self, "_query_value"):
            result = self.storage.get(self._query_value)
            data = [result] if result else []
        else:
            data = list(self.storage.values())

        class Response:
            def __init__(self, d):
                self.data = d

        return Response(data)


@pytest.fixture
def mock_persistence(monkeypatch) -> StatePersistence[SimpleTestState]:
    """Create StatePersistence with mocked Supabase client."""
    mock_client = MockSupabaseClient()

    def mock_create_client(url: str, key: str):
        return mock_client

    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    monkeypatch.setenv("SUPABASE_SERVICE_KEY", "mock-key")
    monkeypatch.setattr(
        "lift_sys.dspy_signatures.state_persistence.create_client", mock_create_client
    )

    return StatePersistence[SimpleTestState]()


@pytest.mark.asyncio
async def test_save_state(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test saving graph state."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    # Verify state was saved
    loaded = await mock_persistence.load(graph_state.execution_id)
    assert loaded.execution_id == graph_state.execution_id
    assert loaded.state_snapshot == graph_state.state_snapshot


@pytest.mark.asyncio
async def test_load_state(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test loading graph state."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    loaded = await mock_persistence.load(graph_state.execution_id)

    assert loaded.execution_id == graph_state.execution_id
    assert loaded.state_type == graph_state.state_type
    assert loaded.user_id == graph_state.user_id


@pytest.mark.asyncio
async def test_load_nonexistent_state(mock_persistence: StatePersistence[SimpleTestState]):
    """Test loading nonexistent state raises KeyError."""
    with pytest.raises(KeyError, match="No state found"):
        await mock_persistence.load("nonexistent-id")


@pytest.mark.asyncio
async def test_update_node_output(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test updating node output."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    output = {
        "signature_name": "TestSig",
        "inputs": {"prompt": "test"},
        "outputs": {"result": "success"},
        "execution_time_ms": 10.5,
    }

    await mock_persistence.update_node_output(graph_state.execution_id, "TestNode", output)

    # Verify provenance updated
    loaded = await mock_persistence.load(graph_state.execution_id)
    assert len(loaded.provenance) == 2  # Original + new
    assert loaded.provenance[-1]["node_name"] == "TestNode"


@pytest.mark.asyncio
async def test_update_node_output_with_state_updates(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test updating node output with state changes."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    output = {
        "signature_name": "TestSig",
        "inputs": {},
        "outputs": {},
        "state_updates": {"counter": 100},
    }

    await mock_persistence.update_node_output(graph_state.execution_id, "TestNode", output)

    # Verify state updated
    loaded = await mock_persistence.load(graph_state.execution_id)
    assert loaded.state_snapshot["counter"] == 100


@pytest.mark.asyncio
async def test_delete_state(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test deleting graph state."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    await mock_persistence.delete(graph_state.execution_id)

    with pytest.raises(KeyError):
        await mock_persistence.load(graph_state.execution_id)


@pytest.mark.asyncio
async def test_list_states(mock_persistence: StatePersistence[SimpleTestState]):
    """Test listing graph states."""
    # Create multiple states
    states = []
    for i in range(3):
        state = GraphState(
            execution_id=f"exec-{i}",
            state_snapshot={"counter": i},
            state_type="test.SimpleTestState",
            user_id="test-user",
        )
        states.append(state)
        await mock_persistence.save(state.execution_id, state)

    # List all states
    listed = await mock_persistence.list_states()
    assert len(listed) >= 3


# Performance tests


@pytest.mark.asyncio
async def test_save_performance(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test save operation completes in <100ms."""
    start = time.perf_counter()
    await mock_persistence.save(graph_state.execution_id, graph_state)
    duration_ms = (time.perf_counter() - start) * 1000

    # Mock should be very fast (<10ms)
    assert duration_ms < 100


@pytest.mark.asyncio
async def test_load_performance(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test load operation completes in <100ms."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    start = time.perf_counter()
    await mock_persistence.load(graph_state.execution_id)
    duration_ms = (time.perf_counter() - start) * 1000

    # Mock should be very fast (<10ms)
    assert duration_ms < 100


@pytest.mark.asyncio
async def test_100_consecutive_save_load_cycles(
    mock_persistence: StatePersistence[SimpleTestState],
):
    """Test 100 consecutive save/load cycles (acceptance criteria)."""
    for i in range(100):
        # Create unique state for each iteration
        state = GraphState(
            execution_id=f"exec-{i}",
            state_snapshot={"counter": i, "user_input": f"input-{i}"},
            state_type="test.SimpleTestState",
            user_id=f"user-{i % 10}",  # 10 different users
            provenance=[{"iteration": i}],
        )

        # Save
        await mock_persistence.save(state.execution_id, state)

        # Load
        loaded = await mock_persistence.load(state.execution_id)

        # Verify
        assert loaded.execution_id == state.execution_id
        assert loaded.state_snapshot["counter"] == i
        assert loaded.user_id == state.user_id

    # All 100 iterations completed successfully
    assert True


# Complex state tests


@pytest.mark.asyncio
async def test_complex_state_serialization(
    mock_persistence: StatePersistence[ComplexState], complex_state: ComplexState
):
    """Test complex nested state serializes correctly."""
    graph_state = GraphState(
        execution_id="complex-123",
        state_snapshot=complex_state.model_dump(),
        state_type=f"{complex_state.__class__.__module__}.{complex_state.__class__.__name__}",
    )

    await mock_persistence.save(graph_state.execution_id, graph_state)
    loaded = await mock_persistence.load(graph_state.execution_id)

    # Verify nested structures preserved
    assert loaded.state_snapshot["nested_data"] == complex_state.nested_data
    assert loaded.state_snapshot["optional_field"] == complex_state.optional_field


# Atomicity tests


@pytest.mark.asyncio
async def test_save_atomicity(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test save operation is atomic (fails completely or succeeds completely)."""
    # First save succeeds
    await mock_persistence.save(graph_state.execution_id, graph_state)

    # Second save with same ID should fail (duplicate execution_id)
    with pytest.raises(ValueError, match="Failed to save state"):
        await mock_persistence.save(graph_state.execution_id, graph_state)

    # Original state should be unchanged
    loaded = await mock_persistence.load(graph_state.execution_id)
    assert loaded.state_snapshot == graph_state.state_snapshot


# Edge cases


@pytest.mark.asyncio
async def test_empty_provenance(mock_persistence: StatePersistence[SimpleTestState]):
    """Test state with empty provenance chain."""
    state = GraphState(
        execution_id="empty-prov",
        state_snapshot={"counter": 0},
        state_type="test.SimpleTestState",
        provenance=[],  # Empty
    )

    await mock_persistence.save(state.execution_id, state)
    loaded = await mock_persistence.load(state.execution_id)

    assert loaded.provenance == []


@pytest.mark.asyncio
async def test_large_state(mock_persistence: StatePersistence[SimpleTestState]):
    """Test large state (many fields, large provenance)."""
    large_snapshot = {f"field_{i}": f"value_{i}" for i in range(1000)}
    large_provenance = [{"node": f"Node{i}", "data": "x" * 100} for i in range(100)]

    state = GraphState(
        execution_id="large-state",
        state_snapshot=large_snapshot,
        state_type="test.SimpleTestState",
        provenance=large_provenance,
    )

    await mock_persistence.save(state.execution_id, state)
    loaded = await mock_persistence.load(state.execution_id)

    assert len(loaded.state_snapshot) == 1000
    assert len(loaded.provenance) == 100


@pytest.mark.asyncio
async def test_concurrent_updates(
    mock_persistence: StatePersistence[SimpleTestState], graph_state: GraphState
):
    """Test concurrent node output updates."""
    await mock_persistence.save(graph_state.execution_id, graph_state)

    # Simulate concurrent updates from multiple nodes
    async def update_node(node_name: str, value: int):
        output = {
            "signature_name": "TestSig",
            "inputs": {},
            "outputs": {"value": value},
        }
        await mock_persistence.update_node_output(graph_state.execution_id, node_name, output)

    # Run 10 concurrent updates
    await asyncio.gather(*[update_node(f"Node{i}", i) for i in range(10)])

    # Verify all updates recorded
    loaded = await mock_persistence.load(graph_state.execution_id)
    assert len(loaded.provenance) >= 10  # Original + 10 updates
