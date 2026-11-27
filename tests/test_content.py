"""Add device's photos and notes: devices/onboarding.json, parsed and fetched."""

from __future__ import annotations

import copy

from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.levoit_esphome.const import GITHUB_RAW
from custom_components.levoit_esphome.content import (
    CONTENT_FILE,
    DeviceContent,
    async_fetch_content,
    parse_content,
    template_folder,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .conftest import CONTENT_JSON

URL = f"{GITHUB_RAW}/main/{CONTENT_FILE}"
RAW = "https://raw.githubusercontent.com/tuct/levoit/main"


def test_parse() -> None:
    """Paths become GitHub URLs: a folder a tree, a file a blob; optional fields stay None."""
    data = copy.deepcopy(CONTENT_JSON)
    data["devices"].append(
        {
            "id": "levoit-dual200s",
            "title": "Dual 200S",
            "photo": "docs/images/devices/levoit-dual200s.jpg",
            "guide": "docs/humidifiers.md",
            "status": "planned",
            "summary": "Ultrasonic",
            "open": "easy",
            "routes": ["add_esp", "flash", "add_esp"],
        }
    )
    content = parse_content(data)
    assert list(content) == [
        "levoit-core300s",
        "levoit-everest-air",
        "levoit-mini",
        "levoit-dual200s",
    ]
    assert content["levoit-mini"] == DeviceContent(
        id="levoit-mini",
        title="Levoit Mini",
        photo_url=f"{RAW}/docs/images/devices/levoit-mini.jpg",
        guide_url="https://github.com/tuct/levoit/tree/main/devices/levoit-mini",
        status="custom",
        summary="Custom PCB and 3D parts, reversible",
        open="easy",
        routes=("custom",),
        status_note="Guide + YAML",
        spec=None,
    )
    dual = content["levoit-dual200s"]
    assert dual.guide_url == "https://github.com/tuct/levoit/blob/main/docs/humidifiers.md"
    assert dual.routes == ("add_esp", "flash")  # a repeat dropped
    assert dual.as_dict()["routes"] == ["add_esp", "flash"]


def test_parse_leaves_out_what_it_cannot_use() -> None:
    """A bad entry is skipped, the rest stays; an unknown version or shape gives nothing."""
    good = CONTENT_JSON["devices"][0]
    bad = [
        {**good, "id": "Bad Id"},
        {**good, "id": "a", "photo": "../secret.jpg"},
        {**good, "id": "b", "photo": "https://example.com/x.jpg"},
        {**good, "id": "c", "photo": "docs/x.svg"},
        {**good, "id": "d", "status": "great"},
        {**good, "id": "e", "open": "sideways"},
        {**good, "id": "f", "routes": []},
        {**good, "id": "g", "routes": ["teleport"]},
        {**good, "id": "h", "summary": ""},
        {**good, "id": "i", "summary": "x" * 121},
        {**good, "id": "j", "spec": 5},
        {k: v for k, v in good.items() if k != "title"},
        "not an object",
    ]
    content = parse_content({"version": 1, "devices": [*bad, good, {**good, "title": "again"}]})
    assert list(content) == ["levoit-core300s"]
    assert content["levoit-core300s"].title == "Core 300S"  # the first entry of an id wins
    assert parse_content({"version": 2, "devices": [good]}) == {}
    assert parse_content({"version": 1, "devices": {}}) == {}
    assert parse_content([good]) == {}


def test_template_folder() -> None:
    """The device folder of a template's builder file."""
    assert (
        template_folder("devices/levoit-core300s/levoit-core300s-builder.yaml") == "levoit-core300s"
    )
    assert template_folder("odd.yaml") == ""


async def test_fetch(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    """Read from main; not there yet (404) is no content, not an error."""
    aioclient_mock.get(URL, json=CONTENT_JSON)
    content = await async_fetch_content(async_get_clientsession(hass))
    assert list(content) == ["levoit-core300s", "levoit-everest-air", "levoit-mini"]

    aioclient_mock.clear_requests()
    aioclient_mock.get(URL, status=404)
    assert await async_fetch_content(async_get_clientsession(hass)) == {}
