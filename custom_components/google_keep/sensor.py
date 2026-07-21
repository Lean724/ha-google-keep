"""Sensor platform for the Google Keep integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoogleKeepConfigEntry
from .api import KeepListData
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoogleKeepConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Google Keep sensors from a config entry."""
    coordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities = []
        for note_id, node in coordinator.data.items():
            if note_id in known_ids:
                continue
            known_ids.add(note_id)
            new_entities.append(GoogleKeepListSensor(coordinator, entry, note_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class GoogleKeepListSensor(CoordinatorEntity, SensorEntity):
    """Represents a single Google Keep list or note as a sensor."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:google-keep"

    def __init__(self, coordinator, entry: GoogleKeepConfigEntry, note_id: str) -> None:
        super().__init__(coordinator)
        self._note_id = note_id
        self._attr_unique_id = f"{entry.entry_id}_{note_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Google Keep",
            manufacturer="Google",
            entry_type="service",
        )

    @property
    def _node(self) -> KeepListData | None:
        return self.coordinator.data.get(self._note_id)

    @property
    def available(self) -> bool:
        return super().available and self._node is not None

    @property
    def name(self) -> str:
        node = self._node
        return node.title if node and node.title else "Untitled note"

    @property
    def native_value(self) -> int | None:
        node = self._node
        if node is None:
            return None
        return node.unchecked_items if node.is_list else node.item_count

    @property
    def extra_state_attributes(self) -> dict:
        node = self._node
        if node is None:
            return {}
        return {
            "title": node.title,
            "id": node.id,
            "item_count": node.item_count,
            "checked_items": node.checked_items,
            "unchecked_items": node.unchecked_items,
            "last_updated": node.timestamps.get("updated"),
            "color": node.color,
            "archived": node.archived,
            "pinned": node.pinned,
            "labels": node.labels,
            "is_list": node.is_list,
        }
