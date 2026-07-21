"""Thin async wrapper around gkeepapi.

Every call into gkeepapi is synchronous (it uses `requests` under the hood),
so every public method on GoogleKeepAPI runs the blocking call inside
`hass.async_add_executor_job` to avoid blocking the event loop.

All gkeepapi-specific error handling lives here so the rest of the
integration only ever has to deal with the exceptions defined in
exceptions.py. This keeps the coordinator/config_flow/services free of
gkeepapi implementation details, which makes it easier to adapt if Google
changes something gkeepapi depends on.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import gkeepapi
import gkeepapi.exception
from gkeepapi.node import ColorValue, List as KeepList, Note as KeepNote

from homeassistant.core import HomeAssistant

from .const import LOGGER_NAME
from .exceptions import (
    GoogleKeepAuthError,
    GoogleKeepConnectionError,
    GoogleKeepNotFoundError,
    GoogleKeepRateLimitError,
    GoogleKeepTokenExpiredError,
    GoogleKeepUpstreamChangedError,
)

_LOGGER = logging.getLogger(LOGGER_NAME)


@dataclass
class KeepListItem:
    """A single checklist item."""

    id: str
    text: str
    checked: bool


@dataclass
class KeepListData:
    """Normalized representation of a Keep list/note used by the coordinator."""

    id: str
    title: str
    color: str
    archived: bool
    trashed: bool
    pinned: bool
    labels: list[str]
    is_list: bool
    items: list[KeepListItem] = field(default_factory=list)
    text: str = ""
    timestamps: dict[str, str] = field(default_factory=dict)

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def checked_items(self) -> int:
        return sum(1 for item in self.items if item.checked)

    @property
    def unchecked_items(self) -> int:
        return sum(1 for item in self.items if not item.checked)


def _wrap_gkeepapi_errors(func):
    """Translate gkeepapi exceptions into our own exception hierarchy."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except gkeepapi.exception.LoginException as err:
            raise GoogleKeepAuthError(str(err)) from err
        except gkeepapi.exception.ResyncRequiredException as err:
            raise GoogleKeepUpstreamChangedError(str(err)) from err
        except gkeepapi.exception.APIException as err:
            message = str(err).lower()
            if "429" in message or "rate" in message:
                raise GoogleKeepRateLimitError(str(err)) from err
            raise GoogleKeepConnectionError(str(err)) from err
        except gkeepapi.exception.KeepException as err:
            raise GoogleKeepUpstreamChangedError(str(err)) from err

    return wrapper


class GoogleKeepAPI:
    """Encapsulates all interaction with gkeepapi.

    Nothing outside this module should import gkeepapi directly - if Google
    changes something and gkeepapi needs to be swapped out or patched, this
    is the only file that should need to change.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        email: str,
        password: str | None = None,
        master_token: str | None = None,
        device_id: str | None = None,
    ) -> None:
        self._hass = hass
        self._email = email
        self._password = password
        self._master_token = master_token
        self._device_id = device_id
        self._keep = gkeepapi.Keep()

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------
    async def async_login(self) -> str:
        """Log in and return a master token that can be stored for later use."""
        return await self._hass.async_add_executor_job(self._login)

    @_wrap_gkeepapi_errors
    def _login(self) -> str:
        if self._master_token:
            try:
                self._keep.resume(
                    self._email, self._master_token, device_id=self._device_id
                )
            except gkeepapi.exception.LoginException as err:
                raise GoogleKeepTokenExpiredError(str(err)) from err
        elif self._password:
            self._keep.login(
                self._email, self._password, device_id=self._device_id
            )
        else:
            raise GoogleKeepAuthError(
                "Either a password or a master token is required"
            )
        return self._keep.getMasterToken()

    async def async_test_credentials(self) -> str:
        """Validate credentials during config flow. Returns the master token."""
        return await self.async_login()

    # ------------------------------------------------------------------
    # Sync
    # ------------------------------------------------------------------
    async def async_sync(self) -> list[KeepListData]:
        """Pull the latest changes from Google and return normalized data."""
        return await self._hass.async_add_executor_job(self._sync)

    @_wrap_gkeepapi_errors
    def _sync(self) -> list[KeepListData]:
        try:
            self._keep.sync()
        except gkeepapi.exception.LoginException as err:
            raise GoogleKeepTokenExpiredError(str(err)) from err
        return [self._normalize(node) for node in self._keep.all()]

    @staticmethod
    def _normalize(node: KeepNote | KeepList) -> KeepListData:
        is_list = isinstance(node, KeepList)
        items: list[KeepListItem] = []
        if is_list:
            items = [
                KeepListItem(id=item.id, text=item.text, checked=item.checked)
                for item in node.items
            ]
        color = node.color.value if isinstance(node.color, ColorValue) else str(
            node.color
        )
        return KeepListData(
            id=node.id,
            title=node.title,
            color=color,
            archived=node.archived,
            trashed=node.trashed,
            pinned=node.pinned,
            labels=[label.name for label in node.labels.all()],
            is_list=is_list,
            items=items,
            text=getattr(node, "text", "") if not is_list else "",
            timestamps={
                "created": str(node.timestamps.created),
                "updated": str(node.timestamps.updated),
            },
        )

    # ------------------------------------------------------------------
    # Mutations - these mutate the local gkeepapi model; a subsequent
    # sync() call flushes the change to Google's servers.
    # ------------------------------------------------------------------
    async def async_create_note(
        self,
        title: str,
        text: str = "",
        color: str | None = None,
        labels: list[str] | None = None,
    ) -> str:
        return await self._hass.async_add_executor_job(
            self._create_note, title, text, color, labels
        )

    @_wrap_gkeepapi_errors
    def _create_note(
        self,
        title: str,
        text: str,
        color: str | None,
        labels: list[str] | None,
    ) -> str:
        note = self._keep.createNote(title, text)
        if color:
            note.color = ColorValue(color)
        if labels:
            for label_name in labels:
                label = self._keep.findLabel(label_name) or self._keep.createLabel(
                    label_name
                )
                note.labels.add(label)
        self._keep.sync()
        return note.id

    async def async_create_checklist(
        self, title: str, items: list[str]
    ) -> str:
        return await self._hass.async_add_executor_job(
            self._create_checklist, title, items
        )

    @_wrap_gkeepapi_errors
    def _create_checklist(self, title: str, items: list[str]) -> str:
        checklist_items = [(text, False) for text in items]
        note = self._keep.createList(title, checklist_items)
        self._keep.sync()
        return note.id

    def _get_list(self, list_id: str) -> KeepList:
        node = self._keep.get(list_id)
        if node is None or not isinstance(node, KeepList):
            raise GoogleKeepNotFoundError(f"List '{list_id}' was not found")
        return node

    def _get_note_or_list(self, note_id: str) -> KeepNote | KeepList:
        node = self._keep.get(note_id)
        if node is None:
            raise GoogleKeepNotFoundError(f"Note/list '{note_id}' was not found")
        return node

    async def async_add_item(self, list_id: str, text: str) -> str:
        return await self._hass.async_add_executor_job(
            self._add_item, list_id, text
        )

    @_wrap_gkeepapi_errors
    def _add_item(self, list_id: str, text: str) -> str:
        keep_list = self._get_list(list_id)
        item = keep_list.add(text, False)
        self._keep.sync()
        return item.id

    async def async_remove_item(self, list_id: str, item_id: str) -> None:
        await self._hass.async_add_executor_job(
            self._remove_item, list_id, item_id
        )

    @_wrap_gkeepapi_errors
    def _remove_item(self, list_id: str, item_id: str) -> None:
        keep_list = self._get_list(list_id)
        item = keep_list.items.get(item_id) if hasattr(keep_list.items, "get") else None
        item = item or next(
            (i for i in keep_list.items if i.id == item_id), None
        )
        if item is None:
            raise GoogleKeepNotFoundError(f"Item '{item_id}' was not found")
        item.delete()
        self._keep.sync()

    async def async_set_item_checked(
        self, list_id: str, item_id: str, checked: bool
    ) -> None:
        await self._hass.async_add_executor_job(
            self._set_item_checked, list_id, item_id, checked
        )

    @_wrap_gkeepapi_errors
    def _set_item_checked(self, list_id: str, item_id: str, checked: bool) -> None:
        keep_list = self._get_list(list_id)
        item = next((i for i in keep_list.items if i.id == item_id), None)
        if item is None:
            raise GoogleKeepNotFoundError(f"Item '{item_id}' was not found")
        item.checked = checked
        self._keep.sync()

    async def async_set_archived(self, note_id: str, archived: bool) -> None:
        await self._hass.async_add_executor_job(
            self._set_archived, note_id, archived
        )

    @_wrap_gkeepapi_errors
    def _set_archived(self, note_id: str, archived: bool) -> None:
        node = self._get_note_or_list(note_id)
        node.archived = archived
        self._keep.sync()

    async def async_set_trashed(self, note_id: str, trashed: bool) -> None:
        await self._hass.async_add_executor_job(
            self._set_trashed, note_id, trashed
        )

    @_wrap_gkeepapi_errors
    def _set_trashed(self, note_id: str, trashed: bool) -> None:
        node = self._get_note_or_list(note_id)
        if trashed:
            node.trash()
        else:
            node.untrash()
        self._keep.sync()

    async def async_close(self) -> None:
        """No persistent connection to close, but keep the interface for symmetry."""
        return None
