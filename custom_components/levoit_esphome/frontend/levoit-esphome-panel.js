// Levoit ESPHome sidebar panel: every device with versions, channel, filter,
// compile and upload. Plain web component, no build step; data comes from the
// integration's WebSocket commands (levoit_esphome/*), admins only.

const INTEGRATION_PAGE = "/config/integrations/integration/levoit_esphome";

// The version this code was loaded as (panel.py adds ?v=<version>). A browser
// defines the page element once per session, so after an update the old code
// keeps running until the page is reloaded; the page then says so.
const LOADED_VERSION = (/[?&]v=([^&#]+)/.exec(import.meta.url) || [])[1] || null;

const KIND_LABELS = {
  original: "Original ESP",
  xiao_c3: "XIAO ESP32-C3",
  c3: "ESP32-C3",
  s3: "XIAO ESP32-S3",
  custom: "Custom config",
};
const BUILD_STEP_LABELS = {
  template: "Updating config…",
  waiting: "Waiting for another build…",
  compile: "Compiling…",
  upload: "Uploading…",
};
// the steps of a build as the integration reads them from its output (build_log.py)
const STEP_LABELS = {
  setup: "Setup",
  compile: "Compile",
  link: "Link and image",
  result: "Result",
  upload: "Upload",
};
const CHANNEL_LABELS = {
  stable: "Stable",
  main: "Main",
  pinned: "Pinned",
  local: "Local",
};
const LV600S_PRESETS = ["Manual", "Humidity", "Sleep"];
// These percentages select MCU levels 1, 5 and 9 with either ESPHome fan
// percentage mapping used by Home Assistant.
const LV600S_MIST_PERCENTAGES = [1, 50, 100];

const ICONS = {
  menu: "M3,6H21V8H3V6M3,11H21V13H3V11M3,16H21V18H3V16Z",
  refresh:
    "M17.65,6.35C16.2,4.9 14.21,4 12,4A8,8 0 0,0 4,12A8,8 0 0,0 12,20C15.73,20 18.84,17.45 19.73,14H17.65C16.83,16.33 14.61,18 12,18A6,6 0 0,1 6,12A6,6 0 0,1 12,6C13.66,6 15.14,6.69 16.22,7.78L13,11H20V4L17.65,6.35Z",
  builder:
    "M14.6,16.6L19.2,12L14.6,7.4L16,6L22,12L16,18L14.6,16.6M9.4,16.6L4.8,12L9.4,7.4L8,6L2,12L8,18L9.4,16.6Z",
  plus: "M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z",
  purifier:
    "M16,2H8A2,2 0 0,0 6,4V20A2,2 0 0,0 8,22H16A2,2 0 0,0 18,20V4A2,2 0 0,0 16,2M12,4A2,2 0 0,1 14,6A2,2 0 0,1 12,8A2,2 0 0,1 10,6A2,2 0 0,1 12,4M16,20H8V18H16V20M16,16H8V14H16V16M16,12H8V10H16V12Z",
  back: "M20,11V13H8L13.5,18.5L12.08,19.92L4.16,12L12.08,4.08L13.5,5.5L8,11H20Z",
  power:
    "M16.56,5.44L15.11,6.89C16.84,7.94 18,9.83 18,12A6,6 0 0,1 12,18A6,6 0 0,1 6,12C6,9.83 7.16,7.94 8.88,6.88L7.44,5.44C5.36,6.88 4,9.28 4,12A8,8 0 0,0 12,20A8,8 0 0,0 20,12C20,9.28 18.64,6.88 16.56,5.44M13,3H11V13H13",
  open: "M14,3V5H17.59L7.76,14.83L9.17,16.24L19,6.41V10H21V3M19,19H5V5H12V3H5C3.89,3 3,3.9 3,5V19A2,2 0 0,0 5,21H19A2,2 0 0,0 21,19V12H19V19Z",
  chevron: "M7.41,8.58L12,13.17L16.59,8.58L18,10L12,16L6,10L7.41,8.58Z",
  download: "M5,20H19V18H5M19,9H15V3H9V9H5L12,16L19,9Z",
  home: "M10,20V14H14V20H19V12H22L12,3L2,12H5V20H10Z",
  group:
    "M20,16V4H8V16H20M22,16A2,2 0 0,1 20,18H8C6.89,18 6,17.1 6,16V4C6,2.89 6.89,2 8,2H20A2,2 0 0,1 22,4V16M16,20V22H4A2,2 0 0,1 2,20V7H4V20H16Z",
  close:
    "M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z",
  check: "M21,7L9,19L3.5,13.5L4.91,12.09L9,16.17L19.59,5.59L21,7Z",
  play: "M8,5.14V19.14L19,12.14L8,5.14Z",
  pencil:
    "M20.71,7.04C21.1,6.65 21.1,6 20.71,5.63L18.37,3.29C18,2.9 17.35,2.9 16.96,3.29L15.12,5.12L18.87,8.87M3,17.25V21H6.75L17.81,9.93L14.06,6.18L3,17.25Z",
  delete: "M19,4H15.5L14.5,3H9.5L8.5,4H5V6H19M6,19A2,2 0 0,0 8,21H16A2,2 0 0,0 18,19V7H6V19Z",
  fan: "M12,11A1,1 0 0,0 11,12A1,1 0 0,0 12,13A1,1 0 0,0 13,12A1,1 0 0,0 12,11M12.5,2C17,2 17.11,5.57 14.75,6.75C13.76,7.24 13.32,8.29 13.13,9.22C13.61,9.42 14.03,9.73 14.35,10.13C18.05,8.13 22.03,8.92 22.03,12.5C22.03,17 18.46,17.1 17.28,14.73C16.78,13.74 15.72,13.3 14.79,13.11C14.59,13.59 14.28,14 13.88,14.34C15.87,18.03 15.08,22 11.5,22C7,22 6.91,18.42 9.27,17.24C10.25,16.75 10.69,15.71 10.89,14.79C10.4,14.59 9.97,14.27 9.65,13.87C5.96,15.85 2,15.07 2,11.5C2,7 5.56,6.89 6.74,9.26C7.24,10.25 8.29,10.68 9.22,10.87C9.41,10.39 9.73,9.97 10.14,9.65C8.15,5.96 8.94,2 12.5,2Z",
  filter: "M14,12V19.88C14.04,20.18 13.94,20.5 13.71,20.71C13.32,21.1 12.69,21.1 12.3,20.71L10.29,18.7C10.06,18.47 9.96,18.16 10,17.87V12H9.97L4.21,4.62C3.87,4.19 3.95,3.56 4.38,3.22C4.57,3.08 4.78,3 5,3H19C19.22,3 19.43,3.08 19.62,3.22C20.05,3.56 20.13,4.19 19.79,4.62L14.03,12H14Z",
  water: "M12 2C9 6 5 10 5 15a7 7 0 0 0 14 0c0-5-4-9-7-13Z",
  waterEmpty: "M12 2C9 6 5 10 5 15a7 7 0 0 0 14 0c0-5-4-9-7-13Zm0 3.5c2.7 3.5 5 6.3 5 9.5a5 5 0 0 1-10 0c0-3.2 2.3-6 5-9.5ZM9 14h6v2H9Z",
  tankOut: "M12 1l4 4-1.4 1.4L13 4.8V10h-2V4.8L9.4 6.4 8 5ZM5 11h2v9h10v-9h2v9a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2Z",
};

// Small outline drawings per purifier family for the overview (48 x 48, drawn
// in the theme's colours; no product photos). Stroke-only shapes plus a wash.
const DEVICE_SHAPES = {
  // Core 200S-600S: a round column with a top grille
  core: `<rect x="14" y="7" width="20" height="35" rx="8"/><path d="M18 12.5h12M18 16h12M18 19.5h12"/><circle cx="24" cy="31" r="2.2"/>`,
  // Eleva 300X: a squat round body with rings on top
  eleva: `<path d="M11 19v17c0 3.3 5.8 6 13 6s13-2.7 13-6V19"/><ellipse cx="24" cy="19" rx="13" ry="5"/><ellipse cx="24" cy="19" rx="7" ry="2.6"/>`,
  // Vital, Everest Air: a rectangular tower
  tower: `<rect x="13" y="6" width="22" height="37" rx="4"/><path d="M17 11h14M17 14.5h14"/><rect x="18" y="22" width="12" height="14" rx="2"/>`,
  // Sprout: a bell with a base
  sprout: `<path d="M15 39c0-13 3.5-26 9-26s9 13 9 26z"/><path d="M12 42h24"/><circle cx="24" cy="10" r="2"/>`,
  // Superior 6000S: a humidifier with a drop on top
  humidifier: `<rect x="12" y="15" width="24" height="28" rx="7"/><path d="M24 4.5c3.2 4 4.4 6.4 4.4 8.2a4.4 4.4 0 0 1-8.8 0c0-1.8 1.2-4.2 4.4-8.2z"/><path d="M17 33h14"/>`,
  // Philips: a rounded block with a fan
  philips: `<rect x="11" y="9" width="26" height="34" rx="10"/><circle cx="24" cy="19" r="5"/><path d="M18 34h12"/>`,
};
const deviceShape = (model) => {
  const m = model || "";
  if (m.startsWith("CORE")) return "core";
  if (m === "ELEVA300X") return "eleva";
  if (m.startsWith("VITAL") || m === "EVERESTAIR") return "tower";
  if (m === "SPROUT") return "sprout";
  if (m === "SUPERIOR6000S" || m === "LV600S") return "humidifier";
  if (m.startsWith("AC0")) return "philips";
  return "core";
};
const deviceImage = (model) =>
  `<svg class="dev-img" viewBox="0 0 48 48" aria-hidden="true">${DEVICE_SHAPES[deviceShape(model)]}</svg>`;

// "2h 30 min", "45 min", "1h 5 min 10 s" -> seconds; anything else -> 0
const parseDuration = (text) => {
  if (!text) return 0;
  const part = (re) => {
    const m = re.exec(text);
    return m ? Number(m[1]) : 0;
  };
  return part(/(\d+)\s*h/) * 3600 + part(/(\d+)\s*min/) * 60 + part(/(\d+)\s*s\b/);
};

const formatMinutes = (minutes) => {
  const m = Math.round(minutes);
  if (m < 60) return `${m} min`;
  return m % 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m / 60} h`;
};

// Older LV600S firmware reports seconds. Newer firmware uses the purifier's
// display format while exposing the original total separately.
const lv600sRemainingSeconds = (value) => {
  if (value === "Off") return 0;
  if (typeof value !== "string" || !/^\d/.test(value)) return NaN;
  return Number.isFinite(Number(value)) ? Number(value) : parseDuration(value);
};

const TIMER_PRESETS = [30, 60, 120, 240, 480, 720];

const formatNumber = (value) =>
  Number.isInteger(value) ? String(value) : String(Math.round(value * 10) / 10);

// Device and group page history: Home Assistant's statistics (the sensors
// have a state_class), 5-minute means up to a day, hourly means beyond.
// tick: the time axis, every so many hours (a time) or days at midnight
// (7 days: on Mondays, as a date)
const HOUR_MS = 3600e3;
const DAY_MS = 24 * HOUR_MS;
const HISTORY_RANGES = {
  half: { label: "12 h", ms: 12 * HOUR_MS, period: "5minute", step: 5 * 60e3, tick: 2 * HOUR_MS },
  day: { label: "24 h", ms: DAY_MS, period: "5minute", step: 5 * 60e3, tick: 6 * HOUR_MS },
  week: { label: "7 days", ms: 7 * DAY_MS, period: "hour", step: HOUR_MS, tick: DAY_MS },
  month: { label: "30 days", ms: 30 * DAY_MS, period: "hour", step: HOUR_MS, tick: 7 * DAY_MS },
};
const HISTORY_REFRESH_MS = 5 * 60e3;
// one small chart each, on a shared time axis: different units, never one axis.
// The 1-4 air quality level is drawn as a coloured band under them.
// One chart, as in the design: PM2.5 as an area on the left axis, CADR as a
// dashed line on the right axis, and the air quality level as a band below.
// The Eleva's 0-500 index is shown with the band (its level when the model has
// no 1-4 level sensor) and in the tooltip.
const HISTORY_SERIES = [
  { key: "sensor.pm25", title: "PM2.5", color: "pm", axis: "left", area: true },
  { key: "sensor.current_cadr", title: "CADR", color: "cadr", axis: "right" },
];
// a group's page: its combined PM values on one left axis, its total CADR on
// the right, and its level as the band (keys of the group's entities)
const GROUP_HISTORY_SERIES = [
  { key: "pm1", title: "PM1", color: "pm1", axis: "left" },
  { key: "pm25", title: "PM2.5", color: "pm", axis: "left", area: true },
  { key: "pm10", title: "PM10", color: "pm10", axis: "left" },
  { key: "cadr", title: "CADR", color: "cadr", axis: "right" },
];
const LV600S_HISTORY = [
  { key: "sensor.humidity", title: "Humidity", color: "pm", axis: "left", bounds: [0, 100], area: true },
  { key: "sensor.temperature", title: "Temperature", precise: true, color: "cadr", axis: "right" },
  { key: "sensor.mist_level", title: "Mist level", color: "mist", axis: "left", bounds: [0, 9], level: true },
  { key: "number.warm_level", title: "Warm mist", color: "warm", axis: "left", bounds: [0, 9], level: true, dashed: true },
];

// Recorder history uses Unix seconds and includes the state at the start of the range.
// Keep unavailable states to break the line, and extend the last known value to the end.
const stateHistory = (rows, start, end) => {
  const points = [];
  for (const row of rows) {
    const time = (row.lc ?? row.lu) * 1000;
    if (!Number.isFinite(time) || time > end) continue;
    const value = Number(row.s);
    const point = [Math.max(start, time), row.s && Number.isFinite(value) ? value : null];
    if (points.at(-1)?.[0] === point[0]) points[points.length - 1] = point;
    else points.push(point);
  }
  if (points.length && points.at(-1)[0] < end) points.push([end, points.at(-1)[1]]);
  return points;
};

// the purifiers' air quality level, 1 (very good) to 4 (poor)
const AQI_WORDS = { 1: "Very good", 2: "Good", 3: "Moderate", 4: "Poor" };
const aqiLevel = (value) => {
  const v = Math.round(Number(value));
  return v >= 1 && v <= 4 ? v : null;
};
// the Eleva's 0-500 index, in the same four steps (for the dot without a level)
const aqiIndexLevel = (value) => {
  const v = Number(value);
  if (!Number.isFinite(v)) return null;
  return v <= 50 ? 1 : v <= 100 ? 2 : v <= 150 ? 3 : 4;
};
// plot geometry in viewBox units; the plot stretches to the card's width
// (preserveAspectRatio none), so all text is HTML beside and under it
// Purifier groups: a new group's settings (as the backend's defaults)
const GROUP_DEFAULTS = {
  name: "",
  area_id: null,
  enabled: true,
  members: [],
  sensors: [],
  removed_sensors: [],
  combine: { pm1: "max", pm25: "max", pm10: "max", aqi: "max" },
  thresholds: { pm1: [12, 35, 55], pm25: [12, 35, 55], pm10: [55, 155, 255] },
  rise: { enabled: true, pm25: 20, window_min: 5 },
  hold_min: 2,
  turn_on: true,
  respect_manual: true,
  manual_pause_min: 30,
  mode: "auto",
  manual_level: 1,
  member_speeds: {},
};
const GROUP_LEVELS = [1, 2, 3, 4];
const SENSOR_TYPES = ["pm1", "pm25", "pm10", "aqi"];
// the PM types have thresholds (where levels 2-4 start); the AQI level is the level
const THRESHOLD_TYPES = ["pm1", "pm25", "pm10"];
const SENSOR_TYPE_INFO = {
  pm1: { label: "PM1", unit: "µg/m³" },
  pm25: { label: "PM2.5", unit: "µg/m³" },
  pm10: { label: "PM10", unit: "µg/m³" },
  aqi: { label: "AQI index", unit: "Levoit 1–4" },
};
const COMBINE_OPTIONS = [
  ["max", "Highest"],
  ["avg", "Average"],
  ["median", "Median"],
  ["min", "Lowest"],
];
const COMBINE_WORDS = { max: "highest", avg: "average", median: "median", min: "lowest" };
// the threshold sliders: 0-500 µg/m³ on a square-root scale, so the low values
// that matter most get most of the width
const TH_MAX = 500;
const thFrac = (v) => Math.sqrt(Math.min(TH_MAX, Math.max(0, v)) / TH_MAX);
const thValue = (u) => Math.round(TH_MAX * u * u);
// a member's steps, slowest first (as groups_logic.member_ladder)
const memberLadder = (p) => [
  "off",
  ...(p?.sleep ? ["sleep"] : []),
  ...Array.from({ length: Math.max(1, p?.speeds || 4) }, (_, i) => i + 1),
];
// a member's lowest and highest step as the group uses them: Sleep without the
// preset is speed 1, a speed above its fastest is its fastest
const memberRange = (p, rng) => {
  const ladder = memberLadder(p);
  const top = ladder[ladder.length - 1];
  const high = Math.min(rng?.highest || top, top);
  let low = rng?.lowest ?? 1;
  if (low === "sleep" && !p?.sleep) low = 1;
  if (typeof low === "number") low = Math.min(low, high);
  return { ladder, low, high };
};
// a step's speed, doubled: Off 0, Sleep 1 (speed 0.5), speed n 2n
const stepValue = (s) => (s === "off" ? 0 : s === "sleep" ? 1 : 2 * s);
// a member's step for a group level, lowest at 1 and highest at 4 (as
// groups_logic.member_step): up to 4 steps one per level, the rest at the
// highest; more spread evenly by speed and rounded up, bigger jumps on the left
const memberStep = (level, p, rng) => {
  if (level <= 0) return null;
  const { ladder, low, high } = memberRange(p, rng);
  const steps = ladder.slice(ladder.indexOf(low), ladder.indexOf(high) + 1);
  const i = Math.min(level, 4) - 1;
  if (steps.length <= 4) return steps[Math.min(i, steps.length - 1)];
  const v0 = stepValue(steps[0]);
  const target = v0 * 3 + i * (stepValue(steps[steps.length - 1]) - v0);
  return steps.find((s) => stepValue(s) * 3 >= target);
};
// a data-value attribute: true / false, a number, or text
const parseValue = (text) =>
  text === "true" ? true : text === "false" ? false : /^-?\d+(\.\d+)?$/.test(text) ? Number(text) : text;

const CHART = { width: 1000, height: 150, top: 6, bottom: 2 };

// a round axis maximum at or above value: 1, 2, 2.5, 5 x 10^n
const niceMax = (value) => {
  if (!(value > 0)) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  for (const m of [1, 2, 2.5, 5, 10]) if (m * magnitude >= value) return m * magnitude;
  return 10 * magnitude;
};

// 22.5 -> "22:30" and back (quiet period hours after midnight)
const hoursToTime = (hours) => {
  const total = Math.round(hours * 60) % (24 * 60);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
};
const timeToHours = (time) => {
  const [h, m] = time.split(":").map(Number);
  return h + (m || 0) / 60;
};

const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c],
  );

const icon = (name) =>
  `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="${ICONS[name]}"></path></svg>`;

class LevoitEsphomePanel extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._data = null;
    this._error = null;
    this._busy = new Set(); // device names with a request in flight
    this._checking = false;
    this._unsub = null;
    this._subscribing = false;
    this._deferred = false;
    this._log = null; // the build log dialog: {name, title, full, lines}; steps and tail from _data
    // device page (route /levoit-esphome/<name>): which entity is which setting
    this._route = null;
    this._view = "overview"; // overview, config or device
    this._pageName = null;
    this._page = null; // levoit_esphome/device_controls result
    this._pageError = null;
    this._pageLoading = false;
    this._seen = {}; // entity_id -> state object last rendered
    this._infoOpen = true; // the device page's Info section: open until closed
    // device page history: {name, range, start, end, at, data: {entity_id: [[t, v]]}}
    this._history = null;
    this._historyRange = "day";
    this._historyLoading = false;
    this._historyError = null;
    this._hoverT = null; // time under the crosshair
    this._histHidden = new Set(); // history series switched off in the legend
    this._updatingAll = false;
    this._lv600sWarmPicker = null;
    this._lv600sWarmFocus = null;
    // purifier groups (route /levoit-esphome/groups/...)
    this._groups = null; // levoit_esphome/groups/subscribe: {groups, purifiers, dismissed_areas}
    this._groupsError = null;
    this._groupsUnsub = null;
    this._groupsSubscribing = false;
    this._groupKey = null; // the editor's group id, "new" or "new/<area_id>"
    this._detailId = null; // the group page's group id
    this._edit = null; // the editor: {draft, addOpen, saving, preview, previewError, previewSeq}
    this._previewTimer = null;
    this.shadowRoot.addEventListener("click", (ev) => this._onClick(ev));
    // the group name: kept as it is typed, so Save sees it without a re-render
    this.shadowRoot.addEventListener("input", (ev) => {
      const field = ev.target?.closest?.('input[data-ed-field="name"]');
      if (field && this._edit?.draft) this._edit.draft.name = field.value;
      // a threshold slider: its number follows while dragging, saved on release
      const th = ev.target?.closest?.("input[data-th]");
      if (th && this._edit?.draft) {
        const [type, i] = th.dataset.th.split(".");
        const v = this._thAt(type, Number(i), Number(th.value) / 1000)[Number(i)];
        const label = th.parentElement?.querySelector(`[data-th-label="${i}"]`);
        if (label) {
          label.textContent = formatNumber(v);
          label.style.left = `calc(10px + (100% - 20px) * ${thFrac(v).toFixed(4)})`;
        }
      }
    });
    // an overview card is a link: Enter or Space opens the device
    this.shadowRoot.addEventListener("keydown", (ev) => {
      const card = ev.target?.closest?.(".dcard");
      if (ev.key === "Escape" && this._lv600sWarmPicker && ev.target.closest(".lv-warm-picker")) {
        ev.preventDefault();
        this._toggleLv600sWarmPicker(this._lv600sWarmPicker);
        return;
      }
      if (card && ev.target === card && (ev.key === "Enter" || ev.key === " ")) {
        ev.preventDefault();
        this._navigate(card.dataset.path);
      }
    });
    this.shadowRoot.addEventListener("change", (ev) => this._onChange(ev));
    this.shadowRoot.addEventListener("focusout", () => {
      if (this._deferred && !this._pressing) {
        this._deferred = false;
        this._render();
      }
    });
    // A click needs press and release on the same element. The page re-renders
    // whenever a shown state changes (a running timer: every second), and a
    // re-render replaces every button: between press and release that loses
    // the click. So hold re-renders from press until just after the click.
    this._pressing = false;
    this.shadowRoot.addEventListener("pointerdown", () => (this._pressing = true), true);
    const release = () =>
      // after the click event, which follows pointerup in the same task
      setTimeout(() => {
        this._pressing = false;
        if (this._deferred) {
          this._deferred = false;
          this._render();
        }
      }, 0);
    this.shadowRoot.addEventListener("pointerup", release, true);
    this.shadowRoot.addEventListener("pointercancel", release, true);
  }

  set hass(hass) {
    const first = !this._hass;
    this._hass = hass;
    if (!this._unsub && !this._subscribing) this._subscribe();
    if (!this._groupsUnsub && !this._groupsSubscribing) this._subscribeGroups();
    if (this._pageName && !this._page && !this._pageLoading && !this._pageError) this._loadPage();
    if (
      (this._page || this._view === "groupdetail") &&
      this._history &&
      !this._historyLoading &&
      Date.now() - this._history.at > HISTORY_REFRESH_MS
    )
      this._loadHistory();
    // the device page shows live states: render when one of its entities changed
    if (first || this._pageStatesChanged()) this._render();
  }

  // Routes under the panel: "" the device overview, "/config" updates and
  // configs, "/device/<name>" a device's page ("/<name>" from 0.6.x too),
  // "/groups" the groups, "/groups/<id>" a group's page, "/groups/<id>/edit"
  // and "/groups/new[/<area_id>]" the editor.
  set route(route) {
    this._route = route;
    if (route?.path && route.path !== "/") this._lv600sWarmPicker = this._lv600sWarmFocus = null;
    const parts = (route?.path || "").split("/").filter(Boolean).map(decodeURIComponent);
    let name = null;
    let groupKey = null;
    let detailId = null;
    if (parts[0] === "config") this._view = "config";
    else if (parts[0] === "groups") {
      const rest = parts.slice(1);
      if (!rest.length) this._view = "groups";
      else if (rest[0] === "new") groupKey = rest.join("/");
      else if (rest[1] === "edit") groupKey = rest[0];
      else detailId = rest[0];
      if (groupKey) this._view = "group";
      if (detailId) this._view = "groupdetail";
    } else if (parts[0] === "device" && parts[1]) name = parts[1];
    else if (parts[0]) name = parts[0];
    if (name) this._view = "device";
    else if (parts[0] !== "config" && parts[0] !== "groups") this._view = "overview";
    if (groupKey !== this._groupKey) {
      this._groupKey = groupKey;
      this._edit = null;
    }
    if (detailId !== this._detailId) {
      this._detailId = detailId;
      this._history = null;
      this._historyRequest = null;
      this._historyLoading = false;
      this._historyError = null;
      this._hoverT = null;
    }
    if (name !== this._pageName) {
      this._pageName = name;
      this._page = null;
      this._pageError = null;
      this._seen = {};
      this._history = null;
      this._historyRequest = null;
      this._historyLoading = false;
      this._historyError = null;
      this._hoverT = null;
      if (name && this._hass) this._loadPage();
    }
    this._render();
  }

  get _base() {
    return this._route?.prefix || "/levoit-esphome";
  }

  async _loadPage() {
    const name = this._pageName;
    this._pageLoading = true;
    try {
      const page = await this._hass.callWS({ type: "levoit_esphome/device_controls", name });
      if (name === this._pageName) {
        this._page = page;
        if (!this._history && !this._historyLoading) this._loadHistory();
      }
    } catch (err) {
      if (name === this._pageName) this._pageError = err?.message || String(err);
    } finally {
      this._pageLoading = false;
      this._render();
    }
  }

  // the entities shown live: the open device's, or every device's on the overview
  _watched() {
    if (this._view === "device") return Object.values(this._page?.controls || {});
    if (this._view === "overview")
      return (this._data?.devices || []).flatMap((d) => Object.values(d.controls || {}));
    if (this._view === "groups") return (this._groups?.groups || []).flatMap((g) => g.members);
    if (this._view === "groupdetail") {
      const g = this._detailGroup();
      if (!g) return [];
      const cadr = (g.members || []).map((m) => this._purifier(m)?.cadr).filter(Boolean);
      return [...g.members, ...g.sensors.map((s) => s.entity_id), ...Object.values(g.entities || {}), ...cadr];
    }
    if (this._view === "group" && this._edit?.draft && this._groups)
      return [...this._edit.draft.members, ...this._draftSensors().map((s) => s.entity_id)];
    return [];
  }

  _pageStatesChanged() {
    if (!this._hass) return false;
    return this._watched().some((entityId) => this._hass.states[entityId] !== this._seen[entityId]);
  }

  _devicePath(name) {
    return `${this._base}/device/${encodeURIComponent(name)}`;
  }

  set narrow(narrow) {
    this._narrow = narrow;
    this._render();
  }

  set panel(panel) {
    this._panel = panel;
  }

  connectedCallback() {
    if (this._hass && !this._unsub && !this._subscribing) this._subscribe();
    if (this._hass && !this._groupsUnsub && !this._groupsSubscribing) this._subscribeGroups();
    this._render();
  }

  disconnectedCallback() {
    if (this._unsub) {
      this._unsub.then((unsub) => unsub()).catch(() => {});
      this._unsub = null;
    }
    if (this._groupsUnsub) {
      this._groupsUnsub.then((unsub) => unsub()).catch(() => {});
      this._groupsUnsub = null;
    }
  }

  async _subscribe() {
    this._subscribing = true;
    try {
      // re-subscribes by itself after a reconnect
      this._unsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._data = data;
          this._error = null;
          // devices changed (one came online, a config was read): find the
          // open device page's entities again
          if (this._pageName && this._page && !this._pageLoading) this._loadPage();
          // the log dialog in full view follows a running build
          if (this._log?.full && this._device(this._log.name)?.building) this._fetchLog();
          this._render();
        },
        { type: "levoit_esphome/subscribe" },
      );
      await this._unsub;
    } catch (err) {
      this._unsub = null;
      this._error = err?.message || String(err);
      this._render();
    } finally {
      this._subscribing = false;
    }
  }

  // --- actions ----------------------------------------------------------------

  _navigate(path) {
    history.pushState(null, "", path);
    window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace: false } }));
  }

  _toast(message) {
    this.dispatchEvent(
      new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }),
    );
  }

  _device(name) {
    return (
      this._data?.devices.find((d) => d.name === name) ||
      (this._data?.pending || []).find((p) => p.name === name)
    );
  }

  async _onClick(ev) {
    // a click outside the editor's Add sensor menu closes it
    if (this._edit?.addOpen && !ev.target.closest(".add-wrap")) {
      this._edit.addOpen = false;
      this._render();
    }
    const target = ev.target.closest("[data-action]");
    if (!target) return;
    const { action, name, path } = target.dataset;
    if (target.tagName === "A") ev.preventDefault();
    switch (action) {
      case "none":
        // a control inside an overview card (the mode dropdown): not the card's link
        break;
      case "lv-warm-picker":
        this._toggleLv600sWarmPicker(target.dataset.entity);
        break;
      case "toggle-series":
        if (this._histHidden.has(target.dataset.key)) this._histHidden.delete(target.dataset.key);
        else this._histHidden.add(target.dataset.key);
        this._render();
        break;
      case "update-all":
        await this._updateAll();
        break;
      case "menu":
        this.dispatchEvent(new CustomEvent("hass-toggle-menu", { bubbles: true, composed: true }));
        break;
      case "navigate":
        this._navigate(path);
        break;
      case "reload":
        location.reload();
        break;
      case "log":
        this._showLog(name);
        break;
      case "log-full":
        await this._toggleFullLog();
        break;
      case "close-log":
        // a click inside the dialog bubbles to the backdrop: close only on the
        // backdrop itself or on the Close button
        if (target.classList.contains("backdrop") && ev.target !== target) break;
        this._log = null;
        this._render();
        break;
      case "retry":
        this._error = null;
        this._render();
        this._subscribe();
        break;
      case "check":
        await this._check();
        break;
      case "compile":
        await this._build(name, false);
        break;
      case "upload":
        await this._build(name, true);
        break;
      case "svc":
        // a device page control: a Home Assistant service on one entity
        if (target.dataset.confirm && !confirm(target.dataset.confirm)) break;
        if (target.closest(".lv-warm-picker") && this._lv600sWarmPicker === target.dataset.entity) {
          this._toggleLv600sWarmPicker(target.dataset.entity);
        }
        await this._callService(
          target.dataset.domain,
          target.dataset.service,
          target.dataset.entity,
          JSON.parse(target.dataset.args || "{}"),
        );
        break;
      case "history-range":
        if (target.dataset.range !== this._historyRange) {
          this._historyRange = target.dataset.range;
          this._hoverT = null;
          this._render(); // the old chart stays, dimmed, until the new data is in
          this._loadHistory();
        }
        break;
      case "toggle-info":
        ev.preventDefault(); // the open state is ours, not the <details> element's
        this._infoOpen = !this._infoOpen;
        this._render();
        break;
      case "groups-retry":
        this._groupsError = null;
        this._render();
        this._subscribeGroups();
        break;
      case "group-set":
        await this._setGroup(target.dataset.id, target.dataset.field, parseValue(target.dataset.value));
        break;
      case "group-level":
        await this._setGroup(target.dataset.id, {
          enabled: true,
          mode: "manual",
          manual_level: Number(target.dataset.value),
        });
        break;
      case "sug-dismiss":
        await this._dismissArea(target.dataset.area);
        break;
      case "ed-set":
        if (this._edit?.draft) this._setDraft(target.dataset.field, parseValue(target.dataset.value));
        break;
      case "ed-add-toggle":
        this._edit.addOpen = !this._edit.addOpen;
        this._render();
        break;
      case "ed-add-sensor": {
        const d = this._edit.draft;
        const entity = target.dataset.entity;
        d.sensors = [...d.sensors, { entity_id: entity, type: target.dataset.type, source: "manual" }];
        this._edit.addOpen = false;
        this._setDraft("removed_sensors", d.removed_sensors.filter((e) => e !== entity));
        break;
      }
      case "ed-restore-sensor":
        this._edit.addOpen = false;
        this._setDraft(
          "removed_sensors",
          this._edit.draft.removed_sensors.filter((e) => e !== target.dataset.entity),
        );
        break;
      case "ed-remove-sensor": {
        const d = this._edit.draft;
        const entity = target.dataset.entity;
        const own = d.sensors.some((x) => x.entity_id === entity && x.source === "manual");
        if (own) this._setDraft("sensors", d.sensors.filter((x) => x.entity_id !== entity));
        else this._setDraft("removed_sensors", [...d.removed_sensors, entity]);
        break;
      }
      case "ed-save":
        await this._saveEdit();
        break;
      case "ed-apply":
        await this._applyEdit();
        break;
      case "ed-delete":
        await this._deleteEdit();
        break;
      case "page-retry":
        this._pageError = null;
        this._page = null;
        this._render();
        this._loadPage();
        break;
    }
  }

  async _callService(domain, service, entityId, args) {
    try {
      await this._hass.callService(domain, service, { entity_id: entityId, ...args });
    } catch (err) {
      this._toast(`${err.message || err}`);
    }
  }

  _toggleLv600sWarmPicker(entityId) {
    this._lv600sWarmPicker = this._lv600sWarmPicker === entityId ? null : entityId;
    this._lv600sWarmFocus = entityId;
    this._render();
  }

  async _check() {
    this._checking = true;
    this._render();
    try {
      await this._hass.callWS({ type: "levoit_esphome/check" });
    } catch (err) {
      this._toast(`Check failed: ${err.message || err}`);
    } finally {
      this._checking = false;
      this._render();
    }
  }

  // every device with an update, one after the other (the Device Builder builds
  // one at a time anyway); asks once
  async _updateAll() {
    const due = (this._data?.devices || []).filter(
      (d) => d.update_available && d.configuration && !d.building && !this._busy.has(d.name),
    );
    if (!due.length || this._updatingAll) return;
    if (
      !confirm(
        `Compile and upload ${due.length} device${due.length === 1 ? "" : "s"} over the air, one after the other?\n\n` +
          due.map((d) => `• ${d.title}`).join("\n") +
          "\n\nTemplate configs are refreshed from the newest builder file first.",
      )
    )
      return;
    this._updatingAll = true;
    this._render();
    try {
      for (const d of due) await this._build(d.name, true, { ask: false });
    } finally {
      this._updatingAll = false;
      this._render();
    }
  }

  async _build(name, upload, { ask = true } = {}) {
    const device = this._device(name);
    if (!device) return;
    if (
      upload &&
      ask &&
      !confirm(
        `Compile ${device.title} in the ESPHome Device Builder and upload it over the air?` +
          (device.config_kind && device.config_kind !== "custom"
            ? "\n\nIts template config is refreshed from the newest builder file first."
            : ""),
      )
    )
      return;
    this._busy.add(name);
    this._render();
    try {
      await this._hass.callWS({ type: "levoit_esphome/build", name, upload });
      this._toast(upload ? `${device.title}: compiled and uploaded` : `${device.title}: compiled`);
    } catch (err) {
      this._toast(`${device.title}: ${err.message || err}`);
    } finally {
      this._busy.delete(name);
      this._render();
    }
  }

  async _onChange(ev) {
    if (this._view === "group" && this._edit?.draft) {
      const t = ev.target;
      if (t.matches?.("input[data-member]")) {
        const d = this._edit.draft;
        const entity = t.dataset.member;
        t.blur();
        this._setDraft("members", t.checked ? [...d.members, entity] : d.members.filter((m) => m !== entity));
        return;
      }
      if (t.matches?.("select[data-member-lo], select[data-member-hi]")) {
        const entity = t.dataset.memberLo || t.dataset.memberHi;
        const all = { ...(this._edit.draft.member_speeds || {}) };
        const rng = { lowest: 1, highest: null, ...(all[entity] || {}) };
        rng[t.dataset.memberLo ? "lowest" : "highest"] = parseValue(t.value);
        const ladder = memberLadder(this._purifier(entity));
        if (rng.highest != null && rng.highest >= ladder[ladder.length - 1]) rng.highest = null;
        if (rng.lowest === 1 && rng.highest == null) delete all[entity];
        else all[entity] = rng;
        t.blur();
        this._setDraft("member_speeds", all);
        return;
      }
      if (t.matches?.("input[data-th]")) {
        const [type, i] = t.dataset.th.split(".");
        this._setDraft(`thresholds.${type}`, this._thAt(type, Number(i), Number(t.value) / 1000));
        return;
      }
      if (t.matches?.("select[data-combine]")) {
        t.blur();
        this._setDraft(`combine.${t.dataset.combine}`, t.value);
        return;
      }
      if (t.matches?.("[data-ed-field]")) {
        const field = t.dataset.edField;
        let value = t.value;
        if (t.type === "number") {
          if (value === "") return;
          value = Number(value);
        } else if (field === "area_id") value = value || null;
        if (t.tagName === "SELECT") t.blur();
        this._setDraft(field, value);
        return;
      }
    }
    const preset = ev.target.closest("select[data-preset]");
    if (preset) {
      // overview card: the mode dropdown
      preset.blur();
      await this._callService("fan", "set_preset_mode", preset.dataset.preset, { preset_mode: preset.value });
      return;
    }
    const input = ev.target.closest("input[data-number]");
    if (input) {
      // device page slider or time: set the number entity
      const value = input.type === "time" ? timeToHours(input.value) : Number(input.value);
      input.blur(); // let the page render the new value
      await this._callService("number", "set_value", input.dataset.number, { value });
      if (input.dataset.also)
        await this._callService("number", "set_value", input.dataset.also, { value });
      return;
    }
    const select = ev.target.closest("select[data-channel]");
    if (!select) return;
    const device = this._device(select.dataset.channel);
    const channel = select.value;
    if (!device || channel === device.channel) return;
    if (
      device.configuration &&
      !confirm(
        `Switch ${device.title} to ${CHANNEL_LABELS[channel]}?\n\n` +
          `This sets ref: ${channel} in ${device.configuration}; the next update builds from it.`,
      )
    ) {
      select.value = device.channel;
      return;
    }
    this._busy.add(device.name);
    this._render();
    try {
      await this._hass.callWS({
        type: "levoit_esphome/set_channel",
        name: device.name,
        channel,
      });
    } catch (err) {
      this._toast(`${device.title}: ${err.message || err}`);
    } finally {
      this._busy.delete(device.name);
      this._render();
    }
  }

  // --- rendering --------------------------------------------------------------

  _time(iso) {
    if (!iso) return "";
    const date = new Date(iso);
    const lang = this._hass?.locale?.language || this._hass?.language;
    const sameDay = date.toDateString() === new Date().toDateString();
    return sameDay
      ? date.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })
      : date.toLocaleString(lang, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });
  }

  _status(d) {
    if (d.building) return this._buildChip(d);
    if (d.online === false) return `<span class="chip">Offline</span>`;
    if (!d.configuration) return `<span class="chip">No config</span>`;
    if (d.update_available) return `<span class="chip warning">Update available</span>`;
    if (d.installed && d.latest) return `<span class="chip success">Up to date</span>`;
    return `<span class="chip">Unknown</span>`;
  }

  _lastBuild(d) {
    const logLink = d.has_build_log
      ? ` · <a href="#" data-action="log" data-name="${esc(d.name)}">Log</a>`
      : "";
    const last = d.last_build;
    if (d.building) return logLink ? `<div class="sub">${logLink.slice(3)}</div>` : "";
    if (!last) return "";
    const when = esc(this._time(last.at));
    if (last.ok) {
      // the result step's summary: Flash and RAM of the finished build
      const result = (d.build?.steps || []).find((s) => s.key === "result");
      const sizes = result?.detail ? ` · ${esc(result.detail)}` : "";
      // what the integration did after the build, e.g. the OTA migration
      const note = last.note ? ` · ${esc(last.note)}` : "";
      return `<div class="sub ok">${last.upload ? "Uploaded" : "Compiled"} ${when}${sizes}${note}${logLink}</div>`;
    }
    const what = last.upload ? "Compile and upload" : "Compile";
    const note = last.note ? ` · ${esc(last.note)}` : "";
    return `<div class="sub bad" title="${esc(last.error)}">${what} failed ${when}${logLink}: ${esc(
      last.error,
    )}${note}</div>`;
  }

  // --- build steps ---------------------------------------------------------------

  _runningStep(d) {
    return (d.build?.steps || []).find((s) => s.state === "running") || null;
  }

  // the compile counter or the upload bar as a fraction, else null
  _stepFraction(step) {
    if (step.total && step.done != null) return Math.min(1, step.done / step.total);
    if (step.percent != null) return Math.min(1, step.percent / 100);
    return null;
  }

  _stepCount(step) {
    if (step.total && step.done != null) return `${step.done} / ${step.total}`;
    if (step.percent != null) return `${step.percent} %`;
    return "";
  }

  _bar(fraction) {
    return fraction == null
      ? ""
      : `<span class="pbar" role="progressbar" aria-valuenow="${Math.round(fraction * 100)}" aria-valuemin="0" aria-valuemax="100"><span style="width:${Math.round(fraction * 100)}%"></span></span>`;
  }

  // the status chip of a running build: the step, its counter, bar and detail
  _buildChip(d) {
    const step = this._runningStep(d);
    if (!step)
      return `<span class="chip info"><span class="spinner"></span>${
        BUILD_STEP_LABELS[d.build_step] || "Building…"
      }</span>`;
    const count = this._stepCount(step);
    const bar = this._bar(this._stepFraction(step));
    const detail = step.detail ? `<div class="sub mono">${esc(step.detail)}</div>` : "";
    return `<span class="chip info"><span class="spinner"></span>${esc(STEP_LABELS[step.key] || step.key)}${
      count ? ` ${count}` : ""
    }</span>${bar}${detail}`;
  }

  // the step list of the log dialog: queued, running (with its detail), done, failed
  _stepsList(build) {
    if (!build) return "";
    return `<ol class="steps">${build.steps
      .map((step) => {
        const mark =
          step.state === "done"
            ? icon("check")
            : step.state === "failed"
              ? icon("close")
              : step.state === "running"
                ? `<span class="spinner"></span>`
                : `<span class="dot-q"></span>`;
        const count = step.state === "running" ? this._stepCount(step) : "";
        const bar = step.state === "running" ? this._bar(this._stepFraction(step)) : "";
        const detail = [count, step.detail ? esc(step.detail) : ""].filter(Boolean).join(" · ");
        return `<li class="${step.state}"><span class="st">${mark}</span><span class="sn">${esc(
          STEP_LABELS[step.key] || step.key,
        )}</span><span class="sd">${bar}${detail ? `<span class="sd-text">${detail}</span>` : ""}</span></li>`;
      })
      .join("")}</ol>`;
  }

  _channel(d) {
    const busy = this._busy.has(d.name) || d.building;
    if (d.can_set_channel && (d.channel === "stable" || d.channel === "main" || !d.configuration)) {
      return `<select data-channel="${esc(d.name)}" ${busy ? "disabled" : ""} aria-label="Channel of ${esc(d.title)}">
        ${["stable", "main"]
          .map(
            (c) =>
              `<option value="${c}" ${d.channel === c ? "selected" : ""}>${CHANNEL_LABELS[c]}</option>`,
          )
          .join("")}
      </select>`;
    }
    if (!d.channel) return `<span class="muted">—</span>`;
    const label = CHANNEL_LABELS[d.channel] || d.channel;
    const ref = d.channel === "pinned" && d.ref ? ` <span class="muted">${esc(d.ref)}</span>` : "";
    const why = d.config_kind === "custom" ? ` title="Set by ref: in your own config"` : "";
    return `<span${why}>${esc(label)}</span>${ref}`;
  }

  _filter(d) {
    if (d.filter_life == null) return `<span class="muted">—</span>`;
    const value = Math.max(0, Math.min(100, d.filter_life));
    const level = value < 10 ? "bad" : value < 25 ? "low" : "good";
    return `<span class="filter ${level}"><span class="bar"><span style="width:${value}%"></span></span>${Math.round(
      d.filter_life,
    )} %</span>`;
  }

  _esphome(d) {
    if (!d.esphome_deployed && !d.esphome_current) return `<span class="muted">—</span>`;
    if (d.esphome_current && d.esphome_deployed && d.esphome_current !== d.esphome_deployed)
      return `${esc(d.esphome_deployed)}<div class="sub" title="The Device Builder runs a newer ESPHome; the next compile and upload brings it">builder ${esc(
        d.esphome_current,
      )}</div>`;
    return esc(d.esphome_deployed || d.esphome_current);
  }

  _actions(d) {
    if (!d.configuration)
      return `<button class="btn" data-action="navigate" data-path="${INTEGRATION_PAGE}" title="Add device → Device already in Home Assistant">Add config</button>`;
    const busy = this._busy.has(d.name) || d.building;
    const dis = busy ? "disabled" : "";
    return `<button class="btn" data-action="compile" data-name="${esc(d.name)}" ${dis}>Compile</button>
      <button class="btn ${d.update_available ? "primary" : ""}" data-action="upload" data-name="${esc(d.name)}" ${dis}>${
        d.update_available ? "Update" : "Compile &amp; upload"
      }</button>`;
  }

  _row(d) {
    // the name opens the device page (settings); the HA device page is linked there
    const pagePath = this._devicePath(d.name);
    const deviceLink = d.device_id
      ? `<a href="${esc(pagePath)}" data-action="navigate" data-path="${esc(pagePath)}" title="Settings of ${esc(d.title)}">${esc(d.title)}</a>`
      : esc(d.title);
    const latest = d.latest
      ? d.latest_url
        ? `<a class="mono" href="${esc(d.latest_url)}" target="_blank" rel="noreferrer">${esc(d.latest)}</a>`
        : `<span class="mono">${esc(d.latest)}</span>`
      : "";
    // installed, and the version it goes to when there is an update
    const firmware = `<div class="fw"><span class="mono muted">${d.installed ? esc(d.installed) : "—"}</span>${
      d.update_available && latest
        ? `<svg class="fw-arrow" viewBox="0 0 24 24" role="img" aria-label="to"><path d="M4,11V13H16L10.5,18.5L11.92,19.92L19.84,12L11.92,4.08L10.5,5.5L16,11H4Z"></path></svg>${latest}`
        : ""
    }</div>`;
    return `<tr class="${d.update_available ? "has-update" : ""}">
      <td class="device" data-label="Device">
        <div class="name">${deviceLink}</div>
        <div class="sub mono">${esc(d.configuration || d.name)}</div>
      </td>
      <td data-label="Hardware">${d.model ? esc(d.model) : `<span class="muted">—</span>`}<div class="sub">${
        d.config_kind ? esc(KIND_LABELS[d.config_kind] || d.config_kind) : d.configuration ? "…" : "No config yet"
      }</div></td>
      <td data-label="Channel">${this._channel(d)}</td>
      <td data-label="Firmware">${firmware}<div class="fw-status">${this._status(d)}</div>${this._lastBuild(d)}</td>
      <td data-label="Filter">${this._filter(d)}</td>
      <td data-label="ESPHome" class="mono">${this._esphome(d)}</td>
      <td class="actions">${this._actions(d)}</td>
    </tr>`;
  }

  // the newest versions per channel, when they were checked, and Update all
  _releases() {
    const heads = this._data?.heads || {};
    const head = (channel) =>
      heads[channel]
        ? `<div class="rel"><span class="rel-label">${CHANNEL_LABELS[channel]}</span><a class="mono" href="${esc(
            heads[channel].url,
          )}" target="_blank" rel="noreferrer">${esc(heads[channel].version)}</a></div>`
        : "";
    const due = (this._data?.devices || []).filter((d) => d.update_available && d.configuration).length;
    const anyBusy = this._updatingAll || (this._data?.devices || []).some((d) => d.building);
    const checked = this._data?.checked_at ? `Checked ${esc(this._time(this._data.checked_at))}` : "";
    const unreachable =
      this._data && !this._data.last_update_success ? `<span class="bad">Device Builder not reachable</span>` : "";
    return `<div class="card releases">
      ${head("stable")}${head("main")}
      <div class="rel-when muted">${[checked, unreachable].filter(Boolean).join(" · ")}</div>
      <button class="btn text" data-action="check" ${this._checking ? "disabled" : ""}>${
        this._checking ? `<span class="spinner"></span> Checking…` : "Check now"
      }</button>
      ${
        due
          ? `<button class="btn primary icon-text" data-action="update-all" ${anyBusy ? "disabled" : ""}>${icon(
              "download",
            )}<span>${this._updatingAll ? "Updating…" : `Update all (${due})`}</span></button>`
          : ""
      }
    </div>`;
  }

  _body() {
    if (this._error)
      return `<div class="card empty"><p class="bad">${esc(this._error)}</p>
        <p class="muted">Is Levoit ESPHome set up and loaded?</p>
        <button class="btn" data-action="retry">Try again</button></div>`;
    if (!this._data) return `<div class="card empty"><span class="spinner"></span> Loading…</div>`;
    const devices = this._data.devices;
    const pending = this._data.pending || [];
    if (!devices.length && !pending.length)
      return `<div class="card empty">
        <div class="big-icon">${icon("purifier")}</div>
        <p>No Levoit or Philips ESPHome device found yet.</p>
        <p class="muted">A device shows up when its Device Builder config loads the levoit or philips component, or when it reports the esp_version or model text sensor.</p>
        <button class="btn primary" data-action="navigate" data-path="${INTEGRATION_PAGE}">Add device</button>
      </div>`;
    const updates = devices.filter((d) => d.update_available).length;
    const noConfig = devices.filter((d) => !d.configuration).length;
    return `<div class="card">
      <div class="card-head">
        <span><b>${devices.length} device${devices.length === 1 ? "" : "s"}</b>${
          updates ? ` · ${updates} to update` : ""
        }${noConfig ? ` · ${noConfig} without a config` : ""}${
          pending.length ? ` · ${pending.length} not flashed yet` : ""
        }</span>
      </div>
      <table>
        <thead><tr>
          <th>Device</th><th>Hardware</th><th>Channel</th><th>Firmware</th>
          <th>Filter</th><th>ESPHome</th><th><span class="sr">Actions</span></th>
        </tr></thead>
        <tbody>${devices.map((d) => this._row(d)).join("")}${pending
          .map((p) => this._pendingRow(p))
          .join("")}</tbody>
      </table>
    </div>`;
  }

  // A config made by Add device whose ESP has not connected yet: flash it once
  // over USB from the Device Builder, then it becomes a normal device row.
  _pendingRow(p) {
    const busy = this._busy.has(p.name) || p.building;
    const builderUrl = this._data?.builder_url;
    const status = p.building ? this._buildChip(p) : `<span class="chip info">Not flashed yet</span>`;
    const none = `<span class="muted">—</span>`;
    return `<tr class="pending">
      <td class="device" data-label="Device">
        <div class="name">${esc(p.title)}</div>
        <div class="sub mono">${esc(p.configuration)}</div>
      </td>
      <td data-label="Hardware">${p.model ? esc(p.model) : none}${
        p.config_kind ? `<div class="sub">${esc(KIND_LABELS[p.config_kind] || p.config_kind)}</div>` : ""
      }</td>
      <td data-label="Channel">${none}</td>
      <td data-label="Firmware"><div class="fw"><span class="muted">not flashed</span></div><div class="fw-status">${status}</div>${this._lastBuild(p)}
        <div class="sub hint">Device Builder: open ${esc(p.configuration)}, Install, Plug into this computer</div>
      </td>
      <td data-label="Filter">${none}</td>
      <td data-label="ESPHome">${none}</td>
      <td class="actions">
        <button class="btn" data-action="compile" data-name="${esc(p.name)}" ${busy ? "disabled" : ""} title="Check that the config builds, before flashing">Compile</button>${
          builderUrl
            ? `<button class="btn primary" data-action="navigate" data-path="${esc(builderUrl)}" title="Flash it there over USB: Install, Plug into this computer">Open Device Builder</button>`
            : ""
        }
      </td>
    </tr>`;
  }

  _render() {
    if (!this.shadowRoot) return;
    // do not pull an open dropdown or a slider being dragged away from under the pointer
    // (or the history chart someone steps through with the arrow keys)
    // and never between pressing and releasing a button (see _pressing)
    const active = this.shadowRoot.activeElement?.tagName;
    if (
      this._pressing ||
      active === "SELECT" ||
      active === "INPUT" ||
      this.shadowRoot.activeElement?.classList?.contains("hist")
    ) {
      this._deferred = true;
      return;
    }
    const showMenu = this._narrow || this._hass?.dockedSidebar === "always_hidden";
    const builderUrl = this._data?.builder_url;
    const version = this._panel?.config?.version;
    const onPage = this._view === "device" && Boolean(this._pageName);
    const onConfig = this._view === "config";
    const onGroups = this._view === "groups";
    const onEditor = this._view === "group";
    const onDetail = this._view === "groupdetail";
    const detail = onDetail ? this._detailGroup() : null;
    const pageTitle =
      this._page?.title || this._device(this._pageName)?.title || this._pageName || "";
    const updates = (this._data?.devices || []).filter((d) => d.update_available).length;
    const onDevices = !onConfig && !onGroups;
    const tabs =
      onPage || onEditor || onDetail
        ? ""
        : `<div class="tabs" role="tablist">
          <button class="tab${onDevices ? " on" : ""}" role="tab" aria-selected="${onDevices}" data-action="navigate" data-path="${esc(this._base)}">Devices</button>
          <button class="tab${onGroups ? " on" : ""}" role="tab" aria-selected="${onGroups}" data-action="navigate" data-path="${esc(this._groupsPath())}">Purifier groups</button>
          <button class="tab${onConfig ? " on" : ""}" role="tab" aria-selected="${onConfig}" data-action="navigate" data-path="${esc(this._base)}/config">Updates &amp; config${
            updates ? `<span class="tab-badge" title="${updates} with an update">${updates}</span>` : ""
          }</button>
        </div>`;
    // the view first: the editor makes its draft, which the toolbar shows
    const view = onPage
      ? this._devicePage()
      : onConfig
        ? `${this._data && !this._error ? this._releases() : ""}${this._body()}`
        : onGroups
          ? this._groupsView()
          : onEditor
            ? this._groupEditor()
            : onDetail
              ? this._groupDetail()
              : this._overview();
    const draft = onEditor ? this._edit?.draft : null;
    const invalid =
      !draft || this._draftMembers().length < 2 || Boolean(this._thresholdError()) || this._edit.saving;
    // the theme's light or dark mode: a few colours of our own follow it
    this.toggleAttribute("dark", Boolean(this._hass?.themes?.darkMode));
    const haDevice = onPage && this._page?.device_id ? `/config/devices/device/${this._page.device_id}` : null;
    // the log dialog: where its lines were scrolled to, before they are replaced
    const oldPre = this.shadowRoot.querySelector(".log pre");
    const atEnd = !oldPre || oldPre.scrollHeight - oldPre.scrollTop - oldPre.clientHeight < 8;
    const oldScroll = oldPre ? oldPre.scrollTop : 0;
    this.shadowRoot.innerHTML = `<style>${STYLE}</style>
      <div class="toolbar">
        ${
          showMenu
            ? `<button class="icon-btn" data-action="menu" aria-label="Menu">${icon("menu")}</button>`
            : ""
        }${
          onPage
            ? `<button class="icon-btn back" data-action="navigate" data-path="${esc(this._base)}" aria-label="All devices" title="All devices">${icon("back")}</button>`
            : onEditor && draft?.id
              ? `<button class="icon-btn back" data-action="navigate" data-path="${esc(this._groupsPath(encodeURIComponent(draft.id)))}" aria-label="Back to the group" title="Back to the group">${icon("back")}</button>`
              : onEditor || onDetail
                ? `<button class="icon-btn back" data-action="navigate" data-path="${esc(this._groupsPath())}" aria-label="All purifier groups" title="All purifier groups">${icon("back")}</button>`
                : ""
        }
        <div class="title">${
          onPage
            ? esc(pageTitle)
            : onEditor
              ? `${esc(draft?.name?.trim() || (draft?.id ? "Purifier group" : "New group"))}<div class="subtitle">Purifier group</div>`
              : detail
                ? `${esc(detail.name)}<div class="subtitle">Purifier group · ${detail.members.length} purifiers</div>`
                : "Levoit ESPHome"
        }</div>
        ${
          detail
            ? `<button class="tb-btn" data-action="navigate" data-path="${esc(
                this._groupsPath(`${encodeURIComponent(detail.id)}/edit`),
              )}" title="Edit the group">${icon("pencil")}<span>Edit group</span></button>`
            : ""
        }
        ${
          draft?.id
            ? `<button class="tb-btn" data-action="ed-delete" title="Delete this group">${icon("delete")}<span>Delete group</span></button>`
            : ""
        }${
          draft
            ? `<button class="tb-btn strong" data-action="ed-save" ${invalid ? "disabled" : ""} title="Save the group">${icon(
                "check",
              )}<span>Save</span></button>`
            : ""
        }
        ${
          haDevice
            ? `<button class="tb-btn" data-action="navigate" data-path="${esc(haDevice)}" title="The Home Assistant device page: every entity">${icon(
                "open",
              )}<span>Device page</span></button>`
            : ""
        }
        ${
          builderUrl && !onPage && !onEditor && !onDetail
            ? `<button class="tb-btn" data-action="navigate" data-path="${esc(builderUrl)}" title="Open the ESPHome Device Builder">${icon(
                "builder",
              )}<span>Device Builder</span></button>`
            : ""
        }
        ${
          onPage || onEditor || onDetail
            ? ""
            : `<button class="tb-btn" data-action="navigate" data-path="${INTEGRATION_PAGE}" title="Add device (on the integration page)">${icon(
                "plus",
              )}<span>Add device</span></button>`
        }
      </div>
      <div class="content">
        ${
          version && LOADED_VERSION && version !== LOADED_VERSION
            ? `<div class="notice">Levoit ESPHome was updated to ${esc(version)}; this page still runs ${esc(
                LOADED_VERSION,
              )}. <button class="btn primary" data-action="reload">Reload this page</button></div>`
            : ""
        }
        ${tabs}
        ${view}
        <div class="footer muted">Levoit ESPHome${version ? ` ${esc(version)}` : ""}${
          onConfig ? " · builds run in the ESPHome Device Builder; the last build's output is under Log" : ""
        }</div>
      </div>
      ${this._logDialog()}`;
    const pre = this.shadowRoot.querySelector(".log pre");
    if (pre) {
      // newest lines in view, unless someone scrolled up in the full log
      if (this._logScroll === "end" || atEnd) pre.scrollTop = pre.scrollHeight;
      else pre.scrollTop = oldScroll;
      this._logScroll = null;
    }
    if (this._hass) {
      this._seen = {};
      for (const entityId of this._watched()) this._seen[entityId] = this._hass.states[entityId];
    }
    if (this._lv600sWarmFocus) {
      const picker = [...this.shadowRoot.querySelectorAll(".lv-warm-picker")]
        .find((element) => element.dataset.entity === this._lv600sWarmFocus);
      (picker?.querySelector('[aria-pressed="true"]') || picker?.querySelector("button"))?.focus({ preventScroll: true });
      this._lv600sWarmFocus = null;
    }
    this._bindHistory();
  }

  // --- overview: every device as a card, for using them --------------------------

  _overview() {
    const devices = this._data?.devices || [];
    const pending = this._data?.pending || [];
    // loading, errors and no devices at all: as on the config tab
    if (this._error || !this._data || (!devices.length && !pending.length)) return this._body();
    const cards = devices.map((d) => this._deviceCard(d)).join("");
    const waiting = pending.length
      ? `<div class="muted overview-note">${pending.length} device${pending.length === 1 ? "" : "s"} not flashed yet: see <a href="${esc(
          this._base,
        )}/config" data-action="navigate" data-path="${esc(this._base)}/config">Updates &amp; config</a></div>`
      : "";
    return `${this._overviewSummary(devices)}<div class="overview">${cards}</div>${waiting}`;
  }

  // "2 running · 4 off · 1 offline", and the device with the worst air
  _overviewSummary(devices) {
    let running = 0;
    let off = 0;
    let offline = 0;
    let worst = null;
    for (const d of devices) {
      const fan = this._dstate(d, "fan.fan");
      if (!fan) continue;
      if (this._isOffline(d, fan)) {
        offline++;
        continue;
      }
      if (fan.state === "on") running++;
      else off++;
      const pm = this._dstate(d, "sensor.pm25");
      const value = this._usable(pm) ? parseFloat(pm.state) : NaN;
      if (Number.isFinite(value) && (!worst || value > worst.value)) worst = { d, value, unit: pm.attributes.unit_of_measurement };
    }
    if (!running && !off && !offline) return "";
    const counts = [
      `<b>${running} running</b>`,
      `${off} off`,
      offline ? `<span class="bad">${offline} offline</span>` : "",
    ].filter(Boolean);
    // only worth a mention when the air is not good (above the WHO day limit)
    const air =
      worst && worst.value > 15
        ? `<span>Worst air: <a href="${esc(this._devicePath(worst.d.name))}" data-action="navigate" data-path="${esc(
            this._devicePath(worst.d.name),
          )}">${esc(worst.d.title)}</a> · PM2.5 ${esc(formatNumber(Math.round(worst.value)))}${
            worst.unit ? ` ${esc(worst.unit)}` : ""
          }</span>`
        : "";
    return `<div class="ov-summary">${`<span>${counts.join(" · ")}</span>`}${air}</div>`;
  }

  _isOffline(d, fan) {
    return d.online === false || (fan && !this._usable(fan) && fan.state !== "off");
  }

  _lvModeLabel(value) {
    if (value === "Humidity") return "Auto";
    if (value === "Humidity Sleep") return "Sleep";
    if (value === "Auto (read only)") return "Auto (Original)";
    return value || "Unknown";
  }

  _lv600sUnsafe(state, controls) {
    if (controls?.["binary_sensor.mcu_connection"] && state("binary_sensor.mcu_connection")?.state !== "on") {
      return true;
    }
    return ["binary_sensor.water_tank_empty", "binary_sensor.tank_removed", "binary_sensor.mcu_fault"]
      .some((key) => controls?.[key] && state(key)?.state !== "off");
  }

  _tankBadge(state, offline) {
    const connection = state("binary_sensor.mcu_connection");
    if (offline || (connection && connection.state !== "on")) return "";
    const tank = state("binary_sensor.tank_removed");
    if (tank && !this._usable(tank)) return "";
    const missing = tank?.state === "on";
    const water = state("binary_sensor.water_tank_empty")?.state;
    if (!missing && water !== "on" && water !== "off") return "";

    const glyph = missing ? "tankOut" : water === "on" ? "waterEmpty" : "water";
    const label = missing ? "Tank missing"
      : water === "on" ? "Water empty"
      : "Water available";
    const tone = glyph === "water" ? "water" : "warning";
    return `<span class="dc-tank ${tone}" title="${esc(label)}">${icon(glyph)}${esc(label)}</span>`;
  }

  _lv600sQuickControls(state, { disabled, compact, on }) {
    const fan = state("fan.fan");
    if (!fan) return "";
    const warm = state("number.warm_level");
    const preset = fan.attributes.preset_mode;
    const options = (fan.attributes.preset_modes || []).filter((value) => LV600S_PRESETS.includes(value));
    const currentMode = on && options.includes(preset) ? preset : "";
    const mode = !options.length ? "" : compact
      ? `<select class="mode-select" data-action="none" data-preset="${esc(fan.entity_id)}" aria-label="Mode" ${disabled ? "disabled" : ""}>
        ${currentMode ? "" : `<option value="" disabled selected>${on ? "Mode" : "Off"}</option>`}
        ${options.map((value) => `<option value="${esc(value)}"${value === currentMode ? " selected" : ""}>${esc(this._lvModeLabel(value))}</option>`).join("")}
      </select>`
      : `<div class="segs" role="group" aria-label="Mode">${options.map((value) => `<button class="seg${value === currentMode ? " on" : ""}" aria-pressed="${value === currentMode}"
        ${disabled ? "disabled" : ""} ${this._svc("fan", "set_preset_mode", fan.entity_id, { preset_mode: value })}>${esc(this._lvModeLabel(value))}</button>`).join("")}</div>`;

    const percentage = Number(fan.attributes.percentage) || 0;
    const mistLevel = on && percentage > 0 ? Math.ceil(percentage * 3 / 100) : 0;
    const mist = Number(fan.attributes.percentage_step) > 0
      ? this._lv600sLevelControl("mist", fan, LV600S_MIST_PERCENTAGES, {
          disabled, compact, on, selected: mistLevel, active: state("binary_sensor.humidifying")?.state === "on",
        })
      : "";
    const warmth = warm
      ? this._lv600sLevelControl("warm", warm, [0, 1, 2, 3], {
          disabled: disabled || !this._usable(warm) || (on && preset === "Sleep"),
          compact, on, selected: this._usable(warm) ? Number(warm.state) : null,
          active: state("binary_sensor.heating_enabled")?.state === "on",
          standby: fan.state === "off",
        })
      : "";
    const levels = `<div class="lv-levels">${mist}${warmth}</div>`;
    return compact ? `${levels}${mode}` : `<div class="lv-quick">${mode}${levels}</div>`;
  }

  _lv600sLevelControl(kind, entity, levels, { disabled, compact, on, selected, active, standby }) {
    const warm = kind === "warm";
    const label = warm ? "Warm mist" : "Mist level";
    const effective = on && active;
    const glyph = warm ? (effective ? "mdi:heat-wave" : "mdi:thermometer-off")
      : (effective ? "mdi:scent" : "mdi:scent-off");
    const tone = effective && !disabled ? (warm ? " heating" : " humidifying") : "";
    const levelIcon = `<ha-icon class="lv-level-icon${tone}" icon="${glyph}" aria-hidden="true" title="${label}"></ha-icon>`;
    const displayedLevel = warm && standby && !compact ? 0 : selected;
    const buttons = levels.map((value, index) => {
      const level = warm ? value : index + 1;
      const chosen = level === displayedLevel;
      const text = level === 0 ? "Off" : level;
      const service = warm ? this._svc("number", "set_value", entity.entity_id, { value })
        : this._svc("fan", "set_percentage", entity.entity_id, { percentage: value });
      return `<button class="seg sm${chosen ? " on" : ""}" aria-label="${label} ${text}"
        aria-pressed="${chosen}" ${disabled ? "disabled" : ""} ${service}>${text}</button>`;
    }).join("");
    const options = `<div class="segs lv-level-options" role="group" aria-label="${label}">${buttons}</div>`;
    if (warm && compact) {
      const expanded = this._lv600sWarmPicker === entity.entity_id && !disabled;
      const text = standby || selected === 0 ? "Off" : selected ?? "—";
      return `<div class="lv-level lv-warm-picker${expanded ? " expanded" : ""}" data-entity="${esc(entity.entity_id)}">
        ${levelIcon}${expanded ? options : `<div class="segs">
          <button class="seg sm" data-action="lv-warm-picker" data-entity="${esc(entity.entity_id)}"
            aria-label="${label}: ${text}" aria-expanded="false" ${disabled ? "disabled" : ""}>${text}</button>
        </div>`}
      </div>`;
    }
    return `<div class="lv-level">${compact ? "" : levelIcon}${options}</div>`;
  }

  // a device's state for a controls key, from the subscription's mapping
  _dstate(d, key) {
    const entityId = d.controls?.[key];
    return entityId ? this._hass?.states?.[entityId] || null : null;
  }

  _deviceCard(d) {
    const humidifier = d.model === "LV600S";
    const fan = this._dstate(d, "fan.fan");
    const state = (key) => this._dstate(d, key);
    const on = fan?.state === "on";
    const a = fan?.attributes || {};
    const step = Number(a.percentage_step) || 25;
    const count = Math.max(1, Math.round(100 / step));
    const level = on ? Math.round((Number(a.percentage) || 0) / step) : 0;
    const offline = this._isOffline(d, fan);
    const humidifierUnsafe = humidifier && this._lv600sUnsafe(state, d.controls);
    // speed buttons and the mode dropdown; picking either turns it on too
    const dis = offline ? "disabled" : "";
    const presets = a.preset_modes || [];
    const current = on && presets.includes(a.preset_mode) ? a.preset_mode : "";
    const modeSelect =
      fan && presets.length
        ? `<select class="mode-select" data-action="none" data-preset="${esc(fan.entity_id)}" aria-label="Mode of ${esc(
            d.title,
          )}" ${dis}>${
            current ? "" : `<option value="" selected disabled>${on ? "Mode" : "Off"}</option>`
          }${presets
            .map((m) => `<option value="${esc(m)}"${m === current ? " selected" : ""}>${esc(m)}</option>`)
            .join("")}</select>`
        : "";
    const speedButtons = fan
      ? Array.from({ length: count }, (_, i) => i + 1)
          .map(
            (n) =>
              `<button class="seg sm${n === level ? " on" : ""}" aria-label="Speed ${n}" ${dis} ${this._svc(
                "fan",
                "set_percentage",
                fan.entity_id,
                { percentage: Math.min(100, Math.floor(n * step)) },
              )}>${d.model === "ELEVA300X" && n === count ? "Turbo" : n}</button>`,
          )
          .join("")
      : "";
    const quickControls = humidifier ? this._lv600sQuickControls(state, {
      disabled: offline || !this._usable(fan) || humidifierUnsafe, compact: true, on,
    }) : `${speedButtons ? `<div class="segs" role="group" aria-label="Speed">${speedButtons}</div>` : ""}${modeSelect}`;
    const controls = quickControls
      ? `<div class="dc-controls${humidifier ? ' humidifier-controls" data-action="none' : ""}">${quickControls}</div>`
      : "";
    const timerLeft =
      (humidifier ? lv600sRemainingSeconds(state("text_sensor.timer_duration_remaining")?.state)
        : parseDuration(state("text_sensor.timer_duration_remaining")?.state)) / 60;
    // the AQI dot: from the 1-4 level, else from the Eleva's index
    const levelSt = this._dstate(d, "sensor.aqi");
    const indexSt = this._dstate(d, "sensor.aqi_index");
    const dotLevel = this._usable(levelSt)
      ? aqiLevel(levelSt.state)
      : this._usable(indexSt)
        ? aqiIndexLevel(indexSt.state)
        : null;
    const stat = (key, label, dot) => {
      const st = this._dstate(d, key);
      if (!st) return "";
      const ok = this._usable(st) && !offline;
      const value = ok ? formatNumber(Math.round(parseFloat(st.state))) : "—";
      const unit = ok ? st.attributes.unit_of_measurement || "" : "";
      // the unit goes with the label, so the number always fits the tile
      return `<div class="dc-stat"><div class="dc-val">${esc(value)}${
        dot && ok ? `<span class="aqi-dot q${dot}" title="${esc(AQI_WORDS[dot])}"></span>` : ""
      }</div><div class="dc-label">${esc(label)}${unit ? ` ${esc(unit)}` : ""}</div></div>`;
    };
    const aqiKey = levelSt || d.controls?.["sensor.aqi"] ? "sensor.aqi" : "sensor.aqi_index";
    const stats = humidifier ? [
      stat("sensor.humidity", "Humidity"),
      stat("sensor.temperature", "Temperature"),
    ].join("") : [
      stat("sensor.pm25", "PM2.5"),
      stat(aqiKey, "AQI", dotLevel),
      stat("sensor.current_cadr", "CADR"),
    ].join("");
    const powerDisabled = offline || (humidifierUnsafe && !on);
    const powerLabel = on ? "Turn off" : "Turn on";
    const power = fan
      ? `<button class="power small${on ? " on" : ""}" aria-label="${esc(d.title)}: ${powerLabel}" title="${powerLabel}"
        ${powerDisabled ? "disabled" : ""} ${this._svc("fan", on ? "turn_off" : "turn_on", fan.entity_id)}>${icon("power")}</button>`
      : "";
    // under the name: model and filter; a line below: timer, update, offline and group
    const filter =
      d.filter_life != null && !offline
        ? (() => {
            const value = Math.max(0, Math.min(100, d.filter_life));
            const lvl = value < 10 ? "bad" : value < 25 ? "low" : "good";
            return `<span class="dc-filter ${lvl}" title="Filter ${Math.round(value)} % left">${icon(
              "filter",
            )}<span class="bar"><span style="width:${value}%"></span></span>${Math.round(value)} %</span>`;
          })()
        : "";
    const modelStatus = humidifier ? this._tankBadge(state, offline) : filter;
    const flags = [
      timerLeft > 0 && on && !offline ? `<span class="chip info">Off in ${esc(formatMinutes(timerLeft))}</span>` : "",
      d.update_available && !offline
        ? `<button class="chip warning chip-btn" data-action="navigate" data-path="${esc(this._base)}/config" title="Open Updates &amp; config">Update</button>`
        : "",
      offline ? `<span class="chip bad-chip"><span class="dot-i"></span>Offline</span>` : "",
    ].join("");
    const groupChip = this._groupChip(d);
    const path = this._devicePath(d.name);
    // A native mode picker can finish with a click on its containing card.
    // Keep the humidifier's navigation on its information areas.
    const infoLink = humidifier ? ` data-action="navigate" data-path="${esc(path)}"` : "";
    return `<div class="dcard${humidifier ? " humidifier" : ""}${on && !offline ? " on" : ""}${offline ? " offline" : ""}" role="link" tabindex="0"${humidifier ? "" : ' data-action="navigate"'} data-path="${esc(
      path,
    )}" aria-label="${esc(d.title)}: open its page">
      <div class="dc-top"${infoLink}>
        <span class="dev-tile">${deviceImage(d.model)}</span>
        <div class="dc-name">
          <div class="name">${esc(d.title)}</div>
          <div class="dc-sub"><span>${esc(d.model || "Levoit")}</span>${modelStatus ? `<span aria-hidden="true">·</span>${modelStatus}` : ""}</div>${
            flags || groupChip ? `<div class="dc-flags">${flags}${groupChip}</div>` : ""
          }
        </div>
        ${power}
      </div>
      ${stats ? `<div class="dc-stats"${infoLink}>${stats}</div>` : ""}
      ${controls}
    </div>`;
  }

  // --- purifier groups ------------------------------------------------------------
  // Routes: /groups the list, /groups/<id> the editor, /groups/new (or
  // /groups/new/<area_id> from a room suggestion) a new group.

  async _subscribeGroups() {
    this._groupsSubscribing = true;
    try {
      this._groupsUnsub = this._hass.connection.subscribeMessage(
        (data) => {
          this._groups = data;
          this._groupsError = null;
          if (this._view === "group") this._schedulePreview(1000);
          // the Devices cards and device pages show a group's status: render
          // them when that changed, not on every reading
          const sig = JSON.stringify(
            (data.groups || []).map((g) => [
              g.id,
              g.name,
              g.enabled,
              g.mode,
              g.state?.status,
              g.state?.level,
              g.state?.reason,
              (g.state?.members || []).map((m) => [m.entity_id, m.in_control, m.paused_until]),
            ]),
          );
          const changed = sig !== this._groupsSig;
          this._groupsSig = sig;
          if (this._view === "groups" || this._view === "group" || changed) this._render();
        },
        { type: "levoit_esphome/groups/subscribe" },
      );
      await this._groupsUnsub;
    } catch (err) {
      this._groupsUnsub = null;
      this._groupsError = err?.message || String(err);
      this._render();
    } finally {
      this._groupsSubscribing = false;
    }
  }

  _groupsPath(rest = "") {
    return `${this._base}/groups${rest ? `/${rest}` : ""}`;
  }

  _purifier(entityId) {
    return (this._groups?.purifiers || []).find((p) => p.entity_id === entityId) || null;
  }

  _areaName(areaId) {
    return (areaId && this._hass?.areas?.[areaId]?.name) || "";
  }

  _offline(entityId) {
    const st = this._hass?.states?.[entityId];
    return !st || st.state === "unavailable" || st.state === "unknown";
  }

  // speed n of a purifier as its panel names it: the top speed of the Eleva
  // (its level 4) and of the Everest Air (its Turbo preset, 3 speeds + Turbo) is Turbo
  _speedLabel(p, n) {
    const turbo = p?.model === "ELEVA300X" || p?.model === "EVERESTAIR";
    return turbo && n === 4 && (p.speeds || 4) === 4 ? "Turbo" : String(n);
  }

  // a member's step as the group editor names it: Off, Sleep or its speed
  _stepLabel(p, step) {
    if (step === "off") return "Off";
    if (step === "sleep") return "Sleep";
    return step == null ? "—" : this._speedLabel(p, step);
  }

  // what a member does right now: Off, Manual · 3, Auto, Offline
  _memberState(entityId, member) {
    if (this._offline(entityId)) return "Offline";
    if (member?.paused_until) return `Changed by hand · until ${this._time(member.paused_until)}`;
    const st = this._hass.states[entityId];
    if (st.state !== "on") return "Off";
    const preset = st.attributes.preset_mode;
    if ((st.attributes.preset_modes || []).length && preset && preset !== "Manual") return preset;
    const step = Number(st.attributes.percentage_step) || 25;
    const n = Math.round((Number(st.attributes.percentage) || 0) / step);
    return `Manual · ${this._speedLabel(this._purifier(entityId), n)}`;
  }

  _levelBars(level, max) {
    const bars = Array.from({ length: max }, (_, i) => `<i${i < level ? ' class="f"' : ""}></i>`).join("");
    return `<span class="lvl" role="img" aria-label="${
      level ? `Level ${level} of ${max}` : "Not controlling"
    }">${bars}</span>`;
  }

  // what the backend takes: the config without its state; sensors picked from
  // the members are picked again there, so only the user's own are sent
  _groupPayload(g) {
    const { state, entities, ...rest } = g;
    return { ...rest, sensors: (rest.sensors || []).filter((s) => s.source === "manual") };
  }

  // change a group's settings: one field, or several as an object
  async _setGroup(id, field, value) {
    const g = (this._groups?.groups || []).find((x) => x.id === id);
    if (!g) return;
    const changes = typeof field === "object" ? field : { [field]: value };
    try {
      await this._hass.callWS({
        type: "levoit_esphome/groups/save",
        group: { ...this._groupPayload(g), ...changes },
      });
    } catch (err) {
      this._toast(`${g.name}: ${err.message || err}`);
    }
  }

  async _dismissArea(areaId) {
    try {
      await this._hass.callWS({ type: "levoit_esphome/groups/dismiss", area_id: areaId });
    } catch (err) {
      this._toast(`${err.message || err}`);
    }
  }

  _groupsView() {
    if (this._groupsError)
      return `<div class="card empty"><p class="bad">${esc(this._groupsError)}</p>
        <button class="btn" data-action="groups-retry">Try again</button></div>`;
    if (!this._groups) return `<div class="card empty"><span class="spinner"></span> Loading…</div>`;
    const { groups, purifiers } = this._groups;
    const head = `<div class="page-head">
        <span class="muted grp-intro">A group watches shared air sensors and sets the speed of all its purifiers together. Each purifier can be in one group.</span>
        <span class="spacer"></span>
        <button class="btn primary" data-action="navigate" data-path="${esc(this._groupsPath("new"))}" ${
          purifiers.length < 2 ? "disabled" : ""
        }>${icon("plus")}New group</button>
      </div>`;
    const body = groups.length
      ? `<div class="groups">${groups.map((g) => this._groupCard(g)).join("")}</div>`
      : `<div class="card empty">
          <div class="big-icon">${icon("purifier")}</div>
          <p>No purifier groups yet.</p>
          <p class="muted">${
            purifiers.length < 2
              ? "A group needs at least 2 purifiers with this integration."
              : "Put purifiers that share a room in a group: the worst air sensor sets the speed of all of them."
          }</p>
        </div>`;
    return `${head}${body}${this._suggestions()}`;
  }

  // the group the purifier with this fan entity is in
  _groupOf(fanEntity) {
    const p = fanEntity ? this._purifier(fanEntity) : null;
    return p?.group_id ? (this._groups?.groups || []).find((g) => g.id === p.group_id) || null : null;
  }

  _groupPill(g) {
    const st = g.state || {};
    const level = st.level || 0;
    const [kind, text] = !g.enabled
      ? ["paused", "Paused"]
      : g.mode === "manual"
        ? ["act", `Manual · level ${level} of 4`]
        : level > 0
          ? ["act", `Auto · level ${level} of 4`]
          : st.status === "no_sensors"
            ? ["warn", "No sensor values"]
            : ["watch", "Auto · watching"];
    return `<span class="pill ${kind}"><i></i>${esc(text)}</span>`;
  }

  _groupReason(g) {
    const st = g.state || {};
    if (!g.enabled) return "Group control is off · purifiers are left alone";
    if (g.mode === "manual") return "All purifiers follow the speed you set";
    if ((st.level || 0) > 0) return st.reason || "";
    if (st.status === "no_sensors")
      return g.sensors.length ? "None of its sensors has a value right now" : "No air sensors: add one in the editor";
    return "Waiting for sensor values · purifiers run on their own";
  }

  // Devices card: the group the purifier is in, tinted while the group runs it
  _groupChip(d) {
    const g = this._groupOf(d.controls?.["fan.fan"]);
    if (!g) return "";
    const active = g.enabled && (g.state?.level || 0) > 0;
    const path = this._groupsPath(encodeURIComponent(g.id));
    return `<button class="chip group-chip${active ? " act" : ""}" data-action="navigate" data-path="${esc(
      path,
    )}" title="${esc(`Purifier group ${g.name}${active ? ": in control" : ""}`)}">${icon("group")}${esc(g.name)}</button>`;
  }

  // device page: which group runs this purifier, and what a change here does
  _groupBanner() {
    const fan = this._page?.controls?.["fan.fan"];
    const g = this._groupOf(fan);
    if (!g) return "";
    const member = (g.state?.members || []).find((m) => m.entity_id === fan);
    const note = !g.enabled
      ? ""
      : member?.paused_until
        ? `Changed by hand: the group leaves this purifier alone until ${this._time(member.paused_until)}.`
        : g.respect_manual
          ? `Changing mode or speed here pauses the group for this purifier for ${g.manual_pause_min} minutes.`
          : "The group sets mode and speed again after a change here.";
    const path = this._groupsPath(encodeURIComponent(g.id));
    return `<div class="card group-banner">
      <span class="gb-icon">${icon("group")}</span>
      <div class="gb-text">
        <div class="gb-title"><span>In the group <b>${esc(g.name)}</b></span>${this._groupPill(g)}</div>
        <div class="gb-reason">${esc(this._groupReason(g))}</div>
        ${note ? `<div class="hint">${esc(note)}</div>` : ""}
      </div>
      <button class="btn" data-action="navigate" data-path="${esc(path)}">Open group</button>
    </div>`;
  }

  _groupCard(g) {
    const st = g.state || {};
    const on = g.enabled;
    const manual = g.mode === "manual";
    const level = st.level || 0;
    const active = on && level > 0;
    const max = GROUP_LEVELS.length;
    const id = esc(g.id);
    const dis = on ? "" : "disabled";
    const seg = (field, value, label, current) =>
      `<button class="seg sm${current ? " on" : ""}" aria-pressed="${current}" ${dis} data-action="group-set" data-id="${id}" data-field="${field}" data-value="${value}">${esc(
        label,
      )}</button>`;
    const modes = [
      ["auto", "Auto"],
      ["manual", "Manual"],
    ]
      .map(([k, l]) => seg("mode", k, l, g.mode === k))
      .join("");
    const speeds = manual
      ? `<div class="segs" role="group" aria-label="Speed for ${esc(g.name)}">${Array.from({ length: max }, (_, i) =>
          seg("manual_level", i + 1, String(i + 1), g.manual_level === i + 1),
        ).join("")}</div>`
      : `<span class="hint">Speed follows the sensors</span>`;
    const members = (st.members || g.members.map((m) => ({ entity_id: m })))
      .map((m) => {
        const p = this._purifier(m.entity_id);
        return `<div class="gc-member"><span class="gc-mname">${esc(p?.title || m.entity_id)}</span><span class="${
          m.in_control && on ? "accent" : "muted"
        }">${esc(this._memberState(m.entity_id, m))}</span></div>`;
      })
      .join("");
    const counts = {};
    for (const s of g.sensors) counts[s.type] = (counts[s.type] || 0) + 1;
    const chips = SENSOR_TYPES.filter((t) => counts[t])
      .map((t) => `<span class="chip">${esc(SENSOR_TYPE_INFO[t].label)} ×${counts[t]}</span>`)
      .join("");
    const path = this._groupsPath(encodeURIComponent(g.id));
    const area = this._areaName(g.area_id);
    return `<div class="card gcard">
      <div class="gc-head">
        <div class="gc-title">
          <a class="gc-name" href="${esc(path)}" data-action="navigate" data-path="${esc(path)}">${esc(g.name)}</a>
          <div class="hint">${g.members.length} purifiers${area ? ` · ${esc(area)}` : ""}</div>
        </div>
        <button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" aria-label="Group control for ${esc(
          g.name,
        )}" data-action="group-set" data-id="${id}" data-field="enabled" data-value="${!on}"><span></span></button>
      </div>
      <div class="gc-status">
        <div>${this._groupPill(g)}<div class="gc-reason">${esc(this._groupReason(g))}</div></div>
        ${this._levelBars(active ? level : 0, max)}
      </div>
      <div class="gc-mode"><div class="segs" role="group" aria-label="Mode for ${esc(g.name)}">${modes}</div>${speeds}</div>
      <div class="gc-members">${members}</div>
      <div class="gc-foot">${chips}<button class="btn text" data-action="navigate" data-path="${esc(
        this._groupsPath(`${encodeURIComponent(g.id)}/edit`),
      )}">Edit</button></div>
    </div>`;
  }

  // rooms with 2 or more purifiers in no group
  _suggestions() {
    const dismissed = new Set(this._groups.dismissed_areas || []);
    const byArea = {};
    for (const p of this._groups.purifiers)
      if (p.area_id && !p.group_id && !dismissed.has(p.area_id)) (byArea[p.area_id] ||= []).push(p);
    const cards = Object.entries(byArea)
      .filter(([, list]) => list.length >= 2)
      .map(
        ([area, list]) => `<div class="sug">
          ${icon("home")}
          <div class="sug-text">
            <div class="sug-name">${esc(this._areaName(area) || area)}</div>
            <div class="hint">${esc(
              list.map((p) => p.title + (this._offline(p.entity_id) ? " (offline)" : "")).join(", "),
            )}</div>
          </div>
          <button class="btn text" data-action="sug-dismiss" data-area="${esc(area)}">Dismiss</button>
          <button class="btn" data-action="navigate" data-path="${esc(
            this._groupsPath(`new/${encodeURIComponent(area)}`),
          )}">Create group</button>
        </div>`,
      )
      .join("");
    if (!cards) return "";
    return `<div class="sug-wrap">
      <h2>Suggested from your rooms</h2>
      <div class="hint">Rooms in Home Assistant with 2 or more purifiers that aren't in a group yet.</div>
      ${cards}
    </div>`;
  }

  // --- group page ------------------------------------------------------------------

  _detailGroup() {
    return (this._groups?.groups || []).find((g) => g.id === this._detailId) || null;
  }

  // a sensor's name: the purifier it belongs to, else its own
  _sensorOwner(entityId) {
    const owner = (this._groups?.purifiers || []).find((p) => p.sensors.some((s) => s.entity_id === entityId));
    return owner ? owner.title : this._hass?.states?.[entityId]?.attributes?.friendly_name || entityId;
  }

  _groupDetail() {
    if (this._groupsError)
      return `<div class="card empty"><p class="bad">${esc(this._groupsError)}</p>
        <button class="btn" data-action="groups-retry">Try again</button></div>`;
    if (!this._groups) return `<div class="card empty"><span class="spinner"></span> Loading…</div>`;
    const g = this._detailGroup();
    if (!g)
      return `<div class="card empty"><p>This group no longer exists.</p>
        <button class="btn" data-action="navigate" data-path="${esc(this._groupsPath())}">All groups</button></div>`;
    if (!this._history && !this._historyLoading && !this._historyError && this._historySeries().length)
      Promise.resolve().then(() => this._loadHistory());
    const st = g.state || {};
    const on = g.enabled;
    const manual = g.mode === "manual";
    const level = st.level || 0;
    const id = esc(g.id);
    const dis = on ? "" : "disabled";

    // power, mode and level
    const modes = [
      ["auto", "Auto"],
      ["manual", "Manual"],
    ]
      .map(
        ([k, l]) =>
          `<button class="seg${on && g.mode === k ? " on" : ""}" aria-pressed="${on && g.mode === k}" ${dis} data-action="group-set" data-id="${id}" data-field="mode" data-value="${k}">${l}</button>`,
      )
      .join("");
    const levels = GROUP_LEVELS.map((n) => {
      const current = on && (manual ? g.manual_level === n : level === n);
      return `<button class="seg${current ? " on" : ""}" aria-pressed="${current}" ${dis} aria-label="Level ${n}" title="Run every purifier at level ${n} (Manual)" data-action="group-level" data-id="${id}" data-value="${n}">${n}</button>`;
    }).join("");
    const title = !on
      ? "Off"
      : manual
        ? `Manual · Level ${g.manual_level}`
        : level
          ? `Auto · Level ${level}`
          : "Auto · not controlling";
    const sub = !on
      ? "Group control is off · purifiers are left alone"
      : manual
        ? "All purifiers follow this level"
        : level
          ? `${AQI_WORDS[level]} · ${st.reason || ""}`
          : this._groupReason(g);

    // tiles: the combined value of each sensor type, and the total CADR
    const values = st.values || {};
    const cap = (text) => text.charAt(0).toUpperCase() + text.slice(1);
    const tiles = SENSOR_TYPES.filter((t) => values[t]).map((t) => {
      const v = values[t];
      const n = v.sensors.length;
      return {
        label: SENSOR_TYPE_INFO[t].label,
        value: t === "aqi" ? formatNumber(Math.round(v.value * 10) / 10) : formatNumber(Math.round(v.value)),
        unit: t === "aqi" ? AQI_WORDS[v.level] : "µg/m³",
        note: n > 1 ? `${cap(COMBINE_WORDS[v.how] || "highest")} of ${n}` : this._sensorOwner(v.sensors[0]),
        dot: `q${v.level}`,
      };
    });
    if (st.cadr?.sensors?.length)
      tiles.push({
        label: "CADR now",
        value: st.cadr.value == null ? "—" : formatNumber(Math.round(st.cadr.value)),
        unit: "m³/h",
        note: `Total of ${st.cadr.sensors.length}`,
        dot: "cadr",
      });
    const tileHtml = tiles.length
      ? `<div class="gd-tiles">${tiles
          .map(
            (t) => `<div class="gd-tile"><div class="gd-tl">${esc(t.label)}</div>
              <div class="gd-tv"><b>${esc(t.value)}</b><span>${esc(t.unit || "")}</span></div>
              <div class="gd-tn"><i class="gd-dot ${t.dot}"></i>${esc(t.note)}</div></div>`,
          )
          .join("")}</div>`
      : `<div class="hint">No sensor values yet</div>`;
    const controls = `<div class="card gd-controls">
      <div class="gd-main">
        <button class="gd-power${on ? " on" : ""}" role="switch" aria-checked="${on}" aria-label="Group control" data-action="group-set" data-id="${id}" data-field="enabled" data-value="${!on}">${icon(
          "power",
        )}</button>
        <div class="gd-state">
          <div class="gd-title"><span>${esc(title)}</span></div>
          <div class="hint">${esc(sub)}</div>
          <div class="gd-segs"><div class="segs" role="group" aria-label="Group mode">${modes}</div>
            <div class="segs" role="group" aria-label="Group level">${levels}</div></div>
        </div>
      </div>
      ${tileHtml}
    </div>`;

    // history of the group's own sensors
    const history = this._historyCard();
    const historyNote = history
      ? `<div class="hint gd-note">Values are the group's combined readings, as set per sensor type in the editor; CADR is the total of its purifiers (right axis); the strip shows the group's level.</div>`
      : "";

    // the purifiers
    const levelOf = st.air_quality_levels || {};
    let online = 0;
    let running = 0;
    const rows = g.members
      .map((m) => {
        const p = this._purifier(m);
        const d = p ? this._device(p.name) : null;
        const member = (st.members || []).find((x) => x.entity_id === m);
        const offline = this._offline(m);
        const isOn = this._hass?.states?.[m]?.state === "on";
        if (!offline) online += 1;
        if (isOn) running += 1;
        const pill = offline ? "warn" : on && member?.in_control ? "act" : isOn ? "watch" : "paused";
        const chips = (p?.sensors || [])
          .map((s) => {
            const lvl = levelOf[s.entity_id];
            return `<span class="chip gd-chip"><i class="gd-dot${lvl ? ` q${lvl}` : ""}"></i>${esc(
              SENSOR_TYPE_INFO[s.type]?.label || s.type,
            )} <b>${esc(this._sensorValue(s.entity_id, s.type))}</b></span>`;
          })
          .join("");
        const name = p?.title || m;
        const link = p?.name
          ? `<a class="gd-name" href="${esc(this._devicePath(p.name))}" data-action="navigate" data-path="${esc(
              this._devicePath(p.name),
            )}">${esc(name)}</a>`
          : `<span class="gd-name">${esc(name)}</span>`;
        return `<div class="gd-row">
          <span class="dev-tile">${deviceImage(p?.model)}</span>
          <div class="gd-who">${link}<div class="gd-meta"><span class="pill ${pill}"><i></i>${esc(
            this._memberState(m, member),
          )}</span><span class="hint">${esc(p?.model || "")}</span></div></div>
          <div class="gd-chips">${chips}</div>
          <div class="gd-filter">${d ? this._filter(d) : ""}</div>
        </div>`;
      })
      .join("");
    const purifiers = `<div class="card gd-card gd-wide">
      <div class="gd-head"><h2>Purifiers</h2><span class="hint">${online} online · ${running} running</span></div>
      ${rows}
    </div>`;

    // sensors added in the editor, not part of a purifier
    const extra = g.sensors.filter((s) => s.source === "manual");
    const extras = extra.length
      ? `<div class="card gd-card gd-side">
          <div class="gd-head"><div><h2>Additional sensors</h2><div class="hint">Not part of a purifier, added in the editor</div></div></div>
          ${extra
            .map((s) => {
              const lvl = levelOf[s.entity_id];
              return `<div class="gd-xrow"><div class="gd-who"><div>${esc(
                this._hass?.states?.[s.entity_id]?.attributes?.friendly_name || s.entity_id,
              )}</div><div class="mono-id">${esc(s.entity_id)}</div></div>
              <span class="chip gd-chip"><i class="gd-dot${lvl ? ` q${lvl}` : ""}"></i>${esc(
                SENSOR_TYPE_INFO[s.type]?.label || s.type,
              )} <b>${esc(this._sensorValue(s.entity_id, s.type))}</b></span></div>`;
            })
            .join("")}
        </div>`
      : "";
    return `<div class="gd">${controls}${history}${historyNote}<div class="gd-cols">${purifiers}${extras}</div></div>`;
  }

  // --- group editor ----------------------------------------------------------------

  // the draft for the route's group, once the groups are in
  _ensureEdit() {
    if (this._edit || !this._groups) return;
    const key = this._groupKey || "new";
    let draft;
    if (key === "new" || key.startsWith("new/")) {
      const area = key.slice(4) || null;
      draft = JSON.parse(JSON.stringify(GROUP_DEFAULTS));
      if (area) {
        draft.area_id = area;
        draft.name = this._areaName(area);
        draft.members = this._groups.purifiers
          .filter((p) => p.area_id === area && !p.group_id)
          .map((p) => p.entity_id);
      }
    } else {
      const g = this._groups.groups.find((x) => x.id === key);
      if (!g) {
        this._edit = { missing: true };
        return;
      }
      const { state, entities, ...rest } = g;
      draft = JSON.parse(JSON.stringify(rest));
    }
    this._edit = { draft, addOpen: false, saving: false, preview: null, previewError: null, previewSeq: 0 };
    this._schedulePreview(0);
  }

  _setPath(obj, path, value) {
    const keys = path.split(".");
    let at = obj;
    for (const k of keys.slice(0, -1)) at = at[k];
    at[keys[keys.length - 1]] = value;
  }

  _setDraft(field, value) {
    const d = this._edit.draft;
    this._setPath(d, field, value);
    if (field === "area_id" && !d.name.trim()) d.name = this._areaName(value);
    this._schedulePreview();
    this._render();
  }

  // members that can be saved: not in another group
  _draftMembers() {
    const d = this._edit.draft;
    return d.members.filter((m) => {
      const p = this._purifier(m);
      return p && (!p.group_id || p.group_id === d.id);
    });
  }

  // the sensors as the backend will pick them: the members' (minus removed
  // ones), then the user's own
  _draftSensors() {
    const d = this._edit.draft;
    const removed = new Set(d.removed_sensors);
    const out = [];
    const seen = new Set();
    for (const m of this._draftMembers()) {
      const p = this._purifier(m);
      for (const s of p.sensors) {
        if (removed.has(s.entity_id) || seen.has(s.entity_id)) continue;
        seen.add(s.entity_id);
        out.push({ ...s, source: "auto", label: p.title });
      }
    }
    for (const s of d.sensors) {
      if (s.source !== "manual" || seen.has(s.entity_id)) continue;
      seen.add(s.entity_id);
      const st = this._hass?.states?.[s.entity_id];
      out.push({ ...s, label: st?.attributes?.friendly_name || s.entity_id });
    }
    return out;
  }

  _sensorValue(entityId, type) {
    const st = this._hass?.states?.[entityId];
    if (!this._usable(st)) return "offline";
    const v = parseFloat(st.state);
    if (!Number.isFinite(v)) return st.state;
    if (type === "aqi") return AQI_WORDS[aqiLevel(v)] || formatNumber(Math.round(v));
    const unit = st.attributes.unit_of_measurement;
    return `${formatNumber(Math.round(v))}${unit ? ` ${unit}` : ""}`;
  }

  _thresholdError() {
    const t = this._edit.draft.thresholds;
    const bad = THRESHOLD_TYPES.find((k) => t[k].some((v, i) => !Number.isFinite(v) || (i && v < t[k][i - 1])));
    return bad ? `${SENSOR_TYPE_INFO[bad].label}: each level must start at or above the one before` : "";
  }

  // the thresholds of a type with handle i moved to slider position u (0-1),
  // kept between its neighbours
  _thAt(type, i, u) {
    const values = [...this._edit.draft.thresholds[type]];
    const low = i ? values[i - 1] + 1 : 1;
    const high = i < values.length - 1 ? values[i + 1] - 1 : TH_MAX;
    values[i] = Math.max(low, Math.min(high, thValue(u)));
    return values;
  }

  _draftPayload() {
    const d = this._edit.draft;
    return {
      ...d,
      id: d.id || undefined,
      members: this._draftMembers(),
      sensors: d.sensors.filter((s) => s.source === "manual"),
    };
  }

  _schedulePreview(delay = 250) {
    clearTimeout(this._previewTimer);
    this._previewTimer = setTimeout(() => this._loadPreview(), delay);
  }

  async _loadPreview() {
    const e = this._edit;
    if (!e || e.missing || !this._hass || this._view !== "group") return;
    const seq = ++e.previewSeq;
    try {
      const result = await this._hass.callWS({
        type: "levoit_esphome/groups/preview",
        group: this._draftPayload(),
      });
      if (this._edit !== e || e.previewSeq !== seq) return;
      e.preview = result;
      e.previewError = null;
    } catch (err) {
      if (this._edit !== e || e.previewSeq !== seq) return;
      e.previewError = err?.message || String(err);
    }
    this._render();
  }

  async _saveEdit() {
    const e = this._edit;
    if (!e?.draft || e.saving) return;
    const d = e.draft;
    if (!d.name.trim()) {
      this._toast("Give the group a name");
      return;
    }
    e.saving = true;
    this._render();
    try {
      await this._hass.callWS({ type: "levoit_esphome/groups/save", group: this._draftPayload() });
      this._toast(`${d.name.trim()} saved`);
      this._edit = null;
      this._navigate(this._groupsPath());
    } catch (err) {
      this._toast(`${err.message || err}`);
    } finally {
      e.saving = false;
      this._render();
    }
  }

  // the apply button: the saved group runs its settings now
  async _applyEdit() {
    const d = this._edit?.draft;
    if (!d?.id) return;
    try {
      await this._hass.callWS({ type: "levoit_esphome/groups/apply", group_id: d.id });
      this._toast(`${d.name.trim() || "Group"}: applied to the purifiers`);
    } catch (err) {
      this._toast(`${err.message || err}`);
    }
  }

  async _deleteEdit() {
    const d = this._edit?.draft;
    if (!d?.id) return;
    if (!confirm(`Delete the group ${d.name}?\n\nIts purifiers keep running as they are.`)) return;
    try {
      await this._hass.callWS({ type: "levoit_esphome/groups/delete", group_id: d.id });
      this._edit = null;
      this._navigate(this._groupsPath());
    } catch (err) {
      this._toast(`${err.message || err}`);
    }
  }

  _edSwitch(field, label) {
    const on = Boolean(field.split(".").reduce((o, k) => o?.[k], this._edit.draft));
    return `<button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" aria-label="${esc(
      label,
    )}" data-action="ed-set" data-field="${field}" data-value="${!on}"><span></span></button>`;
  }

  _edNumber(field, label, { min = 0, step = "1" } = {}) {
    const value = field.split(".").reduce((o, k) => o?.[k], this._edit.draft);
    return `<input class="num" type="number" min="${min}" step="${step}" value="${esc(value)}" data-ed-field="${field}" aria-label="${esc(
      label,
    )}">`;
  }

  _edSegs(field, options, current, label) {
    return `<div class="segs" role="group" aria-label="${esc(label)}">${options
      .map(
        ([value, text]) =>
          `<button class="seg${value === current ? " on" : ""}" aria-pressed="${value === current}" data-action="ed-set" data-field="${field}" data-value="${value}">${esc(
            text,
          )}</button>`,
      )
      .join("")}</div>`;
  }

  _groupEditor() {
    if (this._groupsError)
      return `<div class="card empty"><p class="bad">${esc(this._groupsError)}</p>
        <button class="btn" data-action="groups-retry">Try again</button></div>`;
    if (!this._groups) return `<div class="card empty"><span class="spinner"></span> Loading…</div>`;
    this._ensureEdit();
    const e = this._edit;
    if (e.missing)
      return `<div class="card empty"><p>This group no longer exists.</p>
        <button class="btn" data-action="navigate" data-path="${esc(this._groupsPath())}">All groups</button></div>`;
    const d = e.draft;
    const manual = d.mode === "manual";
    const autoOnly = manual ? `<span class="tag">Used in Auto only</span>` : "";
    const levels = GROUP_LEVELS;

    // General
    const areas = Object.values(this._hass?.areas || {}).sort((a, b) => a.name.localeCompare(b.name));
    const areaOptions = `<option value="">No room</option>${areas
      .map(
        (a) =>
          `<option value="${esc(a.area_id)}"${a.area_id === d.area_id ? " selected" : ""}>${esc(a.name)}</option>`,
      )
      .join("")}`;
    const general = `<div class="card section">
      <div class="sec-head"><h2>General</h2></div>
      <div class="ged-fields">
        <label class="field">Name<input class="inp" type="text" data-ed-field="name" value="${esc(d.name)}" placeholder="Living room"></label>
        <label class="field">Room (Home Assistant area)<select class="inp" data-ed-field="area_id">${areaOptions}</select></label>
      </div>
      ${this._setting(
        "Mode",
        manual ? "You pick one speed; every purifier follows it" : "The sensors pick the speed",
        `<div class="ged-modes">${this._edSegs(
          "mode",
          [
            ["auto", "Auto"],
            ["manual", "Manual"],
          ],
          d.mode,
          "Group mode",
        )}${
          manual
            ? this._edSegs(
                "manual_level",
                levels.map((n) => [n, String(n)]),
                d.manual_level,
                "Group speed",
              )
            : ""
        }</div>`,
      )}
      ${this._setting("Group control", "When off, the purifiers are left alone", this._edSwitch("enabled", "Group control"))}
    </div>`;

    // Purifiers
    const chosen = new Set(this._draftMembers());
    const rows = this._groups.purifiers
      .map((p) => {
        const other = p.group_id && p.group_id !== d.id;
        const tags = [];
        if (other)
          tags.push(["", `In ${this._groups.groups.find((g) => g.id === p.group_id)?.name || "a group"}`]);
        else if (d.area_id && p.area_id === d.area_id) tags.push(["sug", "In this room"]);
        else if (p.area_id) tags.push(["", this._areaName(p.area_id)]);
        if (this._offline(p.entity_id)) tags.push(["err", "Offline"]);
        const sub = `${p.model || "Levoit"} · ${p.speeds} speeds${p.sensors.length ? "" : " · no air sensor"}`;
        return `<label class="mem${other ? " dis" : ""}">
          <input type="checkbox" data-member="${esc(p.entity_id)}" ${chosen.has(p.entity_id) ? "checked" : ""} ${
            other ? "disabled" : ""
          } aria-label="${esc(p.title)}">
          <span class="dev-tile">${deviceImage(p.model)}</span>
          <span class="mem-text"><span class="mem-name">${esc(p.title)}</span><span class="hint">${esc(sub)}</span></span>
          <span class="tags">${tags
            .filter(([, label]) => label)
            .map(([kind, label]) => `<span class="tag ${kind}">${esc(label)}</span>`)
            .join("")}</span>
        </label>`;
      })
      .join("");
    const count = chosen.size;
    const purifiers = `<div class="card section">
      <div class="sec-head"><div><h2>Purifiers</h2><div class="hint">Purifiers in ${esc(
        this._areaName(d.area_id) || "the group's room",
      )} are suggested; you can add any purifier.</div></div>
        <span class="tag ${count < 2 ? "err" : "sug"}">${count} selected${count < 2 ? " · pick at least 2" : ""}</span></div>
      ${rows}
      <div class="mem dis"><input type="checkbox" disabled aria-label="Other fans"><span class="dev-tile">${icon(
        "fan",
      )}</span><span class="mem-text"><span class="mem-name">Other fans</span><span class="hint">Any Home Assistant fan entity</span></span><span class="tags"><span class="tag">Coming later</span></span></div>
    </div>`;

    // Air quality sensors
    const shown = this._draftSensors();
    const shownIds = new Set(shown.map((s) => s.entity_id));
    const typeRows = SENSOR_TYPES.map((t) => {
      const chips = shown
        .filter((s) => s.type === t)
        .map(
          (s) => `<span class="schip"><span>${esc(s.label)}</span><b>${esc(this._sensorValue(s.entity_id, t))}</b>
            <button data-action="ed-remove-sensor" data-entity="${esc(s.entity_id)}" aria-label="Remove ${esc(
              s.label,
            )} ${esc(SENSOR_TYPE_INFO[t].label)}">${icon("close")}</button></span>`,
        )
        .join("");
      const several = shown.filter((s) => s.type === t).length > 1;
      const how = d.combine?.[t] || "max";
      const combine = several
        ? `<label class="combine"><span class="hint">Combine</span><select class="inp sm" data-combine="${t}" aria-label="Combine the ${esc(
            SENSOR_TYPE_INFO[t].label,
          )} sensors">${COMBINE_OPTIONS.map(
            ([value, label]) => `<option value="${value}"${value === how ? " selected" : ""}>${label}</option>`,
          ).join("")}</select></label>`
        : "";
      return `<div class="stype"><div class="stype-label">${esc(SENSOR_TYPE_INFO[t].label)}<div class="hint">${esc(
        SENSOR_TYPE_INFO[t].unit,
      )}</div></div><div class="stype-chips">${chips || `<span class="hint">None: this type is not used</span>`}</div>${combine}</div>`;
    }).join("");
    const removed = [];
    const removedIds = new Set(d.removed_sensors);
    const knownTypes = {};
    for (const p of this._groups.purifiers) for (const s of p.sensors) knownTypes[s.entity_id] = s.type;
    for (const m of this._draftMembers()) {
      const p = this._purifier(m);
      for (const s of p.sensors) if (removedIds.has(s.entity_id)) removed.push({ ...s, label: p.title });
    }
    const extras = Object.values(this._hass?.states || {})
      .filter((st) => {
        const dc = st.attributes.device_class;
        return (
          st.entity_id.startsWith("sensor.") &&
          (dc === "pm1" || dc === "pm25" || dc === "pm10" || knownTypes[st.entity_id]) &&
          !shownIds.has(st.entity_id) &&
          !removedIds.has(st.entity_id)
        );
      })
      .map((st) => ({
        entity_id: st.entity_id,
        type: knownTypes[st.entity_id] || st.attributes.device_class,
        label: st.attributes.friendly_name || st.entity_id,
      }))
      .sort((a, b) => a.label.localeCompare(b.label))
      .slice(0, 40);
    const menu = e.addOpen
      ? `<div class="menu" role="menu">${
          removed.length
            ? `<div class="mh">From this group's purifiers</div>${removed
                .map(
                  (s) =>
                    `<button role="menuitem" data-action="ed-restore-sensor" data-entity="${esc(s.entity_id)}"><span>${esc(
                      s.label,
                    )} · ${esc(SENSOR_TYPE_INFO[s.type].label)}</span><span class="hint">${esc(
                      this._sensorValue(s.entity_id, s.type),
                    )}</span></button>`,
                )
                .join("")}`
            : ""
        }<div class="mh">Other Home Assistant sensors</div>${
          extras.length
            ? extras
                .map(
                  (x) =>
                    `<button role="menuitem" data-action="ed-add-sensor" data-entity="${esc(x.entity_id)}" data-type="${x.type}"><span>${esc(
                      x.label,
                    )} · ${esc(SENSOR_TYPE_INFO[x.type].label)}</span><span class="mono-id">${esc(x.entity_id)}</span></button>`,
                )
                .join("")
            : `<div class="hint menu-empty">No other PM1, PM2.5 or PM10 sensors</div>`
        }</div>`
      : "";
    const sensors = `<div class="card section">
      <div class="sec-head"><div><h2>Air quality sensors${autoOnly}</h2><div class="hint">Picked from the purifiers above. With several sensors of one type, pick how they are combined; the worst type decides the group's level.</div></div></div>
      ${typeRows}
      <div class="add-wrap"><button class="btn" data-action="ed-add-toggle" aria-haspopup="menu" aria-expanded="${e.addOpen}">${icon(
        "plus",
      )}Add sensor</button>${menu}</div>
    </div>`;

    // Speeds: each purifier's lowest and highest step, and its step per level
    const members = [...chosen].map((m) => this._purifier(m)).filter(Boolean);
    const ranges = d.member_speeds || {};
    const now = d.enabled && e.preview ? e.preview.level || 0 : 0;
    const mapRows = members
      .map((p) => {
        const rng = ranges[p.entity_id] || {};
        const { ladder, low, high } = memberRange(p, rng);
        const li = ladder.indexOf(low);
        const hi = ladder.indexOf(high);
        const option = (step, current) =>
          `<option value="${step}"${step === current ? " selected" : ""}>${esc(this._stepLabel(p, step))}</option>`;
        const lows = ladder.filter((_, i) => i < hi || i === li).map((s) => option(s, low));
        const highs = ladder
          .filter((s, i) => typeof s === "number" && (i > li || i === hi))
          .map((s) => option(s, high));
        return `<div class="gl"><span class="mem-name">${esc(p.title)}</span><span class="hint">${p.speeds} speeds${
          p.sleep ? " + Sleep" : ""
        }</span></div>
          <div><select class="inp sm" data-member-lo="${esc(p.entity_id)}" aria-label="Lowest step of ${esc(
            p.title,
          )}">${lows.join("")}</select></div>
          <div><select class="inp sm" data-member-hi="${esc(p.entity_id)}" aria-label="Highest speed of ${esc(
            p.title,
          )}">${highs.join("")}</select></div>
          ${levels
            .map((l) => `<div class="${l === now ? "cur" : ""}">${esc(this._stepLabel(p, memberStep(l, p, rng)))}</div>`)
            .join("")}`;
      })
      .join("");
    const speed = `<div class="card section">
      <div class="sec-head"><div><h2>Speeds</h2><div class="hint">The group works in 4 levels; each purifier spreads them over its own speeds</div></div>
        ${now ? `<span class="tag sug">Now: level ${now} · ${esc(AQI_WORDS[now])}</span>` : ""}</div>
      ${
        members.length
          ? `<div class="tbl-scroll"><div class="grid-tbl speeds" style="--cols:6"><div class="gh gl">Purifier</div><div class="gh">Lowest</div><div class="gh">Highest</div>${levels
              .map(
                (l) =>
                  `<div class="gh lvh${l === now ? " cur" : ""}">Level ${l}<span>${esc(AQI_WORDS[l])}</span></div>`,
              )
              .join("")}${mapRows}</div></div>`
          : ""
      }
      <div class="hint pad">Pick what each purifier runs at in very good air (Off, Sleep or a speed) and its highest speed; the levels in between are spread across that range.</div>
    </div>`;

    // When to step in
    const thError = this._thresholdError();
    const pos = (v) => `calc(10px + (100% - 20px) * ${thFrac(v).toFixed(4)})`;
    const pct = (v) => `${(thFrac(v) * 100).toFixed(2)}%`;
    const ticks = [0, 10, 25, 50, 100, 250, 500]
      .map((v) => `<span class="mt" style="left: ${pos(v)}">${v}</span>`)
      .join("");
    const thRows = THRESHOLD_TYPES.map((t) => {
      const th = d.thresholds[t];
      const label = SENSOR_TYPE_INFO[t].label;
      const track = `linear-gradient(90deg, var(--lv-q1) 0 ${pct(th[0])}, var(--lv-q2) ${pct(th[0])} ${pct(
        th[1],
      )}, var(--lv-q3) ${pct(th[1])} ${pct(th[2])}, var(--lv-q4) ${pct(th[2])} 100%)`;
      const handles = th
        .map(
          (v, i) =>
            `<span class="mv" data-th-label="${i}" style="left: ${pos(v)}">${esc(formatNumber(v))}</span>
            <input type="range" min="0" max="1000" step="1" value="${Math.round(thFrac(v) * 1000)}" data-th="${t}.${i}" aria-label="${esc(
              label,
            )}: level ${i + 2} starts at" aria-valuetext="${esc(formatNumber(v))} µg/m³">`,
        )
        .join("");
      return `<div class="th-row"><div class="stype-label">${esc(label)}<div class="hint">µg/m³</div></div>
        <div class="ms"><div class="trk" style="background: ${track}"></div>${handles}${ticks}</div></div>`;
    }).join("");
    const legend = GROUP_LEVELS.map(
      (l) => `<span class="lg"><i class="q${l}"></i>${l} · ${esc(AQI_WORDS[l])}</span>`,
    ).join("");
    const aqiMap = GROUP_LEVELS.map((l) => `<span class="lmap q${l}">${l} → level ${l}</span>`).join("");
    const stepIn = `<div class="card section">
      <div class="sec-head"><div><h2>When to step in${autoOnly}</h2><div class="hint">Level 1 is the baseline (very good air). A reading at or above a value starts that level; the worst sensor type wins.</div></div></div>
      <div class="lgs">${legend}</div>
      ${thRows}
      <div class="th-row"><div class="stype-label">${esc(SENSOR_TYPE_INFO.aqi.label)}<div class="hint">${esc(
        SENSOR_TYPE_INFO.aqi.unit,
      )}</div></div><div class="lmaps">${aqiMap}</div></div>
      ${thError ? `<div class="err-line">${esc(thError)}</div>` : ""}
      <div class="rise">
        ${this._edSwitch("rise.enabled", "Rising fast rule")}
        <span>Rising fast: go straight to level 4 if PM2.5 climbs</span>
        ${this._edNumber("rise.pm25", "PM2.5 rise in µg/m³", { min: 1, step: "any" })}
        <span class="hint">µg/m³ within</span>
        ${this._edNumber("rise.window_min", "Rise window in minutes", { min: 1 })}
        <span class="hint">min</span>
      </div>
    </div>`;

    // When the air is clean again
    const clean = `<div class="card section">
      <div class="sec-head"><h2>When the air is clean again${autoOnly}</h2></div>
      ${this._setting(
        "Stay at a level for at least",
        "Then step down one level at a time",
        `<span class="num-unit">${this._edNumber("hold_min", "Minimum minutes per level")}<span class="hint">min</span></span>`,
      )}
      ${this._setting(
        "Turn purifiers on when needed",
        "Otherwise purifiers that are off stay off",
        this._edSwitch("turn_on", "Turn purifiers on when needed"),
      )}
      ${this._setting(
        "Respect manual changes",
        "If someone changes a purifier by hand, leave it alone for",
        `<span class="num-unit">${this._edNumber("manual_pause_min", "Pause minutes after a manual change", {
          min: 1,
        })}<span class="hint">min</span>${this._edSwitch("respect_manual", "Respect manual changes")}</span>`,
      )}
    </div>`;

    return `<div class="ged">
      <div class="ged-main">${general}${purifiers}${sensors}${speed}${stepIn}${clean}</div>
      <aside class="ged-aside" aria-label="Live preview">${this._rightNow()}
        <div class="hint now-note">The preview uses the current readings and updates as you change settings. Nothing is sent to the purifiers until you save. ▶ runs the saved settings now: the sensors' level without waiting for the hold time, also for purifiers changed by hand.</div>
      </aside>
    </div>`;
  }

  // the editor's live preview: what the group would do with these settings now
  _rightNow() {
    const e = this._edit;
    const d = e.draft;
    const p = e.preview;
    const manual = d.mode === "manual";
    if (e.previewError)
      return `<div class="card now"><div class="now-k">Right now</div><div class="now-reason bad">${esc(
        e.previewError,
      )}</div></div>`;
    if (!p)
      return `<div class="card now"><div class="now-k">Right now</div><div class="now-reason"><span class="spinner"></span> Working it out…</div></div>`;
    const level = p.level || 0;
    const usable = p.sensors.some((s) => s.value != null);
    const title = !d.enabled
      ? "Paused"
      : manual
        ? `Manual · level ${level} of 4`
        : level
          ? `Level ${level} · ${AQI_WORDS[level]}`
          : "Not controlling";
    const reason = !d.enabled
      ? "Group control is off."
      : manual
        ? "Every purifier runs at the group speed, whatever the sensors say."
        : level
          ? p.reason || ""
          : !p.sensors.length
            ? "No air sensors: the group never steps in."
            : usable
              ? ""
              : "No sensor has a value right now: the purifiers run on their own.";
    const members = p.members
      .map((m) => {
        const pur = this._purifier(m.entity_id);
        const target = this._offline(m.entity_id)
          ? "Offline · skipped"
          : !d.enabled
            ? "Left alone"
            : level === 0 || m.speed == null
              ? "Left as it is"
              : typeof m.speed === "number"
                ? `Manual · ${this._speedLabel(pur, m.speed)}`
                : this._stepLabel(pur, m.speed);
        return `<div class="now-row"><span>${esc(pur?.title || m.entity_id)}</span><b>${esc(target)}</b></div>`;
      })
      .join("");
    const sensors = p.sensors
      .map((s) => {
        const owner = (this._groups.purifiers || []).find((x) => x.sensors.some((y) => y.entity_id === s.entity_id));
        const name = owner ? owner.title : this._hass?.states?.[s.entity_id]?.attributes?.friendly_name || s.entity_id;
        const lvl = s.value == null ? "skipped" : `level ${s.level}`;
        return `<div class="now-row"><span>${esc(name)} ${esc(SENSOR_TYPE_INFO[s.type].label)}</span><span><b>${esc(
          s.value == null ? "—" : this._sensorValue(s.entity_id, s.type),
        )}</b> <span class="hint">→ ${esc(lvl)}</span></span></div>`;
      })
      .join("");
    // a type with several sensors: the one value they make
    const combined = (p.types || [])
      .filter((t) => t.sensors.length > 1)
      .map((t) => {
        const how = COMBINE_WORDS[d.combine?.[t.type] || "max"];
        const value =
          t.type === "aqi" ? AQI_WORDS[Math.round(t.value)] || formatNumber(t.value) : `${formatNumber(Math.round(t.value))} µg/m³`;
        return `<div class="now-row"><span>${esc(SENSOR_TYPE_INFO[t.type].label)} · ${esc(how)} of ${
          t.sensors.length
        }</span><span><b>${esc(value)}</b> <span class="hint">→ level ${t.level}</span></span></div>`;
      })
      .join("");
    const saved = (this._groups?.groups || []).find((g) => g.id === d.id);
    const canApply = Boolean(saved?.enabled);
    return `<div class="card now">
      <div class="now-head"><div class="now-k">Right now</div>
        <button class="play" data-action="ed-apply" ${canApply ? "" : "disabled"} aria-label="Apply the saved settings to the purifiers now" title="${
          saved ? (canApply ? "Apply the saved settings to the purifiers now" : "Group control is off") : "Save the group first"
        }">${icon("play")}</button></div>
      <div class="now-title"><span>${esc(title)}</span>${this._levelBars(d.enabled ? level : 0, 4)}</div>
      <div class="now-reason">${esc(reason)}</div>
      ${members ? `<div class="now-h">Purifiers</div>${members}` : ""}
      ${sensors ? `<div class="now-h">Sensors</div>${sensors}${combined}` : ""}
    </div>`;
  }

  // --- device page: control helpers -------------------------------------------
  // Each takes a controls key ("select.auto_mode", ...) and renders nothing when
  // the device has no such entity, so a section shows what the model has.

  _state(key) {
    const entityId = this._page?.controls?.[key];
    return entityId ? this._hass?.states?.[entityId] || null : null;
  }

  _usable(st) {
    return Boolean(st) && st.state !== "unavailable" && st.state !== "unknown";
  }

  _number(key) {
    const st = this._state(key);
    const value = st ? parseFloat(st.state) : NaN;
    return Number.isNaN(value) ? null : value;
  }

  // attributes for a button that calls a service on one entity
  _svc(domain, service, entityId, args, confirmText) {
    return `data-action="svc" data-domain="${domain}" data-service="${service}" data-entity="${esc(
      entityId,
    )}" data-args="${esc(JSON.stringify(args || {}))}"${
      confirmText ? ` data-confirm="${esc(confirmText)}"` : ""
    }`;
  }

  _setting(label, hint, control, dim) {
    return `<div class="setting${dim ? " dim" : ""}">
      <div class="s-label">${esc(label)}${hint ? `<div class="hint">${esc(hint)}</div>` : ""}</div>
      <div class="s-control">${control}</div>
    </div>`;
  }

  _toggle(key, label, hint, { dim = false } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const on = st.state === "on";
    const off = !this._usable(st) || dim;
    return this._setting(
      label,
      hint,
      `<button class="switch${on ? " on" : ""}" role="switch" aria-checked="${on}" aria-label="${esc(
        label,
      )}" ${off ? "disabled" : ""} ${this._svc("switch", on ? "turn_off" : "turn_on", st.entity_id)}><span></span></button>`,
      dim,
    );
  }

  _choices(key, label, hint, { dim = false, labels = {} } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const off = !this._usable(st) || dim;
    const buttons = (st.attributes.options || [])
      .map(
        (option) =>
          `<button class="seg${option === st.state ? " on" : ""}" ${off ? "disabled" : ""} ${this._svc(
            "select",
            "select_option",
            st.entity_id,
            { option },
          )}>${esc(labels[option] || option)}</button>`,
      )
      .join("");
    return this._setting(label, hint, `<div class="segs">${buttons}</div>`, dim);
  }

  // `also`: a second number entity set to the same value (see the room size)
  _slider(key, label, hint, { dim = false, unit, also } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const alsoEntity = also ? this._page?.controls?.[also] : null;
    const a = st.attributes;
    const value = parseFloat(st.state);
    const known = !Number.isNaN(value);
    const off = !this._usable(st) || dim;
    const shown = known ? `${formatNumber(value)}${(unit ?? a.unit_of_measurement) ? ` ${unit ?? a.unit_of_measurement}` : ""}` : "—";
    return this._setting(
      label,
      hint,
      `<div class="slider"><input type="range" min="${esc(a.min)}" max="${esc(a.max)}" step="${esc(
        a.step || 1,
      )}" value="${esc(known ? value : a.min)}" data-number="${esc(st.entity_id)}"${
        alsoEntity ? ` data-also="${esc(alsoEntity)}"` : ""
      } aria-label="${esc(
        label,
      )}" ${off ? "disabled" : ""}><span class="val">${esc(shown)}</span></div>`,
      dim,
    );
  }

  _stepper(key, label, hint, { dim = false, format } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const a = st.attributes;
    const value = parseFloat(st.state);
    const known = !Number.isNaN(value);
    const off = !this._usable(st) || dim || !known;
    const step = Number(a.step) || 1;
    const show = format || ((v) => `${formatNumber(v)}${a.unit_of_measurement ? ` ${a.unit_of_measurement}` : ""}`);
    const button = (delta, text) => {
      const next = Math.min(Number(a.max), Math.max(Number(a.min), value + delta));
      return `<button class="step" aria-label="${delta < 0 ? "Less" : "More"}" ${
        off || next === value ? "disabled" : ""
      } ${this._svc("number", "set_value", st.entity_id, { value: next })}>${text}</button>`;
    };
    return this._setting(
      label,
      hint,
      `<div class="stepper">${button(-step, "−")}<span class="val">${
        known ? esc(show(value)) : "—"
      }</span>${button(step, "+")}</div>`,
      dim,
    );
  }

  _readout(key, label, { unit, format } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const value = this._usable(st)
      ? format
        ? format(st.state)
        : `${st.state}${(unit ?? st.attributes.unit_of_measurement) ? ` ${unit ?? st.attributes.unit_of_measurement}` : ""}`
      : "—";
    return this._setting(label, "", `<span class="readout">${esc(value)}</span>`);
  }

  // a reading: whole numbers (a sensor's "783.0" is 783); `level`: the 1-4
  // air quality level, shown as a word beside it
  _tile(key, label, { level } = {}) {
    const st = this._state(key);
    if (!st) return "";
    const ok = this._usable(st);
    const number = parseFloat(st.state);
    const value = !ok ? "—" : Number.isFinite(number) ? formatNumber(Math.round(number)) : st.state;
    const unit = ok ? st.attributes.unit_of_measurement || "" : "";
    const badge = ok && level ? `<span class="aqi-badge q${level}">${esc(AQI_WORDS[level])}</span>` : "";
    return `<div class="tile"><div class="t-label">${esc(label)}</div><div class="t-val">${esc(value)}${
      unit ? `<span class="unit">${esc(unit)}</span>` : ""
    }${badge}</div></div>`;
  }

  // `action`: a button on the right of the heading (the timer's Cancel)
  _section(title, rows, hint, action = "") {
    const body = rows.filter(Boolean).join("");
    if (!body) return "";
    return `<div class="card section">
      <div class="sec-head"><div><h2>${esc(title)}</h2>${hint ? `<div class="hint">${esc(hint)}</div>` : ""}</div>${action}</div>
      ${body}
    </div>`;
  }

  _subhead(text) {
    return `<div class="subhead">${esc(text)}</div>`;
  }

  // --- device page: sections ---------------------------------------------------

  _devicePage() {
    if (this._pageError)
      return `<div class="card empty"><p class="bad">${esc(this._pageError)}</p>
        <button class="btn" data-action="page-retry">Try again</button></div>`;
    const page = this._page;
    if (!page) return `<div class="card empty"><span class="spinner"></span> Loading…</div>`;
    const haDevice = `/config/devices/device/${page.device_id}`;
    const haLink = `<button class="btn" data-action="navigate" data-path="${esc(haDevice)}">${icon(
      "open",
    )}<span>Home Assistant device page</span></button>`;
    if (!page.supported)
      return `<div class="card empty">
        <div class="big-icon">${icon("purifier")}</div>
        <p>${page.model ? `The ${esc(page.model)}` : "This device"} has no settings page here yet.</p>
        <p class="muted">Its settings are on the Home Assistant device page.</p>
        ${haLink}
      </div>`;
    if (page.model === "LV600S") return this._humidifierPage();
    const settings = Object.keys(page.controls).filter((key) => !key.startsWith("text_sensor."));
    if (!settings.length)
      return `<div class="card empty">
        <p>No settings of this device found.</p>
        <p class="muted">They are found by entity name, as the tuct/levoit configs name them${
          page.from_config ? " or as its config does" : ""
        }. Renamed entities are on the Home Assistant device page.</p>
        ${haLink}
      </div>`;
    return `${this._alerts()}
      ${this._hero()}
      ${this._groupBanner()}
      ${this._historyCard()}
      <div class="sections">
        ${this._autoSection()}
        ${this._sleepSection()}
        ${this._quietSection()}
        ${this._timerSection()}
        ${this._displaySection()}
        ${this._filterSection()}
        ${this._infoSection()}
      </div>`;
  }

  _alerts() {
    const alerts = [];
    if (this._state("binary_sensor.cover_open")?.state === "on")
      alerts.push("The cover is open: the purifier stays off until it is closed.");
    const error = this._state("text_sensor.error_message");
    if (this._usable(error) && !/^ok$/i.test(error.state)) alerts.push(`Error: ${error.state}`);
    if (this._state("binary_sensor.filter_low")?.state === "on")
      alerts.push("The filter is nearly used up: time for a new one.");
    return alerts.map((text) => `<div class="notice warn">${esc(text)}</div>`).join("");
  }

  _hero() {
    const fan = this._state("fan.fan");
    const levelSt = this._state("sensor.aqi");
    const level = this._usable(levelSt) ? aqiLevel(levelSt.state) : null;
    const tiles = [
      this._tile("sensor.pm25", "PM2.5"),
      this._tile("sensor.pm1_0", "PM1.0"),
      this._tile("sensor.pm10", "PM10"),
      // the 1-4 level on every model, with its word; the Eleva also has its 0-500 index
      this._tile("sensor.aqi", "AQI", { level }),
      this._tile("sensor.aqi_index", "AQI index"),
      this._tile("sensor.current_cadr", "CADR now"),
    ].join("");
    let controls = "";
    if (fan) {
      const usable = this._usable(fan);
      const on = fan.state === "on";
      const a = fan.attributes;
      const step = Number(a.percentage_step) || 25;
      const count = Math.max(1, Math.round(100 / step));
      const level = on ? Math.round((Number(a.percentage) || 0) / step) : 0;
      const turbo = this._page.model === "ELEVA300X";
      const speedName = (n) => (turbo && n === count ? "Turbo" : `Speed ${n}`);
      // what it is doing, in words: "Running · Auto · Room Size · off in 1 h"
      const offline = !usable && fan.state !== "off";
      const autoMode = this._state("select.auto_mode");
      const timerLeft = parseDuration(this._state("text_sensor.timer_duration_remaining")?.state) / 60;
      const doing = [];
      if (on) {
        if (a.preset_mode) doing.push(a.preset_mode);
        if (a.preset_mode === "Auto" && this._usable(autoMode)) doing.push(autoMode.state);
        else if ((!a.preset_mode || a.preset_mode === "Manual") && level) doing.push(speedName(level));
        if (timerLeft > 0) doing.push(`off in ${formatMinutes(timerLeft)}`);
      }
      const status = offline ? "Offline" : on ? "Running" : "Off";
      const statusSub = offline ? "Not connected to Home Assistant" : doing.join(" · ");
      const speeds = Array.from({ length: count }, (_, i) => i + 1)
        .map(
          (n) =>
            `<button class="seg${n === level ? " on" : ""}" aria-label="${esc(speedName(n))}" ${usable ? "" : "disabled"} ${this._svc(
              "fan",
              "set_percentage",
              fan.entity_id,
              // floor: 2 of 3 speeds is 66 %, which Home Assistant maps to speed 2 (67 % would be 3)
              { percentage: Math.min(100, Math.floor(n * step)) },
            )}>${turbo && n === count ? "Turbo" : n}</button>`,
        )
        .join("");
      const presets = (a.preset_modes || [])
        .map(
          (mode) =>
            `<button class="seg${on && mode === a.preset_mode ? " on" : ""}" ${usable ? "" : "disabled"} ${this._svc(
              "fan",
              "set_preset_mode",
              fan.entity_id,
              { preset_mode: mode },
            )}>${esc(mode)}</button>`,
        )
        .join("");
      // the speed buttons look pressed in Manual only; in Auto or Sleep they show
      // the speed it picked, dimmed (a click switches to Manual)
      const manual = on && (!a.preset_mode || a.preset_mode === "Manual");
      controls = `<div class="hero-controls">
        <button class="power${on ? " on" : ""}" aria-label="${on ? "Turn off" : "Turn on"}" title="${
          on ? "Turn off" : "Turn on"
        }" ${usable || fan.state === "off" ? "" : "disabled"} ${this._svc(
          "fan",
          on ? "turn_off" : "turn_on",
          fan.entity_id,
        )}>${icon("power")}</button>
        <div class="hero-rows">
          <div class="hero-status"><span class="hs-title">${esc(status)}</span>${
            statusSub ? `<span class="hs-sub">${esc(statusSub)}</span>` : ""
          }</div>
          <div class="hero-segs">
            ${presets ? `<div class="segs" role="group" aria-label="Mode">${presets}</div>` : ""}
            <div class="segs${manual ? "" : " dim"}" role="group" aria-label="Speed">${speeds}</div>
          </div>
        </div>
      </div>`;
    }
    const vent = this._slider("number.vent_angle", "Vent angle", "45° points up, 90° straight ahead");
    return `<div class="card hero">
      <div class="hero-main">
        ${controls}
        ${tiles ? `<div class="tiles">${tiles}</div>` : ""}
      </div>
      ${vent}
    </div>`;
  }

  _humidifierPage() {
    const state = (key) => this._state(key);
    const fan = state("fan.fan");
    const on = fan?.state === "on";
    const offline = !this._usable(fan);
    const unsafe = offline || this._lv600sUnsafe(state, this._page.controls);
    const mode = fan?.attributes.preset_mode;
    const storedTarget = this._page.target_humidity_preset === true;
    const powerLabel = on ? "Humidifier: Turn off" : "Humidifier: Turn on";
    const status = offline ? "Offline" : on ? "Running" : "Off";
    const binary = { format: (value) => value === "on" ? "Yes" : "No" };
    const modeLabel = on && LV600S_PRESETS.includes(mode) ? this._lvModeLabel(mode) : "";
    const ready = on && !unsafe;
    const reported = state("text_sensor.reported_mode");
    const reportedMode = this._lvModeLabel(this._usable(reported) ? reported.state : mode);
    const error = state("text_sensor.error_message");
    const fault = this._usable(error) && !/^(?:ok|unknown|no reported mcu fault)?$/i.test(error.state.trim());
    return `${fault ? `<div class="notice warn">Error: ${esc(error.state)}</div>` : ""}
      <div class="card hero" aria-label="${esc(this._page.title || "LV600S")}">
        <div class="hero-main">
          <div class="hero-controls lv-hero-controls">
            ${fan ? `<button class="power${on ? " on" : ""}" aria-label="${powerLabel}" title="${powerLabel}"
              ${offline || (unsafe && !on) ? "disabled" : ""} ${this._svc("fan", on ? "turn_off" : "turn_on", fan.entity_id)}>${icon("power")}</button>` : ""}
            <div class="hero-rows">
              <div class="hero-status"><span class="hs-title">${status}</span>
                ${modeLabel ? `<span class="hs-sub">${esc(modeLabel)}</span>` : ""}
                ${this._tankBadge(state, offline)}
              </div>
              <div class="hero-segs">${this._lv600sQuickControls(state, { disabled: unsafe, compact: false, on })}</div>
            </div>
          </div>
          <div class="tiles">${this._tile("sensor.humidity", "Humidity")}${this._tile("sensor.temperature", "Temperature")}</div>
        </div>
      </div>
      ${this._historyCard()}
      <div class="sections">${this._timerSection({ lv600s: true, unsafe })}
      ${this._section("Configuration", [
        this._slider("number.humidity_target", "Target humidity",
          "40–80 % in Auto mode",
          { dim: offline || (!storedTarget && (!ready || mode !== "Humidity")), unit: "%" }),
        this._toggle("switch.display", "Display", "", { dim: !ready || mode === "Sleep" }),
      ])}
      ${this._section("Appliance status", [
        this._setting("Reported mode", "", `<span class="readout">${esc(reportedMode)}</span>`),
        this._readout("binary_sensor.water_tank_empty", "Water tank empty", binary),
        this._readout("binary_sensor.tank_removed", "Tank removed", binary),
        this._readout("binary_sensor.humidifying", "Humidifying", binary),
        this._readout("binary_sensor.heating_enabled", "Heating enabled", binary),
        this._readout("binary_sensor.mcu_connection", "MCU connected", binary),
      ])}${this._infoSection()}</div>`;
  }

  _autoSection() {
    const mode = this._state("select.auto_mode");
    const roomSize = mode && /room|effic/i.test(mode.state);
    const highFan = this._state("text_sensor.auto_mode_room_size_high_fan");
    const highFanLeft = this._usable(highFan) && parseDuration(highFan.state) > 0;
    return this._section(
      "Automatic",
      [
        this._choices("select.auto_mode", "Auto mode", "How Auto picks the speed. Choosing one switches the fan to Auto"),
        // The preset number is only remembered on the ESP (sent when Room
        // Size is picked); the room size number sends it to the purifier now.
        // Set both, so a change applies at once and survives a mode change.
        roomSize
          ? this._state("number.auto_profile_room_size_input")
            ? this._slider("number.auto_profile_room_size_input", "Room size", "Auto runs for a room this size", {
                also: "number.efficiency_room_size",
              })
            : this._slider("number.efficiency_room_size", "Room size", "Auto runs for a room this size")
          : "",
        highFanLeft ? this._readout("text_sensor.auto_mode_room_size_high_fan", "High speed for another") : "",
        this._toggle("switch.dynamic_manual", "Dynamic manual", "In Manual, the speed goes up when the air gets bad"),
        this._toggle("switch.adaptive_start", "Adaptive start", "Stored on the purifier; VeSync runs it in its cloud"),
      ],
    );
  }

  // Vital 200S: a custom sleep profile runs quick clean, then sleep, then the
  // daytime mode. On the Default profile the purifier ignores these settings.
  _sleepSection() {
    const profile = this._state("select.sleep_preference");
    if (!profile) return "";
    const dim = profile.state === "Default";
    const sleepLevel = (v) => (v >= 5 ? "Auto" : `Level ${formatNumber(v)}`);
    return this._section(
      "Sleep",
      [
        this._choices("select.sleep_preference", "Sleep profile", "Custom1 / Custom2 use the steps below; Default uses the purifier's own"),
        dim ? `<div class="hint pad">Pick Custom1 or Custom2 to change the steps below.</div>` : "",
        this._subhead("1 · Quick clean first"),
        this._toggle("switch.quick_clean", "Quick clean", "Run fast for a while before sleep", { dim }),
        this._stepper("number.quick_clean_minutes", "For", "", { dim, format: (v) => formatMinutes(v) }),
        this._stepper("number.quick_clean_fan_level", "At level", "", { dim, format: (v) => `Level ${formatNumber(v)}` }),
        this._subhead("2 · Sleep"),
        this._stepper("number.sleep_minutes", "Sleep for", "", { dim, format: (v) => formatMinutes(v) }),
        this._stepper("number.sleep_fan_level", "At level", "", { dim, format: sleepLevel }),
        this._subhead("3 · Then"),
        this._toggle("switch.daytime_enabled", "Daytime mode", "Switch to a daytime mode when sleep ends", { dim }),
        this._choices("select.daytime_fan_mode", "Mode", "", { dim }),
        this._stepper("number.daytime_fan_level", "Level", "", { dim, format: (v) => `Level ${formatNumber(v)}` }),
      ],
    );
  }

  // Eleva 300X: the purifier lowers the fan one level during its quiet period
  _quietSection() {
    if (!this._state("switch.quiet_period") && !this._state("switch.dynamic_sleep")) return "";
    const trigger = this._state("select.quiet_trigger");
    const byTime = trigger?.state === "Timer";
    const active = this._state("binary_sensor.quiet_active")?.state === "on";
    const start = this._state("number.quiet_start");
    const end = this._state("number.quiet_end");
    const time = (st) =>
      st
        ? `<input type="time" step="1800" value="${esc(
            this._usable(st) ? hoursToTime(parseFloat(st.state)) : "",
          )}" data-number="${esc(st.entity_id)}" ${this._usable(st) ? "" : "disabled"}>`
        : "";
    return this._section(
      "Quiet period",
      [
        this._toggle(
          "switch.quiet_period",
          "Quiet period",
          active ? "Active now: the fan runs one level lower" : "Runs the fan one level lower",
        ),
        this._choices("select.quiet_trigger", "Starts", "", { labels: { Light: "When dark", Timer: "At set times" } }),
        byTime && (start || end)
          ? this._setting("From – to", "", `<div class="times">${time(start)}<span>–</span>${time(end)}</div>`)
          : "",
        this._toggle("switch.dynamic_sleep", "Dynamic sleep", "In Sleep, the speed goes up when the air gets bad"),
      ],
    );
  }

  _timerSection({ lv600s = false, unsafe = false } = {}) {
    const timer = this._state("number.timer");
    if (!timer) return "";
    const left = (lv600s ? lv600sRemainingSeconds(this._state("text_sensor.timer_duration_remaining")?.state)
      : parseDuration(this._state("text_sensor.timer_duration_remaining")?.state)) / 60;
    const total = parseDuration(this._state("text_sensor.timer_duration_initial")?.state) / 60;
    const running = Number.isFinite(left) && left > 0;
    const pendingMinutes = lv600s && !running && this._state("fan.fan")?.state === "off" ? Number(timer.state) : 0;
    const pending = Number.isFinite(pendingMinutes) && pendingMinutes > 0;
    const max = Number(timer.attributes.max) || 1440;
    const usable = lv600s ? !unsafe && timer.state !== "unavailable" : this._usable(timer);
    // whole minutes the timer number takes, up to its max
    const min = lv600s ? Number(timer.attributes.min) || 0 : 0;
    const presets = TIMER_PRESETS.filter((m) => m >= min && m <= max);
    const set = (minutes, text, cls) => {
      const enabled = usable || (minutes === 0 && pending && timer.state !== "unavailable");
      return `<button class="${cls}" ${enabled ? "" : "disabled"} ${this._svc("number", "set_value", timer.entity_id, {
        value: minutes,
      })}>${esc(text)}</button>`;
    };
    const status = running
      ? `<div class="timer-run">
          <div class="big">${esc(formatMinutes(left))} <span class="muted">left${
            total ? ` of ${esc(formatMinutes(total))}` : ""
          }</span></div>
          ${total ? `<div class="bar"><span style="width:${Math.min(100, Math.round((left / total) * 100))}%"></span></div>` : ""}
        </div>`
      : pending
        ? `<div class="muted pad">${esc(formatMinutes(pendingMinutes))} starts when switched on</div>`
        : `<div class="muted pad">${!lv600s
        ? "No timer running. Pick a time to turn the purifier off."
        : Number.isFinite(left)
          ? "No timer running. Pick a time to turn the humidifier off."
          : "Timer status unavailable."}</div>`;
    return this._section(
      "Timer",
      [
        status,
        `<div class="opts" role="group" aria-label="${running ? "New timer" : "Turn off in"}">${presets
          .map((m) => set(m, formatMinutes(m), "opt"))
          .join("")}</div>`,
      ],
      "",
      running || pending ? set(0, "Cancel", "btn text") : "",
    );
  }

  _displaySection() {
    const dark = this._state("binary_sensor.dark_detected");
    const lightHint = `Dims the display in the dark${
      dark && this._usable(dark) ? ` (now: ${dark.state === "on" ? "dark" : "light"})` : ""
    }`;
    return this._section("Display & panel", [
      this._toggle("switch.display", "Display", "The panel's lights"),
      this._toggle("switch.light_detect", "Light detect", lightHint),
      this._choices("select.nightlight", "Night light", ""),
      this._toggle("switch.aqi_ring_dim", "Dim the AQI ring", ""),
      this._toggle("switch.mute", "Mute", "No beeps from the panel"),
      this._toggle("switch.child_lock", "Child lock", "The buttons on the purifier do nothing"),
    ]);
  }

  _filterSection() {
    const life = this._number("sensor.filter_life_left");
    const reset = this._state("button.reset_filter_stats");
    const bar =
      life === null
        ? ""
        : `<div class="filter-big${life < 5 ? " bad" : life < 20 ? " low" : ""}">
            <div class="big">${esc(formatNumber(Math.round(life)))}<span class="muted"> % left</span></div>
            <div class="bar"><span style="width:${Math.max(0, Math.min(100, life))}%"></span></div>
          </div>`;
    return this._section(
      "Filter",
      [
        bar,
        this._stepper("number.filter_lifetime_months", "Filter lasts", "Used to work out the %", {
          format: (v) => `${formatNumber(v)} month${v === 1 ? "" : "s"}`,
        }),
        reset
          ? this._setting(
              "New filter fitted?",
              "Starts the filter life at 100 % again",
              `<button class="btn" ${this._usable(reset) || reset.state === "unknown" ? "" : "disabled"} ${this._svc(
                "button",
                "press",
                reset.entity_id,
                {},
                "Reset the filter life to 100 %? Do this after fitting a new filter.",
              )}>Reset</button>`,
            )
          : "",
      ],
      "Worked out on the ESP from the air moved, not measured",
    );
  }

  // --- device page: history chart ----------------------------------------------

  // whose history is shown: the device page's or the group page's
  _historyKey() {
    if (this._view === "groupdetail") return this._detailId ? `group:${this._detailId}` : null;
    return this._pageName ? `device:${this._pageName}` : null;
  }

  // The recorder can supply either purifier statistics or recorded humidifier states.
  _historySeries() {
    if (this._view === "groupdetail") {
      const entities = this._detailGroup()?.entities || {};
      const series = GROUP_HISTORY_SERIES.filter((s) => entities[s.key]).map((s) => ({
        ...s,
        entity: entities[s.key],
      }));
      if (entities.level) series.push({ key: "band", title: "Level", band: true, entity: entities.level });
      return series;
    }
    const controls = this._page?.controls || {};
    if (this._page?.model === "LV600S") {
      return LV600S_HISTORY.filter((s) => controls[s.key])
        .map((s) => ({ ...s, entity: controls[s.key] }));
    }
    const series = HISTORY_SERIES.filter((s) => controls[s.key]).map((s) => ({ ...s, entity: controls[s.key] }));
    const level = controls["sensor.aqi"];
    const index = controls["sensor.aqi_index"];
    if (level || index)
      series.push({ key: "band", title: "AQI", band: true, entity: level || index, fromIndex: !level, index: index || null });
    return series;
  }

  // the band's level of a reading: the 1-4 sensor, or the level of the 0-500 index
  _bandLevel(s, value) {
    return s.fromIndex ? aqiIndexLevel(value) : aqiLevel(value);
  }

  // the ones switched on in the legend
  _shownSeries() {
    return this._historySeries().filter((s) => !this._histHidden.has(s.key));
  }

  // a legend chip: switches its chart on and off, and shows the reading now
  _legendChip(s) {
    const st = this._hass?.states?.[s.entity];
    const ok = this._usable(st);
    let now = "—";
    if (ok && s.band) {
      // the level and its word, "4 Poor" (the index without a level sensor: "232 Poor")
      const shownValue = formatNumber(Math.round(parseFloat(st.state)));
      now = `${shownValue} ${AQI_WORDS[this._bandLevel(s, st.state)] || ""}`.trim();
    } else if (ok) {
      const unit = st.attributes.unit_of_measurement || "";
      const value = parseFloat(st.state);
      now = `${formatNumber(s.precise ? value : Math.round(value))}${unit ? ` ${unit}` : ""}`;
    }
    const shown = !this._histHidden.has(s.key);
    const swatch = s.band
      ? `<span class="sw band"></span>`
      : `<span class="sw c-${s.color}${s.axis === "right" ? " line" : ""}"></span>`;
    return `<button class="lg${shown ? "" : " off"}" data-action="toggle-series" data-key="${esc(s.key)}" aria-pressed="${shown}" title="${
      shown ? "Hide" : "Show"
    } ${esc(s.title)}">${swatch}<span>${esc(s.title)}</span><b>${esc(now)}</b></button>`;
  }

  async _loadHistory() {
    const series = this._historySeries();
    if (!series.length || !this._hass) return;
    const name = this._historyKey();
    const rangeKey = this._historyRange;
    const range = HISTORY_RANGES[rangeKey];
    const end = Date.now();
    const start = end - range.ms;
    const raw = this._page?.model === "LV600S";
    const ids = [...new Set(series.flatMap((s) => [s.entity, s.index].filter(Boolean)))];
    const request = {};
    this._historyRequest = request;
    this._historyLoading = true;
    try {
      const result = await this._hass.callWS({
        start_time: new Date(start).toISOString(),
        end_time: new Date(end).toISOString(),
        ...(raw ? {
          type: "history/history_during_period", entity_ids: ids, include_start_time_state: true,
          minimal_response: true, no_attributes: true,
        } : {
          type: "recorder/statistics_during_period", statistic_ids: ids, period: range.period, types: ["mean"],
        }),
      });
      if (this._historyRequest !== request) return;
      const data = {};
      for (const id of ids) {
        const records = result?.[id] || [];
        data[id] = raw ? stateHistory(records, start, end) : records
          .map((p) => [typeof p.start === "number" ? p.start : Date.parse(p.start), p.mean])
          .filter(([t, v]) => Number.isFinite(t) && v !== null && v !== undefined);
      }
      this._history = { name, range: rangeKey, start, end, at: Date.now(), data, raw };
      this._historyError = null;
    } catch (err) {
      if (this._historyRequest === request) this._historyError = err?.message || String(err);
    } finally {
      if (this._historyRequest === request) {
        this._historyLoading = false;
        this._render();
      }
    }
  }

  _historyCard() {
    const series = this._historySeries();
    if (!series.length) return "";
    const h = this._history;
    const humidifier = this._page?.model === "LV600S";
    const ranges = Object.entries(HISTORY_RANGES)
      .map(
        ([key, r]) =>
          `<button class="seg${key === this._historyRange ? " on" : ""}" data-action="history-range" data-range="${key}">${esc(r.label)}</button>`,
      )
      .join("");
    const shown = this._shownSeries();
    let body;
    if (this._historyError && !h)
      body = `<div class="muted pad">History unavailable: ${esc(this._historyError)}</div>`;
    else if (!h) body = `<div class="muted pad"><span class="spinner"></span> Loading…</div>`;
    else if (!shown.length) body = `<div class="muted pad">Select a reading to see its history.</div>`;
    else {
      const stale = this._historyLoading || h.range !== this._historyRange;
      const band = shown.find((s) => s.band);
      const readings = shown.filter((s) => !s.band && !s.level);
      const levels = shown.filter((s) => s.level);
      const historyLabel = humidifier ? "Humidifier history" : "Air quality history";
      const range = HISTORY_RANGES[h.range].label;
      body = `<div class="hist${stale ? " stale" : ""}" tabindex="0" aria-label="${historyLabel}, ${range}. Use the arrow keys to move through the readings.">
        ${readings.length ? this._plot(readings, h) : ""}
        ${band ? `<div class="hist-row band-row"><div></div>${this._bandStrip(band, h)}<div></div></div>` : ""}
        ${levels.length ? `<div class="hist-levels">${this._plot(levels, h)}</div>` : ""}
        ${this._timeAxis(h)}
        <div class="hist-tip" hidden></div>
      </div>`;
    }
    return `<div class="card history">
      <div class="hist-head">
        <h2>History</h2>
        <div class="legend">${series.map((s) => this._legendChip(s)).join("")}</div>
        <div class="segs" role="group" aria-label="Range">${ranges}</div>
      </div>
      ${body}
    </div>`;
  }

  // the 1-4 level over time: a strip coloured by level (words in the tooltip)
  _bandStrip(s, h) {
    const points = h.data[s.entity] || [];
    // one block per run of the same level (adjoining pieces would show seams);
    // a gap of more than two periods (offline) ends a run
    const step = HISTORY_RANGES[h.range].step;
    const runs = [];
    for (const [t, v] of points) {
      const lvl = this._bandLevel(s, v);
      if (!lvl) continue;
      const run = runs[runs.length - 1];
      if (run && run.lvl === lvl && t - run.end <= step * 2.5) run.end = t + step;
      else runs.push({ lvl, start: t, end: t + step });
    }
    const rects = runs
      .map(({ lvl, start, end }) => {
        const x = this._x(start, h);
        const w = Math.max(0.5, this._x(Math.min(end, h.end), h) - x);
        return `<rect class="q${lvl}" x="${x.toFixed(1)}" y="0" width="${w.toFixed(2)}" height="10"></rect>`;
      })
      .join("");
    return `<svg class="hist-band" viewBox="0 0 ${CHART.width} 10" preserveAspectRatio="none" role="img" aria-label="${esc(
      `Air quality level, ${HISTORY_RANGES[h.range].label}`,
    )}">${rects}<line class="xhair" y1="0" y2="10" x1="0" x2="0" visibility="hidden"></line></svg>`;
  }

  _x(t, h) {
    return ((t - h.start) / (h.end - h.start)) * CHART.width;
  }

  // Up to two axes per row. Recorded settings are steps; averaged purifier readings are lines.
  _plot(series, h) {
    const { width, height, top, bottom } = CHART;
    const y = (min, max) => (v) => top + ((max - v) / (max - min)) * (height - top - bottom);
    // a gap of more than two periods (device offline) breaks a line
    const gap = HISTORY_RANGES[h.range].step * 2.5;
    const runsOf = (points) => {
      const runs = [];
      let run;
      for (const pt of points) {
        if (pt[1] === null) {
          if (run) run.push([pt[0], run.at(-1)[1]]);
          run = null;
        } else if (run && (h.raw || pt[0] - run.at(-1)[0] <= gap)) {
          run.push(pt);
        } else {
          run = [pt];
          runs.push(run);
        }
      }
      return runs;
    };
    const axes = { left: "", right: "" };
    const paths = [];
    let any = false;
    // series on one axis share its scale (a group's PM1, PM2.5 and PM10)
    const peak = { left: 0, right: 0 };
    for (const s of series)
      for (const [, v] of h.data[s.entity] || []) peak[s.axis] = Math.max(peak[s.axis], v);
    for (const s of series) {
      const points = h.data[s.entity] || [];
      const runs = runsOf(points);
      if (!runs.length) continue;
      any = true;
      let [min, max] = s.bounds || [0, null];
      if (max === null) {
        if (h.raw) {
          const limits = points.reduce(([low, high], [, v]) => v === null
            ? [low, high] : [Math.min(low, v), Math.max(high, v)], [Infinity, -Infinity]);
          min = Math.floor(limits[0] / 5) * 5;
          max = Math.max(min + 5, Math.ceil(limits[1] / 5) * 5);
        } else {
          max = niceMax(peak[s.axis]);
        }
      }
      const yOf = y(min, max);
      const base = yOf(0);
      const line = (run) => run.map(([t, v], i) => {
        const x = this._x(t, h).toFixed(1);
        const value = yOf(v).toFixed(1);
        return i && h.raw ? `H${x}V${value}` : `${i ? "L" : "M"}${x},${value}`;
      }).join("");
      if (s.area)
        paths.push(
          ...runs.map(
            (run) =>
              `<path class="area c-${s.color}" d="${line(run)}L${this._x(run[run.length - 1][0], h).toFixed(1)},${base}L${this._x(run[0][0], h).toFixed(1)},${base}Z"></path>`,
          ),
        );
      // a lone reading (between gaps) is a dot: a zero-length line with round caps
      paths.push(
        ...runs.map((run) =>
          run.length > 1
            ? `<path class="line c-${s.color}${s.axis === "right" || s.dashed ? " dashed" : ""}" d="${line(run)}"></path>`
            : `<path class="line dot c-${s.color}" d="${line(run)}h0.01"></path>`,
        ),
      );
      if (axes[s.axis]) continue;
      const ticks = s.level ? [9, 6, 3, 0] : [max, (min + max) / 2, min];
      const unit = h.raw ? this._hass?.states?.[s.entity]?.attributes?.unit_of_measurement || "" : "";
      axes[s.axis] = ticks
        .map(
          (v) =>
            `<span class="ytick${s.level ? "" : ` c-${s.color}`}" style="top:${((yOf(v) / height) * 100).toFixed(1)}%">${esc(formatNumber(v) + unit)}</span>`,
        )
        .join("");
    }
    if (!any) return `<div class="hist-empty muted">No history yet</div>`;
    const intervals = series[0]?.level ? [0, 1/3, 2/3, 1] : [0, 1/2, 1];
    const grid = intervals.map((ratio) => top + ratio * (height - top - bottom))
      .map((v) => `<line class="grid" x1="0" x2="${width}" y1="${v}" y2="${v}"></line>`)
      .join("");
    const label = series.map((s) => `${s.title}${s.axis === "right" ? " (right axis)" : ""}`).join(" and ");
    // PM2.5 underneath: its area must not cover the CADR line
    const order = (path) => (path.includes("c-pm") ? 0 : 1);
    paths.sort((a, b) => order(a) - order(b));
    return `<div class="hist-row"><div class="hist-y left" aria-hidden="true">${axes.left}</div>
      <svg class="hist-plot" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="${esc(
        `${label}, ${HISTORY_RANGES[h.range].label}`,
      )}">
        ${grid}
        ${paths.join("")}
        <line class="xhair" y1="0" y2="${height}" x1="0" x2="0" visibility="hidden"></line>
      </svg><div class="hist-y right" aria-hidden="true">${axes.right}</div></div>`;
  }

  // shared time axis under the charts: every few hours, every day at midnight,
  // or every Monday for 30 days
  _timeAxis(h) {
    const lang = this._hass?.locale?.language;
    const { tick } = HISTORY_RANGES[h.range];
    const ticks = [];
    const at = new Date(h.start);
    if (tick < DAY_MS) {
      const hours = tick / HOUR_MS;
      at.setMinutes(0, 0, 0);
      at.setHours(Math.ceil((at.getHours() + 1) / hours) * hours);
      for (let t = at.getTime(); t <= h.end; t += tick)
        ticks.push([t, new Date(t).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })]);
    } else {
      const days = tick / DAY_MS;
      at.setHours(24, 0, 0, 0);
      if (days === 7) at.setDate(at.getDate() + ((8 - at.getDay()) % 7));
      // by the calendar, so a tick stays at midnight across a clock change
      for (; at.getTime() <= h.end; at.setDate(at.getDate() + days))
        ticks.push([
          at.getTime(),
          days === 1
            ? at.toLocaleDateString(lang, { weekday: "short" })
            : at.toLocaleDateString(lang, { day: "numeric", month: "short" }),
        ]);
    }
    return `<div class="hist-row"><div></div><div class="hist-axis" aria-hidden="true">${ticks
      .map(
        ([t, text]) =>
          `<span class="xtick" style="left:${((this._x(t, h) / CHART.width) * 100).toFixed(2)}%">${esc(text)}</span>`,
      )
      .join("")}</div><div></div></div>`;
  }

  // the crosshair and tooltip are drawn into the rendered chart, not re-rendered
  _bindHistory() {
    const hist = this.shadowRoot?.querySelector?.(".hist");
    if (!hist || !this._history) return;
    const timeAt = (clientX) => {
      const rect = hist.querySelector(".hist-plot")?.getBoundingClientRect();
      if (!rect || !rect.width) return null;
      const h = this._history;
      return h.start + ((clientX - rect.left) / rect.width) * (h.end - h.start);
    };
    hist.addEventListener("pointermove", (ev) => this._showHover(timeAt(ev.clientX)));
    hist.addEventListener("pointerleave", () => this._showHover(null));
    hist.addEventListener("blur", () => this._showHover(null));
    hist.addEventListener("keydown", (ev) => {
      if (ev.key !== "ArrowLeft" && ev.key !== "ArrowRight") return;
      ev.preventDefault();
      const h = this._history;
      const step = HISTORY_RANGES[h.range].step * (ev.key === "ArrowLeft" ? -1 : 1);
      this._showHover(Math.min(h.end, Math.max(h.start, (this._hoverT ?? h.end) + step)));
    });
    if (this._hoverT !== null) this._showHover(this._hoverT);
  }

  _showHover(t) {
    const hist = this.shadowRoot?.querySelector?.(".hist");
    const h = this._history;
    if (!hist || !h) return;
    const tip = hist.querySelector(".hist-tip");
    const hairs = hist.querySelectorAll(".xhair");
    if (t === null || t < h.start || t > h.end) {
      this._hoverT = null;
      tip.hidden = true;
      hairs.forEach((line) => line.setAttribute("visibility", "hidden"));
      return;
    }
    // Statistics are individual buckets; recorded states hold until the next change.
    let snapped = h.raw ? t : null;
    if (!h.raw) {
      for (const points of Object.values(h.data))
        for (const [pt] of points) if (snapped === null || Math.abs(pt - t) < Math.abs(snapped - t)) snapped = pt;
    }
    if (snapped === null) return;
    this._hoverT = snapped;
    const x = this._x(snapped, h);
    hairs.forEach((line) => {
      line.setAttribute("x1", x);
      line.setAttribute("x2", x);
      line.setAttribute("visibility", "visible");
    });
    // values lead, names follow; text via textContent
    const lang = this._hass?.locale?.language;
    const when = new Date(snapped);
    tip.textContent = "";
    const time = document.createElement("div");
    time.className = "tip-time";
    const span = HISTORY_RANGES[h.range].ms;
    time.textContent =
      span <= DAY_MS
        ? when.toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" })
        : span <= 7 * DAY_MS
          ? when.toLocaleString(lang, { weekday: "short", hour: "2-digit", minute: "2-digit" })
          : when.toLocaleString(lang, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
    tip.appendChild(time);
    const tolerance = HISTORY_RANGES[h.range].step / 2;
    for (const s of this._shownSeries()) {
      const points = h.data[s.entity] || [];
      const hit = h.raw ? points.findLast(([pt]) => pt <= snapped)
        : points.find(([pt]) => Math.abs(pt - snapped) <= tolerance);
      const unit = this._hass?.states?.[s.entity]?.attributes?.unit_of_measurement || "";
      const row = document.createElement("div");
      row.className = "tip-row";
      const value = document.createElement("strong");
      if (s.band) {
        const index = s.index ? (h.data[s.index] || []).find(([pt]) => Math.abs(pt - snapped) <= tolerance) : null;
        const word = hit ? AQI_WORDS[this._bandLevel(s, hit[1])] || "—" : "—";
        value.textContent = index ? `${formatNumber(Math.round(index[1]))} · ${word}` : word;
      } else value.textContent = hit && hit[1] !== null ? `${formatNumber(hit[1])}${unit ? ` ${unit}` : ""}` : "—";
      const label = document.createElement("span");
      label.textContent = s.title;
      row.append(value, label);
      tip.appendChild(row);
    }
    tip.hidden = false;
    // keep the tooltip inside the chart: left of the crosshair past the middle.
    // Positioned in the plot column (an axis of 40px and a gap of 8px each side).
    const share = x / CHART.width;
    tip.style.left = share > 0.5 ? "" : `calc(48px + (100% - 96px) * ${share.toFixed(4)} + 12px)`;
    tip.style.right = share > 0.5 ? `calc(48px + (100% - 96px) * ${(1 - share).toFixed(4)} + 12px)` : "";
  }

  _infoSection() {
    const rows = [
      this._readout("text_sensor.model", "Model"),
      this._readout("text_sensor.esp_version", "Component"),
      this._readout("text_sensor.mcu_version", "MCU firmware"),
      this._readout("text_sensor.error_message", "Status"),
      this._readout("sensor.ambient_light", "Ambient light"),
    ].filter(Boolean);
    if (!rows.length) return "";
    // open state kept here: the page re-renders on every state change
    return `<details class="card section info" ${this._infoOpen ? "open" : ""}>
      <summary class="sec-head" data-action="toggle-info" aria-expanded="${Boolean(this._infoOpen)}">
        <h2>Info</h2>${icon("chevron")}
      </summary>
      ${rows.join("")}
      <div class="hint pad">${this._page.from_config
        ? "Settings matched to entity names in the device configuration."
        : "Settings matched to entity names in the tuct/levoit configuration."}</div>
    </details>`;
  }

  // --- build log ----------------------------------------------------------------

  // The dialog shows the build's steps and its newest lines from the device
  // snapshot, so it follows a running build by itself; the full kept output
  // is fetched on request.
  _showLog(name) {
    const device = this._device(name);
    this._log = { name, title: device ? device.title : name, full: false, lines: null };
    this._logScroll = "end";
    this._render();
  }

  async _fetchLog() {
    if (!this._log || this._logFetching) return;
    this._logFetching = true;
    try {
      const result = await this._hass.callWS({ type: "levoit_esphome/build_log", name: this._log.name });
      if (this._log) this._log.lines = result.lines;
    } catch (err) {
      this._toast(`Log: ${err.message || err}`);
    } finally {
      this._logFetching = false;
    }
    this._render();
  }

  async _toggleFullLog() {
    if (!this._log) return;
    this._log.full = !this._log.full;
    this._logScroll = "end";
    if (this._log.full) await this._fetchLog();
    else this._render();
  }

  _logDialog() {
    if (!this._log) return "";
    const { title, full } = this._log;
    const d = this._device(this._log.name);
    const building = Boolean(d?.building);
    const lines = full ? this._log.lines || [] : d?.build?.tail || [];
    const what = building ? "running build" : d?.last_build ? `last build, ${esc(this._time(d.last_build.at))}` : "last build";
    return `<div class="backdrop" data-action="close-log">
      <div class="log" role="dialog" aria-label="Build log of ${esc(title)}">
        <div class="log-head">
          <span>${esc(title)}: ${what}</span>
          <button class="btn" data-action="log-full" ${this._logFetching ? "disabled" : ""}>${full ? "Last lines" : "Full log"}</button>
          <button class="btn" data-action="close-log">Close</button>
        </div>
        ${this._stepsList(d?.build)}
        <pre class="${full ? "full" : "tail"}">${lines.length ? lines.map(esc).join("\n") : "No output yet."}</pre>
      </div>
    </div>`;
  }
}

const STYLE = `
:host {
  display: block;
  min-height: 100vh;
  background: var(--primary-background-color);
  color: var(--primary-text-color);
  font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, Roboto, sans-serif));
  -webkit-font-smoothing: antialiased;
  /* accent text that reads on cards: the theme colour pulled towards the text colour */
  --lv-accent-text: color-mix(in srgb, var(--primary-color) 72%, var(--primary-text-color));
  --lv-track: var(--secondary-background-color, rgba(127, 127, 127, 0.12));
  --lv-tile: rgba(127, 127, 127, 0.08);
  --lv-pm: var(--primary-color);
  --lv-pm1: #4fb3e8;
  --lv-pm10: #1a4f8b;
  --lv-cadr: #e65100;
  /* air quality level 1-4: lighter to darker as well as green to red */
  --lv-q1: #43a047; --lv-q2: #c0ca33; --lv-q3: #ffa000; --lv-q4: #c62828;
  --lv-q1-bg: #e8f5e9; --lv-q1-fg: #1b5e20; --lv-q2-bg: #f1f8e9; --lv-q2-fg: #33691e;
  --lv-q3-bg: #fff3e0; --lv-q3-fg: #8a4b00; --lv-q4-bg: #ffebee; --lv-q4-fg: #b71c1c;
}
:host([dark]) {
  --lv-cadr: #ffa726;
  --lv-pm1: #8fd3f7;
  --lv-pm10: #5b8fd6;
  --lv-q4: #e53935;
  --lv-q1-bg: #1b3a1e; --lv-q1-fg: #a5d6a7; --lv-q2-bg: #2b3a1a; --lv-q2-fg: #c5e1a5;
  --lv-q3-bg: #3d2a10; --lv-q3-fg: #ffcc80; --lv-q4-bg: #421a1a; --lv-q4-fg: #ef9a9a;
}
h2 { margin: 0; font-size: 16px; font-weight: 500; }
.sr { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
a { color: var(--primary-color); text-decoration: none; }
a:hover { text-decoration: underline; }
svg { width: 24px; height: 24px; fill: currentColor; flex: none; }
.muted { color: var(--secondary-text-color); }
.bad { color: var(--error-color, #db4437); }
.warn-text { color: var(--warning-color, #ffa600); }
.mono { font-variant-numeric: tabular-nums; }

.toolbar {
  display: flex; align-items: center; gap: 4px;
  height: var(--header-height, 56px); padding: 0 8px 0 16px;
  background: var(--app-header-background-color, var(--primary-color));
  color: var(--app-header-text-color, var(--text-primary-color, #fff));
  border-bottom: var(--app-header-border-bottom, none);
  box-sizing: border-box; position: sticky; top: 0; z-index: 2;
}
.toolbar .title { flex: 1; font-size: 20px; font-weight: 400; margin-left: 8px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.icon-btn, .tb-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  background: none; border: none; color: inherit; cursor: pointer; font: inherit;
  border-radius: 20px; height: 40px;
}
.icon-btn { width: 40px; margin-left: -8px; }
.toolbar .icon-btn[data-action="check"] { margin-left: 0; }
.tb-btn { padding: 0 12px; font-size: 14px; font-weight: 500; }
.icon-btn:hover, .tb-btn:hover { background: rgba(127, 127, 127, 0.15); }
.icon-btn:disabled { opacity: 0.6; cursor: default; }

.content { max-width: 1400px; margin: 0 auto; padding: 16px; box-sizing: border-box; }
.summary { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 0; margin: 0 4px 12px; font-size: 14px; }
.summary .dot { margin: 0 10px; color: var(--secondary-text-color); }

.card {
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: var(--ha-card-border-radius, 12px);
  border: 1px solid var(--ha-card-border-color, var(--divider-color, #e0e0e0));
  box-shadow: var(--ha-card-box-shadow, none);
  overflow: hidden;
}
.card-head { padding: 12px 16px; font-size: 14px; color: var(--secondary-text-color);
  border-bottom: 1px solid var(--divider-color); }
.empty { padding: 32px 24px; text-align: center; }
.empty p { margin: 8px auto; max-width: 560px; }
.big-icon svg { width: 48px; height: 48px; color: var(--secondary-text-color); }

table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; font-weight: 500; color: var(--secondary-text-color); font-size: 12px;
  padding: 10px 8px; white-space: nowrap; border-bottom: 1px solid var(--divider-color); }
td { padding: 10px 8px; vertical-align: middle; border-bottom: 1px solid var(--divider-color); }
tbody tr:last-child td { border-bottom: none; }
th:first-child, td:first-child { padding-left: 16px; }
th:last-child, td:last-child { padding-right: 16px; }
tr.has-update td:first-child { box-shadow: inset 3px 0 0 var(--warning-color, #ffa600); }
.device .name { font-weight: 500; }
.sub { font-size: 12px; color: var(--secondary-text-color); margin-top: 2px; max-width: 280px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub.ok { color: var(--success-color, #43a047); }
.sub.bad { color: var(--error-color, #db4437); }
td.actions { text-align: right; white-space: nowrap; }

select {
  font: inherit; font-size: 14px; color: var(--primary-text-color);
  background: var(--input-fill-color, var(--secondary-background-color, transparent));
  border: 1px solid var(--divider-color); border-radius: 8px; padding: 4px 8px;
}
select:disabled { opacity: 0.6; }

.btn {
  font: inherit; font-size: 14px; font-weight: 500; cursor: pointer;
  border-radius: 18px; padding: 6px 14px; margin-left: 4px;
  background: none; color: var(--primary-color);
  border: 1px solid var(--divider-color);
}
.btn:hover { background: rgba(127, 127, 127, 0.1); }
.btn.primary { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color); }
.btn.primary:hover { filter: brightness(1.08); }
.btn:disabled { opacity: 0.5; cursor: default; filter: none; }
.btn.text { border-color: transparent; color: var(--lv-accent-text); }
.btn.icon-text { display: inline-flex; align-items: center; gap: 6px; }
.btn.icon-text svg { width: 18px; height: 18px; }

.releases { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 28px;
  padding: 14px 16px 14px 20px; margin-bottom: 16px; }
.rel { display: flex; flex-direction: column; gap: 2px; }
.rel-label { font-size: 12px; color: var(--secondary-text-color); }
.rel a { font-size: 14px; color: var(--lv-accent-text); }
.rel-when { font-size: 13px; margin-right: auto; }
.releases .btn { margin: 0; }
.card-head b { font-weight: 500; color: var(--primary-text-color); }
.fw { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.fw .mono, .fw a { font-size: 13px; }
.fw a { color: var(--lv-accent-text); }
.fw-arrow { width: 14px; height: 14px; color: var(--secondary-text-color); }
.fw-status { margin-top: 4px; }

.chip { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 500;
  padding: 3px 10px; border-radius: 12px; white-space: nowrap;
  background: rgba(127, 127, 127, 0.15); color: var(--secondary-text-color); }
.chip.success { background: rgba(67, 160, 71, 0.15); color: var(--success-color, #43a047); }
.chip.warning { background: rgba(255, 166, 0, 0.18); color: var(--warning-color, #ffa600); }
.chip.info { background: rgba(3, 155, 229, 0.15); color: var(--info-color, #039be5); }

.filter { display: inline-flex; align-items: center; gap: 8px; white-space: nowrap; }
.filter .bar { width: 48px; height: 6px; border-radius: 3px; background: rgba(127, 127, 127, 0.2); overflow: hidden; }
.filter .bar span { display: block; height: 100%; background: var(--success-color, #43a047); }
.filter.low .bar span { background: var(--warning-color, #ffa600); }
.filter.bad .bar span { background: var(--error-color, #db4437); }

.spinner { width: 12px; height: 12px; border-radius: 50%; display: inline-block;
  border: 2px solid currentColor; border-right-color: transparent;
  animation: spin 0.8s linear infinite; vertical-align: middle; }
.spinner.light { width: 18px; height: 18px; }
@keyframes spin { to { transform: rotate(360deg); } }

.footer { font-size: 12px; text-align: center; margin: 16px 0 8px; }
.notice { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px;
  margin: 0 0 12px; padding: 10px 16px; border-radius: 12px; font-size: 14px;
  background: rgba(3, 155, 229, 0.12); color: var(--primary-text-color); }
.notice .btn { margin-left: auto; }

.backdrop { position: fixed; inset: 0; z-index: 10; background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center; padding: 16px; }
.log { background: var(--ha-card-background, var(--card-background-color, #fff));
  color: var(--primary-text-color); border-radius: 12px; width: min(1000px, 100%);
  max-height: 85vh; display: flex; flex-direction: column; overflow: hidden; }
.log-head { display: flex; align-items: center; gap: 8px; padding: 12px 16px;
  border-bottom: 1px solid var(--divider-color); font-weight: 500; }
.log-head span { flex: 1; }
.log pre { margin: 0; padding: 12px 16px; overflow: auto; font-size: 12px; line-height: 1.45;
  font-family: var(--code-font-family, ui-monospace, Menlo, Consolas, monospace);
  white-space: pre-wrap; word-break: break-word; box-sizing: border-box; }
/* a fixed height, so the dialog does not jump as the lines come and go */
.log pre.tail { height: min(300px, 45vh); }
.log pre.full { height: min(640px, 65vh); }
/* the build's steps: mark, name, what it does or how it ended */
.steps { list-style: none; margin: 0; padding: 10px 16px; border-bottom: 1px solid var(--divider-color);
  display: grid; grid-template-columns: 20px auto minmax(0, 1fr); gap: 6px 12px; align-items: center;
  font-size: 13px; }
.steps li { display: contents; }
.steps .st { display: flex; justify-content: center; align-items: center; color: var(--secondary-text-color); }
.steps .st svg { width: 16px; height: 16px; fill: currentColor; }
.steps .sn { font-weight: 500; white-space: nowrap; }
.steps .sd { display: flex; align-items: center; gap: 8px; min-width: 0; color: var(--secondary-text-color); }
.steps .sd-text { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-variant-numeric: tabular-nums; }
.steps .queued .sn, .steps .queued .st { color: var(--disabled-text-color, var(--secondary-text-color)); }
.steps .done .st { color: var(--success-color, #43a047); }
.steps .failed .st, .steps .failed .sd { color: var(--error-color, #db4437); }
.steps .running .st { color: var(--info-color, #039be5); }
.dot-q { width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: 0.6; }
.pbar { display: inline-block; flex: none; width: 140px; height: 6px; border-radius: 3px;
  background: rgba(127, 127, 127, 0.2); overflow: hidden; vertical-align: middle; }
.pbar span { display: block; height: 100%; background: var(--primary-color); transition: width 0.4s; }
.fw-status .pbar { width: 72px; margin-left: 8px; }

/* --- tabs and overview --- */
.tabs { display: flex; gap: 4px; margin: 0 4px 16px; border-bottom: 1px solid var(--divider-color); }
.tab { font: inherit; font-size: 14px; font-weight: 500; cursor: pointer; background: none; border: none;
  padding: 10px 14px; color: var(--secondary-text-color); border-bottom: 2px solid transparent; margin-bottom: -1px;
  display: inline-flex; align-items: center; gap: 6px; }
.tab:hover { color: var(--primary-text-color); }
.tab.on { color: var(--lv-accent-text); border-bottom-color: var(--primary-color); }
.tab-badge { display: inline-flex; align-items: center; justify-content: center; min-width: 20px; height: 20px;
  padding: 0 6px; box-sizing: border-box; border-radius: 10px; font-size: 12px; font-weight: 500;
  background: var(--lv-q3-bg); color: var(--lv-q3-fg); }
.ov-summary { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 20px; margin: 0 4px 16px;
  font-size: 14px; color: var(--secondary-text-color); }
.ov-summary b { font-weight: 500; color: var(--primary-text-color); }
.ov-summary a { color: var(--lv-accent-text); }
.overview { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr)); gap: 16px; }
.overview-note { margin: 16px 4px 0; font-size: 14px; }
.dcard { padding: 16px; cursor: pointer; outline: none; transition: border-color 0.15s, box-shadow 0.15s;
  display: flex; flex-direction: column; gap: 14px;
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border-radius: var(--ha-card-border-radius, 12px);
  border: 1px solid var(--ha-card-border-color, var(--divider-color, #e0e0e0)); }
.dcard:hover { border-color: var(--primary-color); box-shadow: 0 2px 10px rgba(0, 0, 0, 0.08); }
.dcard.humidifier { cursor: default; }
.dcard.humidifier [data-action="navigate"] { cursor: pointer; }
.dcard:focus-visible { box-shadow: 0 0 0 2px var(--primary-color); }
.dc-top { display: flex; align-items: center; gap: 12px; }
.dev-tile { width: 44px; height: 44px; border-radius: 12px; flex: none; display: inline-flex; align-items: center;
  justify-content: center; background: var(--lv-track); }
.dcard.on .dev-tile { background: color-mix(in srgb, var(--primary-color) 16%, transparent); }
.dcard.offline .dev-tile { opacity: 0.5; }
.dev-img { width: 34px; height: 34px; flex: none; fill: none; stroke: var(--secondary-text-color);
  stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.dcard.on .dev-img { stroke: var(--lv-accent-text); }
.dc-name { flex: 1; min-width: 0; }
.dc-name .name { font-size: 16px; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.dc-sub { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 8px; margin-top: 3px;
  font-size: 12px; color: var(--secondary-text-color); }
.dc-flags { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 6px; }
.dc-filter { display: inline-flex; align-items: center; gap: 4px; white-space: nowrap; font-variant-numeric: tabular-nums;
  color: var(--primary-text-color); }
.dc-filter svg { width: 12px; height: 12px; color: var(--secondary-text-color); }
.dc-filter .bar { width: 28px; height: 4px; border-radius: 2px; background: var(--divider-color); overflow: hidden; }
.dc-filter .bar span { display: block; height: 100%; border-radius: 2px; background: var(--success-color, #43a047); }
.dc-filter.low .bar span { background: var(--warning-color, #ffa600); }
.dc-filter.bad .bar span { background: var(--error-color, #db4437); }
.dc-filter.low, .dc-filter.bad { color: var(--lv-q3-fg); }
.dc-tank { display: inline-flex; align-items: center; gap: 4px; min-width: 0; color: var(--secondary-text-color); }
.hero-status .dc-tank { font-size: 14px; }
.dc-tank svg { width: 14px; height: 14px; flex: none; }
.dc-tank.warning { color: var(--lv-q3-fg); }
.dc-tank.water svg { color: var(--lv-accent-text); }
.chip.bad-chip { background: var(--lv-q4-bg); color: var(--lv-q4-fg); padding: 1px 8px 1px 6px; }
.dot-i { width: 7px; height: 7px; border-radius: 50%; background: var(--error-color, #db4437); }
.dc-flags .chip { font-size: 11px; padding: 1px 8px; }
.chip-btn { font: inherit; font-size: 12px; font-weight: 500; border: none; cursor: pointer; }
.chip-btn:hover { filter: brightness(0.95); }
.power.small { width: 44px; height: 44px; }
.power.small svg { width: 22px; height: 22px; }
.dc-controls { display: flex; align-items: center; gap: 8px; margin-top: auto; }
.dc-controls .segs { flex-wrap: nowrap; }
.humidifier-controls { container: lv-card-controls / inline-size; flex-wrap: wrap; }
.humidifier-controls > .lv-levels { flex: none; align-items: center; gap: 8px; }
.humidifier-controls .lv-warm-picker { gap: 4px; }
.humidifier-controls .lv-warm-picker .seg.sm { min-width: 28px; padding: 0 6px; }
.humidifier-controls .lv-warm-picker .seg.sm:first-child { min-width: 36px; }
@container lv-card-controls (width < 374px) {
  .lv-levels:has(.lv-warm-picker.expanded) + .mode-select { display: none; }
}
.seg.sm { font-size: 13px; height: 32px; padding: 0 10px; min-width: 32px; }
.lv-quick { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; min-width: 0; width: 100%; }
.lv-levels { display: flex; flex-wrap: wrap; align-items: flex-start; gap: 8px 14px; }
.lv-level { display: flex; align-items: center; gap: 6px; min-width: 0; }
.lv-level-icon { display: inline-flex; flex: none; --mdc-icon-size: 18px;
  width: var(--mdc-icon-size); height: var(--mdc-icon-size); color: var(--secondary-text-color); }
.lv-level-icon.humidifying { color: var(--lv-accent-text); }
.lv-level-icon.heating { color: var(--lv-q3-fg); }
.lv-level-options > .seg.sm { padding: 0 8px; }
.mode-select { margin-left: auto; height: 36px; min-width: 100px; padding: 0 10px 0 14px; border-radius: 18px;
  font-weight: 500; font-size: 13px; background: var(--card-background-color, #fff); cursor: pointer; }
.mode-select:hover:not(:disabled) { border-color: var(--primary-color); }
.dc-stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.dc-stat { padding: 10px 12px; border-radius: 10px; background: var(--lv-tile); min-width: 0; }
.dc-val { display: flex; align-items: center; gap: 6px; font-size: 20px; font-weight: 500;
  font-variant-numeric: tabular-nums; white-space: nowrap; overflow: hidden; }
.dcard.offline .dc-val { color: var(--secondary-text-color); }
.dc-label { font-size: 11px; color: var(--secondary-text-color); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aqi-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; }
.aqi-dot.q1 { background: var(--lv-q1); } .aqi-dot.q2 { background: var(--lv-q2); }
.aqi-dot.q3 { background: var(--lv-q3); } .aqi-dot.q4 { background: var(--lv-q4); }
.aqi-badge { display: inline-flex; align-items: center; height: 22px; padding: 0 8px; margin-left: 8px;
  border-radius: 11px; font-size: 12px; font-weight: 500; vertical-align: middle; }
.aqi-badge.q1 { background: var(--lv-q1-bg); color: var(--lv-q1-fg); }
.aqi-badge.q2 { background: var(--lv-q2-bg); color: var(--lv-q2-fg); }
.aqi-badge.q3 { background: var(--lv-q3-bg); color: var(--lv-q3-fg); }
.aqi-badge.q4 { background: var(--lv-q4-bg); color: var(--lv-q4-fg); }

/* --- device page --- */
.toolbar .back { margin-left: -8px; }
.page-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin: 0 4px 12px; }
.page-head .spacer { flex: 1; }
.page-head .btn, .empty .btn { display: inline-flex; align-items: center; gap: 6px; }
.page-head .btn svg, .empty .btn svg { width: 18px; height: 18px; }
.notice.warn { background: rgba(255, 166, 0, 0.16); }
.hint { font-size: 12px; font-weight: 400; color: var(--secondary-text-color); margin-top: 2px; }
.hint.pad, .muted.pad { padding: 4px 16px 12px; }

.hero { padding: 20px; margin-bottom: 16px; }
.hero-main { display: flex; flex-wrap: wrap; align-items: center; gap: 24px 32px; }
.hero-controls { display: flex; align-items: center; gap: 18px; flex: 1 1 420px; min-width: 0; }
.lv-hero-controls { flex-basis: max-content; }
.hero-rows { flex: 1; display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.hero-status { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 10px; }
.hs-title { font-size: 22px; font-weight: 500; }
.hs-sub { font-size: 14px; color: var(--secondary-text-color); }
.hero-segs { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; }
.power { width: 72px; height: 72px; border-radius: 50%; cursor: pointer; flex: none;
  border: 1.5px solid var(--divider-color); background: none; color: var(--secondary-text-color);
  display: inline-flex; align-items: center; justify-content: center; transition: background 0.15s, box-shadow 0.15s; }
.power svg { width: 32px; height: 32px; }
.power.on { background: var(--primary-color); color: var(--text-primary-color, #fff); border-color: var(--primary-color);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--primary-color) 40%, transparent); }
.power.small.on { box-shadow: none; }
.power:disabled { opacity: 0.45; cursor: default; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; flex: 1 1 420px; }
.tile { padding: 12px 14px; border-radius: 10px; background: var(--lv-tile); min-width: 0; }
.t-val { font-size: 26px; font-weight: 500; font-variant-numeric: tabular-nums; margin-top: 2px; white-space: nowrap; }
.t-val .unit { font-size: 13px; font-weight: 400; color: var(--secondary-text-color); margin-left: 4px; }
.t-label { font-size: 12px; color: var(--secondary-text-color); }
.hero .setting { padding: 16px 0 0; margin-top: 16px; border-top: 1px solid var(--divider-color); }

/* segmented buttons: a track with the picked one raised */
.segs { display: inline-flex; flex-wrap: wrap; gap: 2px; padding: 3px; border-radius: 20px; background: var(--lv-track); }
.seg { font: inherit; font-size: 14px; font-weight: 500; cursor: pointer; height: 34px; padding: 0 14px;
  border-radius: 17px; border: 0; background: none; color: var(--secondary-text-color); min-width: 40px; white-space: nowrap; }
.seg:hover:not(:disabled) { color: var(--primary-text-color); }
.seg.on { background: var(--card-background-color, #fff); color: var(--lv-accent-text);
  box-shadow: inset 0 0 0 1.5px var(--primary-color), 0 1px 2px rgba(0, 0, 0, 0.12); }
.seg:disabled { opacity: 0.45; cursor: default; }
.segs.dim .seg.on { box-shadow: inset 0 0 0 1.5px var(--divider-color); color: var(--secondary-text-color); }
.opts { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 20px 16px; }
.opt { font: inherit; font-size: 14px; cursor: pointer; height: 36px; min-width: 44px; padding: 0 14px;
  border-radius: 18px; border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); }
.opt:hover:not(:disabled) { border-color: var(--primary-color); color: var(--lv-accent-text); }
.opt:disabled { opacity: 0.45; cursor: default; }

.sections { columns: 2 420px; column-gap: 16px; }
.section { break-inside: avoid; margin-bottom: 16px; }
.sec-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 16px 20px 8px; }
.sec-head .btn { margin: -8px -8px -8px 0; }
details.section > summary { cursor: pointer; list-style: none; display: flex; align-items: center; justify-content: space-between; }
details.section > summary svg { color: var(--secondary-text-color); transition: transform 0.15s; }
details.section[open] > summary svg { transform: rotate(180deg); }
details.section > summary:hover { background: rgba(127, 127, 127, 0.06); }
details.section > summary::-webkit-details-marker { display: none; }
details.section > summary { padding-bottom: 12px; }
details.section[open] > summary { padding-bottom: 8px; }
.subhead { padding: 14px 20px 2px; font-size: 12px; font-weight: 500; text-transform: uppercase;
  letter-spacing: 0.04em; color: var(--secondary-text-color); border-top: 1px solid var(--divider-color); }
.setting { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 12px 20px;
  border-top: 1px solid var(--divider-color); }
.subhead + .setting { border-top: none; }
.setting.dim .s-label { opacity: 0.55; }
.s-label { font-size: 15px; min-width: 0; }
.s-label .hint { font-size: 13px; }
.s-control { flex: none; max-width: 65%; display: flex; justify-content: flex-end; }
.readout { font-variant-numeric: tabular-nums; color: var(--secondary-text-color); text-align: right; }

.switch { position: relative; width: 46px; height: 26px; border-radius: 13px; cursor: pointer; padding: 0;
  border: none; background: rgba(127, 127, 127, 0.55); transition: background 0.15s; flex: none; }
.switch span { position: absolute; top: 3px; left: 3px; width: 20px; height: 20px; border-radius: 50%;
  background: #fff; transition: transform 0.15s; }
.switch.on { background: var(--primary-color); }
.switch.on span { transform: translateX(20px); }
.switch:disabled { opacity: 0.45; cursor: default; }

.slider { display: flex; align-items: center; gap: 10px; }
.slider input { width: 160px; accent-color: var(--primary-color); }
.val { font-variant-numeric: tabular-nums; min-width: 64px; text-align: right; font-size: 14px; }
.stepper { display: inline-flex; align-items: center; gap: 6px; }
.stepper .val { min-width: 80px; text-align: center; }
.step { width: 40px; height: 40px; border-radius: 50%; cursor: pointer; font: inherit; font-size: 18px; line-height: 1;
  border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); }
.step:hover:not(:disabled) { background: rgba(127, 127, 127, 0.1); }
.step:disabled { opacity: 0.4; cursor: default; }
.times { display: inline-flex; align-items: center; gap: 6px; }
.times input { font: inherit; font-size: 14px; color: var(--primary-text-color); padding: 4px 6px;
  background: var(--input-fill-color, var(--secondary-background-color, transparent));
  border: 1px solid var(--divider-color); border-radius: 8px; }

.timer-run, .filter-big { padding: 8px 20px 16px; }
.timer-run .big, .filter-big .big { font-size: 34px; line-height: 1.1; font-weight: 500; font-variant-numeric: tabular-nums; }
.timer-run .big .muted, .filter-big .big .muted { font-size: 16px; font-weight: 400; }
.timer-run .big { font-size: 26px; }
.timer-run .bar, .filter-big .bar { height: 8px !important; border-radius: 4px !important; margin-top: 12px !important; }
.section .muted.pad { padding: 4px 20px 12px; font-size: 13px; }
.section .hint.pad { padding: 10px 20px 14px; border-top: 1px solid var(--divider-color); }
.timer-run .bar, .filter-big .bar { height: 6px; border-radius: 3px; margin-top: 8px; overflow: hidden;
  background: rgba(127, 127, 127, 0.2); }
.timer-run .bar span, .filter-big .bar span { display: block; height: 100%; background: var(--primary-color); }
.filter-big .bar span { background: var(--success-color, #43a047); }
.filter-big.low .bar span { background: var(--warning-color, #ffa600); }
.filter-big.bad .bar span { background: var(--error-color, #db4437); }

.history { margin-bottom: 16px; }
.hist-head { display: flex; align-items: center; gap: 10px 16px; flex-wrap: wrap; padding: 16px 20px 6px; }
.hist-head h2 { margin-right: auto; }
.legend { display: flex; flex-wrap: wrap; gap: 6px; }
.lg { font: inherit; font-size: 13px; display: inline-flex; align-items: center; gap: 8px; height: 34px; padding: 0 12px;
  border-radius: 17px; border: 1px solid var(--divider-color); background: none; color: var(--primary-text-color); cursor: pointer; }
.lg b { font-weight: 500; font-variant-numeric: tabular-nums; }
.lg:hover { border-color: var(--primary-color); }
.lg.off { opacity: 0.45; }
.lg.off .sw { background: none !important; box-shadow: inset 0 0 0 1.5px var(--secondary-text-color); }
.sw { width: 12px; height: 12px; border-radius: 3px; flex: none; }
.sw.c-pm { background: var(--lv-pm); } .sw.c-cadr { background: var(--lv-cadr); }
.sw.c-mist { background: var(--lv-q1); }
.sw.c-warm { height: 0; width: 14px; border-top: 2px dashed var(--lv-q4); border-radius: 0; }
.sw.band { width: 16px; height: 8px; border-radius: 2px;
  background: linear-gradient(90deg, var(--lv-q1) 25%, var(--lv-q2) 25% 50%, var(--lv-q3) 50% 75%, var(--lv-q4) 75%); }
.hist-band { display: block; width: 100%; height: 8px; border-radius: 4px; overflow: hidden; background: var(--lv-track); }
.hist-band .q1 { fill: var(--lv-q1); } .hist-band .q2 { fill: var(--lv-q2); }
.hist-band .q3 { fill: var(--lv-q3); } .hist-band .q4 { fill: var(--lv-q4); }
.hist-band .xhair { stroke: var(--primary-text-color); stroke-width: 1.5; vector-effect: non-scaling-stroke; }
.hist { position: relative; margin: 0 20px 14px; outline: none; transition: opacity 0.2s; }
.hist:focus-visible { outline: 2px solid var(--primary-color); outline-offset: 4px; border-radius: 4px; }
.hist.stale { opacity: 0.5; }
.hist-row { display: grid; grid-template-columns: 40px 1fr 40px; column-gap: 8px; }
.band-row { margin-top: 6px; }
.hist-y { position: relative; }
.ytick { position: absolute; right: 8px; transform: translateY(-50%); font-size: 11px;
  color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
.hist-plot { display: block; width: 100%; height: 150px; overflow: visible; }
.hist-plot .area.c-pm { fill: var(--lv-pm); fill-opacity: 0.14; }
.hist-plot .line.c-pm { stroke: var(--lv-pm); }
.hist-plot .line.c-cadr { stroke: var(--lv-cadr); }
.hist-plot .line.c-mist { stroke: var(--lv-q1); }
.hist-plot .line.c-warm { stroke: var(--lv-q4); }
.hist-levels { margin-top: 14px; }
.hist-levels .hist-plot { height: 76px; }
.hist-plot .line.dashed { stroke-dasharray: 5 3; }
.hist-y.left .ytick { right: 0; }
.hist-y.right .ytick { left: 0; right: auto; }
.ytick.c-pm { color: var(--lv-accent-text); }
.ytick.c-cadr { color: var(--lv-cadr); }
.sw.c-cadr.line { height: 0; border-radius: 0; background: none; border-top: 2px dashed var(--lv-cadr); width: 14px; }
.hist-plot .grid { stroke: var(--divider-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
.hist-plot .area { fill: var(--primary-color); fill-opacity: 0.1; stroke: none; }
.hist-plot .line { fill: none; stroke: var(--primary-color); stroke-width: 2; stroke-linejoin: round;
  stroke-linecap: round; vector-effect: non-scaling-stroke; }
.hist-plot .line.dot { stroke-width: 4; }
.hist-plot .xhair { stroke: var(--secondary-text-color); stroke-width: 1; vector-effect: non-scaling-stroke; }
.hist-empty { margin-left: 48px; padding: 8px 0; font-size: 13px; }
.hist-axis { position: relative; height: 20px; }
.xtick { position: absolute; top: 4px; transform: translateX(-50%); font-size: 11px; white-space: nowrap;
  color: var(--secondary-text-color); }
.hist-tip { position: absolute; top: 28px; z-index: 1; pointer-events: none; min-width: 120px;
  padding: 6px 10px; border-radius: 8px; font-size: 12px;
  background: var(--ha-card-background, var(--card-background-color, #fff));
  border: 1px solid var(--divider-color); box-shadow: 0 2px 8px rgba(0, 0, 0, 0.18); }
.tip-time { color: var(--secondary-text-color); margin-bottom: 4px; }
.tip-row { display: flex; justify-content: space-between; gap: 12px; line-height: 1.6; }
.tip-row strong { font-weight: 600; font-variant-numeric: tabular-nums; }
.tip-row span { color: var(--secondary-text-color); }

/* purifier groups */
.grp-intro { max-width: 640px; font-size: 14px; }
.page-head .btn.primary svg { width: 18px; height: 18px; }
.groups { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 400px), 1fr)); gap: 16px; }
.gcard { padding: 16px 20px 12px; display: flex; flex-direction: column; gap: 12px; }
.gc-head { display: flex; align-items: flex-start; gap: 12px; }
.gc-title { flex: 1; min-width: 0; }
.gc-name { font-size: 18px; font-weight: 500; color: var(--primary-text-color); }
.gc-status { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 12px;
  padding: 12px 14px; border-radius: 10px; background: var(--lv-track); }
.gc-reason { font-size: 13px; color: var(--secondary-text-color); margin-top: 6px; }
.pill { display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 10px; border-radius: 12px;
  font-size: 12px; font-weight: 500; white-space: nowrap; background: var(--card-background-color, #fff);
  color: var(--secondary-text-color); }
.pill i { width: 7px; height: 7px; border-radius: 50%; background: var(--secondary-text-color); }
.pill.act { background: color-mix(in srgb, var(--primary-color) 14%, var(--card-background-color, #fff)); color: var(--lv-accent-text); }
.pill.act i { background: var(--primary-color); }
.pill.watch i { background: var(--success-color, #43a047); }
.pill.warn { background: var(--lv-q3-bg); color: var(--lv-q3-fg); }
.pill.warn i { background: var(--lv-q3); }
.lvl { display: inline-flex; gap: 3px; }
.lvl i { width: 22px; height: 8px; border-radius: 2px; background: var(--divider-color); }
.lvl i.f { background: var(--primary-color); }
.gc-mode { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; }
.gc-mode .hint { margin: 0; }
.gc-member { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0;
  border-top: 1px solid var(--divider-color); font-size: 14px; }
.gc-mname { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gc-member > span:last-child { white-space: nowrap; }
.accent { color: var(--lv-accent-text); font-weight: 500; }
.gc-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.gc-foot .btn { margin-left: auto; }
.sug-wrap { margin-top: 24px; }
.sug-wrap h2 { margin: 0 4px; }
.sug-wrap > .hint { margin: 2px 4px 12px; font-size: 13px; }
.sug { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 16px; padding: 14px 20px; margin-bottom: 12px;
  border: 1px dashed var(--divider-color); border-radius: 12px; background: var(--card-background-color, #fff); }
.sug > svg { color: var(--secondary-text-color); }
.sug-text { flex: 1; min-width: 200px; }
.sug-name { font-size: 15px; font-weight: 500; }
.toolbar .subtitle { font-size: 12px; opacity: 0.8; line-height: 1.2; }
.toolbar .title:has(.subtitle) { line-height: 1.25; }
.tb-btn.strong { border: 1px solid currentColor; }

.group-chip { font: inherit; font-size: 12px; font-weight: 500; border: 0; cursor: pointer; }
.group-chip svg { width: 14px; height: 14px; }
.group-chip.act { background: color-mix(in srgb, var(--primary-color) 14%, transparent); color: var(--lv-accent-text); }
.group-chip:hover { filter: brightness(0.95); }
.group-banner { display: flex; flex-wrap: wrap; align-items: center; gap: 12px 16px; padding: 14px 20px; margin-bottom: 16px; }
.gb-icon { color: var(--lv-accent-text); display: inline-flex; }
.gb-text { flex: 1; min-width: 220px; }
.gb-title { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 10px; font-size: 15px; }
.gb-title b { font-weight: 500; }
.gb-reason { font-size: 13px; color: var(--secondary-text-color); margin-top: 4px; }
.group-banner .btn { margin: 0; }
/* group editor */
.ged { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }
.ged-main { flex: 999 1 560px; min-width: 0; display: flex; flex-direction: column; gap: 16px; }
.ged-main .section { margin: 0; overflow: visible; }
.ged-aside { flex: 1 1 300px; min-width: 0; position: sticky; top: calc(var(--header-height, 56px) + 16px); }
.now-note { padding: 8px 4px 0; }
.ged-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; padding: 8px 20px 16px; }
.field { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: var(--secondary-text-color); }
.inp { font: inherit; font-size: 15px; height: 40px; padding: 0 12px; border-radius: 8px; box-sizing: border-box;
  border: 1px solid var(--divider-color); background: var(--card-background-color, #fff); color: var(--primary-text-color); }
.num { font: inherit; font-size: 14px; width: 68px; height: 34px; padding: 0 8px; border-radius: 8px; box-sizing: border-box;
  border: 1px solid var(--divider-color); background: var(--card-background-color, #fff); color: var(--primary-text-color);
  text-align: right; font-variant-numeric: tabular-nums; }
.inp:focus, .num:focus { outline: 2px solid var(--primary-color); outline-offset: -1px; border-color: transparent; }
.num-unit { display: inline-flex; align-items: center; gap: 8px; }
.inp.sm { height: 32px; font-size: 13px; padding: 0 6px; }
.num-unit .hint { margin: 0; }
.ged-modes { display: flex; flex-wrap: wrap; gap: 8px; justify-content: flex-end; }
.sec-head .tag { margin-left: 8px; vertical-align: middle; }
.tag { display: inline-flex; align-items: center; height: 20px; padding: 0 8px; border-radius: 10px; font-size: 11px;
  font-weight: 500; background: var(--lv-track); color: var(--secondary-text-color); white-space: nowrap; }
.tag.sug { background: color-mix(in srgb, var(--primary-color) 14%, transparent); color: var(--lv-accent-text); }
.tag.err { background: var(--lv-q4-bg); color: var(--lv-q4-fg); }
.mem { display: flex; align-items: center; gap: 14px; padding: 10px 20px; border-top: 1px solid var(--divider-color); cursor: pointer; }
.mem.dis { cursor: default; opacity: 0.55; }
.mem input { width: 20px; height: 20px; margin: 0; accent-color: var(--primary-color); flex: none; }
.mem .dev-tile { width: 36px; height: 36px; border-radius: 10px; }
.mem .dev-tile svg { width: 28px; height: 28px; }
.mem-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.mem-name { font-size: 15px; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; justify-content: flex-end; }
.stype { display: flex; align-items: flex-start; gap: 16px; padding: 12px 20px; border-top: 1px solid var(--divider-color); }
.stype-label { width: 104px; flex: none; padding-top: 8px; font-size: 14px; font-weight: 500; }
.stype-chips { display: flex; flex-wrap: wrap; gap: 8px; flex: 1; min-width: 0; }
.stype-chips > .hint { padding-top: 9px; margin: 0; }
.schip { display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 4px 0 12px; border-radius: 18px;
  border: 1px solid var(--divider-color); font-size: 13px; white-space: nowrap; }
.schip b { font-weight: 500; }
.schip button { width: 28px; height: 28px; padding: 0; border-radius: 50%; border: 0; background: none; cursor: pointer;
  color: var(--secondary-text-color); display: inline-flex; align-items: center; justify-content: center; }
.schip button svg { width: 16px; height: 16px; }
.schip button:hover { background: var(--lv-track); color: var(--primary-text-color); }
.add-wrap { position: relative; padding: 12px 20px 16px; border-top: 1px solid var(--divider-color); }
.add-wrap > .btn { margin: 0; display: inline-flex; align-items: center; gap: 6px; }
.add-wrap > .btn svg { width: 18px; height: 18px; }
.menu { position: absolute; top: 56px; left: 20px; z-index: 3; width: min(380px, calc(100% - 40px)); max-height: 320px;
  overflow: auto; padding: 6px; box-sizing: border-box; border-radius: 12px; background: var(--card-background-color, #fff);
  border: 1px solid var(--divider-color); box-shadow: 0 8px 24px rgba(0, 0, 0, 0.16); }
.menu .mh { padding: 8px 12px 4px; font-size: 11px; font-weight: 500; color: var(--secondary-text-color);
  text-transform: uppercase; letter-spacing: 0.04em; }
.menu button { width: 100%; display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 40px;
  padding: 0 12px; border: 0; border-radius: 8px; background: none; color: var(--primary-text-color); font: inherit;
  font-size: 14px; text-align: left; cursor: pointer; }
.menu button:hover { background: var(--lv-track); }
.menu .hint { margin: 0; }
.mono-id { font-family: ui-monospace, monospace; font-size: 11px; color: var(--secondary-text-color);
  overflow: hidden; text-overflow: ellipsis; }
.menu-empty { padding: 6px 12px 10px; }
.tbl-scroll { overflow-x: auto; padding-right: 14px; }
.grid-tbl { display: grid; grid-template-columns: minmax(170px, 1fr) repeat(var(--cols), minmax(64px, auto));
  align-items: stretch; font-size: 14px; min-width: max-content; }
.grid-tbl > div { padding: 8px 6px; border-top: 1px solid var(--divider-color); white-space: nowrap;
  display: flex; align-items: center; justify-content: center; gap: 4px; font-variant-numeric: tabular-nums; }
.grid-tbl > .gh { font-size: 12px; font-weight: 500; color: var(--secondary-text-color); border-top: 0; }
.grid-tbl > .gl { justify-content: flex-start; flex-wrap: wrap; padding-left: 20px; }
.grid-tbl .hint { margin: 0; }
.rise { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 12px; padding: 14px 20px;
  border-top: 1px solid var(--divider-color); font-size: 15px; }
.rise .hint { margin: 0; }
.stype .combine { flex: none; display: flex; align-items: center; gap: 8px; padding-top: 2px; }
.stype .combine .hint { margin: 0; }
.grid-tbl > .cur { background: color-mix(in srgb, var(--primary-color) 8%, transparent); }
.grid-tbl > .gh.lvh { flex-direction: column; gap: 0; }
.grid-tbl > .gh.lvh span { font-weight: 400; }
.grid-tbl.speeds .gl { flex-direction: column; align-items: flex-start; gap: 2px; }
.grid-tbl.speeds .gl .hint { font-size: 11px; }
.lgs { display: flex; flex-wrap: wrap; gap: 6px 16px; padding: 8px 20px 4px; }
.lg { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--secondary-text-color); }
.lg i { width: 12px; height: 12px; border-radius: 3px; }
.lg i.q1 { background: var(--lv-q1); } .lg i.q2 { background: var(--lv-q2); }
.lg i.q3 { background: var(--lv-q3); } .lg i.q4 { background: var(--lv-q4); }
.th-row { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 20px; padding: 10px 20px 6px;
  border-top: 1px solid var(--divider-color); }
.th-row .stype-label { padding-top: 0; }
.ms { position: relative; height: 62px; flex: 1 1 360px; min-width: 0; }
.ms .trk { position: absolute; left: 10px; right: 10px; top: 28px; height: 8px; border-radius: 4px; }
.ms input { position: absolute; left: 0; top: 21px; width: 100%; height: 22px; margin: 0; padding: 0;
  -webkit-appearance: none; appearance: none; background: transparent; pointer-events: none; }
.ms input::-webkit-slider-runnable-track { background: transparent; height: 22px; }
.ms input::-moz-range-track { background: transparent; }
.ms input::-webkit-slider-thumb { -webkit-appearance: none; pointer-events: auto; width: 20px; height: 20px; margin-top: 1px;
  border-radius: 50%; background: var(--card-background-color); border: 2px solid var(--primary-text-color);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3); cursor: grab; }
.ms input::-moz-range-thumb { pointer-events: auto; width: 16px; height: 16px; border-radius: 50%;
  background: var(--card-background-color); border: 2px solid var(--primary-text-color); cursor: grab; }
.ms input:focus-visible::-webkit-slider-thumb { outline: 2px solid var(--primary-color); outline-offset: 2px; }
.ms .mv { position: absolute; top: 2px; transform: translateX(-50%); font-size: 12px; font-weight: 600;
  white-space: nowrap; font-variant-numeric: tabular-nums; }
.ms .mt { position: absolute; top: 46px; transform: translateX(-50%); font-size: 10.5px;
  color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
.lmaps { display: flex; flex-wrap: wrap; gap: 6px; padding: 4px 0 8px; }
.lmap { display: inline-flex; align-items: center; height: 24px; padding: 0 8px; border-radius: 12px;
  font-size: 12px; font-weight: 500; white-space: nowrap; }
.lmap.q1 { background: var(--lv-q1-bg); color: var(--lv-q1-fg); }
.lmap.q2 { background: var(--lv-q2-bg); color: var(--lv-q2-fg); }
.lmap.q3 { background: var(--lv-q3-bg); color: var(--lv-q3-fg); }
.lmap.q4 { background: var(--lv-q4-bg); color: var(--lv-q4-fg); }
.gd { display: flex; flex-direction: column; gap: 16px; }
.gd-controls { margin: 0; padding: 20px; display: flex; flex-wrap: wrap; align-items: center; gap: 24px 32px; }
.gd-main { display: flex; align-items: center; gap: 18px; flex: 1 1 380px; min-width: 0; }
.gd-power { width: 72px; height: 72px; flex: none; border-radius: 50%; border: 1.5px solid var(--divider-color);
  background: transparent; color: var(--secondary-text-color); display: inline-flex; align-items: center;
  justify-content: center; cursor: pointer; padding: 0; }
.gd-power svg { width: 30px; height: 30px; }
.gd-power.on { background: var(--primary-color); border-color: var(--primary-color); color: #fff; }
.gd-state { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.gd-state .hint { margin: 0; }
.gd-title { font-size: 22px; font-weight: 500; }
.gd-segs { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 6px; }
.gd-tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; flex: 1 1 520px; }
.gd-tile { background: var(--lv-track); border-radius: 10px; padding: 12px 14px; min-width: 0; }
.gd-tl { font-size: 12px; color: var(--secondary-text-color); }
.gd-tv { display: flex; align-items: baseline; gap: 6px; margin-top: 2px; }
.gd-tv b { font-size: 24px; font-weight: 500; }
.gd-tv span { font-size: 12px; color: var(--secondary-text-color); }
.gd-tn { display: flex; align-items: center; gap: 6px; margin-top: 4px; font-size: 11px; color: var(--secondary-text-color);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gd-dot { width: 8px; height: 8px; border-radius: 50%; flex: none; background: var(--divider-color); display: inline-block; }
.gd-dot.q1 { background: var(--lv-q1); } .gd-dot.q2 { background: var(--lv-q2); }
.gd-dot.q3 { background: var(--lv-q3); } .gd-dot.q4 { background: var(--lv-q4); }
.gd-dot.cadr { background: var(--lv-cadr); }
.gd-note { margin: -8px 4px 0; }
.gd .history { margin: 0; }
.gd-cols { display: flex; flex-wrap: wrap; gap: 16px; align-items: flex-start; }
.gd-card { margin: 0; overflow: hidden; min-width: 0; }
.gd-wide { flex: 999 1 600px; }
.gd-side { flex: 1 1 300px; }
.gd-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 16px 20px 10px; }
.gd-head h2 { margin: 0; font-size: 16px; font-weight: 500; }
.gd-head .hint { margin: 2px 0 0; }
.gd-row { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 16px; padding: 12px 20px;
  border-top: 1px solid var(--divider-color); }
.gd-who { flex: 1 1 200px; min-width: 0; }
.gd-name { display: block; font-size: 15px; font-weight: 500; color: var(--primary-text-color); text-decoration: none;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gd-name:hover { color: var(--lv-accent-text); }
.gd-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin-top: 4px; }
.gd-meta .hint { margin: 0; }
.gd-chips { display: flex; flex-wrap: wrap; gap: 6px; flex: 1 1 220px; }
.gd-chip { gap: 6px; font-variant-numeric: tabular-nums; }
.gd-chip b { font-weight: 500; }
.gd-filter { flex: none; width: 112px; }
.gd-xrow { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 12px 20px;
  border-top: 1px solid var(--divider-color); }
.sw.c-pm1 { background: var(--lv-pm1); } .sw.c-pm10 { background: var(--lv-pm10); }
.sw.c-pm1, .sw.c-pm10 { height: 0; border-radius: 0; width: 14px; border-top: 2px solid; background: none; }
.sw.c-pm1 { border-color: var(--lv-pm1); } .sw.c-pm10 { border-color: var(--lv-pm10); }
.hist-plot .line.c-pm1 { stroke: var(--lv-pm1); } .hist-plot .line.c-pm10 { stroke: var(--lv-pm10); }
.ytick.c-pm1, .ytick.c-pm10 { color: var(--lv-accent-text); }
.now-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: -6px -8px 0 0; }
.play { width: 40px; height: 40px; padding: 0; border-radius: 50%; border: 0; background: var(--primary-color);
  color: #fff; display: inline-flex; align-items: center; justify-content: center; cursor: pointer; flex: none; }
.play svg { width: 20px; height: 20px; }
.play:hover:not(:disabled) { filter: brightness(1.08); }
.play:disabled { opacity: 0.4; cursor: not-allowed; }
.err-line { padding: 8px 20px 12px; font-size: 13px; color: var(--error-color, #db4437); }
.now { padding: 18px 20px; }
.now-k { font-size: 12px; font-weight: 500; color: var(--secondary-text-color); text-transform: uppercase; letter-spacing: 0.04em; }
.now-title { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px;
  margin-top: 8px; font-size: 24px; font-weight: 500; }
.now-reason { font-size: 14px; color: var(--secondary-text-color); margin-top: 6px; }
.now-h { margin-top: 16px; font-size: 12px; font-weight: 500; color: var(--secondary-text-color); }
.now-row { display: flex; justify-content: space-between; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--divider-color); font-size: 14px; }
.now-row > span:first-child { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.now-row b { font-weight: 500; white-space: nowrap; }
.now-row > span:last-child { flex: none; white-space: nowrap; }
.now-row .hint { display: inline; margin: 0; }
.ged .sec-head { flex-wrap: wrap; }
.ged .segs { flex-wrap: nowrap; }
@media (max-width: 900px) {
  .ged-aside { position: static; }
}
@media (max-width: 600px) {
  .stype { flex-wrap: wrap; }
  .stype-label { width: auto; padding-top: 0; }
  .mem { padding: 10px 16px; }
  .tags { display: none; }
  .grid-tbl { grid-template-columns: minmax(84px, 1fr) repeat(var(--cols), minmax(48px, auto)); min-width: 0; }
  .grid-tbl > div { padding: 6px 3px; }
  .grid-tbl > .gl { padding-left: 16px; white-space: normal; }
  .grid-tbl .num { width: 50px; padding: 0 4px; }
}

@media (max-width: 600px) {
  .hero-controls { align-items: flex-start; flex-basis: 100%; }
  .power:not(.small) { width: 60px; height: 60px; }
  .tiles { flex-basis: 100%; }
  .hist-head h2 { flex-basis: 100%; }
  .setting { flex-wrap: wrap; }
  .s-control { max-width: 100%; }
  .slider input { width: 120px; }
}

@media (max-width: 1100px) {
  .tb-btn span { display: none; }
  .tb-btn { width: 40px; padding: 0; }
  table, tbody { display: block; }
  thead { display: none; }
  tr { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 16px;
    padding: 12px 16px; border-bottom: 1px solid var(--divider-color); }
  tbody tr:last-child { border-bottom: none; }
  tr.has-update { box-shadow: inset 3px 0 0 var(--warning-color, #ffa600); }
  tr.has-update td:first-child { box-shadow: none; }
  td { display: block; padding: 0 !important; border: none; }
  td[data-label]::before { content: attr(data-label); display: block; font-size: 11px;
    color: var(--secondary-text-color); margin-bottom: 1px; }
  td.device { grid-column: 1 / -1; }
  td.device::before { display: none !important; }
  td.device .name { font-size: 16px; }
  td.actions { grid-column: 1 / -1; text-align: left; display: flex; gap: 8px; margin-top: 4px; }
  td.actions .btn { margin: 0; flex: 1; }
}
@media (max-width: 420px) {
  .content { padding: 8px; }
  tr { grid-template-columns: 1fr; }
}
`;

customElements.get("levoit-esphome-panel") ||
  customElements.define("levoit-esphome-panel", LevoitEsphomePanel);
