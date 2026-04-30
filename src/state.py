from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    """
    Global state object representing the data flow through the Awaas AI cognitive pipeline.
    Enforces strict typing and default instantiation to prevent state bleeding between sessions.
    """
    pincode: str
    location: Dict[str, Any]
    rawdata: Dict[str, Any]
    
    # Optional parameters based on user input
    usercriteria: Optional[Dict[str, Any]] = None
    
    # AI Generated Outputs
    aisummary: str = ""
    riskflags: List[str] = Field(default_factory=list)
    recommendation: str = ""
    
    # Auditability Tracking
    sourcelinks: List[str] = Field(default_factory=list)
    
    # Execution Status
    report_generated: bool = False