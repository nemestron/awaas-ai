import os
import json
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from src.state import AgentState

logger = logging.getLogger(__name__)

# Model Specification
VALIDATION_MODEL = "llama-3.1-8b-instant"
SYNTHESIS_MODEL = "deepseek-r1-distill-qwen-32b"
RISK_MODEL = "llama-3.3-70b-versatile"
RECOMMENDATION_MODEL = "llama-3.1-8b-instant"
TOOL_CALLING_FALLBACK = "llama-3.3-70b-versatile"

def get_llm(model_name: str, temperature: float = 0.0) -> ChatGroq:
    """Instantiates the Groq LLM client securely."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
         raise ValueError("GROQ_API_KEY is missing or invalid in .env file.")
    return ChatGroq(temperature=temperature, model_name=model_name, groq_api_key=api_key)

def invoke_with_fallback(primary_model: str, prompt: str, schema: Optional[type[BaseModel]] = None) -> Any:
    """Standard execution with fallback for simple prompt-response generation."""
    try:
        llm = get_llm(primary_model)
        if schema:
            return llm.with_structured_output(schema).invoke(prompt)
        return llm.invoke(prompt)
    except Exception as e:
        logger.warning(f"Primary model {primary_model} failed: {str(e)}. Falling back.")
        fallback_llm = get_llm(TOOL_CALLING_FALLBACK)
        if schema:
            return fallback_llm.with_structured_output(schema).invoke(prompt)
        return fallback_llm.invoke(prompt)

# --- STRUCTURED OUTPUT SCHEMAS ---

class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True if enough data is present to generate a report, False otherwise.")
    missing_fields: List[str] = Field(description="List of critical data categories missing.")

class RiskResult(BaseModel):
    top_risks: List[str] = Field(description="Top 3 prioritized risk concerns explained in one sentence each.")

class RecommendationResult(BaseModel):
    suitability_score: int = Field(description="Score from 1 to 10.")
    good_for: str = Field(description="e.g., 'Good for long-term hold, not for immediate rental yield'.")
    justification: str = Field(description="One-line justification of the score.")

# --- COGNITIVE NODES ---

def validate_node(state: AgentState) -> AgentState:
    logger.info("Executing Validation Node...")
    raw_data = state.rawdata
    
    # First Principles Fix: Safely handle NoneType data payloads
    amenities_data = raw_data.get("amenities", {}).get("data")
    safe_amenities = amenities_data if amenities_data is not None else []
    
    data_presence = {
        "demographics": raw_data.get("demographics", {}).get("error") is None,
        "amenities": len(safe_amenities) > 0,
        "risks": raw_data.get("risks", {}).get("crime", {}).get("error") is None
    }
    
    prompt = f"Review data availability: {data_presence}. Is there sufficient data for a report? Critical fields are demographics and risks. Identify missing items."
    
    try:
        result: ValidationResult = invoke_with_fallback(VALIDATION_MODEL, prompt, ValidationResult)
        if not result.is_valid:
            state.riskflags.append("CRITICAL: Insufficient data to generate a highly accurate report.")
    except Exception as e:
         logger.error(f"Validation failed: {str(e)}")
         state.riskflags.append("Warning: Data validation bypassed.")
    return state

def synthesize_node(state: AgentState) -> AgentState:
    logger.info("Executing Tool-Augmented Synthesis Node...")
    user_type = state.usercriteria.get("investment_type", "general buyer") if state.usercriteria else "general buyer"
    
    @tool
    def get_census() -> str:
        """Use this tool to get demographic and census data for the neighborhood."""
        data = state.rawdata.get("demographics", {})
        safe_data = data if data is not None else {}
        return json.dumps(safe_data)[:1000]
        
    @tool
    def get_amenities() -> str:
        """Use this tool to get local amenities like schools and hospitals."""
        amenities_data = state.rawdata.get("amenities", {}).get("data")
        safe_amenities = amenities_data if amenities_data is not None else []
        
        counts = {}
        for item in safe_amenities:
            if isinstance(item, dict):
                atype = item.get("tags", {}).get("amenity", "unknown")
                counts[atype] = counts.get(atype, 0) + 1
            
        return f"Amenities count within 2km: {json.dumps(counts)}"
        
    @tool
    def check_flood_zone() -> str:
        """Use this tool to check the flood risk and zone status."""
        data = state.rawdata.get("risks", {}).get("flood_zone", {})
        safe_data = data if data is not None else {}
        return json.dumps(safe_data)[:500]

    tools = [get_census, get_amenities, check_flood_zone]
    tool_map = {t.name: t for t in tools}
    
    try:
        llm = get_llm(TOOL_CALLING_FALLBACK).bind_tools(tools)
        messages = [
            SystemMessage(content=f"You are an analytical Indian Real Estate expert advising a {user_type}. Use tools to extract data, then write a factual 3-sentence neighborhood summary. Do not invent information."),
            HumanMessage(content=f"Please analyze the neighborhood and generate a summary for PIN {state.pincode}.")
        ]
        
        response = llm.invoke(messages)
        messages.append(response)
        
        if response.tool_calls:
            for tool_call in response.tool_calls:
                tool_func = tool_map[tool_call["name"]]
                tool_output = tool_func.invoke(tool_call["args"])
                messages.append(ToolMessage(content=tool_output, tool_call_id=tool_call["id"]))
            
            final_response = llm.invoke(messages)
            state.aisummary = final_response.content.strip()
        else:
            state.aisummary = response.content.strip()
            
    except Exception as e:
        logger.error(f"Tool-Augmented Synthesis failed: {str(e)}")
        state.aisummary = "Synthesis generation failed due to an API processing error."
        
    return state

def assess_risk_node(state: AgentState) -> AgentState:
    logger.info("Executing Risk Assessment Node...")
    user_type = state.usercriteria.get("investment_type", "general buyer") if state.usercriteria else "general buyer"
    
    risk_data = state.rawdata.get('risks', {})
    safe_risk_data = risk_data if risk_data is not None else {}
    
    prompt = f"""
    Analyze the following risk data (Flood, AQI, Crime).
    Extract and prioritize the top 3 specific concerns for a {user_type}. Explain why each matters briefly.
    DATA: {json.dumps(safe_risk_data)[:1500]}
    """
    
    try:
        result: RiskResult = invoke_with_fallback(RISK_MODEL, prompt, RiskResult)
        state.riskflags.extend(result.top_risks)
    except Exception as e:
        logger.error(f"Risk Assessment failed: {str(e)}")
        state.riskflags.append("Could not assess specific risks due to processing error.")
    return state

def recommend_node(state: AgentState) -> AgentState:
    logger.info("Executing Recommendation Node...")
    
    prompt = f"""
    Based on the following summary and risks, provide a recommendation.
    SUMMARY: {state.aisummary}
    RISKS: {state.riskflags}
    USER CRITERIA: {state.usercriteria}
    
    Output exactly: (1) Suitability score 1-10, (2) 'Good for X, not for Y', (3) One-line justification.
    """
    
    try:
        result: RecommendationResult = invoke_with_fallback(RECOMMENDATION_MODEL, prompt, RecommendationResult)
        state.recommendation = f"**Score: {result.suitability_score}/10**. {result.good_for}. *Justification*: {result.justification}"
    except Exception as e:
        logger.error(f"Recommendation failed: {str(e)}")
        state.recommendation = "Recommendation unavailable at this time."
    return state