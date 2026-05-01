import asyncio
import time
import json
import sys
import os
from dotenv import load_dotenv

# First Principles Fix 1: Load environment variables BEFORE any custom imports.
load_dotenv()

# First Principles Fix 2: Dynamically inject project root into sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the fully encapsulated graph engine
from src.graph_engine import run_awaas_analysis

async def main():
    test_pin = "560034"
    print(f"\n================ STARTING AUTONOMOUS GRAPH TEST ================")
    print(f"Target PIN: {test_pin}")
    
    start_time = time.time()
    
    try:
        # Step 1: Execute the encapsulated autonomous flow
        print("Invoking LangGraph Engine...")
        final_state_dict = await run_awaas_analysis(test_pin, user_criteria={"investment_type": "rental"})
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("\n================ FINAL GRAPH OUTPUT ================")
        print(f"[{test_pin} - {final_state_dict.get('location', {}).get('ward_id', 'Unknown')}]\n")
        print(f"AI SUMMARY:\n{final_state_dict.get('aisummary', 'N/A')}\n")
        print(f"RISK FLAGS:\n{json.dumps(final_state_dict.get('riskflags', []), indent=2)}\n")
        print(f"RECOMMENDATION:\n{final_state_dict.get('recommendation', 'N/A')}\n")
        print(f"SOURCE LINKS:\n{json.dumps(final_state_dict.get('sourcelinks', []), indent=2)}\n")
        print("====================================================")
        print(f"Total Graph Latency: {execution_time:.2f} seconds")
        
    except ValueError as ve:
        if "GROQ_API_KEY" in str(ve):
            print(f"\n[DIAGNOSTIC HALT] {str(ve)}")
            print("Please add your actual Groq API key to the .env file to execute LLM nodes.")
        else:
            print(f"\n[CRITICAL FAILURE] {str(ve)}")
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Graph execution halted: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())