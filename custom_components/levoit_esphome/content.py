"""Add device's photos and notes: devices/onboarding.json of tuct/levoit.

Per device a photo, its status, spec and a few words, how easy it is to open
and the routes (flash the original ESP, add an ESP, custom hardware), taken
from the tuct/levoit README gallery, and the component's model codes, by which
every device of that model gets the photo (sidebar page, dashboard cards).
Read from main like the templates, so the Add device page changes with a PR
there and no release here.

The file is optional: without it (or with entries this version does not
understand) the page shows the line drawings and no notes. Paths become
GitHub URLs here; nothing else of the file reaches the page.
Plain Python without Home Assistant, so it is easy to test.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

import aiohttp

from .const import GITHUB_RAW, GITHUB_REPO

CONTENT_FILE = "devices/onboarding.json"
CONTENT_REF = "main"
STATUSES = ("tested", "partly_tested", "untested", "development", "planned", "custom")
OPENS = ("easy", "medium", "hard")
ROUTES = ("flash", "add_esp", "custom")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_MODEL = re.compile(r"^[A-Z0-9]+$")
# a path in the repo, no way out of it
_PATH = re.compile(r"^(?!/)(?!.*\.\.)[A-Za-z0-9_./-]+$")
_PHOTO = (".jpg", ".jpeg", ".png", ".webp")
_MAX_TEXT = 120
_TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass(frozen=True)
class DeviceContent:
    """One device of onboarding.json, ready for the page."""

    id: str  # the device folder of tuct/levoit, e.g. levoit-core300s
    title: str
    photo_url: str
    guide_url: str
    status: str
    summary: str
    open: str
    routes: tuple[str, ...]
    status_note: str | None = None
    spec: str | None = None
    models: tuple[str, ...] = ()  # the component's model codes, e.g. CORE300S

    def as_dict(self) -> dict[str, Any]:
        """For the WebSocket answer."""
        data = asdict(self)
        data["routes"] = list(self.routes)
        data["models"] = list(self.models)
        return data


def _text(entry: dict[str, Any], key: str, *, required: bool = True) -> str | None:
    value = entry.get(key)
    if value is None and not required:
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT:
        raise ValueError(key)
    return value.strip()


def _path(entry: dict[str, Any], key: str) -> str:
    value = _text(entry, key)
    assert value is not None
    if not _PATH.match(value):
        raise ValueError(key)
    return value


def _guide_url(path: str) -> str:
    """A folder opens as a tree on GitHub, a file (docs/humidifiers.md) as a blob."""
    kind = "blob" if "." in path.rsplit("/", 1)[-1] else "tree"
    return f"https://github.com/{GITHUB_REPO}/{kind}/{CONTENT_REF}/{path}"


def _models(value: Any) -> tuple[str, ...]:
    """The model codes of an entry; none if the list is not what it should be."""
    if not isinstance(value, list) or not all(
        isinstance(m, str) and _MODEL.match(m) for m in value
    ):
        return ()
    return tuple(dict.fromkeys(value))


def parse_content(data: Any) -> dict[str, DeviceContent]:
    """The devices of onboarding.json by id; entries this version cannot use are left out."""
    if not isinstance(data, dict) or data.get("version") != 1:
        return {}
    devices = data.get("devices")
    if not isinstance(devices, list):
        return {}
    found: dict[str, DeviceContent] = {}
    for entry in devices:
        if not isinstance(entry, dict):
            continue
        try:
            ident = _text(entry, "id")
            photo = _path(entry, "photo")
            guide = _path(entry, "guide")
            status = _text(entry, "status")
            opens = _text(entry, "open")
            routes = entry.get("routes")
            if (
                ident is None
                or not _ID.match(ident)
                or not photo.lower().endswith(_PHOTO)
                or status not in STATUSES
                or opens not in OPENS
                or not isinstance(routes, list)
                or not routes
                or not all(r in ROUTES for r in routes)
            ):
                continue
            content = DeviceContent(
                id=ident,
                title=str(_text(entry, "title")),
                photo_url=f"{GITHUB_RAW}/{CONTENT_REF}/{photo}",
                guide_url=_guide_url(guide),
                status=status,
                summary=str(_text(entry, "summary")),
                open=opens,
                routes=tuple(dict.fromkeys(routes)),
                status_note=_text(entry, "status_note", required=False),
                spec=_text(entry, "spec", required=False),
                models=_models(entry.get("models")),
            )
        except ValueError:
            continue
        found.setdefault(ident, content)
    return found


async def async_fetch_content(session: aiohttp.ClientSession) -> dict[str, DeviceContent]:
    """devices/onboarding.json of tuct/levoit (main); empty while it is not there."""
    url = f"{GITHUB_RAW}/{CONTENT_REF}/{CONTENT_FILE}"
    async with session.get(url, timeout=_TIMEOUT) as resp:
        if resp.status == 404:
            return {}
        resp.raise_for_status()
        data = await resp.json(content_type=None)
    return parse_content(data)


def photo_for(
    model: str | None, content: dict[str, DeviceContent], templates: list[Any]
) -> str | None:
    """A model's photo: by the entry that names the model, else by its template's folder."""
    if not model or not content:
        return None
    for entry in content.values():
        if model in entry.models:
            return entry.photo_url
    for template in templates:
        if template.model == model and (entry := content.get(template_folder(template.file))):
            return entry.photo_url
    return None


def template_folder(template_file: str) -> str:
    """devices/levoit-core300s/levoit-core300s-builder.yaml -> levoit-core300s."""
    parts = template_file.split("/")
    return parts[1] if len(parts) > 2 else ""
