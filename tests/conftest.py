"""Shared fixtures for Google Keep integration tests."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.google_keep.api import KeepListData, KeepListItem
from custom_components.google_keep.const import (
    CONF_MASTER_TOKEN,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Make the custom_components/google_keep package discoverable in tests."""
    yield


@pytest.fixture
def mock_config_entry():
    """Return a MockConfigEntry-like object with sane defaults."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    return MockConfigEntry(
        domain=DOMAIN,
        title="user@example.com",
        data={
            "email": "user@example.com",
            CONF_MASTER_TOKEN: "fake-master-token",
            "device_id": "fake-device-id",
        },
        options={CONF_UPDATE_INTERVAL: 5},
        unique_id="user@example.com",
    )


@pytest.fixture
def sample_list_data() -> dict[str, KeepListData]:
    """A minimal sample of normalized Keep data: one checklist, one plain note."""
    checklist = KeepListData(
        id="list-1",
        title="Shopping list",
        color="white",
        archived=False,
        trashed=False,
        pinned=False,
        labels=["home"],
        is_list=True,
        items=[
            KeepListItem(id="item-1", text="Milk", checked=False),
            KeepListItem(id="item-2", text="Eggs", checked=True),
        ],
        timestamps={"created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z"},
    )
    note = KeepListData(
        id="note-1",
        title="Ideas",
        color="yellow",
        archived=False,
        trashed=False,
        pinned=False,
        labels=[],
        is_list=False,
        text="Some free text",
        timestamps={"created": "2026-01-01T00:00:00Z", "updated": "2026-01-01T00:00:00Z"},
    )
    return {"list-1": checklist, "note-1": note}


@pytest.fixture
def mock_api(sample_list_data):
    """A mocked GoogleKeepAPI with common methods stubbed out."""
    api = MagicMock()
    api.async_login = AsyncMock(return_value="fake-master-token")
    api.async_test_credentials = AsyncMock(return_value="fake-master-token")
    api.async_sync = AsyncMock(return_value=list(sample_list_data.values()))
    api.async_create_note = AsyncMock(return_value="new-note-id")
    api.async_create_checklist = AsyncMock(return_value="new-list-id")
    api.async_add_item = AsyncMock(return_value="new-item-id")
    api.async_remove_item = AsyncMock(return_value=None)
    api.async_set_item_checked = AsyncMock(return_value=None)
    api.async_set_archived = AsyncMock(return_value=None)
    api.async_set_trashed = AsyncMock(return_value=None)
    api.async_close = AsyncMock(return_value=None)
    return api
