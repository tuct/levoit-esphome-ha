"""Add device's shared steps (onboarding.py) and the panel's commands for them."""

from __future__ import annotations

from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.typing import WebSocketGenerator

from custom_components.levoit_esphome import onboarding as onb
from custom_components.levoit_esphome.const import DOMAIN
from custom_components.levoit_esphome.templates import (
    MARKER_PREFIX,
    ConfigValues,
    CustomEsp,
    Value,
    config_values,
)
from homeassistant.core import HomeAssistant

from .conftest import (
    CORE300S,
    CORE300S_S3,
    EVEREST_C3,
    EVEREST_ORIGINAL,
    MAC,
    TEMPLATES,
    FakeBuilder,
    add_esphome_device,
)

KEY = "ZXhpc3Rpbmcta2V5LW9mLXRoZS1kZXZpY2UtMzJieXRlcyE="

# --- the rules, without Home Assistant ---------------------------------------------


def test_models_and_variants() -> None:
    """Models by title; a model's ESPs in the order of templates.json; the custom base."""
    assert onb.models(TEMPLATES) == [
        ("CORE300S", "Levoit Core 300S"),
        ("EVERESTAIR", "Levoit Everest Air"),
    ]
    assert onb.variants(TEMPLATES, "EVERESTAIR") == [EVEREST_ORIGINAL, EVEREST_C3]
    assert onb.variants(TEMPLATES, "LV600S") == []
    # closest to a bare ESP: the XIAO C3 where there is one, else the S3, else the original
    assert onb.custom_base(onb.variants(TEMPLATES, "EVERESTAIR")) == EVEREST_C3
    assert onb.custom_base(onb.variants(TEMPLATES, "CORE300S")) == CORE300S_S3
    assert onb.custom_base([CORE300S]) == CORE300S


def test_validate_custom_and_check_name() -> None:
    """Board and pins normalised, errors per field; names checked against what is taken."""
    assert onb.validate_custom(" Seeed_XIAO_esp32s3 ", "5", "gpio04") == (
        CustomEsp(board="seeed_xiao_esp32s3", rx_pin="GPIO5", tx_pin="GPIO4"),
        {},
    )
    assert onb.validate_custom("My Board", "IO5", "5") == (
        None,
        {"board": "invalid_board", "rx_pin": "invalid_pin"},
    )
    assert onb.validate_custom("esp32dev", "5", "GPIO05") == (None, {"tx_pin": "same_pin"})

    taken = {"bedroom-purifier"}
    assert onb.check_name("hall-air", taken) is None
    assert onb.check_name("bedroom-purifier", taken) == "name_taken"
    assert onb.check_name("My Purifier", taken) == "invalid_name"


def test_onboarding_error_message() -> None:
    """The code is the config flow's error key; the message has its placeholders filled in."""
    err = onb.OnboardingError("missing_wifi_secrets", missing="wifi_ssid, wifi_password")
    assert err.code == "missing_wifi_secrets"
    assert err.placeholders == {"missing": "wifi_ssid, wifi_password"}
    assert err.message.startswith(
        "The Device Builder's secrets.yaml has no wifi_ssid, wifi_password."
    )
    assert onb.OnboardingError("secret_exists").message == (
        "secrets.yaml already has . Remove it there or pick another name."
    )
    assert onb.OnboardingError("something_else").message == "something_else"


@pytest.mark.parametrize(
    "case",
    [
        # (existing, api key, OTA password, Device Builder's ESPHome) -> (api, ota pw, encrypted)
        ((False, None, None, "2026.11.0"), (True, False, True)),
        ((False, None, None, None), (True, False, True)),  # version unknown: new enough
        ((False, None, None, "2026.8.2"), (True, True, False)),  # too old for encryption
        ((True, KEY, None, "2026.11.0"), (True, False, False)),  # encrypted after its first update
        ((True, KEY, "pw", "2026.11.0"), (True, True, False)),
        ((True, None, None, "2026.11.0"), (False, False, False)),
        ((True, None, "pw", "2026.11.0"), (False, True, False)),
    ],
)
def test_protection_table(case: tuple[tuple, tuple]) -> None:
    """Which secrets a config gets, and how its OTA is protected."""
    (existing, api_key, ota_password, version), (has_api, has_pw, encrypted) = case
    chosen = onb.protection(
        "hall-air",
        "stable",
        existing=existing,
        api_key=api_key,
        ota_password=ota_password,
        esphome_version=version,
    )
    expected_secrets = set()
    if has_api:
        expected_secrets.add("hall_air_api_key")
    if has_pw:
        expected_secrets.add("hall_air_ota_password")
    assert set(chosen.secrets) == expected_secrets
    assert chosen.values == ConfigValues(
        name="hall-air",
        api_key=Value(secret="hall_air_api_key") if has_api else None,
        ota_password=Value(secret="hall_air_ota_password") if has_pw else None,
        channel="stable",
        ota_uses_api_key=encrypted,
    )
    assert chosen.encrypted_ota is encrypted
    if existing:
        # an existing device's own credentials, as given
        assert chosen.secrets.get("hall_air_api_key") == api_key
        assert chosen.secrets.get("hall_air_ota_password") == ota_password
    else:
        assert len(chosen.secrets["hall_air_api_key"]) == 44
        if has_pw:
            assert len(chosen.secrets["hall_air_ota_password"]) == 32


# --- the panel's commands --------------------------------------------------------------


async def _setup(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(domain=DOMAIN, title="Levoit ESPHome", data={})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


@pytest.fixture
def frontend_served() -> Generator[None]:
    """The frontend folder counts as served.

    Creating a device sets the entry up again. With the test web server running
    (hass_ws_client), that would register the folder on its router, which aiohttp
    froze at start; Home Assistant's own server never freezes it.
    """
    with patch("custom_components.levoit_esphome.panel._async_serve_frontend", AsyncMock()):
        yield


async def _call(client: Any, message: dict[str, Any]) -> dict[str, Any]:
    """Send a command; its result, skipping subscription events."""
    await client.send_json_auto_id(message)
    while True:
        msg = await client.receive_json()
        if msg["id"] == message["id"] and msg["type"] == "result":
            return msg


@pytest.mark.usefixtures("esphome_devices")
async def test_options(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """The models with their ESPs, the Device Builder's state, the missing secrets."""
    await _setup(hass)
    client = await hass_ws_client(hass)
    result = await _call(client, {"type": "levoit_esphome/onboarding/options"})
    assert result["success"]
    options = result["result"]
    assert [m["model"] for m in options["models"]] == ["CORE300S", "EVERESTAIR"]
    everest = options["models"][1]
    assert everest["title"] == "Levoit Everest Air"
    assert [v["variant"] for v in everest["variants"]] == ["original", "xiao_c3"]
    assert everest["variants"][1] == {
        "variant": "xiao_c3",
        "title": "Seeed XIAO ESP32-C3",
        "board": "seeed_xiao_esp32c3",
        "name": "levoit-everest-air-c3",
        "file": EVEREST_C3.file,
    }
    assert everest["custom_base"] == EVEREST_C3.file
    assert options["models"][0]["custom_base"] == CORE300S_S3.file
    assert options["existing"] == []  # the purifier has a config
    assert options["channels"] == ["stable", "main"]
    assert options["boards"][0] == "seeed_xiao_esp32s3"
    assert options["esphome_version"] == "2026.11.0"
    assert options["ota_encryption"] is True
    assert options["missing_secrets"] == []
    assert options["builder_url"] == "/app/5c53de3b_esphome"
    # photos and notes by the templates' device folder; the rest as others
    raw = "https://raw.githubusercontent.com/tuct/levoit/main"
    assert everest["content"]["photo_url"] == f"{raw}/docs/images/devices/levoit-everest-air.jpg"
    assert everest["content"]["summary"] == "Vent louver, PM1.0/2.5/10, Turbo"
    assert options["models"][0]["content"]["title"] == "Core 300S"
    assert [o["id"] for o in options["others"]] == ["levoit-mini"]
    assert options["others"][0]["guide_url"] == (
        "https://github.com/tuct/levoit/tree/main/devices/levoit-mini"
    )

    del builder.files.secrets["wifi_password"]
    for device in builder.api.configured:
        device["current_version"] = "2026.8.2"
    options = (await _call(client, {"type": "levoit_esphome/onboarding/options"}))["result"]
    assert options["missing_secrets"] == ["wifi_password"]
    assert options["ota_encryption"] is False


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_custom_defaults_and_check_name(
    hass: HomeAssistant, hass_ws_client: WebSocketGenerator
) -> None:
    """Board and pins of a template's builder file; names checked against the Device Builder."""
    await _setup(hass)
    client = await hass_ws_client(hass)

    result = await _call(
        client, {"type": "levoit_esphome/onboarding/custom_defaults", "template": EVEREST_C3.file}
    )
    assert result["result"] == {
        "board": "seeed_xiao_esp32c3",
        "rx_pin": "GPIO05",
        "tx_pin": "GPIO06",
        "boards": list(onb.COMMON_BOARDS),
    }
    result = await _call(
        client, {"type": "levoit_esphome/onboarding/custom_defaults", "template": "nope.yaml"}
    )
    assert result["error"]["code"] == "unknown_template"

    result = await _call(
        client, {"type": "levoit_esphome/onboarding/check_name", "name": " Bedroom-Purifier "}
    )
    assert result["result"] == {
        "name": "bedroom-purifier",
        "ok": False,
        "error": "name_taken",
        "message": onb.MESSAGES["name_taken"],
        "suggestion": "bedroom-purifier-2",
    }
    result = await _call(
        client, {"type": "levoit_esphome/onboarding/check_name", "name": "Hall Air"}
    )
    assert result["result"]["error"] == "invalid_name"
    assert result["result"]["suggestion"] is None
    result = await _call(
        client, {"type": "levoit_esphome/onboarding/check_name", "name": "hall-air"}
    )
    assert result["result"]["ok"] is True
    assert result["result"]["suggestion"] == "hall-air"


@pytest.mark.usefixtures("esphome_devices", "frontend_served")
async def test_create_new_device(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """The config, its secrets and the sub-entry, as the integration page's flow makes them."""
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    result = await _call(
        client,
        {
            "type": "levoit_esphome/onboarding/create",
            "template": EVEREST_C3.file,
            "name": "levoit-everest-air-c3",
            "channel": "main",
        },
    )
    assert result["success"], result
    assert result["result"] == {
        "name": "levoit-everest-air-c3",
        "configuration": "levoit-everest-air-c3.yaml",
        "existing": False,
        "custom": False,
        "encrypted_ota": True,
        "builder_url": "/app/5c53de3b_esphome",
    }
    text = builder.files.configs["levoit-everest-air-c3.yaml"]
    assert text.startswith(f"{MARKER_PREFIX}{EVEREST_C3.file}\n")
    assert config_values(text) == ConfigValues(
        name="levoit-everest-air-c3",
        api_key=Value(secret="levoit_everest_air_c3_api_key"),
        channel="main",
        ota_uses_api_key=True,
    )
    assert len(builder.files.secrets["levoit_everest_air_c3_api_key"]) == 44
    assert "levoit_everest_air_c3_ota_password" not in builder.files.secrets

    await hass.async_block_till_done(wait_background_tasks=True)
    (subentry,) = entry.subentries.values()
    assert subentry.subentry_type == "device"
    assert subentry.unique_id == "levoit-everest-air-c3"
    assert dict(subentry.data) == {
        "configuration": "levoit-everest-air-c3.yaml",
        "template": EVEREST_C3.file,
        "existing": False,
        "custom": False,
    }

    # the name is taken now, by the sub-entry, before the Device Builder lists it
    result = await _call(
        client,
        {
            "type": "levoit_esphome/onboarding/create",
            "template": EVEREST_C3.file,
            "name": "levoit-everest-air-c3",
            "channel": "main",
        },
    )
    assert result["error"] == {"code": "name_taken", "message": onb.MESSAGES["name_taken"]}


@pytest.mark.usefixtures("esphome_devices", "frontend_served")
async def test_create_custom_device(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """Other ESP: own board and pins on the model's builder file, a custom config."""
    entry = await _setup(hass)
    client = await hass_ws_client(hass)
    message = {
        "type": "levoit_esphome/onboarding/create",
        "template": EVEREST_C3.file,
        "name": "hall-air",
        "channel": "stable",
        "custom": {"board": "My Board", "rx_pin": "IO5", "tx_pin": "5"},
    }
    result = await _call(client, message)
    assert result["error"]["code"] == "invalid_board"
    assert result["error"]["message"].startswith("board: ")
    assert "hall-air.yaml" not in builder.files.configs

    message["custom"] = {"board": "seeed_xiao_esp32s3", "rx_pin": "5", "tx_pin": "gpio4"}
    result = await _call(client, message)
    assert result["success"], result
    assert result["result"]["custom"] is True
    text = builder.files.configs["hall-air.yaml"]
    assert MARKER_PREFIX not in text
    assert "board: seeed_xiao_esp32s3" in text
    assert "  rx_pin: GPIO5\n" in text
    assert "  tx_pin: GPIO4\n" in text
    await hass.async_block_till_done(wait_background_tasks=True)
    (subentry,) = entry.subentries.values()
    assert subentry.data["custom"] is True


@pytest.mark.usefixtures("frontend_served")
async def test_create_existing_device(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """A device without a config keeps its name, API key and OTA password."""
    hass.config.components.add("esphome")
    builder.api.configured = []
    builder.files.configs.clear()
    add_esphome_device(
        hass,
        "bedroom-purifier",
        MAC,
        "Bedroom purifier",
        "1.7.0 esphome",
        model="EVERESTAIR",
        noise_psk=KEY,
    )
    entry = await _setup(hass)
    client = await hass_ws_client(hass)

    options = (await _call(client, {"type": "levoit_esphome/onboarding/options"}))["result"]
    assert options["existing"] == [
        {
            "name": "bedroom-purifier",
            "title": "Bedroom purifier",
            "model": "EVERESTAIR",
            "api_key": True,
        }
    ]

    result = await _call(
        client,
        {
            "type": "levoit_esphome/onboarding/create",
            "template": EVEREST_C3.file,
            "name": "garage-sensor",
            "channel": "stable",
            "existing": True,
        },
    )
    assert result["error"]["code"] == "unknown_device"

    result = await _call(
        client,
        {
            "type": "levoit_esphome/onboarding/create",
            "template": EVEREST_C3.file,
            "name": "bedroom-purifier",
            "channel": "stable",
            "existing": True,
            "ota_password": "its-ota-pw",
        },
    )
    assert result["success"], result
    assert result["result"]["existing"] is True
    assert result["result"]["encrypted_ota"] is False
    assert config_values(builder.files.configs["bedroom-purifier.yaml"]) == ConfigValues(
        name="bedroom-purifier",
        api_key=Value(secret="bedroom_purifier_api_key"),
        ota_password=Value(secret="bedroom_purifier_ota_password"),
        channel="stable",
    )
    assert builder.files.secrets["bedroom_purifier_api_key"] == KEY
    assert builder.files.secrets["bedroom_purifier_ota_password"] == "its-ota-pw"
    await hass.async_block_till_done(wait_background_tasks=True)
    (subentry,) = entry.subentries.values()
    assert subentry.data["existing"] is True


@pytest.mark.usefixtures("esphome_devices")
async def test_create_refuses(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    patch_sources: AsyncMock,
    builder: FakeBuilder,
) -> None:
    """Unknown template, bad channel or name, missing Wi-Fi secrets, a secret that exists."""
    await _setup(hass)
    client = await hass_ws_client(hass)
    message = {
        "type": "levoit_esphome/onboarding/create",
        "template": EVEREST_C3.file,
        "name": "hall-air",
        "channel": "stable",
    }
    result = await _call(client, {**message, "template": "nope.yaml"})
    assert result["error"]["code"] == "unknown_template"
    result = await _call(client, {**message, "channel": "dev"})
    assert result["error"]["code"] == "invalid_channel"
    result = await _call(client, {**message, "name": "Hall Air"})
    assert result["error"]["code"] == "invalid_name"

    del builder.files.secrets["wifi_password"]
    result = await _call(client, message)
    assert result["error"]["code"] == "missing_wifi_secrets"
    assert "wifi_password" in result["error"]["message"]

    builder.files.secrets["wifi_password"] = "wifi-pw"
    builder.files.secrets["hall_air_api_key"] = "already there"
    result = await _call(client, message)
    assert result["error"]["code"] == "secret_exists"
    assert "hall_air_api_key" in result["error"]["message"]
    assert builder.files.secrets["hall_air_api_key"] == "already there"
    assert "hall-air.yaml" not in builder.files.configs
    assert hass.config_entries.async_entries(DOMAIN)[0].subentries == {}


@pytest.mark.usefixtures("esphome_devices", "patch_sources")
async def test_admins_only(
    hass: HomeAssistant,
    hass_ws_client: WebSocketGenerator,
    hass_read_only_access_token: str,
) -> None:
    """A user who is not an admin gets nothing."""
    await _setup(hass)
    client = await hass_ws_client(hass, hass_read_only_access_token)
    await client.send_json_auto_id({"type": "levoit_esphome/onboarding/options"})
    assert (await client.receive_json())["error"]["code"] == "unauthorized"
