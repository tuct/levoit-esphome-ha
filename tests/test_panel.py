"""Sidebar panel: the option, and its WebSocket commands."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.levoit_esphome.const import DOMAIN, PANEL_URL_PATH
from custom_components.levoit_esphome.panel import PANEL_GRACE
from homeassistant.components.frontend import DATA_PANELS, EVENT_PANELS_UPDATED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .conftest import FakeBuilder, assert_compiled


async def _setup(hass: HomeAssistant, options: dict[str, Any] | None = None) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Levoit ESPHome", data={}, options=options or {})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _set_option(hass: HomeAssistant, entry: MockConfigEntry, show: bool) -> None:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["step_id"] == "init"
    await hass.config_entries.options.async_configure(result["flow_id"], {"show_panel": show})
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_panel_behind_option(hass: HomeAssistant) -> None:
    """Off by default; the option adds and removes it; admins only."""
    entry = await _setup(hass)
    assert PANEL_URL_PATH not in hass.data.get(DATA_PANELS, {})

    await _set_option(hass, entry, True)
    panel = hass.data[DATA_PANELS][PANEL_URL_PATH]
    assert panel.require_admin
    assert panel.sidebar_title == "Levoit ESPHome"
    custom = panel.config["_panel_custom"]
    assert custom["name"] == "levoit-esphome-panel"
    assert custom["module_url"].startswith("/levoit_esphome_static/levoit-esphome-panel.js?v=")

    await _set_option(hass, entry, False)
    assert PANEL_URL_PATH not in hass.data.get(DATA_PANELS, {})


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_panel_stays_through_a_reload(hass: HomeAssistant) -> None:
    """Adding a device sets the entry up again: the open page must not be sent away.

    Removing the panel for that moment makes the frontend open the default
    dashboard; so the sidebar entry stays, and goes only when the entry stays
    unloaded, or at once when it is deleted.
    """
    entry = await _setup(hass, {"show_panel": True})
    panel = hass.data[DATA_PANELS][PANEL_URL_PATH]
    updates: list[Event] = []

    @callback
    def panels_updated(event: Event) -> None:
        updates.append(event)

    hass.bus.async_listen(EVENT_PANELS_UPDATED, panels_updated)

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert hass.data[DATA_PANELS][PANEL_URL_PATH] is panel  # the same entry, untouched
    assert updates == []
    # nothing left to remove it later either
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=PANEL_GRACE + 1))
    await hass.async_block_till_done()
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]

    # unloaded and not set up again: gone after the grace
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=2 * PANEL_GRACE + 2))
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data.get(DATA_PANELS, {})

    # deleted: gone at once
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert PANEL_URL_PATH in hass.data[DATA_PANELS]
    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert PANEL_URL_PATH not in hass.data.get(DATA_PANELS, {})


def _assert_steps(
    build: dict[str, Any], *, upload: bool, done: int, tail: list[str] | None = None
) -> None:
    """The build's steps as the panel gets them: the first `done` done, the rest not."""
    keys = ["setup", "compile", "link", "result"] + (["upload"] if upload else [])
    assert build["upload"] is upload
    assert [s["key"] for s in build["steps"]] == keys
    assert [s["state"] == "done" for s in build["steps"]] == [i < done for i in range(len(keys))]
    assert build["tail"] == (tail or [])


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    """Send a command; its result, skipping subscription events."""
    await client.send_json_auto_id(message)
    while True:
        msg = await client.receive_json()
        if msg["id"] == message["id"] and msg["type"] == "result":
            return msg


@pytest.mark.usefixtures("esphome_devices")
async def test_subscribe_and_build(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """The devices come with versions and state; build compiles in the Device Builder."""
    await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "levoit_esphome/subscribe"})
    sub = await client.receive_json()
    assert sub["success"]
    event = (await client.receive_json())["event"]
    assert event["heads"]["stable"]["version"] == "1.8.0+abcdef1"
    assert event["builder_url"] == "/app/5c53de3b_esphome"
    (device,) = event["devices"]
    assert device["name"] == "bedroom-purifier"
    assert device["installed"] == "1.7.0+10361cc"
    assert device["latest"] == "1.8.0+abcdef1"
    assert device["update_available"] is True
    assert device["configuration"] == "bedroom-purifier.yaml"
    assert device["config_kind"] == "custom"
    assert device["can_set_channel"] is False
    assert device["building"] is False
    assert device["build_step"] is None
    assert device["build"] is None
    assert device["device_id"]

    build = {"type": "levoit_esphome/build", "name": "bedroom-purifier", "upload": False}
    await client.send_json_auto_id(build)
    build_id = build["id"]
    seen_building = False
    while True:
        msg = await client.receive_json()
        if msg["type"] == "event":
            seen_building |= msg["event"]["devices"][0]["building"]
            continue
        assert msg["id"] == build_id
        assert msg["success"]
        break
    assert seen_building
    assert_compiled(builder, "bedroom-purifier.yaml")
    builder.api.upload.assert_not_awaited()
    coordinator = hass.config_entries.async_entries(DOMAIN)[0].runtime_data
    last = coordinator.last_builds["bedroom-purifier"]
    assert last.ok
    assert not last.upload
    # the build's steps, for the panel: nothing was printed, so all done, no detail
    _assert_steps(coordinator.build_summary("bedroom-purifier"), upload=False, done=4)


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_build_fails(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, builder: FakeBuilder
) -> None:
    """A failed compile: an error naming the cause, the failure and the output kept."""
    await _setup(hass)
    client = await hass_ws_client(hass)

    async def failing_compile(configuration: str, line_received_cb: Any = None) -> bool:
        for line in (
            r"\033[32mINFO Compiling app...\033[0m",
            "\x1b[31msrc/main.cpp:12: error: 'foo' was not declared\x1b[0m",
            "========== [FAILED] ==========",
        ):
            line_received_cb(line)
        return False

    builder.api.compile.side_effect = failing_compile
    result = await _call(
        client, {"type": "levoit_esphome/build", "name": "bedroom-purifier", "upload": True}
    )
    assert not result["success"]
    last = hass.config_entries.async_entries(DOMAIN)[0].runtime_data.last_builds["bedroom-purifier"]
    assert not last.ok
    assert "src/main.cpp:12: error: 'foo' was not declared" in last.error
    builder.api.upload.assert_not_awaited()

    log = await _call(client, {"type": "levoit_esphome/build_log", "name": "bedroom-purifier"})
    assert log["result"]["building"] is False
    assert log["result"]["lines"] == [
        "INFO Compiling app...",
        "src/main.cpp:12: error: 'foo' was not declared",  # colour codes removed
        "========== [FAILED] ==========",
    ]
    # the steps: nothing compiled yet, so the setup failed, with the reason
    _assert_steps(log["result"]["build"], upload=True, done=0, tail=log["result"]["lines"])
    assert log["result"]["build"]["steps"][0] == {
        "key": "setup",
        "state": "failed",
        "detail": "src/main.cpp:12: error: 'foo' was not declared",
    }


@pytest.mark.usefixtures("esphome_devices")
async def test_commands_refuse(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, patch_sources: AsyncMock
) -> None:
    """Unknown device, custom config channel, bad channel."""
    await _setup(hass)
    client = await hass_ws_client(hass)

    result = await _call(client, {"type": "levoit_esphome/build", "name": "nope", "upload": True})
    assert result["error"]["code"] == "not_found"

    result = await _call(
        client,
        {"type": "levoit_esphome/set_channel", "name": "bedroom-purifier", "channel": "main"},
    )
    assert not result["success"]

    result = await _call(
        client, {"type": "levoit_esphome/set_channel", "name": "bedroom-purifier", "channel": "dev"}
    )
    assert result["error"]["code"] == "invalid_format"


@pytest.mark.usefixtures("esphome_devices")
async def test_check_now(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, patch_sources: AsyncMock
) -> None:
    """Check reads GitHub again, without waiting for the 6 hours."""
    await _setup(hass)
    assert patch_sources.await_count == 1
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": "levoit_esphome/check"})
    assert result["success"]
    assert patch_sources.await_count == 2


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_admins_only(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """A user who is not an admin gets nothing."""
    await _setup(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": "levoit_esphome/subscribe"})
    result = await client.receive_json()
    assert result["error"]["code"] == "unauthorized"
