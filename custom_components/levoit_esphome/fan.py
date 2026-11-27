"""Fans: each purifier group as one fan, to run a whole room like one purifier.

On / off is the group's control. Preset Auto lets the sensors pick the level;
Manual runs all members at one level, set with the fan's 4 speeds. Setting a
speed switches the group to Manual.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.util.percentage import (
    percentage_to_ranged_value,
    ranged_value_to_percentage,
)

from .group_entity import LevoitGroupEntity, async_add_per_group
from .groups_logic import MAX_LEVEL, MODE_AUTO, MODE_MANUAL, GroupError

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import LevoitEsphomeConfigEntry
    from .groups import GroupManager

PARALLEL_UPDATES = 0

PRESET_AUTO = "Auto"
PRESET_MANUAL = "Manual"
SPEED_RANGE = (1, MAX_LEVEL)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LevoitEsphomeConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the fan per purifier group."""
    entry.async_on_unload(
        async_add_per_group(
            entry.runtime_data.groups,
            async_add_entities,
            lambda manager, group_id: [GroupFan(manager, group_id)],
        )
    )


class GroupFan(LevoitGroupEntity, FanEntity):
    """A purifier group as one fan: on / off, Auto / Manual and 4 speeds."""

    _attr_name = None  # the group's name
    _attr_preset_modes: ClassVar[list[str]] = [PRESET_AUTO, PRESET_MANUAL]
    _attr_speed_count = MAX_LEVEL
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )

    def __init__(self, manager: GroupManager, group_id: str) -> None:
        """Initialize."""
        super().__init__(manager, group_id, "fan")

    @property
    def is_on(self) -> bool | None:
        """On while the group controls its purifiers."""
        group = self.purifier_group
        return group.enabled if group else None

    @property
    def preset_mode(self) -> str | None:
        """Auto (the sensors pick the level) or Manual."""
        group = self.purifier_group
        if group is None:
            return None
        return PRESET_MANUAL if group.mode == MODE_MANUAL else PRESET_AUTO

    @property
    def percentage(self) -> int | None:
        """The level the purifiers run at: the manual level, or the sensors' level in Auto."""
        group = self.purifier_group
        if group is None:
            return None
        if not group.enabled:
            return 0
        level = group.manual_level if group.mode == MODE_MANUAL else self.group_state["level"]
        return ranged_value_to_percentage(SPEED_RANGE, level) if level else 0

    async def _async_change(self, **changes: Any) -> None:
        try:
            await self._manager.async_change(self._group_id, **changes)
        except GroupError as err:
            raise HomeAssistantError(str(err)) from err

    @staticmethod
    def _level(percentage: int) -> int:
        return max(1, math.ceil(percentage_to_ranged_value(SPEED_RANGE, percentage)))

    async def async_turn_on(
        self, percentage: int | None = None, preset_mode: str | None = None, **kwargs: Any
    ) -> None:
        """Let the group run its purifiers; a speed switches it to Manual at that level."""
        changes: dict[str, Any] = {"enabled": True}
        if preset_mode is not None:
            changes["mode"] = MODE_MANUAL if preset_mode == PRESET_MANUAL else MODE_AUTO
        if percentage:
            changes["mode"] = MODE_MANUAL
            changes["manual_level"] = self._level(percentage)
        await self._async_change(**changes)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the group and its purifiers off."""
        await self._async_change(enabled=False)

    async def async_set_percentage(self, percentage: int) -> None:
        """Run every purifier at this level (Manual); 0 turns the group off."""
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._async_change(
            enabled=True, mode=MODE_MANUAL, manual_level=self._level(percentage)
        )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Auto or Manual; turns the group on."""
        await self._async_change(
            enabled=True, mode=MODE_MANUAL if preset_mode == PRESET_MANUAL else MODE_AUTO
        )
