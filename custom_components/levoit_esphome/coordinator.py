"""Coordinator: which devices are ours, what they run, what is available."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from contextlib import AbstractAsyncContextManager, nullcontext
from dataclasses import dataclass, field, replace
from datetime import datetime
import logging
import re
from typing import TYPE_CHECKING, Any

import aiohttp

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    ATTR_ICON,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_HOST,
    CONF_PORT,
    PERCENTAGE,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from . import content as cnt, templates as tpl
from .build_log import (
    BUILD_LOG_IN_HA_LOG,
    BUILD_PUSH_INTERVAL,
    STAGE_COMPILE,
    STAGE_TEMPLATE,
    STAGE_UPLOAD,
    STAGE_WAITING,
    BuildLog,
)
from .const import (
    AUTO_ADD_INTERVAL,
    CHANNEL_STABLE,
    COMPONENTS,
    CONFIG_INTERVAL,
    DOMAIN,
    GITHUB_INTERVAL,
    KNOWN_MODELS,
    SCAN_INTERVAL,
)
from .controls import config_names
from .device_builder import (
    DeviceBuilder,
    DeviceBuilderCommandError,
    async_get_device_builder,
    async_read_config,
    async_secret_names,
    async_write_config,
)
from .github import async_fetch_heads
from .versions import (
    ChannelHead,
    Reported,
    component_model,
    component_source,
    parse_reported,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .groups import GroupManager

_LOGGER = logging.getLogger(__name__)

ESPHOME_DOMAIN = "esphome"
ESPHOME_API_PORT = 6053


@dataclass(frozen=True)
class ConfigFacts:
    """What we keep from a resolved config: never the config itself (secrets)."""

    model: str | None
    channel: str | None
    ref: str | None
    read_at: datetime
    deployed_version: str | None
    # builder file the config was made from; config_kind original / xiao_c3 / c3
    # for a template config, custom without one, None while unknown
    template: str | None = None
    config_kind: str | None = None
    # entity names of the levoit settings, per controls key (device page)
    control_names: Mapping[str, str] = field(default_factory=dict)


@dataclass
class LevoitDevice:
    """One ESPHome device that runs the levoit or philips component."""

    name: str
    mac: str
    title: str
    esphome_device_id: str
    components: frozenset[str]
    reported: Reported | None
    version_entity_id: str | None
    model_entity_id: str | None = None
    # the device's own filter-life sensor (ESPHome), shown by our Filter life
    filter_entity_id: str | None = None
    configuration: str | None = None
    esphome_deployed: str | None = None
    esphome_current: str | None = None
    model: str | None = None
    channel: str | None = None
    ref: str | None = None
    template: str | None = None
    config_kind: str | None = None
    # entity names from its config, per controls key (empty without a config)
    control_names: Mapping[str, str] = field(default_factory=dict)
    # False: known from before (our device entry exists) but nothing tells
    # right now that it runs the component: offline since a restart, no config
    detected: bool = True
    # its version / model sensor has a value (None: no such sensor)
    online: bool | None = None


@dataclass
class _FoundSensors:
    """What a device's own ESPHome sensors tell."""

    reported: Reported | None = None
    version_entity_id: str | None = None
    model: str | None = None
    model_entity_id: str | None = None
    filter_entity_id: str | None = None


_PRE_FILTER = re.compile(r"\bpre[- ]?filter")


def _filter_score(entity: er.RegistryEntry, state: State | None) -> int | None:
    """How well a sensor fits as the device's filter life; None if it does not.

    The levoit / philips filter sensors report `%` with the `mdi:air-filter`
    icon by default; the name may be anything ("Filter %", "HEPA Filter" ...),
    so "filter" in the name also counts. With several, the main filter wins:
    HEPA over the pre-filter, the computed value over the MCU's.
    """
    attrs = state.attributes if state is not None else {}
    unit = entity.unit_of_measurement or attrs.get(ATTR_UNIT_OF_MEASUREMENT)
    if unit != PERCENTAGE:
        return None
    icon = entity.icon or entity.original_icon or attrs.get(ATTR_ICON)
    name = " ".join(
        str(n) for n in (entity.name, entity.original_name, attrs.get(ATTR_FRIENDLY_NAME)) if n
    ).lower()
    if icon != "mdi:air-filter" and "filter" not in name:
        return None
    score = 0
    if "hepa" in name:
        score += 2
    if _PRE_FILTER.search(name):
        score -= 2
    if "mcu" in name:
        score -= 1
    return score


BUILD_STEP_TEMPLATE = STAGE_TEMPLATE  # rewriting a template config from the newest builder file
BUILD_STEP_WAITING = STAGE_WAITING  # an older Device Builder compiles another device first
BUILD_STEP_COMPILE = STAGE_COMPILE
BUILD_STEP_UPLOAD = STAGE_UPLOAD
# progress bar of the update entity per step, in %, until the build's output
# says more (BuildLog.percent)
BUILD_STEPS = {
    BUILD_STEP_TEMPLATE: 5,
    BUILD_STEP_WAITING: 5,
    BUILD_STEP_COMPILE: 10,
    BUILD_STEP_UPLOAD: 85,
}


@dataclass(frozen=True)
class BuildResult:
    """How the last compile / upload of a device ended."""

    ok: bool
    upload: bool
    at: datetime
    error: str | None = None
    note: str | None = None  # what the integration did after the build (OTA migration)


@dataclass(frozen=True)
class PendingConfig:
    """A config made by Add device whose ESP has not connected yet (not flashed)."""

    name: str
    configuration: str
    template: str | None = None  # the builder file it was made from
    custom: bool = False  # Other ESP: the user's own board and pins
    address: str | None = None  # where the Device Builder expects it (name.local)


@dataclass
class LevoitData:
    """Coordinator data."""

    devices: dict[str, LevoitDevice] = field(default_factory=dict)
    heads: dict[str, ChannelHead] = field(default_factory=dict)
    # configs made by Add device, flashed not yet: listed until the ESP connects
    pending: dict[str, PendingConfig] = field(default_factory=dict)


class LevoitEsphomeCoordinator(DataUpdateCoordinator[LevoitData]):
    """Joins Home Assistant's ESPHome devices, Device Builder configs and GitHub."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self._heads: dict[str, ChannelHead] = {}
        self._heads_at: datetime | None = None
        self.templates: list[tpl.Template] = []
        # Add device's photos and notes (devices/onboarding.json); None: not read yet
        self.content: dict[str, cnt.DeviceContent] | None = None
        self._facts: dict[str, ConfigFacts] = {}
        self._facts_task: asyncio.Task[None] | None = None
        # Channel per device name, for devices without a Device Builder config;
        # set (and restored after a restart) by the "Update channel" select.
        self._chosen_channels: dict[str, str] = {}
        # Version / model sensors found per device, kept while they are
        # unavailable (device restarting).
        self._sensors: dict[str, _FoundSensors] = {}
        self._tracked: frozenset[str] = frozenset()
        self._unsub_states: CALLBACK_TYPE | None = None
        # Device Builders before 2026.6 have no build queue: one compile at a time.
        self.build_lock = asyncio.Lock()
        self._building: set[str] = set()
        # step of each running build (BUILD_STEPS), for the update's progress bar
        self._build_steps: dict[str, str] = {}
        self.last_builds: dict[str, BuildResult] = {}
        # output of each device's last build, newest lines only, read into steps
        self.build_logs: dict[str, BuildLog] = {}
        # the panel follows a running build's output, at most once a second
        self._build_push: asyncio.TimerHandle | None = None
        self._build_pushed_at = 0.0
        # Auto-add: while configs wait for their first flash, look for them.
        self._unsub_auto_add: CALLBACK_TYPE | None = None
        self._auto_add_task: asyncio.Task[None] | None = None
        # purifier groups; set up with the entry
        self.groups: GroupManager

    @property
    def device_builder(self) -> DeviceBuilder | None:
        """Home Assistant's Device Builder connection."""
        return async_get_device_builder(self.hass)

    async def _async_update_data(self) -> LevoitData:
        builder = self.device_builder
        if builder is None:
            raise UpdateFailed("The ESPHome Device Builder add-on is not available")
        try:
            listing = await builder.api.get_devices()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise UpdateFailed(f"Device Builder: {err}") from err
        configured: dict[str, dict[str, Any]] = {
            dev["name"]: dev for dev in listing.get("configured", []) if dev.get("name")
        }

        await self._async_refresh_heads()

        devices = self._collect_devices(configured)
        self._schedule_config_reads(builder, devices)
        self._track_version_entities(devices)
        pending = self._collect_pending(configured, devices)
        self._watch_pending(pending)
        return LevoitData(devices=devices, heads=dict(self._heads), pending=pending)

    @callback
    def _collect_pending(
        self, configured: dict[str, dict[str, Any]], devices: dict[str, LevoitDevice]
    ) -> dict[str, PendingConfig]:
        """Configs made by Add device that have no device yet: not flashed.

        A new device's config exists from Add device on, but the ESP joins Home
        Assistant only after its first flash over USB. Until then it is listed
        here, so the sidebar page shows what to do next. A config deleted in the
        Device Builder is not listed, and neither is one for a device that was
        already in Home Assistant (it is updated over the air).
        """
        pending: dict[str, PendingConfig] = {}
        for sub in self.config_entry.subentries.values():
            name = sub.unique_id
            if sub.subentry_type != "device" or not name or name in devices:
                continue
            if sub.data.get("existing"):
                continue
            configuration = sub.data.get("configuration")
            if not configuration or name not in configured:
                continue
            pending[name] = PendingConfig(
                name=name,
                configuration=configuration,
                template=sub.data.get("template"),
                custom=bool(sub.data.get("custom")),
                address=configured[name].get("address"),
            )
        return pending

    @callback
    def _watch_pending(self, pending: dict[str, PendingConfig]) -> None:
        """Look for not yet flashed devices every AUTO_ADD_INTERVAL, while any."""
        if pending and self._unsub_auto_add is None:
            self._unsub_auto_add = async_track_time_interval(
                self.hass, self._async_auto_add_tick, AUTO_ADD_INTERVAL
            )
        elif not pending and self._unsub_auto_add is not None:
            self._unsub_auto_add()
            self._unsub_auto_add = None

    @callback
    def _async_auto_add_tick(self, _now: datetime) -> None:
        if self._auto_add_task is not None and not self._auto_add_task.done():
            return  # the last round is still waiting on a device
        pending = dict(self.data.pending) if self.data else {}
        if pending:
            self._auto_add_task = self.config_entry.async_create_background_task(
                self.hass, self._async_auto_add(pending), f"{DOMAIN} auto-add"
            )

    async def _async_auto_add(self, pending: dict[str, PendingConfig]) -> None:
        """Add freshly flashed devices to the ESPHome integration.

        Home Assistant only offers a flashed ESP as a discovered device, to be
        confirmed by hand. A device made by Add device is ours, so it is added
        right away: the ESPHome integration's own flow connects to it, gets its
        key from the Device Builder and creates the entry, as if the user had
        typed its address. A device that is not reachable (not flashed yet,
        not on the Wi-Fi) leaves nothing behind; it is tried again next time.
        """
        known = {
            entry.data.get("device_name")
            for entry in self.hass.config_entries.async_entries(ESPHOME_DOMAIN)
        }
        added = False
        for config in pending.values():
            if config.name not in known:
                added |= await self._async_try_add(config)
        if added:
            await self.async_request_refresh()

    async def _async_try_add(self, config: PendingConfig) -> bool:
        """Start the ESPHome integration's flow for one device; True if added."""
        flows = self.hass.config_entries.flow
        host = config.address or f"{config.name}.local"
        try:
            result = await flows.async_init(
                ESPHOME_DOMAIN,
                context={"source": SOURCE_USER},
                data={CONF_HOST: host, CONF_PORT: ESPHOME_API_PORT},
            )
        except HomeAssistantError as err:
            _LOGGER.debug("Auto-add of %s failed: %s", config.name, err)
            return False
        if result["type"] is FlowResultType.CREATE_ENTRY:
            _LOGGER.info("Added %s to the ESPHome integration", config.name)
            return True
        if result["type"] is FlowResultType.FORM:
            # not reachable, or it wants input (a key, a name conflict): leave
            # it to Home Assistant's discovery and the user
            flows.async_abort(result["flow_id"])
            _LOGGER.debug("%s not added yet: %s", config.name, result.get("errors"))
        return False

    def pending_device(self, name: str) -> LevoitDevice | None:
        """A pending config as a device, to compile it (it cannot be uploaded)."""
        config = self.data.pending.get(name) if self.data else None
        if config is None:
            return None
        return LevoitDevice(
            name=config.name,
            mac="",
            title=config.name,
            esphome_device_id="",
            components=frozenset(),
            reported=None,
            version_entity_id=None,
            configuration=config.configuration,
            detected=False,
        )

    async def _async_refresh_heads(self) -> None:
        now = dt_util.utcnow()
        if self._heads_at is not None and now - self._heads_at < GITHUB_INTERVAL:
            return
        session = async_get_clientsession(self.hass)
        try:
            self._heads = await async_fetch_heads(session)
        except (aiohttp.ClientError, TimeoutError, KeyError, ValueError) as err:
            # Keep the last known heads; try again on the next refresh.
            _LOGGER.warning("Could not read the latest versions from GitHub: %s", err)
            return
        self._heads_at = now
        try:
            self.templates = await tpl.async_fetch_templates(session)
        except (aiohttp.ClientError, TimeoutError, KeyError, TypeError, ValueError) as err:
            _LOGGER.warning("Could not read the device templates from GitHub: %s", err)
        # Add device's content, and the photo of every device
        await self.async_get_content(refresh=True)

    @property
    def heads_checked_at(self) -> datetime | None:
        """When the latest versions were last read from GitHub."""
        return self._heads_at

    async def async_check_now(self) -> None:
        """Read the latest versions from GitHub and the devices again, now."""
        self._heads_at = None
        await self.async_refresh()

    async def async_get_content(self, *, refresh: bool = False) -> dict[str, cnt.DeviceContent]:
        """Add device's photos and notes; read now if not yet (or `refresh`).

        Optional: when GitHub does not answer, Add device goes on without them
        (and the last ones read are kept).
        """
        if self.content is None or refresh:
            try:
                self.content = await cnt.async_fetch_content(async_get_clientsession(self.hass))
            except (aiohttp.ClientError, TimeoutError, ValueError) as err:
                _LOGGER.debug("Could not read the Add device content from GitHub: %s", err)
        return self.content or {}

    def photo_url(self, model: str | None) -> str | None:
        """The product photo of a model (tuct/levoit), if there is one."""
        return cnt.photo_for(model, self.content or {}, self.templates)

    async def async_get_templates(self) -> list[tpl.Template]:
        """The device templates; fetched now if not loaded yet."""
        if not self.templates:
            self.templates = await tpl.async_fetch_templates(async_get_clientsession(self.hass))
        return self.templates

    async def async_refresh_from_template(self, builder: DeviceBuilder, configuration: str) -> bool:
        """Rewrite a template config from the newest builder file; True if it changed.

        Keeps the device's name, secret names (or inline values) and channel.
        A custom config is left alone. Written only if the file did not change
        in the meantime (the Device Builder checks `expected`).
        """
        text = await async_read_config(self.hass, builder, configuration)
        template = tpl.template_of(text, await self.async_get_templates())
        if template is None:
            return False
        values = tpl.config_values(text)
        source = await tpl.async_fetch_template_text(async_get_clientsession(self.hass), template)
        new = tpl.render(source, template, values)
        if tpl.config_values(new) != values:
            raise tpl.TemplateError("template refresh could not preserve the device configuration")
        if new == text:
            return False
        await async_write_config(self.hass, builder, configuration, new, expected=text)
        return True

    @callback
    def _collect_devices(self, configured: dict[str, dict[str, Any]]) -> dict[str, LevoitDevice]:
        dev_reg = dr.async_get(self.hass)
        ent_reg = er.async_get(self.hass)
        devices: dict[str, LevoitDevice] = {}

        for entry in self.hass.config_entries.async_entries(ESPHOME_DOMAIN):
            name = entry.data.get("device_name")
            if not name:
                continue
            device = next(
                (
                    d
                    for d in dr.async_entries_for_config_entry(dev_reg, entry.entry_id)
                    if any(c[0] == dr.CONNECTION_NETWORK_MAC for c in d.connections)
                ),
                None,
            )
            if device is None:
                continue
            mac = next(c[1] for c in device.connections if c[0] == dr.CONNECTION_NETWORK_MAC)

            found = self._scan_sensors(ent_reg, name, device.id)
            config = configured.get(name)
            components = frozenset(
                COMPONENTS & set((config or {}).get("loaded_integrations") or [])
            )
            detected = bool(components) or found.reported is not None or found.model is not None
            if not detected and not self._known(dev_reg, mac):
                continue  # not one of ours

            levoit_device = LevoitDevice(
                name=name,
                mac=mac,
                title=device.name_by_user or device.name or name,
                esphome_device_id=device.id,
                components=components,
                reported=found.reported,
                version_entity_id=found.version_entity_id,
                model_entity_id=found.model_entity_id,
                filter_entity_id=found.filter_entity_id,
                model=found.model,
                detected=detected,
                online=self._online(found) if detected else False,
            )
            if config is not None:
                levoit_device.configuration = config.get("configuration")
                levoit_device.esphome_deployed = config.get("deployed_version")
                levoit_device.esphome_current = config.get("current_version")
            self._apply_facts(levoit_device)
            devices[name] = levoit_device
        return devices

    def _apply_facts(self, device: LevoitDevice) -> None:
        """Model and channel: from the config read, else the user's choice.

        A device without a Device Builder config has no `ref:` to read; its
        channel is the one picked in its "Update channel" select (default
        stable). The model then comes from its `model` text sensor.
        """
        if not device.configuration:
            device.channel = self._chosen_channels.get(device.name, CHANNEL_STABLE)
            return
        if facts := self._facts.get(device.configuration):
            device.model = facts.model or device.model
            device.channel = facts.channel
            device.ref = facts.ref
            device.template = facts.template
            device.config_kind = facts.config_kind
            device.control_names = facts.control_names

    @callback
    def async_choose_channel(self, name: str, channel: str) -> None:
        """Set the channel of a device without a Device Builder config."""
        self._chosen_channels[name] = channel
        if self.data is None or name not in self.data.devices:
            return
        self._async_reapply_facts()

    @callback
    def _async_reapply_facts(self) -> None:
        """Push the stored facts and choices to the current data, without a refresh."""
        devices = {n: replace(d) for n, d in self.data.devices.items()}
        for device in devices.values():
            self._apply_facts(device)
        self.async_set_updated_data(
            LevoitData(devices=devices, heads=self.data.heads, pending=self.data.pending)
        )

    def can_set_channel(self, device: LevoitDevice) -> bool:
        """Without a config (the user's choice) or with a template config (its `ref:`).

        A custom config is the user's own file: its `ref:` is changed there.
        """
        return not device.configuration or device.template is not None

    async def async_set_channel(self, device: LevoitDevice, channel: str) -> None:
        """Switch a device to `channel`.

        Without a config this only changes what it is compared with. A template
        config gets its component `ref:` rewritten in the Device Builder (only
        if the file did not change meanwhile); the next install builds from
        the new channel.
        """
        if not device.configuration:
            self.async_choose_channel(device.name, channel)
            return
        builder = self.device_builder
        if builder is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_device_builder")
        if not self.can_set_channel(device):
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="custom_channel")
        configuration = device.configuration
        try:
            text = await async_read_config(self.hass, builder, configuration)
            if tpl.template_of(text, await self.async_get_templates()) is None:
                raise HomeAssistantError(
                    translation_domain=DOMAIN, translation_key="custom_channel"
                )
            new = tpl.with_channel(text, channel)
            if new != text:
                await async_write_config(self.hass, builder, configuration, new, expected=text)
        except (
            DeviceBuilderCommandError,
            tpl.TemplateError,
            aiohttp.ClientError,
            TimeoutError,
        ) as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="channel_failed",
                translation_placeholders={"configuration": configuration, "error": str(err)},
            ) from err
        # the ref is known now; no new `esphome config` run needed
        if (facts := self._facts.get(configuration)) is not None:
            self._facts[configuration] = replace(facts, channel=channel, ref=channel)
        if self.data is not None:
            self._async_reapply_facts()

    def _scan_sensors(self, ent_reg: er.EntityRegistry, name: str, device_id: str) -> _FoundSensors:
        """Version and model, from the device's `esp_version` and `model` sensors.

        Matched by their states (the version format, a known model name), so
        the sensors' names do not matter. ESPHome text sensors are `sensor`
        entities in Home Assistant.

        While the device restarts (after an update) its sensors are
        unavailable and match nothing. Then the sensors found before are kept,
        with their last values, so the device keeps its installed version and
        the sensors stay watched: the new version shows as soon as it is back.
        """
        found = _FoundSensors()
        best_filter: int | None = None
        for entity in er.async_entries_for_device(ent_reg, device_id):
            if entity.domain != Platform.SENSOR or entity.platform != ESPHOME_DOMAIN:
                continue
            state = self.hass.states.get(entity.entity_id)
            score = _filter_score(entity, state)
            if score is not None and (best_filter is None or score > best_filter):
                best_filter = score
                found.filter_entity_id = entity.entity_id
            if state is None:
                continue
            if found.reported is None and (reported := parse_reported(state.state)):
                found.reported = reported
                found.version_entity_id = entity.entity_id
            elif found.model is None and state.state in KNOWN_MODELS:
                found.model = state.state
                found.model_entity_id = entity.entity_id

        if (before := self._sensors.get(name)) is not None:
            if found.version_entity_id is None and self._offline(ent_reg, before.version_entity_id):
                found.reported = before.reported
                found.version_entity_id = before.version_entity_id
            if found.model_entity_id is None and self._offline(ent_reg, before.model_entity_id):
                found.model = before.model
                found.model_entity_id = before.model_entity_id
        self._sensors[name] = found
        return found

    def _known(self, dev_reg: dr.DeviceRegistry, mac: str) -> bool:
        """Whether this integration made a device for it before.

        A device without a Device Builder config is recognised by its sensors'
        values only. While it is offline (after a restart) they have none; the
        device entry from before keeps it listed, as offline, until it is back
        or deleted.
        """
        return (
            dev_reg.async_get_device_by_identifier((DOMAIN, mac), self.config_entry.entry_id)
            is not None
        )

    def _online(self, found: _FoundSensors) -> bool | None:
        """Whether its version (else model) sensor has a value now."""
        entity_id = found.version_entity_id or found.model_entity_id
        if entity_id is None:
            return None
        state = self.hass.states.get(entity_id)
        return state is not None and state.state not in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    def _offline(self, ent_reg: er.EntityRegistry, entity_id: str | None) -> bool:
        """The sensor still exists but has no value right now."""
        if entity_id is None or ent_reg.async_get(entity_id) is None:
            return False
        state = self.hass.states.get(entity_id)
        return state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN)

    @callback
    def _schedule_config_reads(
        self, builder: DeviceBuilder, devices: dict[str, LevoitDevice]
    ) -> None:
        """Read model and channel of configs that are new, changed or stale."""
        if self._facts_task is not None and not self._facts_task.done():
            return
        now = dt_util.utcnow()
        stale = [
            (d.configuration, d.esphome_deployed)
            for d in devices.values()
            if d.configuration
            and (
                (facts := self._facts.get(d.configuration)) is None
                or now - facts.read_at >= CONFIG_INTERVAL
                or facts.deployed_version != d.esphome_deployed
            )
        ]
        if not stale:
            return
        # Not eager: the task must not run inside the refresh that schedules it,
        # or that refresh's result would overwrite what the task applies.
        self._facts_task = self.config_entry.async_create_background_task(
            self.hass,
            self._async_read_configs(builder, stale),
            f"{DOMAIN} config read",
            eager_start=False,
        )

    async def _async_read_configs(
        self, builder: DeviceBuilder, stale: list[tuple[str, str | None]]
    ) -> None:
        """Run `esphome config` per config (in the Device Builder), one at a time."""
        changed = False
        for configuration, deployed in stale:
            try:
                config = await builder.api.get_config(configuration)
            except (aiohttp.ClientError, TimeoutError) as err:
                _LOGGER.debug("Could not read %s: %s", configuration, err)
                continue
            # The resolved config contains secrets: keep only model and source.
            source = component_source(config or {})
            template, kind = await self._async_config_kind(builder, configuration)
            self._facts[configuration] = ConfigFacts(
                model=component_model(config or {}),
                channel=source[0] if source else None,
                ref=source[1] if source else None,
                read_at=dt_util.utcnow(),
                deployed_version=deployed,
                template=template,
                config_kind=kind,
                control_names=config_names(config or {}),
            )
            changed = True
        if changed and self.data is not None:
            # Apply to the current data instead of a new refresh: no second
            # round of Device Builder and state lookups, and no refresh in
            # flight can overwrite it.
            self._async_reapply_facts()

    async def _async_config_kind(
        self, builder: DeviceBuilder, configuration: str
    ) -> tuple[str | None, str | None]:
        """Template file and kind of a config, from its YAML as written."""
        if not self.templates:
            return None, None
        try:
            text = await async_read_config(self.hass, builder, configuration)
        except DeviceBuilderCommandError as err:
            _LOGGER.debug("Could not read %s as written: %s", configuration, err)
            return None, None
        if (template := tpl.template_of(text, self.templates)) is None:
            return None, tpl.VARIANT_CUSTOM
        return template.file, template.variant

    @callback
    def async_forget_config(self, configuration: str) -> None:
        """Read a config again on the next refresh (after a build)."""
        self._facts.pop(configuration, None)

    def is_building(self, name: str) -> bool:
        """Whether a compile / upload of this device is running."""
        return name in self._building

    def build_step(self, name: str) -> str | None:
        """What a running build of this device does now (a BUILD_STEPS key)."""
        return self._build_steps.get(name) if name in self._building else None

    def build_progress(self, name: str) -> int | None:
        """Progress of a running build in %, None when not building.

        The Device Builder does not report progress; the build's output does:
        the compile counter moves the bar from 10 to 80 %, the upload's own
        bar from 85 to 100. Before the output says anything, the step's value.
        """
        step = self.build_step(name)
        if step is None:
            return None
        log = self.build_logs.get(name)
        percent = log.percent() if log is not None else None
        return percent if percent is not None else BUILD_STEPS[step]

    def build_summary(self, name: str) -> dict[str, Any] | None:
        """The steps and newest lines of a device's last (or running) build."""
        log = self.build_logs.get(name)
        return log.summary() if log is not None else None

    @callback
    def _async_set_build_step(self, name: str, step: str) -> None:
        self._build_steps[name] = step
        if (log := self.build_logs.get(name)) is not None:
            log.stage(step)
        self.async_update_listeners()

    @callback
    def _async_build_output(self) -> None:
        """A line of build output arrived: tell the listeners, at most once a second."""
        if self._build_push is not None:
            return
        loop = self.hass.loop
        delay = max(0.0, self._build_pushed_at + BUILD_PUSH_INTERVAL - loop.time())
        self._build_push = loop.call_later(delay, self._async_push_build_output)

    @callback
    def _async_push_build_output(self) -> None:
        self._build_push = None
        self._build_pushed_at = self.hass.loop.time()
        self.async_update_listeners()

    @callback
    def _async_cancel_build_push(self) -> None:
        if self._build_push is not None:
            self._build_push.cancel()
            self._build_push = None

    async def async_build(self, device: LevoitDevice, *, upload: bool) -> None:
        """Compile a device's config in the Device Builder; with `upload`, also install it.

        One build per device at a time. Installing first rewrites a template
        config from the newest builder file (a custom config is built as it
        is); compiling alone builds the config as it is now. A failed compile
        never uploads.
        """
        builder = self.device_builder
        if not device.configuration:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_configuration")
        if builder is None:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="no_device_builder")
        if device.name in self._building:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="already_building")
        configuration = device.configuration
        lock: AbstractAsyncContextManager[Any] = (
            nullcontext() if getattr(builder, "supports_build_queue", False) else self.build_lock
        )

        self._building.add(device.name)
        # The Device Builder streams the output to us only; it keeps none of it.
        log = BuildLog(upload=upload, on_line=self._async_build_output)
        self.build_logs[device.name] = log
        self.async_update_listeners()
        try:
            await self._async_run_build(
                builder, device, configuration, upload=upload, lock=lock, log=log
            )
        except (HomeAssistantError, aiohttp.ClientError, TimeoutError) as err:
            # shown in the panel; the caller still gets the error
            log.finish(False, log.reason() if isinstance(err, HomeAssistantError) else str(err))
            self.last_builds[device.name] = BuildResult(
                ok=False, upload=upload, at=dt_util.utcnow(), error=str(err), note=log.note
            )
            _LOGGER.error(
                "Building %s failed: %s\nLast lines of the build:\n%s",
                configuration,
                err,
                "\n".join(log.lines[-BUILD_LOG_IN_HA_LOG:]),
            )
            raise
        else:
            log.finish(True)
            self.last_builds[device.name] = BuildResult(
                ok=True, upload=upload, at=dt_util.utcnow(), note=log.note
            )
        finally:
            self._async_cancel_build_push()
            self._building.discard(device.name)
            self._build_steps.pop(device.name, None)
            if upload:
                self.async_forget_config(configuration)
            self.async_update_listeners()
            await self.async_request_refresh()

    async def _async_run_build(
        self,
        builder: DeviceBuilder,
        device: LevoitDevice,
        configuration: str,
        *,
        upload: bool,
        lock: AbstractAsyncContextManager[Any],
        log: BuildLog,
    ) -> None:
        """Template refresh (install), compile, upload (install)."""
        placeholders = {"configuration": configuration}
        if upload and device.template:
            self._async_set_build_step(device.name, BUILD_STEP_TEMPLATE)
            try:
                await self.async_refresh_from_template(builder, configuration)
            except (
                DeviceBuilderCommandError,
                tpl.TemplateError,
                aiohttp.ClientError,
                TimeoutError,
            ) as err:
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="template_refresh_failed",
                    translation_placeholders={**placeholders, "error": str(err)},
                ) from err
        if isinstance(lock, asyncio.Lock) and lock.locked():
            # an older Device Builder compiles one at a time: another device first
            self._async_set_build_step(device.name, BUILD_STEP_WAITING)
        async with lock:
            self._async_set_build_step(device.name, BUILD_STEP_COMPILE)
            compiled = await builder.api.compile(configuration, line_received_cb=log.add)
        if not compiled:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="compile_failed",
                translation_placeholders={**placeholders, "reason": log.reason()},
            )
        if not upload:
            return
        self._async_set_build_step(device.name, BUILD_STEP_UPLOAD)
        if await builder.api.upload(configuration, "OTA", line_received_cb=log.add):
            if device.template:
                log.note = await self._async_encrypt_ota_after_upload(builder, device, log)
            return
        if device.template and log.encryption_refused:
            log.note = await self._async_undo_ota_encryption(builder, device)
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="upload_failed",
            translation_placeholders={**placeholders, "reason": log.reason()},
        )

    # --- OTA encryption: the migration from a password, as ESPHome describes it ------
    #
    # A firmware built by ESPHome 2026.9.0 or newer with an API key offers OTA
    # encryption, whatever its own `ota:` says. So after a successful password
    # (or unprotected) upload of such a build, the config can require
    # encryption for the next one: the line is swapped, nothing is built. Should
    # that next upload be refused ("did not offer encryption"), the config goes
    # back to what it had: the password line while its secret exists, else no
    # OTA credential.

    async def _async_encrypt_ota_after_upload(
        self, builder: DeviceBuilder, device: LevoitDevice, log: BuildLog
    ) -> str | None:
        """Make a template config's OTA inherit the API key's encryption; the note, or None.

        From a password line, or from no OTA credential at all (a device that
        was added without a password); a config without an API key, or with an
        explicit OTA key, is left as it is.
        """
        assert device.configuration
        if not tpl.supports_ota_encryption(log.esphome_version or device.esphome_current):
            return None
        try:
            text = await async_read_config(self.hass, builder, device.configuration)
            values = tpl.config_values(text)
            if values.api_key is None or values.ota_encryption_key is not None:
                return None
            if values.ota_uses_api_key:
                return None  # done already
            if values.ota_password is None:
                new = tpl.ota_encryption_from_none(text)
            else:
                new = tpl.ota_encryption_from_password(text)
            expected = replace(values, ota_password=None, ota_uses_api_key=True)
            if tpl.config_values(new) != expected:
                raise tpl.TemplateError("the OTA line could not be swapped for encryption")
            await async_write_config(self.hass, builder, device.configuration, new, expected=text)
        except (
            DeviceBuilderCommandError,
            tpl.TemplateError,
            aiohttp.ClientError,
            TimeoutError,
        ) as err:
            _LOGGER.warning(
                "%s: the OTA credential stays; could not switch the config to encryption: %s",
                device.configuration,
                err,
            )
            return None
        self.async_forget_config(device.configuration)
        _LOGGER.info("%s: OTA encrypted from the next update on", device.configuration)
        return "OTA encrypted from the next update on"

    async def _async_undo_ota_encryption(
        self, builder: DeviceBuilder, device: LevoitDevice
    ) -> str | None:
        """After a refused encrypted upload: the password line back while its secret exists,
        else no OTA credential, so the next update is a plain one again.
        """
        assert device.configuration
        secret = tpl.secret_key(device.name, "ota_password")
        try:
            text = await async_read_config(self.hass, builder, device.configuration)
            values = tpl.config_values(text)
            if not values.ota_uses_api_key:
                return None
            if secret in await async_secret_names(self.hass, builder):
                new = tpl.ota_password_from_encryption(text, secret)
                expected = replace(
                    values, ota_password=tpl.Value(secret=secret), ota_uses_api_key=False
                )
                note = "OTA password restored for the next update"
            else:
                new = tpl.ota_none_from_encryption(text)
                expected = replace(values, ota_uses_api_key=False)
                note = "OTA encryption dropped for the next update"
            if tpl.config_values(new) != expected:
                raise tpl.TemplateError("the OTA line could not be swapped back")
            await async_write_config(self.hass, builder, device.configuration, new, expected=text)
        except (
            DeviceBuilderCommandError,
            tpl.TemplateError,
            aiohttp.ClientError,
            TimeoutError,
        ) as err:
            _LOGGER.warning(
                "%s: could not undo the OTA encryption after the refused upload: %s",
                device.configuration,
                err,
            )
            return None
        self.async_forget_config(device.configuration)
        _LOGGER.warning(
            "%s: the device did not offer OTA encryption; %s", device.configuration, note.lower()
        )
        return note

    @callback
    def _track_version_entities(self, devices: dict[str, LevoitDevice]) -> None:
        """Refresh as soon as a device reports a new version or model (after an update).

        For a device that is only remembered (offline), every ESPHome sensor of
        it: whichever comes back first brings it back.
        """
        ent_reg = er.async_get(self.hass)
        wanted = frozenset(
            entity_id
            for d in devices.values()
            for entity_id in (d.version_entity_id, d.model_entity_id)
            if entity_id
        ) | frozenset(
            entity.entity_id
            for d in devices.values()
            if not d.detected
            for entity in er.async_entries_for_device(ent_reg, d.esphome_device_id)
            if entity.domain == Platform.SENSOR and entity.platform == ESPHOME_DOMAIN
        )
        if wanted == self._tracked:
            return
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        self._tracked = wanted
        if wanted:
            self._unsub_states = async_track_state_change_event(
                self.hass, list(wanted), self._async_version_changed
            )

    async def _async_version_changed(self, event: Event[EventStateChangedData]) -> None:
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Stop tracking states and looking for new devices."""
        self._async_cancel_build_push()
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        self._watch_pending({})
        await super().async_shutdown()
