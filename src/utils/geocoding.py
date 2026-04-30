import os
import logging
import requests
from typing import Dict, Any, Optional
from diskcache import Cache
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# Initialize local cache for geocoding to prevent rate limit hits
# Cache expires in 30 days (2592000 seconds)
# Path is relative to the execution root (C:\Projects\Awaas AI\awaas)
CACHE_DIR = os.path.join(os.getcwd(), "local_db", "geocode_cache")
cache = Cache(CACHE_DIR)

USER_AGENT = "AwaasAI/1.0 (Research Pipeline)"
HEADERS = {"User-Agent": USER_AGENT}

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_from_nominatim(query: str) -> Optional[Dict[str, Any]]:
    """Resolves location using OpenStreetMap Nominatim API."""
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{query}, India",
        "format": "json",
        "addressdetails": 1,
        "limit": 1
    }
    
    response = requests.get(url, headers=HEADERS, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    if not data:
        return None
        
    result = data[0]
    address = result.get("address", {})
    
    # Safely extract Indian administrative hierarchy mapping
    return {
        "pincode": address.get("postcode", query if query.isdigit() else "Unknown"),
        "ward_id": address.get("suburb", address.get("neighbourhood", "Unknown")),
        "district": address.get("state_district", address.get("county", "Unknown")),
        "state": address.get("state", "Unknown"),
        "lat": float(result.get("lat")),
        "lon": float(result.get("lon")),
        "source_url": response.url
    }

def resolve_location(location_query: str) -> Dict[str, Any]:
    """
    Resolves a PIN code or area name to a structured location object.
    Uses local diskcache to bypass network requests for known queries.
    """
    # Normalize query for cache key consistency
    cache_key = f"geocode_{str(location_query).strip().lower()}"
    
    if cache_key in cache:
        logger.info(f"Cache hit for location: {location_query}")
        return cache[cache_key]
        
    logger.info(f"Cache miss. Fetching location via API: {location_query}")
    
    try:
        # Extensible architecture: Mappls fallback can be injected here.
        # Currently utilizing Nominatim for guaranteed open-data compliance.
        location_data = fetch_from_nominatim(str(location_query))
        
        if not location_data:
            raise ValueError(f"Could not resolve location for query: {location_query}")
            
        # Store successful resolution in cache
        cache.set(cache_key, location_data, expire=2592000)
        return location_data
        
    except Exception as e:
        logger.error(f"Geocoding failed for {location_query}: {str(e)}")
        raise