"""Exceptions for the Google Keep integration."""
from __future__ import annotations

from homeassistant.exceptions import HomeAssistantError


class GoogleKeepError(HomeAssistantError):
    """Base exception for the Google Keep integration."""


class GoogleKeepAuthError(GoogleKeepError):
    """Raised when authentication with Google fails (bad credentials)."""


class GoogleKeepTokenExpiredError(GoogleKeepAuthError):
    """Raised when the stored master token is no longer valid."""


class GoogleKeepConnectionError(GoogleKeepError):
    """Raised when the integration cannot reach Google's servers."""


class GoogleKeepRateLimitError(GoogleKeepError):
    """Raised when Google throttles/rate-limits our requests."""


class GoogleKeepUpstreamChangedError(GoogleKeepError):
    """Raised when gkeepapi fails in a way that suggests Google changed their API."""


class GoogleKeepNotFoundError(GoogleKeepError):
    """Raised when a note/list/item referenced by id can no longer be found."""
