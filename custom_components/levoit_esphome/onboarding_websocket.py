"""WebSocket commands for Add device from the sidebar panel (admins only).

* levoit_esphome/onboarding/options: the models and their ESPs (with their
  photo and notes from devices/onboarding.json), the devices of tuct/levoit
  without a template, the devices Home Assistant knows without a config,
  channels, boards, what the Device Builder supports and which Wi-Fi secrets
  are missing
* levoit_esphome/onboarding/custom_defaults: board and UART pins of a model's
  template, to start a custom config (Other ESP) from
* levoit_esphome/onboarding/check_name: whether a name can be used, and a
  free one
* levoit_esphome/onboarding/create: the secrets and the config in the Device
  Builder, and the device's sub-entry; the config is then listed as pending
  until the device connects (a new one), or updated over the air (existing)

The same steps as the integration page's Add device, through onboarding.py.
An error carries the config flow's error key as its code and the text as
its message.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp
import probatio

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import content as cnt, onboarding as onb, templates as tpl
from .const import DOMAIN
from .device_builder import DeviceBuilderCommandError, async_secret_names, builder_page_url
from .onboarding import OnboardingError

if TYPE_CHECKING:
    from .coordinator import LevoitEsphomeCoordinator

ERR_NOT_LOADED = "not_loaded"


@callback
def async_register(hass: HomeAssistant) -> None:
    """Register the commands (once, at integration setup)."""
    websocket_api.async_register_command(hass, ws_options)
    websocket_api.async_register_command(hass, ws_custom_defaults)
    websocket_api.async_register_command(hass, ws_check_name)
    websocket_api.async_register_command(hass, ws_create)


def _send_error(
    connection: websocket_api.ActiveConnection, msg_id: int, error: OnboardingError
) -> None:
    connection.send_error(msg_id, error.code, error.message)


async def _context(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> tuple[LevoitEsphomeCoordinator, Any, list[tpl.Template]] | None:
    """The coordinator, the Device Builder and the templates; the error sent if any is missing."""
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        connection.send_error(msg["id"], ERR_NOT_LOADED, "Levoit ESPHome is not set up")
        return None
    coordinator: LevoitEsphomeCoordinator = entries[0].runtime_data
    builder = coordinator.device_builder
    if builder is None:
        _send_error(connection, msg["id"], OnboardingError("no_device_builder"))
        return None
    try:
        templates = await coordinator.async_get_templates()
    except (aiohttp.ClientError, TimeoutError, KeyError, TypeError, ValueError):
        templates = []
    if not templates:
        _send_error(connection, msg["id"], OnboardingError("templates_unavailable"))
        return None
    return coordinator, builder, templates


def _content_of(
    content: dict[str, cnt.DeviceContent], variants: list[tpl.Template]
) -> dict[str, Any] | None:
    """A model's photo and notes, by the device folder of its templates."""
    for template in variants:
        if found := content.get(cnt.template_folder(template.file)):
            return found.as_dict()
    return None


def _template_dict(template: tpl.Template) -> dict[str, Any]:
    return {
        "variant": template.variant,
        "title": tpl.VARIANT_TITLES.get(template.variant, template.variant),
        "board": template.board,
        "name": template.name,
        "file": template.file,
    }


@websocket_api.require_admin
@websocket_api.websocket_command({probatio.Required("type"): "levoit_esphome/onboarding/options"})
@websocket_api.async_response
async def ws_options(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Everything the wizard's screens choose from."""
    if (found := await _context(hass, connection, msg)) is None:
        return
    coordinator, builder, templates = found
    content = await coordinator.async_get_content()
    with_template = {cnt.template_folder(t.file) for t in templates}
    try:
        state = await onb.async_builder_state(hass, builder, coordinator)
        present = await async_secret_names(hass, builder)
    except OnboardingError as err:
        _send_error(connection, msg["id"], err)
        return
    except DeviceBuilderCommandError:
        _send_error(connection, msg["id"], OnboardingError("cannot_connect"))
        return
    connection.send_result(
        msg["id"],
        {
            "models": [
                {
                    "model": model,
                    "title": title,
                    "variants": [_template_dict(t) for t in onb.variants(templates, model)],
                    "custom_base": onb.custom_base(onb.variants(templates, model)).file,
                    "content": _content_of(content, onb.variants(templates, model)),
                }
                for model, title in onb.models(templates)
            ],
            # devices of tuct/levoit without a template: their guide, no config
            "others": [c.as_dict() for c in content.values() if c.id not in with_template],
            "existing": [
                {
                    "name": d.name,
                    "title": d.title,
                    "model": d.model,
                    "api_key": onb.existing_api_key(hass, d.name) is not None,
                }
                for d in onb.unconfigured(coordinator)
            ],
            "channels": list(onb.CHANNELS),
            "boards": list(onb.COMMON_BOARDS),
            "esphome_version": state.esphome_version,
            "ota_encryption": tpl.supports_ota_encryption(state.esphome_version),
            "missing_secrets": [key for key in onb.WIFI_SECRETS if key not in present],
            "builder_url": builder_page_url(builder),
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/onboarding/custom_defaults",
        probatio.Required("template"): str,
    }
)
@websocket_api.async_response
async def ws_custom_defaults(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Board and UART pins of a template's builder file, and the boards to offer."""
    if (found := await _context(hass, connection, msg)) is None:
        return
    _, _, templates = found
    template = next((t for t in templates if t.file == msg["template"]), None)
    if template is None:
        _send_error(connection, msg["id"], OnboardingError("unknown_template"))
        return
    try:
        source = await tpl.async_fetch_template_text(async_get_clientsession(hass), template)
    except (aiohttp.ClientError, TimeoutError):
        _send_error(connection, msg["id"], OnboardingError("templates_unavailable"))
        return
    esp = tpl.builder_esp(source)
    boards = list(onb.COMMON_BOARDS)
    if esp.board and esp.board not in boards:
        boards.insert(0, esp.board)
    connection.send_result(
        msg["id"],
        {"board": esp.board, "rx_pin": esp.rx_pin, "tx_pin": esp.tx_pin, "boards": boards},
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/onboarding/check_name",
        probatio.Required("name"): str,
    }
)
@websocket_api.async_response
async def ws_check_name(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Whether the name can be used for a new device; `suggestion` is a free one like it."""
    if (found := await _context(hass, connection, msg)) is None:
        return
    coordinator, builder, _ = found
    try:
        state = await onb.async_builder_state(hass, builder, coordinator)
    except OnboardingError as err:
        _send_error(connection, msg["id"], err)
        return
    name = msg["name"].strip().lower()
    error = onb.check_name(name, state.taken)
    connection.send_result(
        msg["id"],
        {
            "name": name,
            "ok": error is None,
            "error": error,
            "message": onb.MESSAGES[error] if error else None,
            "suggestion": tpl.suggest_name(name, set(state.taken))
            if tpl.valid_name(name)
            else None,
        },
    )


@websocket_api.require_admin
@websocket_api.websocket_command(
    {
        probatio.Required("type"): "levoit_esphome/onboarding/create",
        probatio.Required("template"): str,
        probatio.Required("name"): str,
        probatio.Required("channel"): str,
        probatio.Optional("existing", default=False): bool,
        probatio.Optional("custom"): probatio.Any(
            None,
            {
                probatio.Required("board"): str,
                probatio.Required("rx_pin"): str,
                probatio.Required("tx_pin"): str,
            },
        ),
        probatio.Optional("ota_password"): probatio.Any(None, str),
    }
)
@websocket_api.async_response
async def ws_create(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    """Make the config (secrets, file, sub-entry); answers with its name."""
    if (found := await _context(hass, connection, msg)) is None:
        return
    coordinator, builder, templates = found
    template = next((t for t in templates if t.file == msg["template"]), None)
    if template is None:
        _send_error(connection, msg["id"], OnboardingError("unknown_template"))
        return
    custom = None
    if msg.get("custom"):
        custom, errors = onb.validate_custom(
            msg["custom"]["board"], msg["custom"]["rx_pin"], msg["custom"]["tx_pin"]
        )
        if errors:
            field, code = next(iter(errors.items()))
            connection.send_error(msg["id"], code, f"{field}: {onb.MESSAGES[code]}")
            return
    try:
        state = await onb.async_builder_state(hass, builder, coordinator)
        name = msg["name"].strip().lower()
        if msg["existing"]:
            if name not in {d.name for d in onb.unconfigured(coordinator)}:
                raise OnboardingError("unknown_device")
        elif error := onb.check_name(name, state.taken):
            raise OnboardingError(error)
        created = await onb.async_create_device(
            hass,
            coordinator,
            builder,
            onb.DeviceRequest(
                template=template,
                name=name,
                channel=msg["channel"],
                existing=msg["existing"],
                custom=custom,
                ota_password=msg.get("ota_password") or None,
            ),
            state.esphome_version,
        )
    except OnboardingError as err:
        _send_error(connection, msg["id"], err)
        return
    onb.async_add_subentry(hass, coordinator.config_entry, created)
    connection.send_result(
        msg["id"],
        {
            "name": created.name,
            "configuration": created.configuration,
            "existing": created.existing,
            "custom": created.custom,
            "encrypted_ota": created.encrypted_ota,
            "builder_url": created.builder_url,
        },
    )
