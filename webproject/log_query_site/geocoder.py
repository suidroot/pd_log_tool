import re
import requests
from typing import Optional, Tuple

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_HEADERS = {"User-Agent": "PWM-Police-Log-DB/1.0 (locutus@the-collective.net)"}


class GeocoderUnavailable(Exception):
    """Raised on transient network errors — task should retry."""


class GeocoderRateLimited(Exception):
    """Raised on HTTP 429 — task should retry once with a long delay then give up."""


def _normalize_address(address: str) -> str:
    # Strip sub-unit suffix (e.g. "134 Congress St,Ste 1" → "134 Congress St")
    address = re.split(r",", address, maxsplit=1)[0].strip()
    return address


def geocode_address(address: str, city: str = "Portland", state: str = "ME") -> Optional[Tuple[float, float]]:
    """Return (lat, lon), None if address not found, or raise on transient/rate-limit errors.

    Handles intersections (e.g. "Riverside St/Forest Ave") and sub-unit suffixes
    (e.g. "134 Congress St,Ste 1") by normalizing the address before querying.
    """
    street = _normalize_address(address)
    query = f"{street}, {city}, {state}"
    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1, "countrycodes": "us"},
            headers=_HEADERS,
            timeout=10,
        )
        if resp.status_code == 429:
            raise GeocoderRateLimited("Nominatim rate limit exceeded")
        resp.raise_for_status()
        results = resp.json()
        return (float(results[0]["lat"]), float(results[0]["lon"])) if results else None
    except (GeocoderUnavailable, GeocoderRateLimited):
        raise
    except requests.RequestException as e:
        raise GeocoderUnavailable(str(e))
