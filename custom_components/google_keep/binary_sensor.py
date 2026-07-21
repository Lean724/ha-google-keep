"""Binary sensor platform for the Google Keep integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoogleKeepConfigEntry
from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoogleKeepConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the 'has pending items' binary sensor."""
    async_add_entities([GoogleKeepHasPendingItemsSensor(entry.runtime_data, entry)])


class GoogleKeepHasPendingItemsSensor(CoordinatorEntity, BinarySensorEntity):
    """True if any tracked list has at least one unchecked item."""

    _attr_has_entity_name = True
    _attr_name = "Has pending items"
    _attr_icon = "mdi:checkbox-marked-circle-outline"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator, entry: GoogleKeepConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_has_pending_items"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Google Keep",
            manufacturer="Google",
            entry_type="service",
        )

    @property
    def is_on(self) -> bool:
        return any(
            node.is_list and node.unchecked_items > 0
            for node in self.coordinator.data.values()
        )
