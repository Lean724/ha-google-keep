"""Tests for google_keep.* services."""
from __future__ import annotations

from unittest.mock import patch

from custom_components.google_keep.const import DOMAIN


async def _setup_integration(hass, mock_config_entry, mock_api):
    mock_config_entry.add_to_hass(hass)
    with patch(
        "custom_components.google_keep.GoogleKeepAPI", return_value=mock_api
    ):
        assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
        await hass.async_block_till_done()
    return mock_config_entry


async def test_sync_service_triggers_refresh(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)
    mock_api.async_sync.reset_mock()

    await hass.services.async_call(DOMAIN, "sync", {}, blocking=True)

    assert mock_api.async_sync.called


async def test_create_note_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN,
        "create_note",
        {"title": "Groceries", "text": "buy stuff", "color": "green"},
        blocking=True,
    )

    mock_api.async_create_note.assert_called_once_with(
        "Groceries", "buy stuff", "green", []
    )


async def test_create_checklist_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN,
        "create_checklist",
        {"title": "Chores", "items": ["Vacuum", "Dishes"]},
        blocking=True,
    )

    mock_api.async_create_checklist.assert_called_once_with(
        "Chores", ["Vacuum", "Dishes"]
    )


async def test_add_item_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN,
        "add_item",
        {"list_id": "list-1", "text": "Butter"},
        blocking=True,
    )

    mock_api.async_add_item.assert_called_once_with("list-1", "Butter")


async def test_complete_item_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN,
        "complete_item",
        {"list_id": "list-1", "item_id": "item-1"},
        blocking=True,
    )

    mock_api.async_set_item_checked.assert_called_once_with("list-1", "item-1", True)


async def test_archive_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN, "archive", {"note_id": "note-1"}, blocking=True
    )

    mock_api.async_set_archived.assert_called_once_with("note-1", True)


async def test_delete_note_service(hass, mock_config_entry, mock_api):
    await _setup_integration(hass, mock_config_entry, mock_api)

    await hass.services.async_call(
        DOMAIN, "delete_note", {"note_id": "note-1"}, blocking=True
    )

    mock_api.async_set_trashed.assert_called_once_with("note-1", True)


async def test_services_removed_after_last_entry_unloaded(
    hass, mock_config_entry, mock_api
):
    await _setup_integration(hass, mock_config_entry, mock_api)
    assert hass.services.has_service(DOMAIN, "sync")

    await hass.config_entries.async_unload(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert not hass.services.has_service(DOMAIN, "sync")
