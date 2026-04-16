import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "PWM-Police-Log-DB/1.0 (locutus@the-collective.net)"}


def geocode_address(address: str, city: str = "Portland", state: str = "ME") -> tuple[float, float] | None:
    """Return (lat, lon) for the given address, or None if geocoding fails."""
    query = f"{address}, {city}, {state}"
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
            headers=_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    except Exception:
        pass
    return None
