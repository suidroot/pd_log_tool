import re
import requests
from typing import Optional, Tuple

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
_HEADERS = {"User-Agent": "PWM-Police-Log-DB/1.0 (locutus@the-collective.net)"}

# Common US street suffix abbreviations → full names (for Overpass name matching)
_ABBREVS = {
    "St": "Street", "Ave": "Avenue", "Rd": "Road", "Dr": "Drive",
    "Ln": "Lane", "Blvd": "Boulevard", "Ct": "Court", "Pl": "Place",
    "Pkwy": "Parkway", "Hwy": "Highway", "Expy": "Expressway",
    "Cir": "Circle", "Ter": "Terrace", "Trl": "Trail", "Sq": "Square",
}


class GeocoderUnavailable(Exception):
    """Raised on transient network errors — task should retry."""


class GeocoderRateLimited(Exception):
    """Raised on HTTP 429 — task should retry once with a long delay then give up."""


def _normalize_address(address: str) -> str:
    # Strip sub-unit suffix (e.g. "134 Congress St,Ste 1" → "134 Congress St")
    return re.split(r",", address, maxsplit=1)[0].strip()


def _expand_abbrevs(street: str) -> str:
    """Expand common suffix abbreviations so they match OSM way names."""
    parts = street.split()
    return " ".join(_ABBREVS.get(p, p) for p in parts)


def _is_intersection(address: str) -> bool:
    return "/" in address


def _geocode_intersection(
    street1: str, street2: str, city: str, state: str
) -> Optional[Tuple[float, float]]:
    """Use Overpass API to find the node where two named streets intersect."""
    s1 = _expand_abbrevs(street1.strip())
    s2 = _expand_abbrevs(street2.strip())

    # Query: within Portland (admin_level 8 city inside the named state),
    # find nodes that are shared members of both named ways.
    query = f"""
[out:json][timeout:15];
area["name"="{state}"]["admin_level"="4"]->.state;
area["name"="{city}"]["admin_level"="8"](area.state)->.city;
way["name"="{s1}"](area.city)->.a;
way["name"="{s2}"](area.city)->.b;
node(w.a)(w.b);
out center 1;
"""
    try:
        resp = requests.post(
            OVERPASS_URL,
            data={"data": query},
            headers=_HEADERS,
            timeout=20,
        )
        if resp.status_code == 429:
            raise GeocoderRateLimited("Overpass rate limit exceeded")
        resp.raise_for_status()
        elements = resp.json().get("elements", [])
        if elements:
            node = elements[0]
            return (float(node["lat"]), float(node["lon"]))
        return None
    except (GeocoderUnavailable, GeocoderRateLimited):
        raise
    except requests.RequestException as e:
        raise GeocoderUnavailable(str(e))


def geocode_address(address: str, city: str = "Portland", state: str = "ME") -> Optional[Tuple[float, float]]:
    """Return (lat, lon), None if address not found, or raise on transient/rate-limit errors.

    Intersections (e.g. "Riverside St/Forest Ave") are resolved via the Overpass API.
    Sub-unit suffixes (e.g. "134 Congress St,Ste 1") are stripped before querying Nominatim.
    """
    street = _normalize_address(address)

    if _is_intersection(street):
        parts = street.split("/", 1)
        return _geocode_intersection(parts[0], parts[1], city, state)

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
