"""Reverse geocoding service to convert coordinates to human-readable addresses."""

import httpx
import structlog
from functools import lru_cache

logger = structlog.get_logger()

# Nominatim requires a User-Agent header identifying the application
USER_AGENT = "FrontierAudioMVP/1.0"

# Cache size for geocoding results (in-memory LRU cache)
CACHE_SIZE = 1000


class GeocodingService:
    """
    Service for reverse geocoding using OpenStreetMap's Nominatim API.

    Nominatim is free to use with reasonable usage (max 1 req/second).
    We use caching to minimize API calls.
    """

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            timeout=5.0,
            headers={"User-Agent": USER_AGENT},
        )
        # In-memory cache for geocoding results
        self._cache: dict[tuple[float, float], str | None] = {}

    def _round_coords(self, lat: float, lon: float) -> tuple[float, float]:
        """Round coordinates to ~11m precision (4 decimal places) for caching."""
        return (round(lat, 4), round(lon, 4))

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
    ) -> str | None:
        """
        Convert latitude/longitude to a human-readable location name.

        Returns a formatted address string, or None if geocoding fails.
        Uses caching to minimize API calls.

        Args:
            latitude: GPS latitude (-90 to 90)
            longitude: GPS longitude (-180 to 180)

        Returns:
            Location string like "123 Main St, San Francisco, CA" or None
        """
        # Round coordinates for cache key (nearby points share cache)
        cache_key = self._round_coords(latitude, longitude)

        # Check cache first
        if cache_key in self._cache:
            logger.debug("Geocoding cache hit", lat=latitude, lon=longitude)
            return self._cache[cache_key]

        try:
            # Call Nominatim API
            response = await self._client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "addressdetails": 1,
                    "zoom": 18,  # Building-level detail
                },
            )
            response.raise_for_status()
            data = response.json()

            # Extract a concise location name
            location_name = self._format_location(data)

            # Cache the result (even None results to avoid repeated failed lookups)
            if len(self._cache) < CACHE_SIZE:
                self._cache[cache_key] = location_name

            logger.info(
                "Reverse geocoded location",
                lat=latitude,
                lon=longitude,
                location=location_name,
            )
            return location_name

        except httpx.HTTPStatusError as e:
            logger.warning(
                "Geocoding HTTP error",
                lat=latitude,
                lon=longitude,
                status=e.response.status_code,
            )
            return None
        except httpx.RequestError as e:
            logger.warning(
                "Geocoding request error",
                lat=latitude,
                lon=longitude,
                error=str(e),
            )
            return None
        except Exception as e:
            logger.warning(
                "Geocoding failed",
                lat=latitude,
                lon=longitude,
                error=str(e),
            )
            return None

    def _format_location(self, data: dict) -> str | None:
        """Format Nominatim response into a concise location string."""
        if "error" in data:
            return None

        address = data.get("address", {})

        # Build location parts from most to least specific
        parts = []

        # Street address (house number + road)
        house_number = address.get("house_number", "")
        road = address.get("road", "")
        if road:
            if house_number:
                parts.append(f"{house_number} {road}")
            else:
                parts.append(road)

        # Neighborhood/suburb (if no road)
        if not parts:
            for key in ["neighbourhood", "suburb", "hamlet", "village"]:
                if key in address:
                    parts.append(address[key])
                    break

        # City
        city = address.get("city") or address.get("town") or address.get("municipality")
        if city:
            parts.append(city)

        # State (abbreviated if USA)
        state = address.get("state")
        country_code = address.get("country_code", "").upper()
        if state:
            # Use state abbreviation for USA
            if country_code == "US":
                state = self._abbreviate_us_state(state)
            parts.append(state)

        if not parts:
            # Fallback to display_name if we couldn't parse address
            display_name = data.get("display_name", "")
            if display_name:
                # Take first few parts of display_name
                return ", ".join(display_name.split(", ")[:3])
            return None

        return ", ".join(parts)

    def _abbreviate_us_state(self, state: str) -> str:
        """Convert US state names to abbreviations."""
        abbreviations = {
            "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR",
            "California": "CA", "Colorado": "CO", "Connecticut": "CT", "Delaware": "DE",
            "Florida": "FL", "Georgia": "GA", "Hawaii": "HI", "Idaho": "ID",
            "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
            "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD",
            "Massachusetts": "MA", "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS",
            "Missouri": "MO", "Montana": "MT", "Nebraska": "NE", "Nevada": "NV",
            "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY",
            "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
            "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
            "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT",
            "Vermont": "VT", "Virginia": "VA", "Washington": "WA", "West Virginia": "WV",
            "Wisconsin": "WI", "Wyoming": "WY", "District of Columbia": "DC",
        }
        return abbreviations.get(state, state)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# Singleton instance
_geocoding_service: GeocodingService | None = None


def get_geocoding_service() -> GeocodingService:
    """Get the singleton GeocodingService instance."""
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service
