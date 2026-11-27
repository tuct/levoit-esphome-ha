"""Purifier groups in Home Assistant: stored groups and the loop that runs them.

The rules (levels, speed mapping, hold, rising fast) are in groups_logic.py.
Here each enabled group follows its sensors and members and puts each member at
its step for the group level: Off, Sleep, or Manual at a speed (Turbo for the
Everest Air's top one). Without any sensor value (or with the group turned
off) it lets go: the purifiers keep running as they are.
Changes the group made carry its own Context; any other change to a member it
controls is a person's, and pauses the group for that member.
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
import logging
import math
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from homeassistant.components.fan import (
    ATTR_PERCENTAGE,
    ATTR_PERCENTAGE_STEP,
    ATTR_PRESET_MODE,
    ATTR_PRESET_MODES,
    DOMAIN as FAN_DOMAIN,
)
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_UNIT_OF_MEASUREMENT,
    EVENT_HOMEASSISTANT_STOP,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
    STATE_OFF,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import (
    CALLBACK_TYPE,
    Context,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.percentage import ranged_value_to_percentage

from .const import DOMAIN
from .controls import match_controls
from .groups_logic import (
    AQI,
    COMBINE_AVG,
    COMBINE_MEDIAN,
    COMBINE_MIN,
    ERR_MEMBERS,
    MODE_AUTO,
    MODE_MANUAL,
    PM1,
    PM10,
    PM25,
    SENSOR_TYPES,
    STEP_OFF,
    STEP_SLEEP,
    Evaluation,
    GroupConfig,
    GroupError,
    GroupSensor,
    History,
    LevelKeeper,
    Reading,
    Step,
    air_quality,
    evaluate,
    member_step,
    merge_sensors,
    parse_config,
    speed_count,
)

if TYPE_CHECKING:
    from .coordinator import LevoitEsphomeCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY = f"{DOMAIN}.groups"
STORAGE_VERSION = 1
TICK = timedelta(seconds=30)

# a group added (its entities are created)
SIGNAL_GROUPS = f"{DOMAIN}_groups"

ERR_NOT_FOUND = "not_found"

PRESET_MANUAL = "Manual"
PRESET_SLEEP = "Sleep"
# the Everest Air's top speed is a preset, above its 3 fan speeds
PRESET_TURBO = "Turbo"

# a group's total CADR, next to its combined sensor types
CADR = "cadr"
CADR_KEY = "sensor.current_cadr"

# controls.py keys of a purifier's air sensors
SENSOR_KEYS = {
    "sensor.pm1_0": PM1,
    "sensor.pm25": PM25,
    "sensor.pm10": PM10,
    "sensor.aqi": AQI,
}
TYPE_LABELS = {PM1: "PM1", PM25: "PM2.5", PM10: "PM10", AQI: "AQI index"}
AQI_WORDS = {1: "Very good", 2: "Good", 3: "Moderate", 4: "Poor"}
COMBINE_WORDS = {COMBINE_AVG: "average", COMBINE_MEDIAN: "median", COMBINE_MIN: "lowest"}

STATUS_PAUSED = "paused"  # control switch off
STATUS_MANUAL = "manual"  # the user's level for all members
STATUS_IN_CONTROL = "in_control"
STATUS_WATCHING = "watching"  # air is clean
STATUS_NO_SENSORS = "no_sensors"  # no sensor with a number: never takes control

OFFLINE = (STATE_UNAVAILABLE, STATE_UNKNOWN)


def signal_group(group_id: str) -> str:
    """Dispatcher signal: this group's config or state changed."""
    return f"{DOMAIN}_group_{group_id}"


def group_identifier(group_id: str) -> tuple[str, str]:
    """Device registry identifier of a group's device."""
    return (DOMAIN, f"group_{group_id}")


def _now() -> float:
    return dt_util.utcnow().timestamp()


def _iso(timestamp: float | None) -> str | None:
    return dt_util.utc_from_timestamp(timestamp).isoformat() if timestamp is not None else None


@dataclass(frozen=True)
class LevoitFan:
    """A purifier that can be in a group: the fan of a Levoit device."""

    entity_id: str
    name: str
    title: str
    model: str | None
    device_id: str
    area_id: str | None
    sensors: tuple[GroupSensor, ...]
    cadr: str | None = None  # its CADR sensor


def _number(state: State | None) -> float | None:
    if state is None:
        return None
    try:
        value = float(state.state)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _fan_view(state: State) -> tuple[Any, ...]:
    """What a group sets on a member: power, mode and speed."""
    return (
        state.state,
        state.attributes.get(ATTR_PRESET_MODE),
        state.attributes.get(ATTR_PERCENTAGE),
    )


def _has_turbo(state: State) -> bool:
    """A Turbo preset (Everest Air): one speed above the fan's own."""
    return PRESET_TURBO in (state.attributes.get(ATTR_PRESET_MODES) or [])


def has_sleep(state: State) -> bool:
    """A Sleep preset: the group can use it as a member's lowest step."""
    return PRESET_SLEEP in (state.attributes.get(ATTR_PRESET_MODES) or [])


def _fan_speeds(state: State) -> int:
    """The fan's speeds as a group counts them (Turbo is the top one)."""
    speeds = speed_count(state.attributes.get(ATTR_PERCENTAGE_STEP))
    return speeds + 1 if _has_turbo(state) else speeds


def _current_speed(state: State) -> int:
    """The member's speed now (0 while off)."""
    if state.state != STATE_ON:
        return 0
    if _has_turbo(state) and state.attributes.get(ATTR_PRESET_MODE) == PRESET_TURBO:
        return _fan_speeds(state)
    speeds = speed_count(state.attributes.get(ATTR_PERCENTAGE_STEP))
    percentage = state.attributes.get(ATTR_PERCENTAGE) or 0
    return round(percentage * speeds / 100)


def _in_manual(state: State) -> bool:
    """In Manual, or a fan without modes."""
    presets = state.attributes.get(ATTR_PRESET_MODES) or []
    return not presets or state.attributes.get(ATTR_PRESET_MODE) in (None, PRESET_MANUAL)


def _at_speed(state: State, speed: int) -> bool:
    """On at that speed as a group sets it: Manual, or Turbo for the top one."""
    if state.state != STATE_ON or _current_speed(state) != speed:
        return False
    if _has_turbo(state) and speed == _fan_speeds(state):
        return state.attributes.get(ATTR_PRESET_MODE) == PRESET_TURBO
    return _in_manual(state)


def _at_step(state: State, step: Step) -> bool:
    """At that step as a group sets it: off, in Sleep, or on at the speed."""
    if step == STEP_OFF:
        return state.state == STATE_OFF
    if step == STEP_SLEEP:
        return state.state == STATE_ON and state.attributes.get(ATTR_PRESET_MODE) == PRESET_SLEEP
    return isinstance(step, int) and _at_speed(state, step)


def step_of(hass: HomeAssistant, config: GroupConfig, member: str, level: int) -> Step | None:
    """A member's step for a group level, from its fan's speeds and presets now."""
    state = hass.states.get(member)
    speeds = _fan_speeds(state) if state else speed_count(None)
    sleep = has_sleep(state) if state else False
    return member_step(level, speeds, sleep, config.speeds_of(member))


class GroupManager:
    """The purifier groups: stored config, one runner per group."""

    def __init__(self, hass: HomeAssistant, coordinator: LevoitEsphomeCoordinator) -> None:
        """Initialize."""
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self.groups: dict[str, GroupConfig] = {}
        self.dismissed_areas: list[str] = []
        self._runners: dict[str, GroupRunner] = {}
        self._listeners: list[Callable[[], None]] = []
        self._started = False

    # ---- storage ----

    async def async_load(self) -> None:
        """Read the groups (a "runtime" part from earlier versions is ignored)."""
        data = await self._store.async_load() or {}
        for raw in data.get("groups", []):
            try:
                config = parse_config(raw, check_members=False)
            except GroupError as err:
                _LOGGER.warning("Skipping a stored purifier group: %s", err)
                continue
            if config.id:
                self.groups[config.id] = config
        self.dismissed_areas = [a for a in data.get("dismissed_areas", []) if isinstance(a, str)]

    @callback
    def _data_to_save(self) -> dict[str, Any]:
        return {
            "groups": [config.as_dict() for config in self.groups.values()],
            "dismissed_areas": self.dismissed_areas,
        }

    async def _async_save(self) -> None:
        await self._store.async_save(self._data_to_save())

    # ---- running ----

    @callback
    def async_start(self, _hass: HomeAssistant | None = None) -> None:
        """Run every group (once Home Assistant has started)."""
        self._started = True
        for config in self.groups.values():
            self._start_runner(config)

    @callback
    def async_stop_with_hass(self) -> CALLBACK_TYPE:
        """Stop the groups when Home Assistant stops; returns the unsubscribe."""
        fired = False

        @callback
        def _stop(_event: Event) -> None:
            nonlocal fired
            fired = True
            self.async_stop()

        unsub = self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _stop)

        @callback
        def _unsub() -> None:
            if not fired:
                unsub()

        return _unsub

    @callback
    def async_stop(self) -> None:
        """Stop all groups (unload, shutdown); the purifiers stay as they are."""
        self._started = False
        for runner in self._runners.values():
            runner.stop()
        self._runners.clear()

    @callback
    def _start_runner(self, config: GroupConfig) -> None:
        runner = GroupRunner(self, config)
        self._runners[config.id] = runner
        runner.start()

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> CALLBACK_TYPE:
        """Call `listener` whenever a group or its state changes."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    @callback
    def async_notify(self, group_id: str | None = None) -> None:
        """A group (or the list) changed: entities and panels follow."""
        if group_id is not None:
            async_dispatcher_send(self.hass, signal_group(group_id))
        for listener in list(self._listeners):
            listener()

    # ---- purifiers and sensors ----

    @callback
    def levoit_fans(self) -> dict[str, LevoitFan]:
        """Fan entity id -> purifier, for every Levoit device with a fan."""
        data = self.coordinator.data
        dev_reg = dr.async_get(self.hass)
        fans: dict[str, LevoitFan] = {}
        for device in data.devices.values() if data else ():
            if "philips" in device.components or device.model == "LV600S":
                continue
            controls = match_controls(
                self.hass, device.esphome_device_id, device.model, device.control_names
            )
            if (fan := controls.get("fan.fan")) is None:
                continue
            entry = dev_reg.async_get(device.esphome_device_id)
            fans[fan] = LevoitFan(
                entity_id=fan,
                name=device.name,
                title=device.title,
                model=device.model,
                device_id=device.esphome_device_id,
                area_id=entry.area_id if entry else None,
                sensors=tuple(
                    GroupSensor(controls[key], kind)
                    for key, kind in SENSOR_KEYS.items()
                    if key in controls
                ),
                cadr=controls.get(CADR_KEY),
            )
        return fans

    @callback
    def cadr_sensors(self, config: GroupConfig) -> tuple[str, ...]:
        """The CADR sensors of a group's purifiers."""
        fans = self.levoit_fans()
        return tuple(c for m in config.members if m in fans and (c := fans[m].cadr))

    @callback
    def value_types(self, group_id: str) -> list[str]:
        """What a group has a combined value of: its sensor types, and CADR.

        A sensor type counts once the group has a sensor of it (with a value or
        not); CADR once one of its purifiers has a CADR sensor.
        """
        if (config := self.groups.get(group_id)) is None:
            return []
        kinds = [t for t in SENSOR_TYPES if any(s.type == t for s in config.sensors)]
        runner = self._runners.get(group_id)
        if runner is not None and runner.cadr_sensors:
            kinds.append(CADR)
        return kinds

    @callback
    def _with_sensors(self, config: GroupConfig, fans: dict[str, LevoitFan]) -> GroupConfig:
        """The config with its members' sensors picked (minus removed ones)."""
        auto = [s for member in config.members if member in fans for s in fans[member].sensors]
        return replace(config, sensors=merge_sensors(auto, config.sensors, config.removed_sensors))

    @callback
    def group_of(self, entity_id: str) -> GroupConfig | None:
        """The group a purifier is in."""
        return next((g for g in self.groups.values() if entity_id in g.members), None)

    # ---- changes from the panel and the switch ----

    async def async_save_group(self, data: dict[str, Any]) -> GroupConfig:
        """Create or change a group; raises GroupError."""
        config = parse_config(data)
        fans = self.levoit_fans()
        if unknown := [m for m in config.members if m not in fans]:
            raise GroupError(ERR_MEMBERS, f"Not a Levoit purifier: {', '.join(unknown)}")
        if config.id and config.id not in self.groups:
            raise GroupError(ERR_NOT_FOUND, "Unknown group")
        group_id = config.id or uuid4().hex
        for other in self.groups.values():
            if other.id != group_id and (taken := set(other.members) & set(config.members)):
                raise GroupError(
                    ERR_MEMBERS, f"Already in the group {other.name}: {', '.join(sorted(taken))}"
                )
        config = self._with_sensors(replace(config, id=group_id), fans)
        await self._async_apply(config)
        return config

    async def async_set_enabled(self, group_id: str, enabled: bool) -> None:
        """Turn the group's control on or off (its switch)."""
        await self.async_change(group_id, enabled=enabled)

    async def async_change(self, group_id: str, **changes: Any) -> None:
        """Change some settings of a group (its switch and fan); raises GroupError."""
        if (config := self.groups.get(group_id)) is None:
            raise GroupError(ERR_NOT_FOUND, "Unknown group")
        changed = parse_config({**config.as_dict(), **changes}, check_members=False)
        if changed != config:
            await self._async_apply(changed)

    async def _async_apply(self, config: GroupConfig) -> None:
        old = self.groups.get(config.id)
        self.groups[config.id] = config
        if (runner := self._runners.get(config.id)) is not None:
            await runner.async_update_config(config)
        elif self._started:
            self._start_runner(config)
        await self._async_save()
        if old is None:
            async_dispatcher_send(self.hass, SIGNAL_GROUPS)
        elif old.name != config.name:
            dev_reg = dr.async_get(self.hass)
            if device := dev_reg.async_get_device_by_identifier(
                group_identifier(config.id), self.coordinator.config_entry.entry_id
            ):
                dev_reg.async_update_device(device.id, name=config.name)
        self.async_notify(config.id)

    async def async_apply_now(self, group_id: str) -> None:
        """The editor's apply button: run the saved settings now.

        The sensors' level is taken at once (no hold time) and purifiers paused
        after a change by hand are set again.
        """
        if group_id not in self.groups:
            raise GroupError(ERR_NOT_FOUND, "Unknown group")
        if (runner := self._runners.get(group_id)) is not None:
            await runner.async_apply_now()

    async def async_delete_group(self, group_id: str) -> None:
        """Delete a group; its purifiers stay as they are."""
        if group_id not in self.groups:
            raise GroupError(ERR_NOT_FOUND, "Unknown group")
        if (runner := self._runners.pop(group_id, None)) is not None:
            await runner.async_release()
        del self.groups[group_id]
        await self._async_save()
        dev_reg = dr.async_get(self.hass)
        if device := dev_reg.async_get_device_by_identifier(
            group_identifier(group_id), self.coordinator.config_entry.entry_id
        ):
            dev_reg.async_remove_device(device.id)
        self.async_notify()

    async def async_dismiss_area(self, area_id: str) -> None:
        """Hide the panel's group suggestion for this area."""
        if area_id not in self.dismissed_areas:
            self.dismissed_areas.append(area_id)
            await self._async_save()
            self.async_notify()

    # ---- state for entities and the panel ----

    @callback
    def state(self, group_id: str) -> dict[str, Any]:
        """Status, level, reason, members and air quality of a group."""
        config = self.groups[group_id]
        runner = self._runners.get(group_id)
        state = runner.state() if runner is not None else self._idle_state(config)
        quality = air_quality(config, readings_of(self.hass, config))
        state["air_quality"] = quality.level
        state["air_quality_sensor"] = quality.worst.top if quality.worst else None
        state["air_quality_levels"] = quality.levels
        # the combined value per sensor type, and the purifiers' total CADR
        state["values"] = {
            t.type: {"value": t.value, "level": t.level, "how": t.how, "sensors": list(t.sensors)}
            for t in quality.types
        }
        cadr = runner.cadr_sensors if runner is not None else ()
        numbers = [v for e in cadr if (v := _number(self.hass.states.get(e))) is not None]
        state["cadr"] = {"value": sum(numbers) if numbers else None, "sensors": list(cadr)}
        return state

    @staticmethod
    def _idle_state(config: GroupConfig) -> dict[str, Any]:
        """The state of a group that does not run yet (Home Assistant starting)."""
        return {
            "status": STATUS_PAUSED if not config.enabled else STATUS_WATCHING,
            "level": 0,
            "reason": None,
            "worst": None,
            "worst_type": None,
            "rising": None,
            "sensor_levels": {},
            "members": [
                {"entity_id": m, "speed": None, "in_control": False, "paused_until": None}
                for m in config.members
            ],
        }

    @callback
    def preview(self, data: dict[str, Any]) -> dict[str, Any]:
        """The editor's "Right now": the level an unsaved config would run at."""
        fans = self.levoit_fans()
        config = self._with_sensors(parse_config(data, check_members=False), fans)
        runner = self._runners.get(config.id)
        history = runner.keeper.history if runner else History()
        result = evaluate(config, readings := readings_of(self.hass, config), history)
        level = config.manual_level if config.mode == MODE_MANUAL else result.target
        values = {r.entity_id: r.value for r in readings}
        return {
            "level": level,
            "reason": describe(self.hass, config, result),
            "worst": result.worst.top if result.worst else None,
            "worst_type": result.worst.type if result.worst else None,
            "rising": result.rising.entity_id if result.rising else None,
            "types": [
                {"type": t.type, "value": t.value, "level": t.level, "sensors": list(t.sensors)}
                for t in result.types
            ],
            "sensors": [
                {
                    "entity_id": s.entity_id,
                    "type": s.type,
                    "source": s.source,
                    "value": values.get(s.entity_id),
                    "level": result.levels.get(s.entity_id),
                }
                for s in config.sensors
            ],
            "members": [
                {
                    "entity_id": m,
                    "speeds": speeds_of(self.hass, m),
                    "speed": step_of(self.hass, config, m, level),
                }
                for m in config.members
            ],
        }


def speeds_of(hass: HomeAssistant, entity_id: str) -> int:
    state = hass.states.get(entity_id)
    return _fan_speeds(state) if state else speed_count(None)


def readings_of(hass: HomeAssistant, config: GroupConfig) -> list[Reading]:
    """The group's sensors now."""
    return [
        Reading(s.entity_id, s.type, _number(hass.states.get(s.entity_id))) for s in config.sensors
    ]


def _value_text(hass: HomeAssistant, kind: str, value: float, entity_id: str) -> str:
    if kind == AQI:
        return AQI_WORDS.get(round(value), f"{value:g}")
    state = hass.states.get(entity_id)
    unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT) if state else None
    return f"{round(value, 1):g}{f' {unit}' if unit else ''}"


def _name(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    return state.name if state else entity_id


def describe(hass: HomeAssistant, config: GroupConfig, result: Evaluation | None) -> str | None:
    """Why the group runs at its level: the worst sensor type (or one rising fast)."""
    if config.mode == MODE_MANUAL:
        return f"Manual level {config.manual_level}"
    if result is None:
        return None
    if not config.sensors:
        return "No air sensors"
    if result.usable == 0:
        return "No air sensor reports a value"
    if (rising := result.rising) is not None and rising.value is not None:
        value = _value_text(hass, rising.type, rising.value, rising.entity_id)
        return f"{TYPE_LABELS[rising.type]} {value} ({_name(hass, rising.entity_id)}), rising fast"
    if (worst := result.worst) is None:
        return None
    value = _value_text(hass, worst.type, worst.value, worst.top)
    if len(worst.sensors) == 1:
        source = _name(hass, worst.top)
    else:
        source = f"{COMBINE_WORDS.get(worst.how, 'highest')} of {len(worst.sensors)}"
    return f"{TYPE_LABELS[worst.type]} {value} ({source})"


class GroupRunner:
    """One group's control loop."""

    def __init__(self, manager: GroupManager, config: GroupConfig) -> None:
        """Initialize."""
        self.hass = manager.hass
        self.manager = manager
        self.config = config
        self.keeper = LevelKeeper()
        self.evaluation: Evaluation | None = None
        self.paused_until: dict[str, float] = {}
        self._targets: dict[str, Step] = {}  # step set per member the group runs
        self.cadr_sensors: tuple[str, ...] = ()  # its purifiers' CADR, for the total
        self._own: deque[str] = deque(maxlen=64)  # context ids of our calls
        self._lock = asyncio.Lock()
        self._unsubs: list[CALLBACK_TYPE] = []
        self._task: asyncio.Task[None] | None = None
        self._again = False
        self._stopped = False

    @callback
    def start(self) -> None:
        """Follow the sensors and members, tick for hold and pause times."""
        self._track()
        self._unsubs.append(async_track_time_interval(self.hass, self._tick, TICK))
        self._schedule()

    @callback
    def _track(self) -> None:
        if self._unsubs:
            self._unsubs.pop(0)()
        self.cadr_sensors = self.manager.cadr_sensors(self.config)
        entities = [
            *self.config.members,
            *(s.entity_id for s in self.config.sensors),
            *self.cadr_sensors,
        ]
        self._unsubs.insert(
            0, async_track_state_change_event(self.hass, entities, self._state_changed)
        )

    @callback
    def stop(self) -> None:
        """Stop following (unload, delete)."""
        self._stopped = True
        while self._unsubs:
            self._unsubs.pop()()

    @callback
    def _tick(self, _now: datetime) -> None:
        self._schedule()

    @callback
    def _schedule(self) -> None:
        """Evaluate soon; once more after a run in progress."""
        if self._stopped:
            return
        if self._task is not None and not self._task.done():
            self._again = True
            return
        self._task = self.manager.coordinator.config_entry.async_create_background_task(
            self.hass, self._async_loop(), f"{DOMAIN} group {self.config.name}"
        )

    async def _async_loop(self) -> None:
        self._again = True
        while self._again and not self._stopped:
            self._again = False
            await self.async_evaluate()

    @callback
    def _state_changed(self, event: Event[EventStateChangedData]) -> None:
        if event.data["entity_id"] in self.config.members:
            self._member_changed(event)
        self._schedule()

    @callback
    def _member_changed(self, event: Event[EventStateChangedData]) -> None:
        """A person's change to a member pauses the group for it."""
        member = event.data["entity_id"]
        old, new = event.data["old_state"], event.data["new_state"]
        if new is None or new.state in OFFLINE:
            return
        if old is None or old.state in OFFLINE:
            return  # back online: gets the current level
        if (
            not self.config.respect_manual
            or member not in self._targets
            or event.context.id in self._own
            or _fan_view(old) == _fan_view(new)
        ):
            return
        if _at_step(new, self._targets[member]):
            return  # what we set, reported late
        self.paused_until[member] = _now() + self.config.manual_pause_min * 60
        self._targets.pop(member, None)
        _LOGGER.debug("%s changed by hand: group %s pauses it", member, self.config.name)
        self.manager.async_notify(self.config.id)

    async def async_update_config(self, config: GroupConfig) -> None:
        """New settings; members that left are let go (they stay as they are)."""
        async with self._lock:
            old = self.config
            self._release([m for m in self._targets if m not in config.members])
            for member in set(self.paused_until) - set(config.members):
                del self.paused_until[member]
            self.config = config
            if old.mode == MODE_MANUAL and config.mode == MODE_AUTO:
                self.keeper.since = None  # step down without waiting
            if set(old.members) != set(config.members) or old.sensors != config.sensors:
                self._track()
        self._schedule()

    async def async_apply_now(self) -> None:
        """Set every member for the sensors' level now, also ones changed by hand."""
        async with self._lock:
            self.paused_until.clear()
        await self.async_evaluate(now_level=True)

    async def async_release(self) -> None:
        """Stop and let go of every member (delete); they stay as they are."""
        self.stop()
        async with self._lock:
            self._release(list(self._targets))

    @callback
    def _release(self, members: Iterable[str]) -> None:
        """Let go of members: nothing is sent, they keep running as they are."""
        for member in members:
            self._targets.pop(member, None)

    async def async_evaluate(self, *, now_level: bool = False) -> None:
        """Move the level and apply it, or let go at level 0.

        `now_level` takes the sensors' level at once, without the hold time.
        """
        async with self._lock:
            if self._stopped:
                return
            now = _now()
            config = self.config
            for member, until in list(self.paused_until.items()):
                if until <= now:
                    del self.paused_until[member]
            if not config.enabled:
                self.keeper.level = 0
                self.evaluation = None
            elif config.mode == MODE_MANUAL:
                self.keeper.manual(config)
                self.evaluation = None
            else:
                self.evaluation = self.keeper.step(
                    config, readings_of(self.hass, config), now, now_level=now_level
                )
            level = self.keeper.level
            if level == 0:
                self._release(list(self._targets))
            else:
                for member in config.members:
                    await self._async_set(member, level)
        self.manager.async_notify(config.id)

    async def _async_set(self, member: str, level: int) -> None:
        """Put a member at its step for the level: Off, Sleep, or Manual at a speed."""
        if member in self.paused_until:
            return
        state = self.hass.states.get(member)
        if state is None or state.state in OFFLINE:
            return
        is_on = state.state == STATE_ON
        if not is_on and not self.config.turn_on and member not in self._targets:
            return
        speeds = _fan_speeds(state)
        step = member_step(level, speeds, has_sleep(state), self.config.speeds_of(member))
        if step is None:
            return
        self._targets[member] = step
        if _at_step(state, step):
            return
        if step == STEP_OFF:
            await self._async_call(SERVICE_TURN_OFF, {ATTR_ENTITY_ID: member})
            return
        if step == STEP_SLEEP:
            await self._async_call(
                SERVICE_TURN_ON, {ATTR_ENTITY_ID: member, ATTR_PRESET_MODE: PRESET_SLEEP}
            )
            return
        speed = int(step)
        if _has_turbo(state) and speed == speeds:
            await self._async_call(
                SERVICE_TURN_ON, {ATTR_ENTITY_ID: member, ATTR_PRESET_MODE: PRESET_TURBO}
            )
            return
        # a speed takes the levoit fan out of Auto / Sleep / Turbo into Manual
        fan_speeds = speed_count(state.attributes.get(ATTR_PERCENTAGE_STEP))
        await self._async_call(
            SERVICE_TURN_ON,
            {
                ATTR_ENTITY_ID: member,
                ATTR_PERCENTAGE: ranged_value_to_percentage((1, fan_speeds), speed),
            },
        )

    async def _async_call(self, service: str, data: dict[str, Any]) -> None:
        """A fan service with our own context (so its changes are not a person's)."""
        context = Context()
        self._own.append(context.id)
        try:
            await self.hass.services.async_call(
                FAN_DOMAIN, service, data, blocking=True, context=context
            )
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Purifier group %s: %s on %s failed: %s",
                self.config.name,
                service,
                data[ATTR_ENTITY_ID],
                err,
            )

    @callback
    def state(self) -> dict[str, Any]:
        """Status, level, reason and members, for entities and the panel."""
        config = self.config
        level = self.keeper.level
        result = self.evaluation
        if not config.enabled:
            status = STATUS_PAUSED
        elif config.mode == MODE_MANUAL:
            status = STATUS_MANUAL
        elif level > 0:
            status = STATUS_IN_CONTROL
        elif not config.sensors or (result is not None and result.usable == 0):
            status = STATUS_NO_SENSORS
        else:
            status = STATUS_WATCHING
        return {
            "status": status,
            "level": level,
            "reason": describe(self.hass, config, result) if config.enabled else None,
            "worst": result.worst.top if result and result.worst else None,
            "worst_type": result.worst.type if result and result.worst else None,
            "rising": result.rising.entity_id if result and result.rising else None,
            "sensor_levels": dict(result.levels) if result else {},
            "members": [
                {
                    "entity_id": member,
                    "speed": self._targets.get(member),
                    "in_control": member in self._targets,
                    "paused_until": _iso(self.paused_until.get(member)),
                }
                for member in config.members
            ],
        }
