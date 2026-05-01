import logging
import uuid
import sys
import os
from typing import Optional, Dict, Any

# First Principles Fix: Dynamically inject project root into sys.path
# This ensures all 'from src...' absolute imports resolve correctly.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph.graph import StateGraph, END
from src.state import AgentState
from src.agents.nodes import validate_node, synthesize_node, assess_risk_node, recommend_node

logger = logging.getLogger(__name__)

# --- STEP 20: Source Link Preservation Node ---
def format_output_node(state: AgentState) -> AgentState:
    """Final node to consolidate source links and prepare state for UI/PDF."""
    logger.info("Executing Format Output Node...")
    
    links = []
    raw = state.rawdata
    
    # Safely extract and format source URLs from the raw data payload
    if demo := raw.get("demographics"):
        if url := demo.get("source_url"): links.append(f"Demographics: {url}")
    if amen := raw.get("amenities"):
        if url := amen.get("source_url"): links.append(f"Amenities: {url}")
        
    risks = raw.get("risks", {})
    if crime := risks.get("crime"):
        if url := crime.get("source_url"): links.append(f"Crime Stats: {url}")
    if aqi := risks.get("air_quality"):
        if url := aqi.get("source_url"): links.append(f"Air Quality: {url}")
    if flood := risks.get("flood_zone"):
        if url := flood.get("source_url"): links.append(f"Flood Atlas: {url}")
        
    # Filter out unavailable data links
    state.sourcelinks = [link for link in links if "data_unavailable" not in link]
    return state


# --- STEP 18: Graph Initialization & Sequential Edges ---
logger.info("Compiling StateGraph...")
workflow = StateGraph(AgentState)

# Add all cognitive and formatting nodes
workflow.add_node("validate", validate_node)
workflow.add_node("synthesize", synthesize_node)
workflow.add_node("assess_risk", assess_risk_node)
workflow.add_node("recommend", recommend_node)
workflow.add_node("format_output", format_output_node)

# Set the deterministic entry point
workflow.set_entry_point("validate")

# Define the sequential, autonomous flow (No human-in-the-loop)
workflow.add_edge("validate", "synthesize")
workflow.add_edge("synthesize", "assess_risk")
workflow.add_edge("assess_risk", "recommend")
workflow.add_edge("recommend", "format_output")
workflow.add_edge("format_output", END)

# Compile into a runnable application
app = workflow.compile()


# --- STEP 19: Async Execution Wrapper ---
async def run_awaas_analysis(pincode: str, user_criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Main entry point for the pipeline. Invokes data acquisition and routes it through the graph.
    """
    from src.utils.geocoding import resolve_location
    from src.data_connectors.aggregator import aggregate_neighborhood_data
    
    try:
        logger.info(f"Initiating Autonomous Flow for PIN: {pincode}")
        
        # Phase 2 Integration: Fetch live data
        location = resolve_location(pincode)
        raw_data = await aggregate_neighborhood_data(location)
        
        # Initialize the strictly typed AgentState
        initial_state = {
            "pincode": pincode,
            "location": location,
            "rawdata": raw_data,
            "usercriteria": user_criteria or {}
        }
        
        # Generate thread ID for stateless graph execution
        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute the graph asynchronously
        final_state = await app.ainvoke(initial_state, config)
        
        return final_state
        
    except Exception as e:
        logger.error(f"Autonomous Flow Failed: {str(e)}")
        # Fail-safe return object matching expected UI schema
        return {
            "pincode": pincode,
            "aisummary": "Data unavailable. Pipeline execution failed.",
            "riskflags": ["Critical system error during analysis."],
            "recommendation": "Unable to provide recommendation.",
            "sourcelinks": []
        }