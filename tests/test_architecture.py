import pytest
from src.state import AgentState

def test_agent_state_initialization():
    """Validates that the AgentState schema initializes correctly with default parameters."""
    state = AgentState(pincode="411033")
    
    assert state.pincode == "411033"
    assert state.aisummary == ""
    assert isinstance(state.riskflags, list)
    assert len(state.riskflags) == 0
    assert state.report_generated is False