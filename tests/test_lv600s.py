"""Discovery, fan controls and extras for the LV600S."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.levoit_esphome.controls import (
    config_names,
    lv600s_stores_target,
    match_controls,
    page_supported,
)
from custom_components.levoit_esphome.versions import component_model, component_source
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .conftest import MAC, add_esphome_device
from .test_controls import _add_entities, _controls
from .test_init import _setup


@pytest.mark.usefixtures("patch_sources")
async def test_standalone_lv600s_still_discovered(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    config = {
        "lv600s_humidifier": {"model": "LV600S", "current_humidity": {"name": "Room humidity"}},
        "external_components": [
            {"source": "github://tuct/levoit@main", "components": ["lv600s_humidifier"]}
        ],
        "switch": [{"platform": "template", "id": "humidifier_power", "name": "Mist power"}],
    }
    assert component_model(config) == "LV600S"
    assert component_source(config) == ("main", "main")
    assert config_names(config) == {"sensor.humidity": "Room humidity"}

    hass.config.components.add("esphome")
    add_esphome_device(hass, "living-humidifier", MAC, "Humidifier", None, model="LV600S")
    _add_entities(hass, MAC, {"switch.power": "Mist power", "fan.auxiliary": "Fan"})
    await _setup(hass)
    state = hass.states.get("sensor.humidifier_component_model")
    assert state is not None and state.state == "LV600S"
    page = await _controls(await hass_ws_client(hass), "living-humidifier")
    assert not page["supported"]
    assert "fan.fan" not in page["controls"]


@pytest.mark.parametrize("device_aware", [False, True])
async def test_lv600s_prefers_available_formatted_timer(
    hass: HomeAssistant, device_aware: bool
) -> None:
    add_esphome_device(hass, "living-humidifier", MAC, "Humidifier", None, model="LV600S")
    ids = _add_entities(hass, MAC, {"sensor.timer_seconds": "Timer Remaining"})
    registry = er.async_get(hass)
    numeric = registry.async_get(ids["sensor.timer_seconds"])
    timer_id = (
        f"{MAC}/0/text_sensor/Timer Remaining"
        if device_aware
        else f"{MAC}-text_sensor-timer_remaining"
    )
    formatted = registry.async_get_or_create(
        "sensor",
        "esphome",
        timer_id,
        device_id=numeric.device_id,
        original_name="Timer Remaining",
        suggested_object_id="formatted_timer",
    )
    hass.states.async_set(numeric.entity_id, "60")
    hass.states.async_set(formatted.entity_id, "1 min")
    key = "text_sensor.timer_duration_remaining"
    assert match_controls(hass, numeric.device_id, "LV600S")[key] == formatted.entity_id
    configured = {key: "Timer Remaining"}
    assert match_controls(hass, numeric.device_id, "LV600S", configured)[key] == formatted.entity_id
    hass.states.async_set(formatted.entity_id, "unavailable")
    assert match_controls(hass, numeric.device_id, "LV600S")[key] == numeric.entity_id
    assert match_controls(hass, numeric.device_id, "LV600S", configured)[key] == numeric.entity_id
    hass.states.async_set(formatted.entity_id, "Unknown")
    assert match_controls(hass, numeric.device_id, "LV600S")[key] == formatted.entity_id


@pytest.mark.usefixtures("patch_sources")
async def test_lv600s_panel_uses_fan_outside_purifier_groups(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    hass.config.components.add("esphome")
    add_esphome_device(hass, "living-humidifier", MAC, "Humidifier", None, model="LV600S")
    names = {
        "fan.fan": "Humidifier",
        "switch.display": "Display",
        "text_sensor.reported_mode": "Operating Mode Status",
        "number.humidity_target": "Target Humidity Preset",
        "sensor.mist_level": "Mist Level",
        "number.warm_level": "Warm Level",
        "number.timer": "Timer (min)",
        "text_sensor.timer_duration_remaining": "Timer Remaining",
        "text_sensor.timer_duration_initial": "Timer Duration",
        "sensor.humidity": "Humidity",
        "sensor.temperature": "Temperature",
        "binary_sensor.water_tank_empty": "Water Tank Empty",
        "binary_sensor.tank_removed": "Tank Removed",
        "binary_sensor.mcu_connection": "MCU Connection",
        "binary_sensor.mcu_fault": "MCU Fault",
    }
    keys = {key: key.replace("text_sensor.", "sensor.", 1) for key in names}
    ids = _add_entities(
        hass, MAC, {**{keys[key]: name for key, name in names.items()}, "number.mist": "Mist Level"}
    )
    await _setup(hass)
    client = await hass_ws_client(hass)
    page = await _controls(client, "living-humidifier")
    assert page["supported"] and page["model"] == "LV600S"
    assert page["controls"] == {key: ids[keys[key]] for key in names}
    assert page["target_humidity_preset"]
    await client.send_json_auto_id({"type": "levoit_esphome/groups/subscribe"})
    assert (await client.receive_json())["success"]
    assert (await client.receive_json())["event"]["purifiers"] == []


@pytest.mark.parametrize("as_list", [False, True])
async def test_shared_core_lv600s_with_renamed_entities(hass: HomeAssistant, as_list: bool) -> None:
    add_esphome_device(hass, "living-humidifier", MAC, "Humidifier", None, model="LV600S")
    model = {"model": "LV600S"}
    config = {
        "levoit": [model] if as_list else model,
        "fan": [{"platform": "levoit", "name": "Bedroom humidifier"}],
        "sensor": [{"platform": "levoit", "type": "mist_level", "name": "Mist output"}],
        "number": [
            {"platform": "template", "id": "humidifier_target_preset", "name": "Desired moisture"}
        ],
        "text_sensor": [
            {"platform": "template", "id": "humidifier_timer_remaining", "name": "Countdown left"}
        ],
    }
    assert component_model(config) == "LV600S"
    names = config_names(config)
    ids = _add_entities(
        hass,
        MAC,
        {
            "fan.humidifier": "Bedroom humidifier",
            "sensor.mist": "Mist output",
            "number.target": "Desired moisture",
            "sensor.timer": "Countdown left",
        },
    )
    entry = er.async_get(hass).async_get(ids["fan.humidifier"])
    found = match_controls(hass, entry.device_id, "LV600S", names)
    assert found == {
        "fan.fan": ids["fan.humidifier"],
        "sensor.mist_level": ids["sensor.mist"],
        "number.humidity_target": ids["number.target"],
        "text_sensor.timer_duration_remaining": ids["sensor.timer"],
    }
    assert page_supported("LV600S", {"levoit"}, found)
    assert lv600s_stores_target(hass, found["number.humidity_target"], names)
