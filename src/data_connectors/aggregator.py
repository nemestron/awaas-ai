import asyncio
import logging
from typing import Dict, Any

# Import the synchronous connector functions built in Step 8
from src.data_connectors.indian_api_client import (
    fetch_census_demographics,
    fetch_crime_stats,
    fetch_osm_amenities,
    fetch_cpcb_aqi,
    fetch_flood_risk
)

logger = logging.getLogger(__name__)

async def safe_fetch(task_name: str, func, *args, **kwargs) -> Dict[str, Any]:
    """
    Wraps a synchronous I/O function in a thread and traps any exceptions 
    to ensure partial data survival during parallel execution.
    """
    try:
        # Offload the blocking requests call to a thread
        result = await asyncio.to_thread(func, *args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"Connector failure [{task_name}]: {str(e)}")
        return {
            "source_url": "data_unavailable",
            "data": None,
            "error": str(e)
        }

async def aggregate_neighborhood_data(location: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes all external API connectors concurrently.
    Accepts the structured location object from the geocoding utility.
    """
    pincode = location.get("pincode")
    ward_id = location.get("ward_id")
    district = location.get("district")
    lat = location.get("lat")
    lon = location.get("lon")
    
    logger.info(f"Initiating parallel data fetch for PIN: {pincode}, District: {district}")

    # Prepare async tasks
    tasks = [
        safe_fetch("demographics", fetch_census_demographics, ward_id, pincode),
        safe_fetch("crime", fetch_crime_stats, district),
        safe_fetch("amenities", fetch_osm_amenities, lat, lon),
        safe_fetch("aqi", fetch_cpcb_aqi, lat, lon),
        safe_fetch("flood", fetch_flood_risk, lat, lon)
    ]

    # Execute all tasks concurrently
    results = await asyncio.gather(*tasks)
    
    # Unpack results in exact order of execution
    demo_res, crime_res, amen_res, aqi_res, flood_res = results

    # Construct unified state dictionary
    aggregated_data = {
        "demographics": demo_res,
        "amenities": amen_res,
        "risks": {
            "crime": crime_res,
            "air_quality": aqi_res,
            "flood_zone": flood_res
        },
        "connectivity": {
            "status": "data_unavailable", # Placeholder for future transit APIs
            "source_url": "N/A"
        }
    }
    
    logger.info("Parallel data aggregation complete.")
    return aggregated_data