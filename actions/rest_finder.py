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
    max_results: int = 3,
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
    import math
    import requests

    # bounding box: roughly radius_km degrees offset
    deg_offset = radius_km / 111.0
    viewbox = (
        f"{longitude - deg_offset},{latitude + deg_offset},"
        f"{longitude + deg_offset},{latitude - deg_offset}"
    )

    results = []
    # query each stop type separately so we get a useful mix
    for amenity in ("rest_area", "fuel", "parking"):
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": amenity,
                "format": "json",
                "limit": max_results,
                "bounded": 1,
                "viewbox": viewbox,
            },
            headers={"User-Agent": "SafeShift/1.0"},
            timeout=5,
        )
        if resp.status_code != 200:
            continue
        for place in resp.json():
            lat2 = float(place["lat"])
            lon2 = float(place["lon"])
            # haversine distance
            dlat = math.radians(lat2 - latitude)
            dlon = math.radians(lon2 - longitude)
            a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(latitude)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
            dist_km = 6371 * 2 * math.asin(math.sqrt(a))
            results.append({
                "name": place.get("display_name", "Unknown").split(",")[0],
                "distance_km": round(dist_km, 1),
                "type": amenity,
            })

    results.sort(key=lambda x: x["distance_km"])
    return results[:max_results]


def format_stop_list(stops: list) -> str:
    """Format stop list into a human-readable string for display or TTS.

    Args:
        stops: list from find_nearby_stops()

    Returns:
        Formatted string, e.g. "1. Flying J (2.3 km)  2. Rest Area 44 (5.1 km)"
    """
    if not stops:
        return "No nearby stops found."
    return "  ".join(
        f"{i + 1}. {s['name']} ({s['distance_km']} km)"
        for i, s in enumerate(stops)
    )
