"""Rest stop / safe pull-over location finder using Nominatim (OpenStreetMap).

Queries Nominatim for nearby rest areas, petrol stations, and parking lots given
the driver's approximate location. Nominatim is free, requires no API key, and
retains no personal data — consistent with SafeShift's privacy-first design.

Called by actions/rest_break.py and also available as context for the Companion
Agent (agents/companion.py) when it wants to name a specific nearby stop.

Returns a list of (name, distance_km) tuples for the handler to present to the driver.

Owner: Emilio
"""
from typing import Optional


def find_nearby_stops(
    latitude: float,
    longitude: float,
    radius_km: int = 10,
    max_results: int = 3
) -> list:
    """Query Nominatim for nearby rest stops.

    Args:
        latitude: driver's approximate latitude
        longitude: driver's approximate longitude
        radius_km: search radius in kilometres
        max_results: maximum number of stops to return

    Returns:
        list of dicts: [{"name": str, "distance_km": float, "type": str}, ...]
    """
    raise NotImplementedError


def format_stop_list(stops: list) -> str:
    """Format stop list into a human-readable string for display or TTS.

    Args:
        stops: list from find_nearby_stops()

    Returns:
        Formatted string, e.g. "1. Flying J (2.3 km)  2. Rest Area 44 (5.1 km)"
    """
    raise NotImplementedError
