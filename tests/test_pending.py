"""Configs made by Add device and not flashed yet: listed, compiled, auto-added."""

from __future__ import annotations

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.levoit_esphome.const import AUTO_ADD_INTERVAL, DOMAIN
from homeassistant.config_entries import SOURCE_USER, ConfigSubentryData
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.util import dt as dt_util

from .conftest import CORE300S, FakeBuilder, add_esphome_device, assert_compiled

NEW_MAC = "de:ad:be:ef:00:01"


def _subentry(name: str, **data: Any) -> ConfigSubentryData:
    return ConfigSubentryData(
        data={
            "configuration": f"{name}.yaml",
            "template": CORE300S.file,
            "existing": False,
            "custom": False,
            **data,
        },
        subentry_type="device",
        title=name,
        unique_id=name,
    )


@pytest.fixture
def pending_builder(builder: FakeBuilder) -> FakeBuilder:
    """The Device Builder also has the new living-room config (not flashed)."""
    builder.api.configured.append(
        {
            "name": "living-room",
            "configuration": "living-room.yaml",
            "address": "living-room.local",
            "loaded_integrations": ["api", "levoit", "uart", "wifi"],
        }
    )
    return builder


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Levoit ESPHome",
        data={},
        subentries_data=[
            _subentry("living-room"),
            # made for a device already in Home Assistant: updated over the air
            _subentry("garage-sensor", existing=True),
            # its config was deleted in the Device Builder
            _subentry("gone"),
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    await client.send_json_auto_id(message)
    while True:
        msg = await client.receive_json()
        if msg["id"] == message["id"] and msg["type"] == "result":
            return msg


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_pending_listed_and_compiled(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator, pending_builder: FakeBuilder
) -> None:
    """Listed until flashed; it compiles, but cannot be uploaded over the air."""
    with patch.object(hass.config_entries.flow, "async_init", AsyncMock()):
        await _setup(hass)
    client = await hass_ws_client(hass)

    await client.send_json_auto_id({"type": "levoit_esphome/subscribe"})
    assert (await client.receive_json())["success"]
    event = (await client.receive_json())["event"]
    assert [d["name"] for d in event["devices"]] == ["bedroom-purifier"]
    (pending,) = event["pending"]
    assert pending["name"] == "living-room"
    assert pending["configuration"] == "living-room.yaml"
    assert pending["model"] == "CORE300S"
    assert pending["config_kind"] == "original"
    assert pending["last_build"] is None

    result = await _call(
        client, {"type": "levoit_esphome/build", "name": "living-room", "upload": True}
    )
    assert result["error"]["code"] == "not_flashed"
    pending_builder.api.compile.assert_not_awaited()

    result = await _call(
        client, {"type": "levoit_esphome/build", "name": "living-room", "upload": False}
    )
    assert result["success"]
    await hass.async_block_till_done(wait_background_tasks=True)
    assert_compiled(pending_builder, "living-room.yaml")
    pending_builder.api.upload.assert_not_awaited()


@pytest.mark.usefixtures("esphome_devices", "patch_sources", "pending_builder")
async def test_auto_add_after_flash(hass: HomeAssistant) -> None:
    """Once flashed, the ESPHome integration's flow adds it; then it stops looking."""
    init = AsyncMock(return_value={"type": FlowResultType.FORM, "flow_id": "f1", "errors": {}})
    abort = MagicMock()
    with (
        patch.object(hass.config_entries.flow, "async_init", init),
        patch.object(hass.config_entries.flow, "async_abort", abort),
    ):
        entry = await _setup(hass)
        coordinator = entry.runtime_data
        assert list(coordinator.data.pending) == ["living-room"]

        # not reachable yet: the flow it started is not left behind
        async_fire_time_changed(hass, dt_util.utcnow() + AUTO_ADD_INTERVAL)
        await hass.async_block_till_done(wait_background_tasks=True)
        init.assert_awaited_once_with(
            "esphome",
            context={"source": SOURCE_USER},
            data={"host": "living-room.local", "port": 6053},
        )
        abort.assert_called_once_with("f1")

        # flashed: the flow creates the ESPHome entry
        init.reset_mock()
        init.return_value = {"type": FlowResultType.CREATE_ENTRY}

        def flashed(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            add_esphome_device(hass, "living-room", NEW_MAC, "living-room", None)
            return init.return_value

        init.side_effect = flashed
        async_fire_time_changed(hass, dt_util.utcnow() + AUTO_ADD_INTERVAL * 2)
        await hass.async_block_till_done(wait_background_tasks=True)
        init.assert_awaited_once()
        assert "living-room" in coordinator.data.devices
        assert coordinator.data.pending == {}

        # nothing pending: no more looking
        init.reset_mock()
        async_fire_time_changed(hass, dt_util.utcnow() + AUTO_ADD_INTERVAL * 3)
        await hass.async_block_till_done(wait_background_tasks=True)
        init.assert_not_awaited()


@pytest.mark.usefixtures("esphome_devices", "patch_sources", "pending_builder")
async def test_auto_add_skips_known_names(hass: HomeAssistant) -> None:
    """An ESPHome entry with that name already exists: no flow is started."""
    init = AsyncMock()
    with patch.object(hass.config_entries.flow, "async_init", init):
        entry = await _setup(hass)
        # in the ESPHome integration, but not detected as ours yet (no MAC device)
        MockConfigEntry(domain="esphome", data={"device_name": "living-room"}).add_to_hass(hass)
        assert list(entry.runtime_data.data.pending) == ["living-room"]
        async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=31))
        await hass.async_block_till_done(wait_background_tasks=True)
    init.assert_not_awaited()


@pytest.mark.usefixtures("esphome_devices", "patch_sources", "pending_builder")
async def test_added_elsewhere_listed_at_next_look(hass: HomeAssistant) -> None:
    """Added from Home Assistant's discovery: listed at the next look, not after the scan."""
    init = AsyncMock()
    with patch.object(hass.config_entries.flow, "async_init", init):
        entry = await _setup(hass)
        coordinator = entry.runtime_data
        assert list(coordinator.data.pending) == ["living-room"]
        # the user confirmed the discovered device: an ESPHome entry and its device
        add_esphome_device(hass, "living-room", NEW_MAC, "living-room", None)
        assert "living-room" not in coordinator.data.devices  # no refresh by itself
        async_fire_time_changed(hass, dt_util.utcnow() + AUTO_ADD_INTERVAL)
        await hass.async_block_till_done(wait_background_tasks=True)
    init.assert_not_awaited()
    assert "living-room" in coordinator.data.devices
    assert coordinator.data.pending == {}
