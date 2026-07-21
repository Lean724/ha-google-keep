"""Tests for the integration setup/unload lifecycle."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState

from custom_components.google_keep.exceptions import (
    GoogleKeepAuthError,
    GoogleKeepConnectionError,
)


async def test_setup_entry_success(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED


async def test_setup_entry_auth_failure_triggers_reauth(
    hass, mock_config_entry, mock_api
):
    mock_api.async_login.side_effect = GoogleKeepAuthError("bad token")
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_setup_entry_connection_error_retries(hass, mock_config_entry, mock_api):
    mock_api.async_login.side_effect = GoogleKeepConnectionError("offline")
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert not await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload_entry(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()

        assert await hass.config_entries.async_unload(mock_config_entry.entry_id)
        await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.NOT_LOADED
    mock_api.async_close.assert_called_once()
