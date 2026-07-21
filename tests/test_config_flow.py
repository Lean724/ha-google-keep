"""Tests for the Google Keep config flow."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from custom_components.google_keep.const import DOMAIN
from custom_components.google_keep.exceptions import (
    GoogleKeepAuthError,
    GoogleKeepConnectionError,
)


async def test_user_flow_success(hass, mock_api):
    """A valid email + password should create a config entry."""
    with patch(
        "custom_components.google_keep.config_flow.GoogleKeepAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] == FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"email": "user@example.com", "password": "hunter2"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"]["email"] == "user@example.com"
    assert "password" not in result["data"]
    assert result["data"]["master_token"] == "fake-master-token"


async def test_user_flow_invalid_auth(hass, mock_api):
    """Invalid credentials should show an invalid_auth error, not create an entry."""
    mock_api.async_test_credentials.side_effect = GoogleKeepAuthError("bad creds")
    with patch(
        "custom_components.google_keep.config_flow.GoogleKeepAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"email": "user@example.com", "password": "wrong"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "invalid_auth"


async def test_user_flow_cannot_connect(hass, mock_api):
    """Connection errors should show cannot_connect, not create an entry."""
    mock_api.async_test_credentials.side_effect = GoogleKeepConnectionError("no net")
    with patch(
        "custom_components.google_keep.config_flow.GoogleKeepAPI",
        return_value=mock_api,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"email": "user@example.com", "password": "hunter2"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "cannot_connect"


async def test_user_flow_missing_credentials(hass):
    """Neither password nor master token should trip validation before login."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"email": "user@example.com"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"] == "missing_credentials"


async def test_reauth_flow_success(hass, mock_config_entry, mock_api):
    """A successful reauth should update the stored token and reload."""
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.config_flow.GoogleKeepAPI",
        return_value=mock_api,
    ), patch(
        "custom_components.google_keep.async_setup_entry", return_value=True
    ):
        result = await mock_config_entry.start_reauth_flow(hass)
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "reauth_confirm"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"password": "new-password"}
        )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
