"""Levoit ESPHome: updates for devices running the levoit / philips components."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import (
    config_validation as cv,
    device_registry as dr,
    entity_registry as er,
)
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.start import async_at_started
from homeassistant.helpers.typing import ConfigType

from . import websocket
from .const import CONF_SHOW_PANEL, DOMAIN, SIGNAL_COORDINATOR
from .coordinator import LevoitEsphomeCoordinator
from .entity import subentry_for
from .groups import GroupManager
from .panel import (
    async_register_cards,
    async_register_panel,
    async_remove_cards,
    async_remove_panel,
)

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.FAN,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.UPDATE,
]

type LevoitEsphomeConfigEntry = ConfigEntry[LevoitEsphomeCoordinator]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """The panel's WebSocket commands."""
    websocket.async_register(hass)
    return True


@callback
def _async_drop_via_device(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the "connected via" link the first version set.

    Home Assistant keeps via_device_id on a device even when the entities no
    longer set it; the purifier's ESPHome device is listed under "Linked
    devices" through the shared MAC instead.
    """
    dev_reg = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if device.via_device_id is not None:
            dev_reg.async_update_device(device.id, via_device_id=None)


@callback
def _async_move_to_subentries(
    hass: HomeAssistant, entry: ConfigEntry, coordinator: LevoitEsphomeCoordinator
) -> None:
    """Put each device under the "Add device" sub-entry of its config.

    A device belongs to one sub-entry (Home Assistant 2026.8+). Adding its
    entities with another sub-entry would make a second device, so a device
    that exists already is moved, with its entities.
    """
    dev_reg = dr.async_get(hass)
    ent_reg = er.async_get(hass)
    for name, device in coordinator.data.devices.items():
        target = subentry_for(entry, name)
        entry_device = dev_reg.async_get_device_by_identifier((DOMAIN, device.mac), entry.entry_id)
        if entry_device is None or entry_device.config_subentry_id == target:
            continue
        dev_reg.async_update_device(entry_device.id, new_config_subentry_id=target)
        for entity in er.async_entries_for_device(
            ent_reg, entry_device.id, include_disabled_entities=True
        ):
            if entity.config_entry_id == entry.entry_id and entity.config_subentry_id != target:
                ent_reg.async_update_entity(entity.entity_id, config_subentry_id=target)


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """A sub-entry or an option changed: set up again (devices move, panel shows)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: LevoitEsphomeConfigEntry) -> bool:
    """Set up from a config entry."""
    _async_drop_via_device(hass, entry)
    coordinator = LevoitEsphomeCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    coordinator.groups = GroupManager(hass, coordinator)
    await coordinator.groups.async_load()
    _async_move_to_subentries(hass, entry, coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    # purifier groups run once the fans and sensors are set up
    entry.async_on_unload(coordinator.groups.async_stop)
    entry.async_on_unload(coordinator.groups.async_stop_with_hass())
    entry.async_on_unload(async_at_started(hass, coordinator.groups.async_start))
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await async_register_cards(hass)
    entry.async_on_unload(lambda: async_remove_cards(hass))
    if entry.options.get(CONF_SHOW_PANEL):
        await async_register_panel(hass)
        # kept for a reload (a device added, an option changed): see async_remove_panel
        entry.async_on_unload(lambda: async_remove_panel(hass, later=True))
    else:
        async_remove_panel(hass)  # the option was switched off
    # an open panel follows the new coordinator
    async_dispatcher_send(hass, SIGNAL_COORDINATOR)
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: LevoitEsphomeConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Allow deleting a device that is gone: offline and without a Device Builder config.

    One with a config would come back on the next refresh (delete the config
    in the Device Builder first); one that reports now is in use.
    """
    macs = {value for domain, value in device_entry.identifiers if domain == DOMAIN}
    data = entry.runtime_data.data
    device = next(
        (d for d in (data.devices.values() if data else ()) if d.mac in macs),
        None,
    )
    return device is None or (not device.configuration and device.online is not True)


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Deleted: the sidebar entry goes now, not after the grace of an unload."""
    async_remove_panel(hass)


async def async_unload_entry(hass: HomeAssistant, entry: LevoitEsphomeConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
