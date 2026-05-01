import os
import asyncio
import logging
import requests
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

def fetch_url(url: str, name: str) -> dict:
    """Executes the HTTP GET request synchronously for the thread pool."""
    try:
        # User-Agent spoofing to prevent automated rejection by gov firewalls
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AwaasAI/1.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return {"data": response.json(), "source_url": url, "error": None}
    except Exception as e:
        logger.error(f"Connector failure [{name}]: {str(e)}")
        return {"data": None, "source_url": url, "error": str(e)}

async def aggregate_neighborhood_data(location: dict) -> dict:
    """
    Asynchronously aggregates data from multiple Indian open-data APIs.
    Dynamically injects the INDIAN_DATA_API_KEY into the request payloads.
    """
    logger.info("Initiating parallel data fetch...")
    
    # First Principles Fix: Explicitly load the user-defined API key
    api_key = os.getenv("INDIAN_DATA_API_KEY", "")
    
    district = location.get("district", "Unknown").replace(" ", "+")
    pin = location.get("pincode", "")
    lat = location.get("lat", "")
    lon = location.get("lon", "")
    
    # Construct URLs with the securely injected API key
    urls = {
        "demographics": f"https://api.data.gov.in/resource/census_endpoint?api-key={api_key}&format=json&filters[pincode]={pin}",
        "crime": f"https://api.data.gov.in/resource/ncrb_district_endpoint?api-key={api_key}&format=json&filters[district]={district}",
        "aqi": f"https://api.data.gov.in/resource/cpcb_aqi_endpoint?api-key={api_key}&format=json",
        "flood": f"https://bhuvan-app1.nrsc.gov.in/api/flood_atlas_endpoint?lat={lat}&lon={lon}&format=json"
    }
    
    # OpenStreetMap Overpass API does not require an API key
    osm_url = f"https://overpass-api.de/api/interpreter?data=[out:json];node(around:2000,{lat},{lon})[amenity];out;"
    urls["amenities"] = osm_url
    
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor(max_workers=5) as pool:
        tasks = {
            name: loop.run_in_executor(pool, fetch_url, url, name)
            for name, url in urls.items()
        }
        # Await all network calls in parallel to preserve the sub-15s SLA
        results = await asyncio.gather(*tasks.values())
        
    final_data = dict(zip(tasks.keys(), results))
    logger.info("Parallel data aggregation complete.")
    
    # Return mapped to the AgentState schema
    return {
        "demographics": final_data["demographics"],
        "risks": {
            "crime": final_data["crime"],
            "air_quality": final_data["aqi"],
            "flood_zone": final_data["flood"]
        },
        "amenities": final_data["amenities"],
        "connectivity": {}
    }