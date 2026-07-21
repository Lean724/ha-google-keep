"""Tests for GoogleKeepCoordinator."""
from __future__ import annotations

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.google_keep.const import CONF_SHOW_ARCHIVED
from custom_components.google_keep.coordinator import GoogleKeepCoordinator
from custom_components.google_keep.exceptions import (
    GoogleKeepConnectionError,
    GoogleKeepTokenExpiredError,
)


async def test_first_refresh_populates_data(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    await coordinator.async_config_entry_first_refresh()

    assert coordinator.last_update_success is True
    assert set(coordinator.data) == {"list-1", "note-1"}


async def test_archived_notes_filtered_by_default(hass, mock_config_entry, mock_api, sample_list_data):
    sample_list_data["list-1"].archived = True
    mock_api.async_sync.return_value = list(sample_list_data.values())
    mock_config_entry.add_to_hass(hass)
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    await coordinator.async_config_entry_first_refresh()

    assert "list-1" not in coordinator.data
    assert "note-1" in coordinator.data


async def test_archived_notes_shown_when_option_enabled(
    hass, mock_config_entry, mock_api, sample_list_data
):
    sample_list_data["list-1"].archived = True
    mock_api.async_sync.return_value = list(sample_list_data.values())
    mock_config_entry.add_to_hass(hass)
    hass.config_entries.async_update_entry(
        mock_config_entry, options={**mock_config_entry.options, CONF_SHOW_ARCHIVED: True}
    )
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    await coordinator.async_config_entry_first_refresh()

    assert "list-1" in coordinator.data


async def test_token_expired_raises_update_failed(hass, mock_config_entry, mock_api):
    mock_api.async_sync.side_effect = GoogleKeepTokenExpiredError("expired")
    mock_config_entry.add_to_hass(hass)
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_connection_error_raises_update_failed(hass, mock_config_entry, mock_api):
    mock_api.async_sync.side_effect = GoogleKeepConnectionError("offline")
    mock_config_entry.add_to_hass(hass)
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    await coordinator.async_refresh()

    assert coordinator.last_update_success is False


async def test_manual_interval_disables_polling(hass, mock_config_entry, mock_api):
    hass.config_entries.async_update_entry(
        mock_config_entry, options={"update_interval": 0}
    )
    mock_config_entry.add_to_hass(hass)
    coordinator = GoogleKeepCoordinator(hass, mock_config_entry, mock_api)

    assert coordinator.update_interval is None
