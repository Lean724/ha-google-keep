"""Todo platform - exposes each Google Keep checklist as a native Todo List."""
from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GoogleKeepConfigEntry
from .const import DOMAIN
from .exceptions import GoogleKeepError


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GoogleKeepConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create a TodoListEntity for every checklist-type Keep note."""
    coordinator = entry.runtime_data
    known_ids: set[str] = set()

    @callback
    def _add_new_entities() -> None:
        new_entities = []
        for note_id, node in coordinator.data.items():
            if note_id in known_ids or not node.is_list:
                continue
            known_ids.add(note_id)
            new_entities.append(GoogleKeepTodoListEntity(coordinator, entry, note_id))
        if new_entities:
            async_add_entities(new_entities)

    _add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(_add_new_entities))


class GoogleKeepTodoListEntity(CoordinatorEntity, TodoListEntity):
    """A single Google Keep checklist, exposed as a Home Assistant Todo List."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:google-keep"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )

    def __init__(self, coordinator, entry: GoogleKeepConfigEntry, note_id: str) -> None:
        super().__init__(coordinator)
        self._note_id = note_id
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{note_id}_todo"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Google Keep",
            manufacturer="Google",
            entry_type="service",
        )

    @property
    def _node(self):
        return self.coordinator.data.get(self._note_id)

    @property
    def available(self) -> bool:
        return super().available and self._node is not None

    @property
    def name(self) -> str:
        node = self._node
        return node.title if node and node.title else "Untitled list"

    @property
    def todo_items(self) -> list[TodoItem] | None:
        node = self._node
        if node is None:
            return None
        return [
            TodoItem(
                summary=item.text,
                uid=item.id,
                status=(
                    TodoItemStatus.COMPLETED
                    if item.checked
                    else TodoItemStatus.NEEDS_ACTION
                ),
            )
            for item in node.items
        ]

    async def async_create_todo_item(self, item: TodoItem) -> None:
        try:
            await self.coordinator.api.async_add_item(self._note_id, item.summary)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        checked = item.status == TodoItemStatus.COMPLETED
        try:
            await self.coordinator.api.async_set_item_checked(
                self._note_id, item.uid, checked
            )
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        try:
            for uid in uids:
                await self.coordinator.api.async_remove_item(self._note_id, uid)
        except GoogleKeepError as err:
            raise HomeAssistantError(str(err)) from err
        await self.coordinator.async_request_refresh()
