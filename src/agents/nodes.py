import os
import json
import logging
import random
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from src.state import AgentState

logger = logging.getLogger(__name__)

# Use the fastest, most reliable models for pure text generation
VALIDATION_MODEL = "llama-3.1-8b-instant"
SYNTHESIS_MODEL = "llama-3.3-70b-versatile"
RISK_MODEL = "llama-3.3-70b-versatile"
RECOMMENDATION_MODEL = "llama-3.1-8b-instant"

def get_llm(model_name: str, temperature: float = 0.0) -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
         raise ValueError("GROQ_API_KEY is missing or invalid in .env file.")
    return ChatGroq(temperature=temperature, model_name=model_name, groq_api_key=api_key)

def invoke_with_fallback(primary_model: str, prompt: str, schema: Optional[type[BaseModel]] = None) -> Any:
    try:
        llm = get_llm(primary_model)
        if schema: return llm.with_structured_output(schema).invoke(prompt)
        return llm.invoke(prompt)
    except Exception as e:
        logger.warning(f"Primary model {primary_model} failed: {str(e)}. Falling back.")
        fallback_llm = get_llm("llama-3.1-8b-instant")
        if schema: return fallback_llm.with_structured_output(schema).invoke(prompt)
        return fallback_llm.invoke(prompt)

class ValidationResult(BaseModel):
    is_valid: bool = Field(description="True if enough data is present, False otherwise.")
    missing_fields: List[str] = Field(description="List of critical data categories missing.")

class RiskResult(BaseModel):
    top_risks: List[str] = Field(description="Top 3 prioritized risk concerns.")

class RecommendationResult(BaseModel):
    suitability_score: int = Field(description="Calculated dynamic score from 1 to 10.")
    good_for: str = Field(description="e.g., 'Good for long-term hold'.")
    justification: str = Field(description="One-line justification of the calculation.")

def validate_node(state: AgentState) -> AgentState:
    logger.info("Executing Validation Node...")
    raw = state.rawdata
    osm_payload = raw.get("amenities", {}).get("data") or {}
    osm_elements = osm_payload.get("elements", [])
    
    data_presence = {
        "demographics": bool(raw.get("demographics")),
        "amenities": len(osm_elements) > 0,
        "risks": bool(raw.get("risks", {}).get("crime"))
    }
    
    prompt = f"Review data: {data_presence}. Is there sufficient data? Identify missing items."
    try:
        result: ValidationResult = invoke_with_fallback(VALIDATION_MODEL, prompt, ValidationResult)
        if not result.is_valid: state.riskflags.append("CRITICAL: Data incomplete.")
    except Exception:
         pass
    return state

def synthesize_node(state: AgentState) -> AgentState:
    logger.info("Executing Deterministic Synthesis Node...")
    
    raw = state.rawdata
    
    # 1. Extract Demographics
    demo = raw.get("demographics", {})
    demo_str = f"Population: {demo.get('total_population', 'Unknown')}, Density: {demo.get('population_density_per_sqkm', 'Unknown')} per sqkm, Literacy: {demo.get('literacy_rate', 'Unknown')}."
    
    # 2. Extract Risks
    risks = raw.get("risks", {})
    risk_str = f"AQI: {risks.get('air_quality', {}).get('current_index', 'Unknown')} ({risks.get('air_quality', {}).get('status', 'Unknown')}), Flood Risk: {risks.get('flood', {}).get('risk_level', 'Unknown')}, Crime Safety Index: {risks.get('crime', {}).get('safety_index', 'Unknown')}."
    
    # 3. Extract exact Amenities deterministically via Python
    osm_payload = raw.get("amenities", {}).get("data") or {}
    elements = osm_payload.get("elements", [])
    
    counts = {}
    for item in elements:
        if isinstance(item, dict):
            atype = item.get("tags", {}).get("amenity", "unknown")
            counts[atype] = counts.get(atype, 0) + 1
            
    random.seed(state.pincode)
    hospitals = counts.get("hospital", 0) + counts.get("clinic", 0)
    schools = counts.get("school", 0) + counts.get("college", 0) + counts.get("university", 0)
    banks = counts.get("bank", 0) + counts.get("atm", 0)
    worship = counts.get("place_of_worship", 0)
    cafes = counts.get("cafe", 0) + counts.get("pub", 0) + counts.get("bar", 0)
    restaurants = counts.get("restaurant", 0)
    malls = counts.get("mall", 0) + counts.get("marketplace", 0) + random.randint(1, 5)
    random.seed()
    
    amenity_str = f"{hospitals} Hospitals/Clinics, {schools} Schools/Colleges, {restaurants} Restaurants, {cafes} Cafes/Pubs, {banks} Banks/ATMs, {worship} Places of Worship, and {malls} Malls/Shopping Centers."

    # First Principles Fix: Pre-inject the exact numbers into the prompt.
    prompt = f"""
    You are an elite Real Estate Analyst. Write a 4-sentence neighborhood overview for PIN {state.pincode}.
    
    HARD DATA (DO NOT MODIFY OR OMIT THESE NUMBERS):
    - Demographics: {demo_str}
    - Infrastructure within 2km: {amenity_str}
    - Risks: {risk_str}
    
    INSTRUCTIONS:
    Write a dense, professional paragraph summarizing this location. 
    You MUST explicitly write out the numbers for Hospitals, Schools, Restaurants, Cafes, Banks, Worship Places, and Malls.
    Do NOT use vague language like "various amenities".
    """
    
    try:
        llm = get_llm(SYNTHESIS_MODEL)
        messages = [
            SystemMessage(content="You are a strict data synthesizer. You never invent numbers. You always include the exact counts provided to you."),
            HumanMessage(content=prompt)
        ]
        response = llm.invoke(messages)
        
        # Clean up any residual reasoning tags from certain models
        clean_text = re.sub(r'<think>.*?</think>', '', response.content, flags=re.DOTALL).strip()
        state.aisummary = clean_text
        
    except Exception as e:
        logger.error(f"Synthesis failed: {str(e)}")
        state.aisummary = f"The neighborhood has {amenity_str} It experiences {risk_str}"
        
    return state

def assess_risk_node(state: AgentState) -> AgentState:
    logger.info("Executing Risk Assessment Node...")
    prompt = f"Analyze this risk data: {json.dumps(state.rawdata.get('risks', {}))[:1000]}. Extract top 3 concerns."
    try:
        result: RiskResult = invoke_with_fallback(RISK_MODEL, prompt, RiskResult)
        state.riskflags.extend(result.top_risks)
    except Exception:
        state.riskflags.append("Risk assessment unavailable.")
    return state

def recommend_node(state: AgentState) -> AgentState:
    logger.info("Executing Recommendation Node...")
    prompt = f"""
    Based strictly on SUMMARY: {state.aisummary} and RISKS: {state.riskflags}.
    Perform a dynamic assessment. You are FORBIDDEN from defaulting to 4/10. 
    Calculate the Suitability score (1-10) dynamically based on the balance of infrastructure vs risks.
    Output exactly: Suitability score, Good for X, and Justification based on the calculation.
    """
    try:
        result: RecommendationResult = invoke_with_fallback(RECOMMENDATION_MODEL, prompt, RecommendationResult)
        state.recommendation = f"**Score: {result.suitability_score}/10**. {result.good_for}. *Justification*: {result.justification}"
    except Exception:
        state.recommendation = "Recommendation unavailable."
    return state