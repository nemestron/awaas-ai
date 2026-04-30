import asyncio
import time
import json
import logging
import sys
import os
from dotenv import load_dotenv

# First Principles Fix 1: Load environment variables immediately
load_dotenv()

# First Principles Fix 2: Dynamically inject project root into sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import Data Layer
from src.utils.geocoding import resolve_location
from src.data_connectors.aggregator import aggregate_neighborhood_data

# Import Cognitive Layer
from src.state import AgentState
from src.agents.nodes import validate_node, synthesize_node, assess_risk_node, recommend_node

# Suppress verbose dependency logging for clear output
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    test_pin = "560034"
    print(f"\n================ STARTING END-TO-END COGNITIVE TEST ================")
    print(f"Target PIN: {test_pin}")
    
    start_time = time.time()
    
    try:
        # --- PHASE 2: DATA ACQUISITION ---
        logger.info("Step 1: Executing Data Acquisition...")
        location = resolve_location(test_pin)
        raw_data = await aggregate_neighborhood_data(location)
        
        # --- PHASE 3: COGNITIVE PROCESSING ---
        logger.info("Step 2: Initializing AgentState...")
        state = AgentState(
            pincode=test_pin,
            location=location,
            rawdata=raw_data,
            usercriteria={"investment_type": "rental"}
        )
        
        logger.info("Step 3: Running Pipeline...")
        # Sequential Graph Simulation (pre-LangGraph)
        state = validate_node(state)
        state = synthesize_node(state)
        state = assess_risk_node(state)
        state = recommend_node(state)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("\n================ FINAL SYSTEM OUTPUT ================")
        print(f"[{test_pin} - {location.get('ward_id', 'Unknown')}]\n")
        print(f"AI SUMMARY:\n{state.aisummary}\n")
        print(f"RISK FLAGS:\n{json.dumps(state.riskflags, indent=2)}\n")
        print(f"RECOMMENDATION:\n{state.recommendation}\n")
        print("=====================================================")
        print(f"Total Latency (Data + AI): {execution_time:.2f} seconds")
        
    except ValueError as ve:
        if "GROQ_API_KEY" in str(ve):
            print(f"\n[DIAGNOSTIC HALT] {str(ve)}")
            print("Please add your actual Groq API key to the .env file to execute LLM nodes.")
        else:
            print(f"\n[CRITICAL FAILURE] {str(ve)}")
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Pipeline execution halted: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())