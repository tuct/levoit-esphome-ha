"""Fixtures: a stub Device Builder and stub GitHub heads.

The esphome integration is marked as loaded instead of set up: its setup needs
Bluetooth, ffmpeg and more, none of which matter here. All access to it goes
through device_builder.py, which these fixtures replace.
"""

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.levoit_esphome.content import parse_content
from custom_components.levoit_esphome.device_builder import DeviceBuilderCommandError
from custom_components.levoit_esphome.templates import Template
from custom_components.levoit_esphome.versions import ChannelHead
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

MAC = "aa:bb:cc:dd:ee:ff"
OTHER_MAC = "11:22:33:44:55:66"

HEADS = {
    "stable": ChannelHead(
        release="1.8.0",
        commit="abcdef1",
        notes="## 1.8.0\n\nRelease notes",
        url="https://github.com/tuct/levoit/releases/tag/1.8.0",
    ),
    "main": ChannelHead(
        release="1.8.0",
        commit="1234567",
        url="https://github.com/tuct/levoit/commits/main",
    ),
}

PURIFIER_CONFIG = {
    "esphome": {"name": "bedroom-purifier"},
    "levoit": {"model": "CORE300S", "id": "levoit_1"},
    "external_components": [
        {
            "source": {"type": "git", "url": "https://github.com/tuct/levoit", "ref": "stable"},
            "components": ["levoit"],
        }
    ],
    # resolved secrets come along in json-config; the integration must not keep them
    "api": {"encryption": {"key": "c2VjcmV0LWtleS1kby1ub3Qta2VlcA=="}},
}


BUILDER_TEXT = (
    Path(__file__).parent / "fixtures" / "levoit-everest-air-builder-c3.yaml"
).read_text(encoding="utf-8")
EVEREST_C3 = Template(
    title="Levoit Everest Air",
    model="EVERESTAIR",
    variant="xiao_c3",
    board="seeed_xiao_esp32c3",
    name="levoit-everest-air-c3",
    file="devices/levoit-everest-air/levoit-everest-air-builder-c3.yaml",
    source="devices/levoit-everest-air/levoit-everest-air-c3.yaml",
)
EVEREST_ORIGINAL = Template(
    title="Levoit Everest Air",
    model="EVERESTAIR",
    variant="original",
    board="esp32dev",
    name="levoit-everest-air",
    file="devices/levoit-everest-air/levoit-everest-air-builder.yaml",
    source="devices/levoit-everest-air/levoit-everest-air.yaml",
)
CORE300S = Template(
    title="Levoit Core 300S",
    model="CORE300S",
    variant="original",
    board="esp32dev",
    name="levoit-core300s",
    file="devices/levoit-core300s/levoit-core300s-builder.yaml",
    source="devices/levoit-core300s/levoit-core300s.yaml",
)
CORE300S_S3 = Template(
    title="Levoit Core 300S",
    model="CORE300S",
    variant="s3",
    board="esp32-s3-devkitc-1",
    name="levoit-core300s-s3",
    file="devices/levoit-core300s/levoit-core300s-builder-s3.yaml",
    source="devices/levoit-core300s/levoit-core300s-s3.yaml",
)
TEMPLATES = [CORE300S, CORE300S_S3, EVEREST_ORIGINAL, EVEREST_C3]
CUSTOM_CONFIG = "esphome:\n  name: bedroom-purifier\n"
# devices/onboarding.json: two devices with a template, one without
CONTENT_JSON = {
    "version": 1,
    "devices": [
        {
            "id": "levoit-core300s",
            "title": "Core 300S",
            "photo": "docs/images/devices/levoit-core300s.jpg",
            "guide": "devices/levoit-core300s",
            "status": "tested",
            "spec": "214 m³/h",
            "summary": "PM2.5 and Auto mode",
            "open": "easy",
            "routes": ["flash", "add_esp"],
        },
        {
            "id": "levoit-everest-air",
            "title": "Everest Air",
            "photo": "docs/images/devices/levoit-everest-air.jpg",
            "guide": "devices/levoit-everest-air",
            "status": "tested",
            "spec": "612 m³/h",
            "summary": "Vent louver, PM1.0/2.5/10, Turbo",
            "open": "easy",
            "routes": ["flash", "add_esp"],
        },
        {
            "id": "levoit-mini",
            "title": "Levoit Mini",
            "photo": "docs/images/devices/levoit-mini.jpg",
            "guide": "devices/levoit-mini",
            "status": "custom",
            "status_note": "Guide + YAML",
            "summary": "Custom PCB and 3D parts, reversible",
            "open": "easy",
            "routes": ["custom"],
        },
    ],
}
CONTENT = parse_content(CONTENT_JSON)
WIFI = {"wifi_ssid": "home", "wifi_password": "wifi-pw", "wifi_ap_password": "ap-pw"}


@dataclass
class FakeFiles:
    """The Device Builder's /ws file commands, on an in-memory config folder."""

    configs: dict[str, str] = field(default_factory=dict)
    secrets: dict[str, str] = field(default_factory=lambda: dict(WIFI))
    writes: list[str] = field(default_factory=list)

    async def command(self, command: str, **args: Any) -> Any:
        if command == "devices/get_config":
            if args["configuration"] not in self.configs:
                raise DeviceBuilderCommandError("not_found")
            return self.configs[args["configuration"]]
        if command == "devices/update_config":
            if self.configs.get(args["configuration"]) != args["expected"]:
                raise DeviceBuilderCommandError("precondition_failed")
            self.configs[args["configuration"]] = args["content"]
            self.writes.append(args["configuration"])
            return None
        if command == "devices/create":
            configuration = f"{args['name']}.yaml"
            if configuration in self.configs:
                raise DeviceBuilderCommandError("already_exists")
            self.configs[configuration] = args["file_content"]
            return {"configuration": configuration}
        if command == "config/get_secrets":
            return sorted(self.secrets)
        if command == "config/set_secret":
            if args["key"] in self.secrets and not args.get("overwrite", True):
                return {"created": False}
            self.secrets[args["key"]] = args["value"]
            return {"created": True}
        raise DeviceBuilderCommandError("unknown_command", command)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Load custom_components/ in every test."""


@dataclass
class FakeApi:
    """Stands in for esphome_dashboard_api.ESPHomeDashboardAPI."""

    configured: list[dict[str, Any]] = field(default_factory=list)
    configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    compile: AsyncMock = field(default_factory=lambda: AsyncMock(return_value=True))
    upload: AsyncMock = field(default_factory=lambda: AsyncMock(return_value=True))
    get_config_calls: list[str] = field(default_factory=list)

    async def get_devices(self) -> dict[str, Any]:
        return {"configured": self.configured, "importable": []}

    async def get_config(self, configuration: str) -> dict[str, Any] | None:
        self.get_config_calls.append(configuration)
        return self.configs.get(configuration)


@dataclass
class FakeBuilder:
    """Stands in for the esphome integration's dashboard coordinator."""

    api: FakeApi
    supports_build_queue: bool = True
    url: str = "http://device-builder.local:6052"
    addon_slug: str = "5c53de3b_esphome"
    files: FakeFiles = field(default_factory=FakeFiles)


@pytest.fixture
def builder() -> FakeBuilder:
    """A Device Builder with the bedroom purifier's config."""
    return FakeBuilder(
        api=FakeApi(
            configured=[
                {
                    "name": "bedroom-purifier",
                    "configuration": "bedroom-purifier.yaml",
                    "deployed_version": "2026.11.0",
                    "current_version": "2026.11.0",
                    "loaded_integrations": ["api", "levoit", "uart", "wifi"],
                },
                {
                    "name": "garage-sensor",
                    "configuration": "garage-sensor.yaml",
                    "deployed_version": "2026.11.0",
                    "current_version": "2026.11.0",
                    "loaded_integrations": ["api", "dht", "wifi"],
                },
            ],
            configs={"bedroom-purifier.yaml": PURIFIER_CONFIG},
        ),
        # the purifier's config as written: custom (no template)
        files=FakeFiles(configs={"bedroom-purifier.yaml": CUSTOM_CONFIG}),
    )


@pytest.fixture
def patch_sources(builder: FakeBuilder) -> Generator[AsyncMock]:
    """Use the fake Device Builder and fixed GitHub heads."""
    heads = AsyncMock(return_value=HEADS)

    async def ws_command(hass: HomeAssistant, b: FakeBuilder, command: str, **args: Any) -> Any:
        return await b.files.command(command, **args)

    with (
        patch("custom_components.levoit_esphome.device_builder._ws_command", ws_command),
        patch(
            "custom_components.levoit_esphome.templates.async_fetch_templates",
            AsyncMock(return_value=TEMPLATES),
        ),
        patch(
            "custom_components.levoit_esphome.templates.async_fetch_template_text",
            AsyncMock(return_value=BUILDER_TEXT),
        ),
        patch(
            "custom_components.levoit_esphome.content.async_fetch_content",
            AsyncMock(return_value=CONTENT),
        ),
        patch(
            "custom_components.levoit_esphome.coordinator.async_get_device_builder",
            return_value=builder,
        ),
        patch(
            "custom_components.levoit_esphome.config_flow.async_get_device_builder",
            return_value=builder,
        ),
        patch("custom_components.levoit_esphome.coordinator.async_fetch_heads", heads),
    ):
        yield heads


def add_esphome_device(
    hass: HomeAssistant,
    name: str,
    mac: str,
    title: str,
    version: str | None,
    *,
    model: str | None = None,
    filters: dict[str, str] | None = None,
    noise_psk: str | None = None,
) -> str | None:
    """Register an ESPHome device like the esphome integration does.

    With `model`, it also gets a `model` text sensor reporting it; `filters`
    adds filter sensors (name -> value, `%`, `mdi:air-filter`).
    Returns the entity_id of its version sensor, if it has one.
    """
    data = {"device_name": name, "host": f"{name}.local"}
    if noise_psk is not None:
        data["noise_psk"] = noise_psk
    entry = MockConfigEntry(domain="esphome", data=data)
    entry.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        name=title,
    )
    for key, (filter_name, value) in enumerate((filters or {}).items()):
        filter_entity = er.async_get(hass).async_get_or_create(
            "sensor",
            "esphome",
            f"{mac}-sensor-filter-{key}",
            device_id=device.id,
            config_entry=entry,
            original_name=filter_name,
            original_icon="mdi:air-filter",
            unit_of_measurement="%",
            suggested_object_id=f"{name}_filter_{key}",
        )
        hass.states.async_set(
            filter_entity.entity_id,
            value,
            {"unit_of_measurement": "%", "friendly_name": filter_name},
        )
    if model is not None:
        model_entity = er.async_get(hass).async_get_or_create(
            "sensor",
            "esphome",
            f"{mac}-text_sensor-model",
            device_id=device.id,
            config_entry=entry,
            suggested_object_id=f"{name}_model",
        )
        hass.states.async_set(model_entity.entity_id, model)
    if version is None:
        return None
    # The MCU's own firmware version, registered first like on a real
    # device: it looks like a version too, but is not the component's.
    mcu = er.async_get(hass).async_get_or_create(
        "sensor",
        "esphome",
        f"{mac}-text_sensor-mcu_version",
        device_id=device.id,
        config_entry=entry,
        suggested_object_id=f"{name}_mcu_version",
    )
    hass.states.async_set(mcu.entity_id, "1.0.2")
    entity = er.async_get(hass).async_get_or_create(
        "sensor",
        "esphome",
        f"{mac}-text_sensor-esp_version",
        device_id=device.id,
        config_entry=entry,
        suggested_object_id=f"{name}_esp_version",
    )
    hass.states.async_set(entity.entity_id, version)
    return entity.entity_id


@pytest.fixture
def esphome_devices(hass: HomeAssistant) -> dict[str, str | None]:
    """The purifier (ours, on 1.7.0) and an unrelated ESPHome device."""
    hass.config.components.add("esphome")
    return {
        "purifier": add_esphome_device(
            hass, "bedroom-purifier", MAC, "Bedroom purifier", "1.7.0+10361cc esphome"
        ),
        "other": add_esphome_device(hass, "garage-sensor", OTHER_MAC, "Garage sensor", None),
    }


def assert_compiled(builder: FakeBuilder, configuration: str) -> None:
    """Compiled once, with the output streamed to the integration."""
    builder.api.compile.assert_awaited_once()
    call = builder.api.compile.await_args
    assert call.args == (configuration,)
    assert callable(call.kwargs["line_received_cb"])


def assert_uploaded(builder: FakeBuilder, configuration: str) -> None:
    """Uploaded once over the air, with the output streamed to the integration."""
    builder.api.upload.assert_awaited_once()
    call = builder.api.upload.await_args
    assert call.args == (configuration, "OTA")
    assert callable(call.kwargs["line_received_cb"])
