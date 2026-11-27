"""Purifier groups in Home Assistant: the loop, entities and panel commands."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.levoit_esphome.const import DOMAIN
from custom_components.levoit_esphome.groups import STORAGE_KEY
from homeassistant.core import Context, HomeAssistant, ServiceCall
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import MAC, add_esphome_device

LIVING_MAC = "de:ad:be:ef:00:03"
UNIT = {"unit_of_measurement": "µg/m³"}
PRESETS = ["Manual", "Sleep", "Auto"]
LEVEL = "sensor.living_room_level"
CONTROL = "switch.living_room_control"
ACTIVE = "binary_sensor.living_room_active"
GROUP_FAN = "fan.living_room"
AIR_QUALITY = "sensor.living_room_air_quality"
MEMBERS = ["fan.bedroom", "fan.living"]

type Calls = list[tuple[str, str, dict[str, Any]]]


def _add_entities(hass: HomeAssistant, mac: str, entities: dict[str, str]) -> None:
    """ESPHome entities ('domain.object_id' -> name) on the device with that MAC."""
    dev_reg = dr.async_get(hass)
    entry, device = next(
        (entry, device)
        for entry in hass.config_entries.async_entries("esphome")
        for device in dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
        if (dr.CONNECTION_NETWORK_MAC, mac) in device.connections
    )
    for key, name in entities.items():
        domain, object_id = key.split(".", 1)
        er.async_get(hass).async_get_or_create(
            domain,
            "esphome",
            f"{mac}-{domain}-{object_id}",
            device_id=device.id,
            config_entry=entry,
            original_name=name,
            suggested_object_id=object_id,
        )


def _purifiers(hass: HomeAssistant) -> None:
    """Two purifiers with a fan and a PM2.5 sensor each.

    Bedroom: 4 speeds, on in Auto. Living: 3 speeds, off.
    """
    hass.config.components.add("esphome")
    add_esphome_device(hass, "bedroom-purifier", MAC, "Bedroom purifier", "1.7.0+10361cc esphome")
    add_esphome_device(
        hass,
        "living-purifier",
        LIVING_MAC,
        "Living purifier",
        "1.7.0+10361cc esphome",
        model="CORE300S",
    )
    _add_entities(hass, MAC, {"fan.bedroom": "Fan", "sensor.bedroom_pm25": "PM 2.5"})
    _add_entities(hass, LIVING_MAC, {"fan.living": "Fan", "sensor.living_pm25": "PM 2.5"})
    hass.states.async_set(
        "fan.bedroom",
        "on",
        {"preset_mode": "Auto", "preset_modes": PRESETS, "percentage": 25, "percentage_step": 25},
    )
    hass.states.async_set(
        "fan.living",
        "off",
        {
            "preset_mode": None,
            "preset_modes": PRESETS,
            "percentage": 0,
            "percentage_step": 100 / 3,
        },
    )
    hass.states.async_set("sensor.bedroom_pm25", "5", UNIT)
    hass.states.async_set("sensor.living_pm25", "5", UNIT)


async def _fake_fans(hass: HomeAssistant) -> Calls:
    """Fan services that act like the purifiers: the state follows, with the call's context.

    The fan integration is set up first, so its services (registered once)
    do not replace these when the integration's group fans load.
    """
    assert await async_setup_component(hass, "fan", {})
    calls: Calls = []

    async def handle(call: ServiceCall) -> None:
        entity_id = call.data["entity_id"]
        calls.append(
            (call.service, entity_id, {k: v for k, v in call.data.items() if k != "entity_id"})
        )
        state = hass.states.get(entity_id)
        attributes = dict(state.attributes)
        value = state.state
        if call.service == "turn_off":
            value = "off"
        elif call.service == "turn_on":
            value = "on"
            if "percentage" in call.data:
                attributes["percentage"] = call.data["percentage"]
                attributes["preset_mode"] = "Manual"
            if "preset_mode" in call.data:
                attributes["preset_mode"] = call.data["preset_mode"]
        elif call.service == "set_preset_mode":
            value = "on"
            attributes["preset_mode"] = call.data["preset_mode"]
        hass.states.async_set(entity_id, value, attributes, context=call.context)

    for service in ("turn_on", "turn_off", "set_preset_mode"):
        hass.services.async_register("fan", service, handle)
    return calls


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Levoit ESPHome", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    """Send a command; its result, skipping subscription events."""
    await client.send_json_auto_id(message)
    while True:
        msg = await client.receive_json()
        if msg["id"] == message["id"] and msg["type"] == "result":
            return msg


async def _save(client: Any, **group: Any) -> dict[str, Any]:
    msg = await _call(
        client,
        {"type": "levoit_esphome/groups/save", "group": {"name": "Living room", **group}},
    )
    assert msg["success"], msg
    return msg["result"]


async def _settle(hass: HomeAssistant) -> None:
    await hass.async_block_till_done(wait_background_tasks=True)


async def _later(hass: HomeAssistant, freezer: FrozenDateTimeFactory, minutes: float) -> None:
    freezer.tick(timedelta(minutes=minutes))
    async_fire_time_changed(hass)
    await _settle(hass)


def _pm(hass: HomeAssistant, value: float, sensor: str = "sensor.living_pm25") -> None:
    hass.states.async_set(sensor, str(value), UNIT)


@pytest.mark.usefixtures("patch_sources")
async def test_group_takes_over_and_steps_down(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_storage: dict[str, Any],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Members at their speed for the level; up at once, down one level per hold."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)

    group = await _save(client, members=MEMBERS)
    assert [(s["entity_id"], s["type"], s["source"]) for s in group["sensors"]] == [
        ("sensor.bedroom_pm25", "pm25", "auto"),
        ("sensor.living_pm25", "pm25", "auto"),
    ]
    assert hass_storage[STORAGE_KEY]["data"]["groups"][0]["name"] == "Living room"
    await _settle(hass)
    # very good air is level 1: speed 1, the bedroom out of Auto, the living room on
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 25}),
        ("turn_on", "fan.living", {"percentage": 33}),
    ]
    assert hass.states.get(CONTROL).state == "on"
    assert hass.states.get(LEVEL).state == "1"
    assert hass.states.get(LEVEL).attributes["status"] == "in_control"
    assert hass.states.get(ACTIVE).state == "on"
    calls.clear()

    _pm(hass, 783)
    await _settle(hass)
    # 4 speeds: 4; 3 speeds: its top speed 3
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 100}),
        ("turn_on", "fan.living", {"percentage": 100}),
    ]
    level = hass.states.get(LEVEL)
    assert level.state == "4"
    assert level.attributes["status"] == "in_control"
    assert level.attributes["reason"].startswith("PM2.5 783 µg/m³")
    assert level.attributes["worst_sensor"] == "sensor.living_pm25"
    assert level.attributes["members_in_control"] == MEMBERS
    assert hass.states.get(ACTIVE).state == "on"

    calls.clear()
    _pm(hass, 3)
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "4"  # holds
    assert calls == []

    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "3"
    # 3 speeds for 4 levels: one each, level 4 stays at the top
    assert calls == [("turn_on", "fan.bedroom", {"percentage": 75})]  # living stays on 3
    calls.clear()
    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "2"
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 50}),
        ("turn_on", "fan.living", {"percentage": 66}),
    ]
    calls.clear()
    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "1"
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 25}),
        ("turn_on", "fan.living", {"percentage": 33}),
    ]
    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "1"  # never below level 1 with a value


@pytest.mark.usefixtures("patch_sources")
async def test_no_sensor_value_lets_go(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, freezer: FrozenDateTimeFactory
) -> None:
    """No sensor with a value: the level holds for hold_min, then the group lets go."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    await _save(client, members=MEMBERS)
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "1"
    calls.clear()

    hass.states.async_set("sensor.bedroom_pm25", "unavailable")
    hass.states.async_set("sensor.living_pm25", "unavailable")
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "1"  # holds for hold_min
    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "0"
    assert hass.states.get(LEVEL).attributes["status"] == "no_sensors"
    # let go: nothing is sent, both keep running on speed 1
    assert calls == []
    assert hass.states.get("fan.bedroom").attributes["percentage"] == 25
    assert hass.states.get(ACTIVE).state == "off"
    assert hass.states.get(LEVEL).attributes["members_in_control"] == []


@pytest.mark.usefixtures("patch_sources")
async def test_manual_change_pauses_that_member(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    freezer: FrozenDateTimeFactory,
) -> None:
    """A person's change pauses the group for that purifier only, for manual_pause_min."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    await _save(client, members=MEMBERS)
    _pm(hass, 783)
    await _settle(hass)
    calls.clear()

    bedroom = hass.states.get("fan.bedroom")
    hass.states.async_set(
        "fan.bedroom", "on", {**bedroom.attributes, "percentage": 25}, context=Context()
    )
    await _settle(hass)
    assert calls == []  # not set back
    assert hass.states.get(LEVEL).attributes["members_in_control"] == ["fan.living"]

    _pm(hass, 20)  # level 2, a level down per hold (level 3 keeps living on 3)
    await _later(hass, freezer, 10)
    await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "2"
    assert calls == [("turn_on", "fan.living", {"percentage": 66})]
    calls.clear()

    await _later(hass, freezer, 15)  # 35 minutes after the change: pause over
    assert calls == [("turn_on", "fan.bedroom", {"percentage": 50})]
    assert hass.states.get(LEVEL).attributes["members_in_control"] == MEMBERS


@pytest.mark.usefixtures("patch_sources")
async def test_control_switch_and_manual_mode(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """The switch off turns the purifiers off; Manual mode runs one level, sensors ignored."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS)
    _pm(hass, 783)
    await _settle(hass)
    calls.clear()

    await hass.services.async_call("switch", "turn_off", {"entity_id": CONTROL}, blocking=True)
    await _settle(hass)
    assert hass.states.get(CONTROL).state == "off"
    assert hass.states.get(LEVEL).attributes["status"] == "paused"
    # off means off: both purifiers, once
    assert calls == [("turn_off", "fan.bedroom", {}), ("turn_off", "fan.living", {})]
    assert hass.states.get(LEVEL).attributes["members_in_control"] == []
    calls.clear()
    await _settle(hass)
    assert calls == []

    await hass.services.async_call("switch", "turn_on", {"entity_id": CONTROL}, blocking=True)
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "4"
    calls.clear()

    await _save(client, id=group["id"], members=MEMBERS, mode="manual", manual_level=2)
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "2"
    assert hass.states.get(LEVEL).attributes["status"] == "manual"
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 50}),
        ("turn_on", "fan.living", {"percentage": 66}),
    ]


@pytest.mark.usefixtures("patch_sources")
async def test_panel_commands(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """Subscribe, validation, preview, dismiss and delete."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "levoit_esphome/groups/subscribe"})
    assert (await client.receive_json())["success"]
    event = (await client.receive_json())["event"]
    assert event["groups"] == []
    assert [(p["entity_id"], p["speeds"], p["group_id"]) for p in event["purifiers"]] == [
        ("fan.bedroom", 4, None),
        ("fan.living", 3, None),
    ]
    assert event["purifiers"][0]["sensors"] == [
        {"entity_id": "sensor.bedroom_pm25", "type": "pm25"}
    ]
    assert event["purifiers"][0]["sleep"] is True

    msg = await _call(
        client,
        {"type": "levoit_esphome/groups/save", "group": {"name": "x", "members": ["fan.bedroom"]}},
    )
    assert msg["error"]["code"] == "members"
    msg = await _call(
        client,
        {
            "type": "levoit_esphome/groups/save",
            "group": {"name": "x", "members": ["fan.bedroom", "fan.unknown"]},
        },
    )
    assert msg["error"]["code"] == "members"

    _pm(hass, 40)
    msg = await _call(
        client,
        {
            "type": "levoit_esphome/groups/preview",
            "group": {"members": MEMBERS, "removed_sensors": ["sensor.bedroom_pm25"]},
        },
    )
    assert msg["success"], msg
    preview = msg["result"]
    assert preview["level"] == 3
    assert preview["worst"] == "sensor.living_pm25"
    assert preview["worst_type"] == "pm25"
    assert preview["sensors"] == [
        {
            "entity_id": "sensor.living_pm25",
            "type": "pm25",
            "source": "auto",
            "value": 40.0,
            "level": 3,
        }
    ]
    assert preview["types"] == [
        {"type": "pm25", "value": 40.0, "level": 3, "sensors": ["sensor.living_pm25"]}
    ]
    assert preview["members"] == [
        {"entity_id": "fan.bedroom", "speeds": 4, "speed": 3},
        {"entity_id": "fan.living", "speeds": 3, "speed": 3},
    ]
    assert calls == []  # a preview changes nothing

    group = await _save(client, members=MEMBERS, removed_sensors=["sensor.bedroom_pm25"])
    assert [s["entity_id"] for s in group["sensors"]] == ["sensor.living_pm25"]
    msg = await _call(
        client,
        {"type": "levoit_esphome/groups/save", "group": {"name": "Other", "members": MEMBERS}},
    )
    assert msg["error"]["code"] == "members"  # already in Living room

    assert (await _call(client, {"type": "levoit_esphome/groups/dismiss", "area_id": "hall"}))[
        "success"
    ]
    await _settle(hass)
    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    assert msg["result"]["dismissed_areas"] == ["hall"]
    (listed,) = msg["result"]["groups"]
    assert listed["state"]["level"] == 3
    assert {p["entity_id"]: p["group_id"] for p in msg["result"]["purifiers"]} == {
        "fan.bedroom": group["id"],
        "fan.living": group["id"],
    }
    assert hass.states.get(LEVEL).state == "3"
    calls.clear()

    msg = await _call(client, {"type": "levoit_esphome/groups/delete", "group_id": group["id"]})
    assert msg["success"], msg
    await _settle(hass)
    assert calls == []  # the purifiers stay as they are
    assert hass.states.get(LEVEL) is None
    assert (
        dr.async_get(hass).async_get_device_by_identifier(
            (DOMAIN, f"group_{group['id']}"), entry.entry_id
        )
        is None
    )
    msg = await _call(client, {"type": "levoit_esphome/groups/delete", "group_id": group["id"]})
    assert msg["error"]["code"] == "not_found"


@pytest.mark.usefixtures("patch_sources")
async def test_old_runtime_is_ignored(hass: HomeAssistant, hass_storage: dict[str, Any]) -> None:
    """Snapshots stored by earlier versions are ignored: nothing is restored after a restart."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    hass.states.async_set(
        "fan.bedroom",
        "on",
        {
            "preset_mode": "Manual",
            "preset_modes": PRESETS,
            "percentage": 100,
            "percentage_step": 25,
        },
    )
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "key": STORAGE_KEY,
        "data": {
            "groups": [{"id": "g1", "name": "Living room", "members": MEMBERS, "hold_min": 0}],
            "runtime": {
                "g1": {
                    "level": 1,
                    "snapshots": {
                        "fan.bedroom": {"state": "on", "preset_mode": "Sleep", "percentage": 25}
                    },
                }
            },
        },
    }
    await _setup(hass)
    await _settle(hass)
    # stored groups keep their sensors as saved: none here, so no number to go on
    assert hass.states.get(LEVEL).state == "0"
    assert calls == []


@pytest.mark.usefixtures("patch_sources")
async def test_group_fan(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """The group as one fan: on / off is its control, Auto / Manual, speeds set the manual level.

    The fan services are the real ones here (the group's own fan has to take
    them); turning the group off turns its purifiers off as the switch does
    (test_control_switch_and_manual_mode).
    """
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    # no rising-fast jump: the level follows the thresholds
    await _save(client, members=MEMBERS, rise={"enabled": False})
    await _settle(hass)

    fan = hass.states.get(GROUP_FAN)
    assert fan.state == "on"
    assert fan.attributes["preset_modes"] == ["Auto", "Manual"]
    assert fan.attributes["preset_mode"] == "Auto"
    assert fan.attributes["percentage"] == 25  # very good air: level 1
    assert fan.attributes["percentage_step"] == 25

    _pm(hass, 40)  # level 3 in Auto
    await _settle(hass)
    assert hass.states.get(GROUP_FAN).attributes["percentage"] == 75

    await hass.services.async_call(
        "fan", "set_percentage", {"entity_id": GROUP_FAN, "percentage": 50}, blocking=True
    )
    await _settle(hass)
    fan = hass.states.get(GROUP_FAN)
    assert fan.attributes["preset_mode"] == "Manual"
    assert fan.attributes["percentage"] == 50
    assert hass.states.get(LEVEL).state == "2"

    await hass.services.async_call(
        "fan", "set_preset_mode", {"entity_id": GROUP_FAN, "preset_mode": "Auto"}, blocking=True
    )
    await _settle(hass)
    assert hass.states.get(GROUP_FAN).attributes["preset_mode"] == "Auto"

    await hass.services.async_call("fan", "turn_off", {"entity_id": GROUP_FAN}, blocking=True)
    await _settle(hass)
    assert hass.states.get(GROUP_FAN).state == "off"
    assert hass.states.get(CONTROL).state == "off"

    await hass.services.async_call(
        "fan", "turn_on", {"entity_id": GROUP_FAN, "percentage": 100}, blocking=True
    )
    await _settle(hass)
    fan = hass.states.get(GROUP_FAN)
    assert fan.state == "on"
    assert fan.attributes["preset_mode"] == "Manual"
    assert fan.attributes["percentage"] == 100
    assert hass.states.get(CONTROL).state == "on"

    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    (group,) = msg["result"]["groups"]
    assert (group["mode"], group["manual_level"], group["enabled"]) == ("manual", 4, True)


@pytest.mark.usefixtures("patch_sources")
async def test_group_air_quality(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """1-4 from the worst sensor type, in Manual and with the group off too."""
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS, mode="manual", manual_level=2)
    await _settle(hass)
    quality = hass.states.get(AIR_QUALITY)
    assert quality.state == "1"
    assert quality.attributes["sensor_levels"] == {
        "sensor.bedroom_pm25": 1,
        "sensor.living_pm25": 1,
    }

    _pm(hass, 40)  # level 3
    await _settle(hass)
    quality = hass.states.get(AIR_QUALITY)
    assert quality.state == "3"
    assert quality.attributes["worst_sensor"] == "sensor.living_pm25"
    assert hass.states.get(LEVEL).state == "2"  # Manual: the group runs at its level

    await _save(client, id=group["id"], members=MEMBERS, enabled=False)
    _pm(hass, 160)
    await _settle(hass)
    assert hass.states.get(AIR_QUALITY).state == "4"
    assert hass.states.get(LEVEL).state == "0"

    hass.states.async_set("sensor.bedroom_pm25", "unavailable")
    hass.states.async_set("sensor.living_pm25", "unavailable")
    await _settle(hass)
    assert hass.states.get(AIR_QUALITY).state == "unknown"


@pytest.mark.usefixtures("patch_sources")
async def test_member_highest_speed(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """A purifier limited to speed 2 never goes above it."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS, member_speeds={"fan.bedroom": {"highest": 2}})
    assert group["member_speeds"] == {"fan.bedroom": {"lowest": 1, "highest": 2}}
    await _settle(hass)
    calls.clear()
    _pm(hass, 783)
    await _settle(hass)
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 50}),  # speed 2 of 4
        ("turn_on", "fan.living", {"percentage": 100}),
    ]


def _everest(hass: HomeAssistant) -> None:
    """The living room purifier as an Everest Air: 3 speeds and a Turbo preset, off."""
    hass.states.async_set(
        "fan.living",
        "off",
        {
            "preset_mode": None,
            "preset_modes": [*PRESETS, "Turbo"],
            "percentage": 0,
            "percentage_step": 100 / 3,
        },
    )


@pytest.mark.usefixtures("patch_sources")
async def test_everest_turbo_is_the_top_speed(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """A fan with a Turbo preset counts it as its 4th speed."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    _everest(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    await _save(client, members=MEMBERS)
    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    speeds = {p["entity_id"]: p["speeds"] for p in msg["result"]["purifiers"]}
    assert speeds == {"fan.bedroom": 4, "fan.living": 4}
    await _settle(hass)
    calls.clear()
    _pm(hass, 783)
    await _settle(hass)
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 100}),
        ("turn_on", "fan.living", {"preset_mode": "Turbo"}),
    ]
    # Turbo is what the group set: no pause, nothing sent again
    _pm(hass, 790)
    await _settle(hass)
    assert len(calls) == 2
    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    living = next(
        m for m in msg["result"]["groups"][0]["state"]["members"] if m["entity_id"] == "fan.living"
    )
    assert living == {
        "entity_id": "fan.living",
        "speed": 4,
        "in_control": True,
        "paused_until": None,
    }


@pytest.mark.usefixtures("patch_sources")
async def test_everest_limited_below_turbo(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Held to speed 3, the Everest Air never gets Turbo."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    _everest(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    await _save(client, members=MEMBERS, member_speeds={"fan.living": {"highest": 3}})
    _pm(hass, 783)
    await _settle(hass)
    assert ("turn_on", "fan.living", {"percentage": 100}) in calls
    assert all(c[2].get("preset_mode") != "Turbo" for c in calls)


@pytest.mark.usefixtures("patch_sources")
async def test_off_and_sleep_as_lowest(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, freezer: FrozenDateTimeFactory
) -> None:
    """Level 1 can put a purifier in Sleep or turn it off; that is not a change by hand."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    await _save(
        client,
        members=MEMBERS,
        member_speeds={"fan.bedroom": {"lowest": "sleep"}, "fan.living": {"lowest": "off"}},
    )
    await _settle(hass)
    # the living room purifier is off already: nothing to send
    assert calls == [("turn_on", "fan.bedroom", {"preset_mode": "Sleep"})]
    state = (await _call(client, {"type": "levoit_esphome/groups/list"}))["result"]["groups"][0]
    assert [(m["entity_id"], m["speed"], m["in_control"]) for m in state["state"]["members"]] == [
        ("fan.bedroom", "sleep", True),
        ("fan.living", "off", True),
    ]
    calls.clear()

    _pm(hass, 783)
    await _settle(hass)
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 100}),
        ("turn_on", "fan.living", {"percentage": 100}),
    ]
    calls.clear()
    _pm(hass, 3)
    for _ in range(3):
        await _later(hass, freezer, 10)
    assert hass.states.get(LEVEL).state == "1"
    assert calls[-2:] == [
        ("turn_on", "fan.bedroom", {"preset_mode": "Sleep"}),
        ("turn_off", "fan.living", {}),
    ]
    # what the group set: nobody is paused
    members = hass.states.get(LEVEL).attributes["members_in_control"]
    assert members == MEMBERS


@pytest.mark.usefixtures("patch_sources")
async def test_combined_sensors(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """Two PM2.5 sensors: the highest by default, or their average."""
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS, rise={"enabled": False})
    _pm(hass, 10, "sensor.bedroom_pm25")
    _pm(hass, 60)
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "4"  # the highest: 60

    await _save(
        client, id=group["id"], members=MEMBERS, rise={"enabled": False}, combine={"pm25": "avg"}
    )
    await _settle(hass)
    level = hass.states.get(LEVEL)
    assert level.state == "4"  # holds: down one level per hold time
    quality = hass.states.get(AIR_QUALITY)
    assert quality.state == "3"  # the average: 35
    assert level.attributes["reason"] == "PM2.5 35 µg/m³ (average of 2)"


@pytest.mark.usefixtures("patch_sources")
async def test_apply_now(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, freezer: FrozenDateTimeFactory
) -> None:
    """The editor's apply button: the sensors' level at once, and paused purifiers again."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS, hold_min=30)
    _pm(hass, 783)
    await _settle(hass)
    bedroom = hass.states.get("fan.bedroom")
    hass.states.async_set(
        "fan.bedroom", "on", {**bedroom.attributes, "percentage": 25}, context=Context()
    )
    _pm(hass, 20)  # level 2, but the hold keeps level 4
    await _later(hass, freezer, 1)
    assert hass.states.get(LEVEL).state == "4"
    calls.clear()

    msg = await _call(client, {"type": "levoit_esphome/groups/apply", "group_id": group["id"]})
    assert msg["success"], msg
    assert msg["result"]["level"] == 2
    await _settle(hass)
    assert hass.states.get(LEVEL).state == "2"
    assert calls == [
        ("turn_on", "fan.bedroom", {"percentage": 50}),
        ("turn_on", "fan.living", {"percentage": 66}),
    ]
    assert hass.states.get(LEVEL).attributes["members_in_control"] == MEMBERS

    msg = await _call(client, {"type": "levoit_esphome/groups/apply", "group_id": "nope"})
    assert msg["error"]["code"] == "not_found"


@pytest.mark.usefixtures("patch_sources")
async def test_group_saved_by_0_6(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, hass_storage: dict[str, Any]
) -> None:
    """A group from 0.6 loads: AQI index dropped, its max speeds become highest speeds."""
    _purifiers(hass)
    hass_storage[STORAGE_KEY] = {
        "version": 1,
        "key": STORAGE_KEY,
        "data": {
            "groups": [
                {
                    "id": "g1",
                    "name": "Living room",
                    "members": MEMBERS,
                    "sensors": [
                        {"entity_id": "sensor.bedroom_pm25", "type": "pm25", "source": "auto"},
                        {"entity_id": "sensor.eleva_aqi", "type": "aqi_index", "source": "manual"},
                    ],
                    "max_speed": 3,
                    "member_max_speed": {"fan.bedroom": 2},
                    "thresholds": {
                        "pm25": [12, 35, 55, 150],
                        "aqi": [2, 3, 4, 4],
                        "aqi_index": [50, 100, 150, 200],
                    },
                    "rise": {"enabled": True, "pm25": 20, "aqi_index": 25, "window_min": 5},
                }
            ]
        },
    }
    await _setup(hass)
    client = await hass_ws_client(hass)
    (group,) = (await _call(client, {"type": "levoit_esphome/groups/list"}))["result"]["groups"]
    assert [s["entity_id"] for s in group["sensors"]] == ["sensor.bedroom_pm25"]
    assert group["thresholds"]["pm25"] == [35, 55, 150]
    assert group["member_speeds"] == {
        "fan.bedroom": {"lowest": 1, "highest": 2},
        "fan.living": {"lowest": 1, "highest": 3},
    }
    assert "max_speed" not in group


@pytest.mark.usefixtures("patch_sources")
async def test_group_value_sensors(hass: HomeAssistant, hass_ws_client: WebSocketGenerator) -> None:
    """One sensor per type the group has, combined as set, and the total CADR."""
    _purifiers(hass)
    _add_entities(hass, MAC, {"sensor.bedroom_cadr": "Current CADR"})
    hass.states.async_set("sensor.bedroom_cadr", "120", {"unit_of_measurement": "m³/h"})
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS, rise={"enabled": False})
    await _settle(hass)

    pm25 = hass.states.get("sensor.living_room_pm2_5")
    assert pm25.state == "5.0"
    assert pm25.attributes["combine"] == "max"
    assert pm25.attributes["sensors"] == ["sensor.bedroom_pm25", "sensor.living_pm25"]
    assert pm25.attributes["level"] == 1
    assert hass.states.get("sensor.living_room_cadr").state == "120.0"
    assert hass.states.get("sensor.living_room_pm1") is None  # no PM1 sensor
    assert hass.states.get("sensor.living_room_pm10") is None

    _pm(hass, 10, "sensor.bedroom_pm25")
    _pm(hass, 60)
    await _save(
        client,
        id=group["id"],
        members=MEMBERS,
        rise={"enabled": False},
        combine={"pm25": "avg"},
        sensors=[{"entity_id": "sensor.wall_pm10", "type": "pm10", "source": "manual"}],
    )
    hass.states.async_set("sensor.wall_pm10", "63", UNIT)
    await _settle(hass)
    assert hass.states.get("sensor.living_room_pm2_5").state == "35.0"
    assert hass.states.get("sensor.living_room_pm10").state == "63.0"
    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    (listed,) = msg["result"]["groups"]
    assert listed["entities"]["pm10"] == "sensor.living_room_pm10"
    assert listed["state"]["values"]["pm25"]["how"] == "avg"
    assert listed["state"]["cadr"] == {"value": 120.0, "sensors": ["sensor.bedroom_cadr"]}

    # the PM10 sensor removed: its group sensor goes too
    await _save(
        client, id=group["id"], members=MEMBERS, rise={"enabled": False}, combine={"pm25": "avg"}
    )
    await _settle(hass)
    assert hass.states.get("sensor.living_room_pm10") is None
    assert (
        er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"group_{group['id']}_pm10")
        is None
    )

    hass.states.async_set("sensor.wall_pm10", "unavailable")
    hass.states.async_set("sensor.bedroom_pm25", "unavailable")
    hass.states.async_set("sensor.living_pm25", "unavailable")
    await _settle(hass)
    assert hass.states.get("sensor.living_room_pm2_5").state == "unavailable"


@pytest.mark.usefixtures("patch_sources")
async def test_cards_for_any_user(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """The dashboard cards' purifiers and groups, for a user who is not an admin."""
    _purifiers(hass)
    await _setup(hass)
    admin = await hass_ws_client(hass)
    group = await _save(admin, members=MEMBERS)
    await _settle(hass)

    client = await hass_ws_client(hass, hass_read_only_access_token)
    msg = await _call(client, {"type": "levoit_esphome/cards"})
    assert msg["success"], msg
    bedroom = msg["result"]["purifiers"][0]
    assert bedroom["entity_id"] == "fan.bedroom"
    assert bedroom["pm25"] == "sensor.bedroom_pm25"
    assert bedroom["group_id"] == group["id"]
    (listed,) = msg["result"]["groups"]
    assert listed["members"] == MEMBERS
    assert listed["entities"]["fan"] == GROUP_FAN
    assert "thresholds" not in listed  # names and entities only

    # the panel's group commands stay admins only
    msg = await _call(client, {"type": "levoit_esphome/groups/list"})
    assert msg["error"]["code"] == "unauthorized"


@pytest.mark.usefixtures("patch_sources")
async def test_off_turns_off_paused_and_skips_off_and_offline(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Off is off for a purifier paused by hand too; one that is off or offline gets nothing."""
    calls = await _fake_fans(hass)
    _purifiers(hass)
    await _setup(hass)
    client = await hass_ws_client(hass)
    group = await _save(client, members=MEMBERS)
    await _settle(hass)
    # someone runs the bedroom one by hand: the group pauses it
    bedroom = hass.states.get("fan.bedroom")
    hass.states.async_set("fan.bedroom", "on", {**bedroom.attributes, "percentage": 100})
    await _settle(hass)
    assert hass.states.get(LEVEL).attributes["members_in_control"] == ["fan.living"]
    living = hass.states.get("fan.living")
    hass.states.async_set("fan.living", "unavailable", living.attributes)
    calls.clear()

    await _save(client, id=group["id"], members=MEMBERS, enabled=False)
    await _settle(hass)
    assert calls == [("turn_off", "fan.bedroom", {})]

    # off already: turning it off again, or saving it off, sends nothing
    calls.clear()
    await _save(client, id=group["id"], members=MEMBERS, enabled=False, hold_min=3)
    await hass.services.async_call("switch", "turn_off", {"entity_id": CONTROL}, blocking=True)
    await _settle(hass)
    assert calls == []

    # a deleted group still lets go
    await hass.services.async_call("switch", "turn_on", {"entity_id": CONTROL}, blocking=True)
    hass.states.async_set("fan.living", "on", living.attributes)
    await _settle(hass)
    calls.clear()
    assert (await _call(client, {"type": "levoit_esphome/groups/delete", "group_id": group["id"]}))[
        "success"
    ]
    await _settle(hass)
    assert calls == []
