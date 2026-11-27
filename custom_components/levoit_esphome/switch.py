"""Switches: a purifier group's control (off = the group leaves its members alone)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant

from .group_entity import LevoitGroupEntity, async_add_per_group

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import LevoitEsphomeConfigEntry
    from .groups import GroupManager

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LevoitEsphomeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the control switch per purifier group."""
    manager = entry.runtime_data.groups
    entry.async_on_unload(
        async_add_per_group(
            manager,
            async_add_entities,
            lambda manager, group_id: [GroupControlSwitch(manager, group_id)],
        )
    )


class GroupControlSwitch(LevoitGroupEntity, SwitchEntity):
    """Whether the group controls its purifiers; automations can pause a group."""

    _attr_translation_key = "group_control"

    def __init__(self, manager: GroupManager, group_id: str) -> None:
        """Initialize."""
        super().__init__(manager, group_id, "control")

    @property
    def is_on(self) -> bool | None:
        """On while the group is enabled."""
        group = self.purifier_group
        return group.enabled if group else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Let the group control its purifiers."""
        await self._manager.async_set_enabled(self._group_id, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the group and its purifiers off."""
        await self._manager.async_set_enabled(self._group_id, False)
