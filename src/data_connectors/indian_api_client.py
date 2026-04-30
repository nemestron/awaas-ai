import os
import requests
import logging
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from requests.exceptions import RequestException, HTTPError

logger = logging.getLogger(__name__)

# Global Configurations
USER_AGENT = "AwaasAI/1.0 (Research Pipeline)"
DEFAULT_TIMEOUT = 5  # Aggressive timeout constraint (reduced from 10)
COMMON_HEADERS = {"User-Agent": USER_AGENT}

def is_retryable(exception: BaseException) -> bool:
    """
    Intelligent retry evaluator. 
    Never retry 4xx Client Errors (e.g., unauthorized, bad request).
    Only retry on network errors or 5xx Server Errors.
    """
    if isinstance(exception, HTTPError) and exception.response is not None:
        if 400 <= exception.response.status_code < 500:
            return False
    return isinstance(exception, RequestException)

# Retry Strategy: 2 attempts max, aggressive backoff, intelligent abort
def resilient_request() -> retry:
    return retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=1, max=3),
        retry=retry_if_exception(is_retryable),
        reraise=True
    )

@resilient_request()
def fetch_census_demographics(ward_id: str, pincode: str) -> Dict[str, Any]:
    """Fetches demographic data from Indian Data Project API (or equivalent open census data)."""
    base_url = "https://api.data.gov.in/resource/census_endpoint"
    api_key = os.getenv("OGD_API_KEY", "")
    params = {
        "api-key": api_key,
        "format": "json",
        "filters[pincode]": pincode
    }
    
    response = requests.get(base_url, headers=COMMON_HEADERS, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    return {
        "source_url": response.url,
        "data": response.json()
    }

@resilient_request()
def fetch_crime_stats(district: str) -> Dict[str, Any]:
    """Fetches NCRB crime statistics via OGD Platform India."""
    base_url = "https://api.data.gov.in/resource/ncrb_district_endpoint"
    api_key = os.getenv("OGD_API_KEY", "")
    params = {
        "api-key": api_key,
        "format": "json",
        "filters[district]": district
    }
    
    response = requests.get(base_url, headers=COMMON_HEADERS, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    return {
        "source_url": response.url,
        "data": response.json()
    }

@resilient_request()
def fetch_osm_amenities(lat: float, lon: float, radius_meters: int = 2000) -> Dict[str, Any]:
    """Fetches local amenities (schools, hospitals, markets) using OSM Overpass API."""
    url = "https://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    (
      node["amenity"~"school|hospital|marketplace"](around:{radius_meters},{lat},{lon});
    );
    out center;
    """
    
    response = requests.post(url, headers=COMMON_HEADERS, data={"data": query}, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    return {
        "source_url": url,
        "data": response.json().get("elements", [])
    }

@resilient_request()
def fetch_cpcb_aqi(lat: float, lon: float) -> Dict[str, Any]:
    """Fetches Air Quality Index data via CPCB or equivalent open data source."""
    base_url = "https://api.data.gov.in/resource/cpcb_aqi_endpoint"
    api_key = os.getenv("OGD_API_KEY", "")
    params = {
        "api-key": api_key,
        "format": "json"
    }
    
    response = requests.get(base_url, headers=COMMON_HEADERS, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    return {
        "source_url": response.url,
        "data": response.json()
    }

@resilient_request()
def fetch_flood_risk(lat: float, lon: float) -> Dict[str, Any]:
    """Checks flood zone status using India Flood Atlas API or Bhuvan endpoints."""
    base_url = "https://bhuvan-app1.nrsc.gov.in/api/flood_atlas_endpoint"
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json"
    }
    
    response = requests.get(base_url, headers=COMMON_HEADERS, params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    
    return {
        "source_url": response.url,
        "data": response.json()
    }