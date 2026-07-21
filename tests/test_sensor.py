"""Tests for the sensor platform."""
from __future__ import annotations

from unittest.mock import patch


async def _setup_integration(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


async def test_list_sensor_state_is_unchecked_count(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    state = hass.states.get("sensor.shopping_list")
    assert state is not None
    assert state.state == "1"
    assert state.attributes["item_count"] == 2
    assert state.attributes["checked_items"] == 1
    assert state.attributes["unchecked_items"] == 1
    assert state.attributes["color"] == "white"


async def test_note_sensor_state_is_item_count(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    state = hass.states.get("sensor.ideas")
    assert state is not None
    # Plain notes have no items, so item_count is 0.
    assert state.state == "0"
