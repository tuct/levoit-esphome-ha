"""WebSocket commands of the sidebar panel (admins only).

* levoit_esphome/subscribe: every device with versions, channel, config and
  build state; sent again whenever that changes
* levoit_esphome/build: compile, or compile and upload (like the buttons)
* levoit_esphome/set_channel: like the Update channel select
* levoit_esphome/check: read the latest versions from GitHub now
* levoit_esphome/build_log: the whole kept output of a device's last (or
  running) build; its steps and newest lines come with every device
* levoit_esphome/device_controls: which entity is which setting, for the
  device page

Purifier groups have their own commands, in groups_websocket.py.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import probatio

from homeassistant.components import websocket_api
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    callback,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_state_change_event

from .const import CHANNEL_MAIN, CHANNEL_STABLE, DOMAIN, SIGNAL_COORDINATOR
from .controls import lv600s_stores_target, match_controls, page_supported
from .device_builder import builder_page_url
from .groups_websocket import async_register as async_register_groups
from .templates import VARIANT_CUSTOM
from .versions import is_behind

if TYPE_CHECKING:
    from .coordinator import LevoitDevice, LevoitEsphomeCoordinator, PendingConfig

ERR_NOT_LOADED = "not_loaded"
ERR_NOT_FLASHED = "not_flashed"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands (once, at integration setup)."""
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_build)
    websocket_api.async_register_command(hass, ws_set_channel)
    websocket_api.async_register_command(hass, ws_check)
    websocket_api.async_register_command(hass, ws_build_log)
    websocket_api.async_register_command(hass, ws_device_controls)
    async_register_groups(hass)


def _coordinator(hass: HomeAssistant) -> LevoitEsphomeCoordinator | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _device_dict(
    hass: HomeAssistant,
    coordinator: LevoitEsphomeCoordinator,
    dev_reg: dr.DeviceRegistry,
    device: LevoitDevice,
) -> dict[str, Any]:
    data = coordinator.data
    head = data.heads.get(device.channel) if device.channel else None
    ours = dev_reg.async_get_device_by_identifier(
        (DOMAIN, device.mac), coordinator.config_entry.entry_id
    )
    filter_life: float | None = None
    if device.filter_entity_id and (state := hass.states.get(device.filter_entity_id)):
        try:
            filter_life = float(state.state)
        except ValueError:
            filter_life = None
    last = coordinator.last_builds.get(device.name)
    # which entity is which setting: the overview shows each device's power,
    # mode, air quality and timer from these, live from the states
    controls = match_controls(hass, device.esphome_device_id, device.model, device.control_names)
    return {
        "name": device.name,
        "title": device.title,
        "device_id": ours.id if ours else None,
        "esphome_device_id": device.esphome_device_id,
        "components": sorted(device.components),
        "model": device.model,
        "configuration": device.configuration,
        "config_kind": device.config_kind,
        "channel": device.channel,
        "ref": device.ref,
        "can_set_channel": coordinator.can_set_channel(device),
        "installed": device.reported.text if device.reported else None,
        "latest": head.text if head else None,
        "latest_url": head.url if head else None,
        "update_available": bool(
            device.reported
            and head
            and device.channel
            and is_behind(device.reported, head, device.channel)
        ),
        "esphome_deployed": device.esphome_deployed,
        "esphome_current": device.esphome_current,
        "filter_life": filter_life,
        "online": device.online,
        "detected": device.detected,
        "building": coordinator.is_building(device.name),
        "build_step": coordinator.build_step(device.name),
        "last_build": None
        if last is None
        else {
            "ok": last.ok,
            "upload": last.upload,
            "at": _iso(last.at),
            "error": last.error,
            "note": last.note,
        },
        "has_build_log": device.name in coordinator.build_logs,
        "build": coordinator.build_summary(device.name),
        "controls": controls,
        "supported": page_supported(device.model, device.components, controls),
    }


def _pending_dict(coordinator: LevoitEsphomeCoordinator, config: PendingConfig) -> dict[str, Any]:
    """A config made by Add device that is not flashed yet."""
    template = next((t for t in coordinator.templates if t.file == config.template), None)
    kind = VARIANT_CUSTOM if config.custom else (template.variant if template else None)
    last = coordinator.last_builds.get(config.name)
    return {
        "name": config.name,
        "title": config.name,
        "configuration": config.configuration,
        "model": template.model if template else None,
        "config_kind": kind,
        "building": coordinator.is_building(config.name),
        "build_step": coordinator.build_step(config.name),
        "last_build": None
        if last is None
        else {
            "ok": last.ok,
            "upload": last.upload,
            "at": _iso(last.at),
            "error": last.error,
            "note": last.note,
        },
        "has_build_log": config.name in coordinator.build_logs,
        "build": coordinator.build_summary(config.name),
    }


@callback
def snapshot(hass: HomeAssistant, coordinator: LevoitEsphomeCoordinator) -> dict[str, Any]:
    """What the panel shows; no secrets (none are kept)."""
    data = coordinator.data
    dev_reg = dr.async_get(hass)
    devices = sorted(data.devices.values(), key=lambda d: d.title.lower()) if data else []
    return {
        "devices": [_device_dict(hass, coordinator, dev_reg, d) for d in devices],
        "pending": [
            _pending_dict(coordinator, p)
            for p in sorted(data.pending.values(), key=lambda p: p.name)
        ]
        if data
        else [],
        "heads": {
            channel: {"version": head.text, "url": head.url}
            for channel, head in (data.heads.items() if data else ())
        },
        "checked_at": _iso(coordinator.heads_checked_at),
        "last_update_success": coordinator.last_update_success,
        "builder_url": builder_page_url(coordinator.device_builder),
    }


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/subscribe"})
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Send the devices now and whenever they change.

    Follows the coordinator across a reload of the entry, and the devices'
    filter sensors (they change without a coordinator update).
    """
    msg_id = msg["id"]
    unsub_coordinator: CALLBACK_TYPE | None = None
    unsub_states: CALLBACK_TYPE | None = None
    tracked: frozenset[str] = frozenset()

    @callback
    def send() -> None:
        nonlocal unsub_states, tracked
        coordinator = _coordinator(hass)
        if coordinator is None or coordinator.data is None:
            return
        wanted = frozenset(
            d.filter_entity_id for d in coordinator.data.devices.values() if d.filter_entity_id
        )
        if wanted != tracked:
            if unsub_states is not None:
                unsub_states()
                unsub_states = None
            tracked = wanted
            if wanted:
                unsub_states = async_track_state_change_event(hass, list(wanted), state_changed)
        connection.send_message(websocket_api.event_message(msg_id, snapshot(hass, coordinator)))

    @callback
    def state_changed(event: Event[EventStateChangedData]) -> None:
        send()

    @callback
    def attach() -> None:
        nonlocal unsub_coordinator
        if unsub_coordinator is not None:
            unsub_coordinator()
            unsub_coordinator = None
        if (coordinator := _coordinator(hass)) is not None:
            unsub_coordinator = coordinator.async_add_listener(send)
        send()

    unsub_signal = async_dispatcher_connect(hass, SIGNAL_COORDINATOR, attach)

    @callback
    def unsubscribe() -> None:
        unsub_signal()
        if unsub_coordinator is not None:
            unsub_coordinator()
        if unsub_states is not None:
            unsub_states()

    if _coordinator(hass) is None:
        unsub_signal()
        connection.send_error(msg_id, ERR_NOT_LOADED, "Levoit ESPHome is not set up")
        return
    connection.subscriptions[msg_id] = unsubscribe
    connection.send_result(msg_id)
    attach()


def _device(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
    *,
    pending_ok: bool = False,
) -> tuple[LevoitEsphomeCoordinator, LevoitDevice] | None:
    """The coordinator and the device named in the message; error sent if none.

    With `pending_ok`, a config made by Add device that is not flashed yet counts
    too (to compile it or read its build log).
    """
    coordinator = _coordinator(hass)
    if coordinator is None or coordinator.data is None:
        connection.send_error(msg["id"], ERR_NOT_LOADED, "Levoit ESPHome is not set up")
        return None
    device = coordinator.data.devices.get(msg["name"])
    if device is None and pending_ok:
        device = coordinator.pending_device(msg["name"])
    if device is None:
        connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, "Unknown device")
        return None
    return coordinator, device


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/build",
        probatio.Required("name"): str,
        probatio.Required("upload"): bool,
    }
)
@websocket_api.async_response
async def ws_build(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Compile, or compile and upload; answers when done (minutes).

    A config that is not flashed yet can be compiled, not uploaded: there is no
    device on the network yet.
    """
    if (found := _device(hass, connection, msg, pending_ok=True)) is None:
        return
    coordinator, device = found
    if msg["upload"] and msg["name"] in coordinator.data.pending:
        connection.send_error(
            msg["id"],
            ERR_NOT_FLASHED,
            "Not flashed yet: flash it once over USB from the Device Builder "
            "(Install, Plug into this computer); updates go over the air after that",
        )
        return
    await coordinator.async_build(device, upload=msg["upload"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/set_channel",
        probatio.Required("name"): str,
        probatio.Required("channel"): probatio.In([CHANNEL_STABLE, CHANNEL_MAIN]),
    }
)
@websocket_api.async_response
async def ws_set_channel(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Switch a device's channel (rewrites a template config's ref:)."""
    if (found := _device(hass, connection, msg)) is None:
        return
    coordinator, device = found
    await coordinator.async_set_channel(device, msg["channel"])
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/check"})
@websocket_api.async_response
async def ws_check(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Read the latest versions from GitHub and the devices again."""
    coordinator = _coordinator(hass)
    if coordinator is None:
        connection.send_error(msg["id"], ERR_NOT_LOADED, "Levoit ESPHome is not set up")
        return
    await coordinator.async_check_now()
    connection.send_result(msg["id"])


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/build_log",
        probatio.Required("name"): str,
    }
)
@callback
def ws_build_log(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The whole kept output of the device's last (or running) build, newest last."""
    if (found := _device(hass, connection, msg, pending_ok=True)) is None:
        return
    coordinator, device = found
    log = coordinator.build_logs.get(device.name)
    connection.send_result(
        msg["id"],
        {
            "lines": log.lines if log else [],
            "building": coordinator.is_building(device.name),
            "build": log.summary() if log else None,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/device_controls",
        probatio.Required("name"): str,
    }
)
@callback
def ws_device_controls(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """The device's settings as entities, per controls key, for its device page.

    Found by entity name, from its config when there is one, otherwise by the
    names the tuct/levoit configs use: no Device Builder config needed.
    """
    if (found := _device(hass, connection, msg)) is None:
        return
    _, device = found
    controls = match_controls(hass, device.esphome_device_id, device.model, device.control_names)
    supported = page_supported(device.model, device.components, controls)
    connection.send_result(
        msg["id"],
        {
            "name": device.name,
            "title": device.title,
            "model": device.model,
            "device_id": device.esphome_device_id,
            "supported": supported,
            "from_config": bool(device.control_names),
            "target_humidity_preset": device.model == "LV600S"
            and lv600s_stores_target(
                hass, controls.get("number.humidity_target"), device.control_names
            ),
            "controls": controls,
        },
    )
