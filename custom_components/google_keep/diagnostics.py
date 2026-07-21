"""Diagnostics support for the Google Keep integration.

Never includes passwords, master tokens, cookies, headers, or any other
credential material - only counts and non-sensitive metadata.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import GoogleKeepConfigEntry
from .const import CONF_DEVICE_ID, CONF_MASTER_TOKEN

TO_REDACT = {
    "password",
    CONF_MASTER_TOKEN,
    CONF_DEVICE_ID,
    "email",
    "cookies",
    "headers",
    "auth",
    "authorization",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: GoogleKeepConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator = entry.runtime_data
    data = coordinator.data or {}

    lists_summary = [
        {
            "id": "REDACTED",
            "is_list": node.is_list,
            "item_count": node.item_count,
            "archived": node.archived,
            "trashed": node.trashed,
            "color": node.color,
            "label_count": len(node.labels),
        }
        for node in data.values()
    ]

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval": str(coordinator.update_interval),
            "note_count": len(data),
        },
        "notes_summary": lists_summary,
    }
