import asyncio
import time
import json
import logging
import sys
import os

# First Principles Fix: Dynamically inject project root into sys.path
# This guarantees absolute imports work regardless of the execution context.
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.utils.geocoding import resolve_location
from src.data_connectors.aggregator import aggregate_neighborhood_data

# Suppress verbose dependency logging for clear output
logging.basicConfig(level=logging.WARNING)

async def main():
    test_pin = "560034"
    print(f"Starting Data Pipeline Test for PIN: {test_pin}")
    
    start_time = time.time()
    
    try:
        # Step 1: Geocoding (Hits Nominatim or DiskCache)
        print("Resolving location coordinates...")
        location = resolve_location(test_pin)
        print(f"Location Resolved: {location.get('ward_id', 'Unknown')}, {location.get('district', 'Unknown')}")
        
        # Step 2: Parallel Data Aggregation
        print("Executing parallel data fetch across all connectors...")
        result = await aggregate_neighborhood_data(location)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("\n================ AGGREGATION RESULT ================")
        print(json.dumps(result, indent=2))
        print("====================================================")
        
        print(f"\nTotal Execution Time: {execution_time:.2f} seconds")
        
        # Performance Assertion
        if execution_time < 10:
            print("Performance Assessment: PASS (Under 10 seconds)")
        else:
            print("Performance Assessment: FAIL (Exceeded 10 seconds)")
            
    except Exception as e:
        print(f"CRITICAL FAILURE: Pipeline execution halted: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())