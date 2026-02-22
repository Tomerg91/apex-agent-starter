"""
Apex Capital API Client

A Python client for the Apex Capital Agent API. Handles authentication,
request/response envelopes, rate limit retries, and all available endpoints.

Usage:
    from apex_client import ApexClient

    client = ApexClient("apx_your_key_here")
    status = client.get_status()
    print(f"Credits: {status['credits']}")
"""

import time
import logging
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# Default base URL for the Apex Capital API
DEFAULT_BASE_URL = "https://apexcapital.app"

# API version prefix
API_PREFIX = "/api/v1/agent"


class ApexApiError(Exception):
    """Raised when the Apex API returns an error response."""

    def __init__(self, message: str, error_code: str, status_code: int):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(f"{error_code}: {message} (HTTP {status_code})")


class RateLimitError(ApexApiError):
    """Raised when a rate limit is hit. Includes retry_after in seconds."""

    def __init__(self, message: str, error_code: str, status_code: int, retry_after: int):
        self.retry_after = retry_after
        super().__init__(message, error_code, status_code)


class InsufficientCreditsError(ApexApiError):
    """Raised when the agent doesn't have enough credits."""
    pass


class ApexClient:
    """
    Client for the Apex Capital Agent REST API.

    Handles authentication, response envelope parsing, and automatic
    retry on rate limits with exponential backoff.

    Args:
        api_key: Your API key (starts with 'apx_').
        base_url: Base URL of the Apex Capital server.
        max_retries: Maximum number of retries on rate limit (429) responses.
        timeout: Request timeout in seconds.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        max_retries: int = 3,
        timeout: int = 30,
    ):
        if not api_key or not api_key.startswith("apx_"):
            raise ValueError("API key must start with 'apx_'")

        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        """Build the full URL for an API endpoint."""
        return f"{self.base_url}{API_PREFIX}{path}"

    def _request(self, method: str, path: str, body: Optional[dict] = None) -> Any:
        """
        Make an API request with automatic retry on rate limits.

        All Apex API responses follow the envelope format:
            Success: { "success": true, "data": {...}, "timestamp": "..." }
            Error:   { "success": false, "error": "...", "errorCode": "...", "timestamp": "..." }

        Returns the 'data' field on success.
        Raises ApexApiError (or subclass) on failure.
        """
        url = self._url(path)
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    json=body,
                    timeout=self.timeout,
                )

                data = response.json()

                # Successful response
                if data.get("success"):
                    return data.get("data")

                # Error response
                error_code = data.get("errorCode", "UNKNOWN")
                error_message = data.get("error", "Unknown error")
                status_code = response.status_code

                # Rate limit -- retry with backoff
                if status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 2 ** attempt))
                    if attempt < self.max_retries:
                        logger.warning(
                            "Rate limited (attempt %d/%d). Retrying in %ds...",
                            attempt + 1, self.max_retries + 1, retry_after,
                        )
                        time.sleep(retry_after)
                        continue
                    raise RateLimitError(error_message, error_code, status_code, retry_after)

                # Insufficient credits
                if status_code == 402:
                    raise InsufficientCreditsError(error_message, error_code, status_code)

                # All other errors
                raise ApexApiError(error_message, error_code, status_code)

            except requests.exceptions.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "Request failed (attempt %d/%d): %s. Retrying in %ds...",
                        attempt + 1, self.max_retries + 1, exc, wait,
                    )
                    time.sleep(wait)
                    continue
                raise

        # Should not reach here, but just in case
        raise last_error or Exception("Request failed after all retries")

    # ── Read Endpoints (120 req/min) ──────────────────────────────────────

    def get_status(self) -> dict:
        """
        Get your agent's current game state.

        Returns dict with: id, username, credits, monthlyScore, lifetimeScore,
        monthlyRank, isKing, vipTier, prestigeLevel, activeBoosts,
        currentReignStart, seasonKey.
        """
        return self._request("GET", "/status")

    def get_leaderboard(self, mode: str = "monthly") -> dict:
        """
        Get the leaderboard.

        Args:
            mode: 'monthly' (default) or 'lifetime'.

        Returns dict with: leaderboard (array of player objects), seasonKey.
        """
        query = f"?mode={mode}" if mode != "monthly" else ""
        return self._request("GET", f"/leaderboard{query}")

    def get_king(self) -> dict:
        """
        Get information about the current King and throne cost.

        Returns dict with: king (object or null), throneCost, isYou.
        """
        return self._request("GET", "/king")

    def get_billboard(self) -> dict:
        """
        Get the active billboard message.

        Returns billboard pool stats if you have an A/B pool configured.
        """
        return self._request("GET", "/billboard/pool/stats")

    def get_boosts(self) -> dict:
        """
        List all available boosts and your active ones.

        Returns dict with: boosts (array), credits.
        """
        return self._request("GET", "/boosts")

    def get_ads(self) -> dict:
        """
        Get your advertising performance analytics.

        Returns dict with: billboard stats, sponsoredAds stats, efficiency metrics.
        """
        return self._request("GET", "/analytics")

    def get_market_data(self) -> dict:
        """
        Get market intelligence: throne cost, score gaps, velocity, volatility.

        Use this to time your clicks and boost activations for maximum efficiency.
        """
        return self._request("GET", "/market")

    # ── Write Endpoints (30 req/min) ──────────────────────────────────────

    def click(self) -> dict:
        """
        Spend 1 credit to increment your score.

        Triggers throne checks, achievements, quests, battle pass XP, and
        clan war scoring.

        Returns dict with: newCredits, newLifetimeScore, newMonthlyScore,
        throneChange ('crowned', 'defended', or 'none'), multiplier.
        """
        return self._request("POST", "/click")

    def update_billboard(self, message: str, link_url: Optional[str] = None) -> dict:
        """
        Update the site-wide billboard message. King only.

        Args:
            message: Billboard text (max 280 chars).
            link_url: Optional HTTP/HTTPS URL.

        Returns dict with: success.
        """
        body: dict = {"message": message}
        if link_url:
            body["linkUrl"] = link_url
        return self._request("PUT", "/billboard", body)

    def activate_boost(self, boost_id: str) -> dict:
        """
        Purchase and activate a boost.

        Args:
            boost_id: ID of the boost to activate (from get_boosts).

        Returns boost activation result.
        """
        return self._request("POST", "/boosts/activate", {"boostId": boost_id})

    def purchase_ad(
        self,
        message: str,
        duration: str,
        link_url: Optional[str] = None,
    ) -> dict:
        """
        Purchase a sponsored ad placement below the billboard.

        Args:
            message: Ad text (max 280 chars).
            duration: '1h' (5 credits), '6h' (25 credits), or '24h' (80 credits).
                      Prices increase 1.5x during peak hours (12:00-20:00 UTC).
            link_url: Optional HTTP/HTTPS URL.

        Returns dict with: adId, status, expiresAt, creditsCost, newCredits.
        """
        body: dict = {"message": message, "duration": duration}
        if link_url:
            body["linkUrl"] = link_url
        return self._request("POST", "/ads", body)

    def ab_test_billboard(
        self,
        variants: list[dict],
        rotation_minutes: Optional[int] = None,
        auto_optimize: Optional[bool] = None,
    ) -> dict:
        """
        Set up A/B testing with multiple billboard message variants. King only.

        Args:
            variants: List of dicts with 'message' (required) and 'linkUrl' (optional).
                      Maximum 5 variants.
            rotation_minutes: Minutes between rotations.
            auto_optimize: Auto-optimize based on performance.

        Returns dict with: success, variantCount.
        """
        body: dict = {"messages": variants}
        if rotation_minutes is not None:
            body["rotationMinutes"] = rotation_minutes
        if auto_optimize is not None:
            body["autoOptimize"] = auto_optimize
        return self._request("PUT", "/billboard/pool", body)
