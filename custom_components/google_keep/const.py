"""Constants for the Google Keep integration."""
from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "google_keep"

# --- Config / options keys -------------------------------------------------
CONF_EMAIL: Final = "email"
CONF_PASSWORD: Final = "password"
CONF_MASTER_TOKEN: Final = "master_token"
CONF_DEVICE_ID: Final = "device_id"

CONF_UPDATE_INTERVAL: Final = "update_interval"
CONF_AUTO_SYNC: Final = "auto_sync"
CONF_DEFAULT_LIST: Final = "default_list"
CONF_SHOW_ARCHIVED: Final = "show_archived"
CONF_SHOW_TRASHED: Final = "show_trashed"
CONF_LABEL_FILTER: Final = "label_filter"
CONF_COLOR_FILTER: Final = "color_filter"

# --- Defaults ---------------------------------------------------------------
DEFAULT_UPDATE_INTERVAL_MINUTES: Final = 5
UPDATE_INTERVAL_OPTIONS: Final = [1, 5, 10, 30]  # 0 == manual, handled separately
MANUAL_UPDATE_INTERVAL: Final = 0

DEFAULT_SCAN_INTERVAL: Final = timedelta(minutes=DEFAULT_UPDATE_INTERVAL_MINUTES)

DEFAULT_AUTO_SYNC: Final = True
DEFAULT_SHOW_ARCHIVED: Final = False
DEFAULT_SHOW_TRASHED: Final = False

# --- Platforms ---------------------------------------------------------------
PLATFORMS: Final = ["sensor", "todo", "binary_sensor"]

# --- Services ----------------------------------------------------------------
SERVICE_SYNC: Final = "sync"
SERVICE_CREATE_NOTE: Final = "create_note"
SERVICE_CREATE_CHECKLIST: Final = "create_checklist"
SERVICE_ADD_ITEM: Final = "add_item"
SERVICE_REMOVE_ITEM: Final = "remove_item"
SERVICE_COMPLETE_ITEM: Final = "complete_item"
SERVICE_UNCOMPLETE_ITEM: Final = "uncomplete_item"
SERVICE_ARCHIVE: Final = "archive"
SERVICE_UNARCHIVE: Final = "unarchive"
SERVICE_DELETE_NOTE: Final = "delete_note"
SERVICE_RESTORE_NOTE: Final = "restore_note"

ATTR_TITLE: Final = "title"
ATTR_TEXT: Final = "text"
ATTR_COLOR: Final = "color"
ATTR_LABELS: Final = "labels"
ATTR_ITEMS: Final = "items"
ATTR_LIST_ID: Final = "list_id"
ATTR_ITEM_ID: Final = "item_id"
ATTR_NOTE_ID: Final = "note_id"

# --- Events -------------------------------------------------------------------
EVENT_NOTE_CREATED: Final = f"{DOMAIN}_note_created"
EVENT_NOTE_UPDATED: Final = f"{DOMAIN}_note_updated"
EVENT_NOTE_DELETED: Final = f"{DOMAIN}_note_deleted"
EVENT_SYNC_FINISHED: Final = f"{DOMAIN}_sync_finished"

# --- Misc ----------------------------------------------------------------------
LOGGER_NAME: Final = "custom_components.google_keep"

VALID_COLORS: Final = [
    "white",
    "red",
    "orange",
    "yellow",
    "green",
    "teal",
    "blue",
    "darkblue",
    "purple",
    "pink",
    "brown",
    "gray",
]
