"""WebSocket commands for purifier groups (admins only).

* levoit_esphome/groups/subscribe: groups with their live state, and the
  purifiers that can be in one; sent again whenever that changes
* levoit_esphome/groups/list: the same, once
* levoit_esphome/groups/save: create (no id) or change a group
* levoit_esphome/groups/delete: delete a group (its purifiers stay as they are)
* levoit_esphome/groups/preview: the editor's "Right now" for an unsaved config
* levoit_esphome/groups/apply: run a group's saved settings now (the editor's
  apply button): the sensors' level at once, purifiers changed by hand too
* levoit_esphome/groups/dismiss: hide the group suggestion for an area

And for the dashboard cards, any user (read only):

* levoit_esphome/cards: every purifier and group with the entities a card shows
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import probatio

from homeassistant.components import websocket_api
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, SIGNAL_COORDINATOR
from .groups import GroupManager, has_sleep, speeds_of
from .groups_logic import GroupError

if TYPE_CHECKING:
    from .coordinator import LevoitEsphomeCoordinator

ERR_NOT_LOADED = "not_loaded"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands (once, at integration setup)."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_list)
    websocket_api.async_register_command(hass, ws_save)
    websocket_api.async_register_command(hass, ws_delete)
    websocket_api.async_register_command(hass, ws_preview)
    websocket_api.async_register_command(hass, ws_apply)
    websocket_api.async_register_command(hass, ws_dismiss)
    websocket_api.async_register_command(hass, ws_cards)


def _manager(hass: HomeAssistant) -> GroupManager | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        return None
    coordinator: LevoitEsphomeCoordinator = entries[0].runtime_data
    return coordinator.groups


def _manager_or_error(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> GroupManager | None:
    if (manager := _manager(hass)) is None:
        connection.send_error(msg["id"], ERR_NOT_LOADED, "Levoit ESPHome is not set up")
    return manager


# a group's entities: unique id key -> domain
GROUP_ENTITIES = {
    "fan": "fan",
    "control": "switch",
    "active": "binary_sensor",
    "level": "sensor",
    "air_quality": "sensor",
    "pm1": "sensor",
    "pm25": "sensor",
    "pm10": "sensor",
    "aqi": "sensor",
    "cadr": "sensor",
}


@callback
def group_entities(hass: HomeAssistant, group_id: str) -> dict[str, str]:
    """A group's entity ids by key (the panel's history and links)."""
    ent_reg = er.async_get(hass)
    found = {
        key: ent_reg.async_get_entity_id(domain, DOMAIN, f"group_{group_id}_{key}")
        for key, domain in GROUP_ENTITIES.items()
    }
    return {key: entity_id for key, entity_id in found.items() if entity_id}


@callback
def groups_snapshot(manager: GroupManager) -> dict[str, Any]:
    """Groups with their state, and every purifier that can be in a group."""
    hass = manager.hass
    return {
        "groups": [
            {
                **config.as_dict(),
                "state": manager.state(group_id),
                "entities": group_entities(hass, group_id),
            }
            for group_id, config in sorted(
                manager.groups.items(), key=lambda item: item[1].name.lower()
            )
        ],
        "purifiers": [
            {
                "entity_id": fan.entity_id,
                "name": fan.name,
                "title": fan.title,
                "model": fan.model,
                "photo_url": manager.coordinator.photo_url(fan.model),
                "device_id": fan.device_id,
                "area_id": fan.area_id,
                "speeds": speeds_of(hass, fan.entity_id),
                "sleep": bool((st := hass.states.get(fan.entity_id)) and has_sleep(st)),
                "sensors": [{"entity_id": s.entity_id, "type": s.type} for s in fan.sensors],
                "cadr": fan.cadr,
                "group_id": group.id if (group := manager.group_of(fan.entity_id)) else None,
            }
            for fan in sorted(manager.levoit_fans().values(), key=lambda f: f.title.lower())
        ],
        "dismissed_areas": list(manager.dismissed_areas),
    }


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/groups/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the groups now and whenever they or their state change.

    Follows the group manager across a reload of the entry.
    """
    msg_id = msg["id"]
    unsub_manager: CALLBACK_TYPE | None = None

    @callback
    def send() -> None:
        if (manager := _manager(hass)) is not None:
            connection.send_message(websocket_api.event_message(msg_id, groups_snapshot(manager)))

    @callback
    def attach() -> None:
        nonlocal unsub_manager
        if unsub_manager is not None:
            unsub_manager()
            unsub_manager = None
        if (manager := _manager(hass)) is not None:
            unsub_manager = manager.async_add_listener(send)
        send()

    if _manager_or_error(hass, connection, msg) is None:
        return
    unsub_signal = async_dispatcher_connect(hass, SIGNAL_COORDINATOR, attach)

    @callback
    def unsubscribe() -> None:
        unsub_signal()
        if unsub_manager is not None:
            unsub_manager()

    connection.subscriptions[msg_id] = unsubscribe
    connection.send_result(msg_id)
    attach()


@callback
def cards_snapshot(manager: GroupManager) -> dict[str, Any]:
    """What the dashboard cards show: purifiers and groups with their entity ids.

    Names and entity ids only: no configs, sensors' values come from the states.
    """
    data = manager.coordinator.data
    devices = data.devices if data else {}
    purifiers = []
    for fan in sorted(manager.levoit_fans().values(), key=lambda f: f.title.lower()):
        sensors = {s.type: s.entity_id for s in fan.sensors}
        device = devices.get(fan.name)
        group = manager.group_of(fan.entity_id)
        purifiers.append(
            {
                "entity_id": fan.entity_id,
                "name": fan.name,
                "title": fan.title,
                "model": fan.model,
                "photo_url": manager.coordinator.photo_url(fan.model),
                "area_id": fan.area_id,
                "pm25": sensors.get("pm25"),
                "aqi": sensors.get("aqi"),
                "cadr": fan.cadr,
                "filter": device.filter_entity_id if device else None,
                "group_id": group.id if group else None,
            }
        )
    groups = [
        {
            "id": group_id,
            "name": config.name,
            "area_id": config.area_id,
            "members": list(config.members),
            "entities": group_entities(manager.hass, group_id),
        }
        for group_id, config in sorted(manager.groups.items(), key=lambda i: i[1].name.lower())
    ]
    return {"purifiers": purifiers, "groups": groups}


@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/cards"})
@callback
def ws_cards(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The purifiers and groups for the dashboard cards (any user)."""
    if (manager := _manager_or_error(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], cards_snapshot(manager))


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/groups/list"})
@callback
def ws_list(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The groups and purifiers, once."""
    if (manager := _manager_or_error(hass, connection, msg)) is not None:
        connection.send_result(msg["id"], groups_snapshot(manager))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/groups/save",
        probatio.Required("group"): dict,
    }
)
@websocket_api.async_response
async def ws_save(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Create or change a group; answers with it as saved (sensors picked)."""
    if (manager := _manager_or_error(hass, connection, msg)) is None:
        return
    try:
        config = await manager.async_save_group(msg["group"])
    except GroupError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], {**config.as_dict(), "state": manager.state(config.id)})


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/groups/delete",
        probatio.Required("group_id"): str,
    }
)
@websocket_api.async_response
async def ws_delete(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Delete a group; its purifiers stay as they are."""
    if (manager := _manager_or_error(hass, connection, msg)) is None:
        return
    try:
        await manager.async_delete_group(msg["group_id"])
    except GroupError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/groups/preview",
        probatio.Required("group"): dict,
    }
)
@callback
def ws_preview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The level, reason and member speeds an unsaved config would run at now."""
    if (manager := _manager_or_error(hass, connection, msg)) is None:
        return
    try:
        result = manager.preview(msg["group"])
    except GroupError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], result)


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/groups/apply",
        probatio.Required("group_id"): str,
    }
)
@websocket_api.async_response
async def ws_apply(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Run a group's saved settings now; answers with its state after."""
    if (manager := _manager_or_error(hass, connection, msg)) is None:
        return
    try:
        await manager.async_apply_now(msg["group_id"])
    except GroupError as err:
        connection.send_error(msg["id"], err.code, str(err))
        return
    connection.send_result(msg["id"], manager.state(msg["group_id"]))


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/groups/dismiss",
        probatio.Required("area_id"): str,
    }
)
@websocket_api.async_response
async def ws_dismiss(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Hide the "Suggested from your rooms" card of an area."""
    if (manager := _manager_or_error(hass, connection, msg)) is None:
        return
    await manager.async_dismiss_area(msg["area_id"])
    connection.send_result(msg["id"])
