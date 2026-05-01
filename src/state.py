from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class AgentState(BaseModel):
    pincode: str
    location: Dict[str, Any] = Field(default_factory=dict)
    rawdata: Dict[str, Any] = Field(default_factory=dict)
    usercriteria: Optional[Dict[str, Any]] = Field(default_factory=dict)
    aisummary: str = ""
    riskflags: List[str] = Field(default_factory=list)
    recommendation: str = ""
    sourcelinks: List[str] = Field(default_factory=list)
    report_generated: bool = False
    markdown_report: str = ""
    pdf_bytes: bytes = b""