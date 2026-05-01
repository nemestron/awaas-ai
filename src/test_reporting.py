import asyncio
import os
import sys
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dynamically inject project root into sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the fully encapsulated graph engine
from src.graph_engine import run_awaas_analysis

async def main():
    test_pin = "560034"
    reports_dir = os.path.join(project_root, "reports")
    pdf_path = os.path.join(reports_dir, f"test_{test_pin}.pdf")
    
    print(f"\n================ STARTING REPORT ENGINE TEST ================")
    print(f"Target PIN: {test_pin}")
    
    start_time = time.time()
    
    try:
        print("Invoking LangGraph Engine (Data + Synthesis + Reporting)...")
        # Step 1: Execute the encapsulated autonomous flow
        final_state = await run_awaas_analysis(test_pin, user_criteria={"investment_type": "rental"})
        
        # Step 2: Verify and write the PDF bytes to disk
        if final_state.get("report_generated") and final_state.get("pdf_bytes"):
            print(f"Writing PDF artifacts to {pdf_path}...")
            with open(pdf_path, "wb") as f:
                f.write(final_state["pdf_bytes"])
            
            print("\n================ REPORT GENERATION SUCCESS ================")
            print(f"File Saved: {pdf_path}")
            print(f"File Size: {os.path.getsize(pdf_path)} bytes")
            
            # Step 3: Verify Markdown generation
            md_preview = final_state.get("markdown_report", "")[:200]
            print(f"\nMARKDOWN PREVIEW (First 200 chars):\n{md_preview}...")
            print("===========================================================")
        else:
            print("\n[CRITICAL FAILURE] Pipeline completed, but report artifacts are missing.")
            
        execution_time = time.time() - start_time
        print(f"Total Pipeline + Reporting Latency: {execution_time:.2f} seconds")
        
    except ValueError as ve:
        if "GROQ_API_KEY" in str(ve):
            print(f"\n[DIAGNOSTIC HALT] {str(ve)}")
            print("Please add your actual Groq API key to the .env file to execute LLM nodes.")
        else:
            print(f"\n[CRITICAL FAILURE] {str(ve)}")
    except Exception as e:
        print(f"\n[CRITICAL FAILURE] Test execution halted: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())