"""DataUpdateCoordinator for the Google Keep integration."""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import GoogleKeepAPI, KeepListData
from .const import (
    CONF_COLOR_FILTER,
    CONF_LABEL_FILTER,
    CONF_SHOW_ARCHIVED,
    CONF_SHOW_TRASHED,
    CONF_UPDATE_INTERVAL,
    DEFAULT_SHOW_ARCHIVED,
    DEFAULT_SHOW_TRASHED,
    DOMAIN,
    EVENT_SYNC_FINISHED,
    LOGGER_NAME,
    MANUAL_UPDATE_INTERVAL,
)
from .exceptions import (
    GoogleKeepAuthError,
    GoogleKeepConnectionError,
    GoogleKeepError,
    GoogleKeepRateLimitError,
    GoogleKeepTokenExpiredError,
)

_LOGGER = logging.getLogger(LOGGER_NAME)


class GoogleKeepCoordinator(DataUpdateCoordinator[dict[str, KeepListData]]):
    """Coordinates polling gkeepapi and fanning out changes to entities."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, api: GoogleKeepAPI
    ) -> None:
        self.api = api
        self.config_entry = entry
        self._previous_ids: set[str] = set()

        interval_minutes = entry.options.get(
            CONF_UPDATE_INTERVAL, entry.data.get(CONF_UPDATE_INTERVAL, 5)
        )
        update_interval = (
            None
            if interval_minutes == MANUAL_UPDATE_INTERVAL
            else timedelta(minutes=interval_minutes)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    def set_update_interval(self, minutes: int) -> None:
        """Reconfigure polling interval, e.g. after an options update."""
        self.update_interval = (
            None if minutes == MANUAL_UPDATE_INTERVAL else timedelta(minutes=minutes)
        )

    async def _async_update_data(self) -> dict[str, KeepListData]:
        try:
            nodes = await self.api.async_sync()
        except GoogleKeepTokenExpiredError as err:
            # Signals config_entries to start a reauth flow.
            raise UpdateFailed(str(err)) from err
        except GoogleKeepAuthError as err:
            raise UpdateFailed(str(err)) from err
        except GoogleKeepRateLimitError as err:
            _LOGGER.warning("Google Keep rate limit hit, will retry later: %s", err)
            raise UpdateFailed(str(err)) from err
        except GoogleKeepConnectionError as err:
            raise UpdateFailed(f"Could not reach Google Keep: {err}") from err
        except GoogleKeepError as err:
            raise UpdateFailed(str(err)) from err

        show_archived = self.config_entry.options.get(
            CONF_SHOW_ARCHIVED, DEFAULT_SHOW_ARCHIVED
        )
        show_trashed = self.config_entry.options.get(
            CONF_SHOW_TRASHED, DEFAULT_SHOW_TRASHED
        )
        label_filter: list[str] = self.config_entry.options.get(CONF_LABEL_FILTER, [])
        color_filter: list[str] = self.config_entry.options.get(CONF_COLOR_FILTER, [])

        filtered: dict[str, KeepListData] = {}
        for node in nodes:
            if node.trashed and not show_trashed:
                continue
            if node.archived and not show_archived:
                continue
            if label_filter and not (set(node.labels) & set(label_filter)):
                continue
            if color_filter and node.color not in color_filter:
                continue
            filtered[node.id] = node

        self._fire_change_events(filtered)
        self._previous_ids = set(filtered)

        self.hass.bus.async_fire(EVENT_SYNC_FINISHED, {"count": len(filtered)})

        return filtered

    def _fire_change_events(self, current: dict[str, KeepListData]) -> None:
        from .const import EVENT_NOTE_CREATED, EVENT_NOTE_DELETED, EVENT_NOTE_UPDATED

        current_ids = set(current)
        for new_id in current_ids - self._previous_ids:
            self.hass.bus.async_fire(
                EVENT_NOTE_CREATED,
                {"id": new_id, "title": current[new_id].title},
            )
        for removed_id in self._previous_ids - current_ids:
            self.hass.bus.async_fire(EVENT_NOTE_DELETED, {"id": removed_id})
        if self.data:
            for existing_id in current_ids & self._previous_ids:
                old = self.data.get(existing_id)
                new = current[existing_id]
                if old is not None and old.timestamps.get(
                    "updated"
                ) != new.timestamps.get("updated"):
                    self.hass.bus.async_fire(
                        EVENT_NOTE_UPDATED,
                        {"id": existing_id, "title": new.title},
                    )
