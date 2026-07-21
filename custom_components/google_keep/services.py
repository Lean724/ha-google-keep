"""Services for the Google Keep integration."""
from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

from .const import (
    ATTR_COLOR,
    ATTR_ITEM_ID,
    ATTR_ITEMS,
    ATTR_LABELS,
    ATTR_LIST_ID,
    ATTR_NOTE_ID,
    ATTR_TEXT,
    ATTR_TITLE,
    DOMAIN,
    LOGGER_NAME,
    SERVICE_ADD_ITEM,
    SERVICE_ARCHIVE,
    SERVICE_COMPLETE_ITEM,
    SERVICE_CREATE_CHECKLIST,
    SERVICE_CREATE_NOTE,
    SERVICE_DELETE_NOTE,
    SERVICE_REMOVE_ITEM,
    SERVICE_RESTORE_NOTE,
    SERVICE_SYNC,
    SERVICE_UNARCHIVE,
    SERVICE_UNCOMPLETE_ITEM,
    VALID_COLORS,
)
from .exceptions import GoogleKeepError

_LOGGER = logging.getLogger(LOGGER_NAME)

SYNC_SCHEMA = vol.Schema({vol.Optional("config_entry_id"): str})

CREATE_NOTE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TITLE): str,
        vol.Optional(ATTR_TEXT, default=""): str,
        vol.Optional(ATTR_COLOR): vol.In(VALID_COLORS),
        vol.Optional(ATTR_LABELS, default=[]): [str],
    }
)

CREATE_CHECKLIST_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TITLE): str,
        vol.Required(ATTR_ITEMS): [str],
    }
)

ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): str,
        vol.Required(ATTR_ITEM_ID): str,
    }
)

ADD_ITEM_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_LIST_ID): str,
        vol.Required(ATTR_TEXT): str,
    }
)

NOTE_ID_SCHEMA = vol.Schema({vol.Required(ATTR_NOTE_ID): str})


def _get_all_coordinators(hass: HomeAssistant):
    """Return the API client for every configured Google Keep entry."""
    return [
        entry.runtime_data
        for entry in hass.config_entries.async_entries(DOMAIN)
        if getattr(entry, "runtime_data", None) is not None
    ]


def _first_coordinator(hass: HomeAssistant, call: ServiceCall):
    entry_id = call.data.get("config_entry_id")
    entries = hass.config_entries.async_entries(DOMAIN)
    if entry_id:
        entries = [e for e in entries if e.entry_id == entry_id]
    if not entries or getattr(entries[0], "runtime_data", None) is None:
        raise HomeAssistantError("No configured Google Keep account found")
    return entries[0].runtime_data


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the google_keep.* services (idempotent)."""
    if hass.services.has_service(DOMAIN, SERVICE_SYNC):
        return

    async def handle_sync(call: ServiceCall) -> None:
        for coordinator in _get_all_coordinators(hass):
            await coordinator.async_request_refresh()

    async def handle_create_note(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_create_note(
                call.data[ATTR_TITLE],
                call.data.get(ATTR_TEXT, ""),
                call.data.get(ATTR_COLOR),
                call.data.get(ATTR_LABELS, []),
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_create_checklist(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_create_checklist(
                call.data[ATTR_TITLE], call.data[ATTR_ITEMS]
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_add_item(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_add_item(
                call.data[ATTR_LIST_ID], call.data[ATTR_TEXT]
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_remove_item(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_remove_item(
                call.data[ATTR_LIST_ID], call.data[ATTR_ITEM_ID]
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_complete_item(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_item_checked(
                call.data[ATTR_LIST_ID], call.data[ATTR_ITEM_ID], True
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_uncomplete_item(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_item_checked(
                call.data[ATTR_LIST_ID], call.data[ATTR_ITEM_ID], False
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_archive(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_archived(call.data[ATTR_NOTE_ID], True)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_unarchive(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_archived(call.data[ATTR_NOTE_ID], False)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_delete_note(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_trashed(call.data[ATTR_NOTE_ID], True)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    async def handle_restore_note(call: ServiceCall) -> None:
        coordinator = _first_coordinator(hass, call)
        try:
            await coordinator.api.async_set_trashed(call.data[ATTR_NOTE_ID], False)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_SYNC, handle_sync, schema=SYNC_SCHEMA)
    hass.services.async_register(
        DOMAIN, SERVICE_CREATE_NOTE, handle_create_note, schema=CREATE_NOTE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_CHECKLIST,
        handle_create_checklist,
        schema=CREATE_CHECKLIST_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ADD_ITEM, handle_add_item, schema=ADD_ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_REMOVE_ITEM, handle_remove_item, schema=ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_COMPLETE_ITEM, handle_complete_item, schema=ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNCOMPLETE_ITEM, handle_uncomplete_item, schema=ITEM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_ARCHIVE, handle_archive, schema=NOTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_UNARCHIVE, handle_unarchive, schema=NOTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_DELETE_NOTE, handle_delete_note, schema=NOTE_ID_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_RESTORE_NOTE, handle_restore_note, schema=NOTE_ID_SCHEMA
    )


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove all google_keep.* services once the last entry is unloaded."""
    for service in (
        SERVICE_SYNC,
        SERVICE_CREATE_NOTE,
        SERVICE_CREATE_CHECKLIST,
        SERVICE_ADD_ITEM,
        SERVICE_REMOVE_ITEM,
        SERVICE_COMPLETE_ITEM,
        SERVICE_UNCOMPLETE_ITEM,
        SERVICE_ARCHIVE,
        SERVICE_UNARCHIVE,
        SERVICE_DELETE_NOTE,
        SERVICE_RESTORE_NOTE,
    ):
        hass.services.async_remove(DOMAIN, service)
