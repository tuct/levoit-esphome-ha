# Levoit ESPHome

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/P4P721ETB5)

A Home Assistant integration for air purifiers and humidifiers running the
`levoit` or `philips` ESPHome components of
**[tuct/levoit](https://github.com/tuct/levoit)**: the project that takes
Levoit and Philips purifiers off the cloud, with the components, device
configs and wiring guides.

What it does, in three parts:

### 1. Use and set up your purifiers

A sidebar page with every purifier as a card: power, mode and speed, PM2.5,
AQI and CADR at a glance. Each purifier has a page of its own with its air
quality history and all its settings, grouped instead of one long list.
[More](#use-and-set-up-your-purifiers)

<p>
  <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/overview.png?v=0.6.8" width="49%" alt="The sidebar page: seven purifiers as cards, each with power, mode and speed, PM2.5, AQI and CADR">
  <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/device-page.png?v=0.6.8" width="49%" alt="The Everest Air's page: power, mode and speed, PM2.5, PM1.0, PM10, AQI and CADR, its group, the 24 hour history and the settings">
</p>

### 2. Run several purifiers as one group

Combine purifiers into a group, for example everything in one room. In
*Auto* the group follows shared air sensors and sets every purifier's speed
by itself: up at once when the air gets worse, down step by step when it
clears. Each group is also one fan entity, so a dashboard, voice or an
automation runs the whole room like one purifier.
[More](#purifier-groups)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/groups.png?v=0.6.8" width="49%" alt="Purifier groups: a group of two purifiers in Auto at level 3 of 4, and a suggested room">

### 3. Manage and update the devices

It finds every ESPHome device built with those components, links it to its
config in the ESPHome Device Builder, and offers an update when the device's
channel has a newer component version. Installing compiles the config in the
Device Builder and uploads it over the air. *Add device* makes the config for
a new purifier.
[More](#manage-and-update-the-devices)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/panel-updates.png?v=0.6.8" width="49%" alt="Updates and config: every device with its channel, installed and latest version, and Compile and Update">

> **Early version.** Part of the
> [firmware update plan](https://github.com/tuct/levoit/blob/main/docs/firmware-updates.md).


## Use and set up your purifiers

Turn on **Settings → Devices & services → Levoit ESPHome → ⚙ (Configure) →
Show in the sidebar** for a *Levoit ESPHome* page, visible to admins only. It
has three tabs and updates live. It is a plain web component served by the
integration; nothing is loaded from outside Home Assistant. After updating the
integration, reload the browser once to get the new page.

### Devices tab

Every purifier as a card, for using them. A line on top counts the purifiers
running, off and offline, and names the one with the worst air. Each card has a
small outline of the model, an air quality dot, power, the mode and the speed,
PM2.5, AQI (the level 1–4 and its word, *1 Very good* to *4 Poor*) and the
current CADR, the filter left, and the time left when a timer runs. Chips under
the model show an update that is out and the purifier's group (tinted while
the group runs it). Offline cards keep their controls, greyed out. Click a
card for the device's page.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/overview.png?v=0.6.8" width="720" alt="Devices: purifiers as cards with power, mode and speed, PM2.5, AQI and CADR">

### Device page

On top, power, mode and speed with PM2.5, AQI and CADR (the Eleva 300X also
shows its AQI index, 0–500). Below, the **history** of the last 12 hours, 24
hours, 7 days or 30 days from Home Assistant's statistics, in one chart: PM2.5 as an area
(left axis), CADR as a dashed line (right axis) and the air quality level as a
coloured band under it; the legend chips switch each one on and off. A
purifier in a group shows a banner with the group's status and what a change
here does.

Then the settings, grouped instead of one long list: *Automatic* (auto mode,
room size only when it applies), *Sleep* (the Vital 200S custom profile: quick
clean, sleep, then daytime mode), *Quiet period* (Eleva 300X, start and end as
times), *Timer* (quick picks and the time left), *Display & panel*, *Filter*
(life %, lifetime, reset) and *Info*. For the Core 200S / 300S / 400S / 600S,
Vital 100S / 200S, Everest Air and Eleva 300X; other models link to Home
Assistant's device page. It needs no Device Builder config: the settings are
found by their entity names, as the tuct/levoit configs name them (or as the
device's config does, when there is one).

The LV600S page uses the ESPHome fan from `levoit` model `LV600S` for power,
mist level and operating mode. It also shows humidity, temperature, tank
status, warm mist and the timer. The older standalone component still appears
in the device list and links to its Home Assistant device page.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/device-page.png?v=0.6.8" width="720" alt="A device page: power, mode and speed, PM2.5, AQI and CADR, the 24 hour history in one chart, and the settings">

## Purifier groups

Run 2 or more purifiers together from shared air sensors, for example
everything in one room. Groups run in the integration, so they keep working
with the page closed and after a restart.

* **The level:** 1 (very good air) to 4 (poor). Each sensor type (PM1, PM2.5,
  PM10, the purifiers' AQI index) gives a level: PM values on the group's
  thresholds, the AQI index 1–4 as it is. Several sensors of one type are
  combined into one value: the highest (default), average, median or lowest.
  The worst type sets the group's level. It goes up at once and down one step
  per hold time (2 minutes); a fast rise in PM2.5 jumps straight to level 4.
* **The purifiers** each have a lowest and a highest step. Level 1 runs at the
  lowest (Off, Sleep or a speed; speed 1 by default), level 4 at the highest,
  and levels 2 and 3 in between. With 4 steps in that range or fewer, each
  level takes the next step and the rest stay at the highest (Sleep to 3:
  Sleep, 1, 2, 3; 1 to 2: 1, 2, 2, 2). With more, levels 2 and 3 are spread
  evenly, Sleep counting as half a speed, and the bigger jumps come first (Off
  to 4: Off, 2, 3, 4). The Everest Air counts its Turbo as speed 4, so its
  highest is Turbo unless set to 3.
* **Letting go:** when no sensor has a value, the group is switched off or
  deleted, or a purifier leaves it, the group sends nothing: each keeps
  running as it is.
* **By hand:** if someone changes a purifier, the group leaves that one alone
  for 30 minutes.
* **Manual:** one level for all its purifiers instead of following the sensors.
* **Apply now:** ▶ in the editor runs the saved settings at once: the
  sensors' level without waiting for the hold time, also for purifiers that
  were changed by hand.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/groups.png?v=0.6.8" width="720" alt="Purifier groups: each group with its level, reason, sensors and purifiers">

Each group has a page of its own: power, Auto or Manual and the level, a tile
per sensor type with the group's combined value and the purifiers' total
CADR, their history over 12 hours, 24 hours, 7 days or 30 days with the level
as a band, and its
purifiers with their state, sensors and filter. *Edit group* opens the editor.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/group-page.png?v=0.6.8" width="720" alt="A group's page: power, Auto or Manual and level 1 to 4, tiles for PM2.5, AQI index and CADR, the 24 hour history with the level as a band, and its two purifiers">

The editor picks the sensors from the purifiers and takes others from Home
Assistant, sets how several sensors of one type are combined, the thresholds,
the hold time and each purifier's lowest and highest step, and shows live what
the group would do right now. Rooms in Home Assistant with 2 or more purifiers
are suggested as groups.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/group-editor.png?v=0.6.8" width="720" alt="The group editor: purifiers, sensors, thresholds, the speed each purifier runs per level, and what the group would do now">

Each group gets a device of its name, for dashboards, voice and automations:

| Entity | What it shows / does |
|--------|----------------------|
| **The group** (fan) | The whole group like one purifier: on / off is *Control*, preset *Auto* or *Manual*, and its 4 speeds set the level for all purifiers (Manual) |
| **Control** (switch) | Off: the group leaves its purifiers alone |
| **Level** (sensor) | 1–4, the level the group runs at, with the reason; 0 while it lets go |
| **Air quality** (sensor) | 1–4, the worst sensor type on the group's thresholds; also in Manual or with the group off |
| **Active** (binary sensor) | On while the group runs its purifiers |
| **PM1**, **PM2.5**, **PM10**, **AQI index** (sensors) | The group's combined value of each sensor type it has (as set in the editor: highest, average, median or lowest), with its level and sensors. Only for the types the group has a sensor of: added and removed as you change its sensors |
| **CADR** (sensor) | The total CADR of its purifiers, m³/h |

Groups saved by 0.6 keep working: their sensors of the Eleva's 0–500 AQI
are dropped, PM2.5 keeps where levels 2–4 started, and the max speed and *Up
to* become each purifier's highest speed. Level 1 now runs the purifiers at
their lowest step instead of letting go.

## Dashboard cards

Cards for any Home Assistant dashboard, for every user (not only admins). The
integration loads them on every page: no resource to add. In the dashboard
editor, *Add card* lists them as **Levoit purifier**, **Levoit group** and
**Levoit list**.

### Purifier card

```yaml
type: custom:levoit-purifier-card
entity: fan.levoit_core600s_c3_fan   # the purifier's fan
show: [pm25, aqi, cadr, filter, group]   # no key: all; a new card lists them
controls: [speed, mode]                  # default: both
grid_options:
  columns: 12   # 6 = medium / small, 3 = compact
  rows: 4       # 4 = large / medium, 2 = small, 1 = compact
```

The card follows its size in a sections view: **large** (12 × 4) with PM2.5,
AQI and CADR, the speeds and a mode list; **medium** (6 × 4) with PM2.5 large,
CADR, filter, speeds and modes; **small** (6 × 2) with the speeds; **compact**
(6 × 1 or 3 × 1) with the state only. The icon or the name opens the fan's
dialog; on the small and compact cards the icon turns it on and off. Turbo
shows as the top speed (the Everest Air's Turbo mode, the Eleva's level 4).
In Sleep, Auto or Pet the speeds are dimmed and show what it runs at; picking
one switches to Manual.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-purifier.png?v=0.6.8" width="720" alt="The purifier card in its sizes: large with PM2.5, AQI, CADR, speeds and mode; small with the speeds; medium with PM2.5 large, the speeds and the modes; compact with the state only">

### Group card

```yaml
type: custom:levoit-group-card
entity: fan.living_room   # the group's fan (or group: <its id>)
show: [pm25, aqi, cadr, members]   # no key: all; a new card lists them
controls: [mode, level]            # default: both
grid_options:
  columns: 12   # 6 = medium / small, 3 = compact
  rows: 5       # 4 = medium, 2 = small, 1 = compact
```

**Large** (12 × 5): the status with the level as 4 bars, PM2.5 (and how it is
combined, "avg of 4"), the AQI index, the total CADR, a chip per purifier with
what it runs at, Auto / Manual and the levels. **Medium** (6 × 4): PM2.5 large
with the air quality, the purifiers and CADR, Auto / Manual and the levels.
**Small** (6 × 2): Auto and the levels in one row. **Compact** (6 × 1 or
3 × 1): "Auto · L4 · 360 µg/m³". The power button (on small cards the icon) is
the group's control: off lets go of the purifiers and greys out the controls.
A level switches the group to Manual at that level. Without an AQI index the
group shows its air quality (its own thresholds, 1–4).

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-group.png?v=0.6.8" width="720" alt="The group card in its sizes: large with the level bars, PM2.5, AQI index, CADR, its purifiers, Auto or Manual and the levels; medium; small with Auto and the levels in one row; compact">

### List card

```yaml
type: custom:levoit-list-card
title: Air purifiers
items: all            # groups / devices / a list of group ids and fan ids
nest_members: true    # the purifiers under their group
controls: [mode, speed, power]
grid_options:
  columns: 12         # 6 = narrow: the controls on a second line
  rows: auto
```

A row per group and purifier: its PM2.5 and air quality, the mode and the
speed (for a group the level) as lists, and power. The name opens the dialog.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-list.png?v=0.6.8" width="720" alt="The list card: a group with its two purifiers under it, then the other purifiers, each with PM2.5, mode, speed or level and power; narrow at 6 columns with the lists on a second line">

## Manage and update the devices

Firmware updates for every purifier, in Home Assistant's *Updates* and on
the sidebar page's *Updates & config* tab, and *Add device* for new ones.

### Updates & config tab

The sidebar page's third tab has:

* every device: model, ESP / config type, channel, installed → latest
  component version, filter %, ESPHome version, status and the last build
* the latest releases on top, with **Update all** (one device after the other)
* **Compile** and **Compile and upload** (*Update* when one is out), with the
  build's step and progress live per device (the compile counter, the upload
  bar), the result, and under **Log** the steps with the last lines or the
  full output
* the channel of a device without a config or with a template config
* configs made by *Add device* that are **not flashed yet**, with what to do
  next; they can be compiled, but not uploaded until the first USB flash
* links to each device's page, the Device Builder and Add device; *check now*
  reads the latest versions from GitHub without waiting for the 6 hours

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/panel-updates.png?v=0.6.8" width="720" alt="Updates and config: every device with model, channel, installed and latest version, and Compile, Update and Log">

A running build, in the row and under **Log**: the steps, the compile counter
with the file being built, then the upload with its bar.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/build-log.png?v=0.7.1" width="720" alt="A running build: the device row says Compile 111 / 117 with a bar; the Log dialog shows Setup done with ESP-IDF 5.5.6, Compile running at 111 of 117 on main.cpp, Link and image, Result and Upload queued, and the last lines of the output">
<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/build-log-upload.png?v=0.7.1" width="720" alt="The same build uploading: Setup, Compile with 107 files, Link and image with a 900 KB image and Result with RAM 30.3 % and Flash 50.2 % done, Upload at 74 % with its bar, and the upload's progress lines">

### Extra ESP or original ESP

Most of these purifiers have an ESP32 for Wi-Fi and a separate MCU that runs
the purifier, talking over UART. ESPHome can run on that ESP in two ways:

| | **Extra ESP** (recommended) | **Original ESP** |
|---|---|---|
| What | A small ESP of your own, wired to the MCU's UART; the original ESP stays on the board, held in reset | The purifier's own ESP, flashed with ESPHome |
| Hardware | A [Seeed XIAO ESP32-C3](https://www.seeedstudio.com/Seeed-XIAO-ESP32C3-p-5431.html) or [XIAO ESP32-S3](https://www.seeedstudio.com/XIAO-ESP32S3-p-5627.html) (or any ESP32 ESPHome supports) and a few wires: power, GND, RX, TX, and the original ESP's EN to GND | None |
| Back to stock | Remove the wires: the stock firmware was never touched | Restore a backup of the stock flash over its UART pads |
| First flash | Over USB from the Device Builder, before you wire it in | Over the board's UART pads, usually with the purifier open |
| Risk | Low: a bad build only hits your ESP, which you can reflash over USB at your desk | A bad build can leave the purifier offline until you open it again |
| Locked modules | Works with every model, also those whose stock ESP can't be flashed (Philips AC0650: secure boot) | Only modules without secure boot |

**Why extra:** the purifier's stock firmware stays intact, and a broken build
is never more than a USB cable away from fixed. The XIAO boards are small
enough to fit inside many of these purifiers (the device guides say where).

### Extra ESP: install it and keep it updated

1. *Add device* → **New device** → the model → **Seeed XIAO ESP32-C3** or
   **Seeed XIAO ESP32-S3**. For another board pick **Other ESP**: any ESPHome
   board name and your own RX / TX pins.
2. The integration makes the Device Builder config: name, API key and OTA
   password generated, Wi-Fi from your secrets.
3. Flash it once over USB from the Device Builder (the config → **Install** →
   **Plug into this computer**), then wire it in (see the model's guide in
   [tuct/levoit/devices](https://github.com/tuct/levoit/tree/main/devices)).
   Until then the sidebar page lists it as *Not flashed yet*. Once it is on
   your Wi-Fi, the integration adds it to Home Assistant's ESPHome
   integration by itself: no *discovered device* to confirm.
4. From then on, every new component version shows up in **Settings →
   Updates** and installs over the air.

### Original ESP, already flashed: keep it updated

Flashed the purifier's own ESP with the `levoit` component already? *Add
device* → **Device already in Home Assistant** → the model → **Original ESP**
gives it a Device Builder config. It keeps its name and API key (Home Assistant
keeps the device), and updates come over the air like for any other device.

<details>
<summary><b>Walkthrough:</b> a Core 400S on its original ESP, from 1.3.1 to 1.7.2</summary>

1. *Add device* → **Device already in Home Assistant, without a config**

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-01-menu.png" width="420" alt="Add device: New device, or Device already in Home Assistant without a config">

2. Pick the device. Its config gets the device's own name and API key

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-02-device.png" width="420" alt="Existing device: Levoit-Core400S">

3. The model: asked here because firmware 1.3.1 has no `model` sensor yet

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-03-model.png" width="420" alt="Model: Levoit Core 400S">

4. **Original ESP**

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-04-esp.png" width="420" alt="ESP: Original ESP, Seeed XIAO ESP32-S3, Seeed XIAO ESP32-C3 or Other ESP">

5. Channel, and the OTA password the device was built with (the API key comes from Home Assistant)

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-05-details.png" width="420" alt="Update channel stable, OTA password entered; the API key is stored as levoit_core400s_api_key">

6. The config is in the Device Builder

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-06-done.png" width="420" alt="Success: config levoit-core400s.yaml created">

7. The sidebar page lists it as **Original ESP** with an update from 1.3.1

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-07-update-available.png" width="720" alt="Core 400S, Original ESP, 1.3.1, Update available">

8. **Update** asks first

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-08-confirm.png" width="560" alt="Compile Levoit-Core400S in the ESPHome Device Builder and upload it over the air?">

9. It compiles in the Device Builder …

   <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-09-building.png" width="720" alt="Core 400S building">

10. … uploads over the air (ESPHome 2026.5.3 on the device, 2026.11.0 in the Device Builder) …

    <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-10-uploading.png" width="720" alt="Core 400S uploading, ESPHome 2026.5.3, builder 2026.11.0">

11. … and the purifier runs 1.7.2 and ESPHome 2026.11.0

    <img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/original-esp-11-up-to-date.png" width="720" alt="Core 400S, 1.7.2, up to date, uploaded 11:41 PM">

</details>

### Already running, but no config in the Device Builder

A purifier that runs the `levoit` or `philips` firmware already (extra or
original ESP), but whose config is not in this Device Builder: flashed from a
PC with the ESPHome CLI, from another Device Builder, or the config is lost.

The integration finds it anyway, by its `esp_version` (or `model`) sensor: it
shows on the sidebar page with **No config**, and its update entity says when a
new version is out, but cannot install it yet. To onboard it:

1. *Add device* → **Device already in Home Assistant, without a config** →
   pick the device. (**Add config** on its row of the sidebar page opens the
   integration page, where *Add device* is.)
2. **Model:** skipped when the device reports it; firmware older than 1.7.1
   has no `model` sensor, so pick it.
3. **ESP:** the template that matches its hardware (XIAO ESP32-C3, XIAO
   ESP32-S3, original ESP), or **Other ESP** with its board and the RX / TX
   pins it uses now. **They must match how the device is wired**: the next
   update flashes this config. With wrong pins the ESP still starts and stays
   on Wi-Fi, but can't talk to the purifier; fix the pins and update again,
   over the air. With a wrong board the new firmware may not start at all,
   and then only a USB reflash helps. If unsure, take board and pins from the
   config it was built with.
4. **Channel**, and its **OTA password** if it has one: Home Assistant does
   not know it, and the update is uploaded with it. Leave it empty if the
   device has none.

The config keeps the device's **name**, so Home Assistant keeps the device and
its history, and its **API encryption key**, taken from Home Assistant's
connection to the device and stored as `<name>_api_key` in `secrets.yaml`.
Wi-Fi comes from the `wifi_ssid` / `wifi_password` / `wifi_ap_password`
secrets, which must exist. The device moves from *No config* to *Update
available*; the first update builds the new config and installs it over the air.

Have the old config at hand and want to keep it as it is? Paste it into the
Device Builder instead (under the device's name). The integration picks it up
as a **custom** config; a pasted builder file of tuct/levoit counts as a
template.

### Supported models

The templates *Add device* offers per model (✓). **Other ESP** works for every
model, with your board and pins.

| Model | XIAO ESP32-C3 | XIAO ESP32-S3 | Original ESP: updates through this integration |
|---|---|---|---|
| Levoit Core 200S | ✓ | ✓ | not tested yet |
| Levoit Core 300S | ✓ | ✓ | not tested yet |
| Levoit Core 400S | ✓ | ✓ | **works**: 1.3.1 → 1.7.2 ([walkthrough](#original-esp-already-flashed-keep-it-updated)) |
| Levoit Core 600S | ✓ | ✓ | not tested yet |
| Levoit Eleva 300X | | ✓ | not tested yet (stock ESP32-C3) |
| Levoit Everest Air | ✓ | ✓ | not tested yet |
| Levoit Superior 6000S | | ✓ | not tested yet |
| Levoit Vital 100S | ✓ | ✓ | not tested yet (stock ESP32-C3) |
| Levoit Vital 200S | ✓ | ✓ | not tested yet (stock ESP32-C3) |
| Philips 600 series (AC0650) | ESP32-C3 template | ✓ | not possible: secure boot |
| Philips 900 series (AC0950) | ✓ | ✓ | |

> **Running the `levoit` firmware on the original ESP of one of these?**
> Add it with *Add device* → *Device already in Home Assistant*, install an
> update, and [tell us how it went](https://github.com/tuct/levoit-esphome-ha/issues/new?title=Original%20ESP%3A%20%3Cmodel%3E):
> the model, and whether the update went through. Each report moves a model
> in this table from *not tested yet* to *works*.

### Entities per purifier

Per purifier, on a device of the same name (its *Visit* link opens the ESPHome Device Builder); Home Assistant lists the purifier's
ESPHome device under *Linked devices* (same MAC address). Since Home Assistant
2026.8 an integration cannot add entities to another integration's device.

Devices made with *Add device* sit under their own entry, the others under
*Devices that don't belong to a sub-entry*:

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/integration-page.png" width="640" alt="The integration page: devices with a Device Builder config under their Add device entry, the others below">

**With a config in the Device Builder** the integration reads model and
channel from it and can install updates; for a template config the *Update
channel* select switches the channel. **Without one** it still shows whether
an update is out: pick the channel in the device's *Update channel* select
(default `stable`); the model comes from the device's `model` text sensor.
Installing and compiling need the config.

| Entity | What it shows / does |
|--------|----------------------|
| **Component firmware** (update) | Installed component version against the newest one on the device's channel; release notes; *Install* compiles and uploads |
| **Compile firmware** (button) | Compiles in the Device Builder without uploading |
| **Compile and upload** (button) | Compiles and uploads over the air at any time, also when the device is up to date (a template config is refreshed from the newest builder file first, like *Install*) |
| **Filter life** | The purifier's filter % from its own ESPHome filter sensor (`%` with the `mdi:air-filter` icon or "filter" in its name; HEPA over pre-filter) |
| **Installed component version** | What the device reports, e.g. `1.7.0` or `1.7.0+3fa21c4` |
| **Latest component version** | Newest version on the device's channel (release + commit), *unknown* without a channel |
| **Component model** | `model:` from the config, else from the device's `model` text sensor, e.g. `CORE300S` |
| **Firmware channel** | `stable` (releases), `main` (every merge), `pinned` (another ref or a fork) or `local`; from the config, else the select below |
| **Update channel** (select) | `stable` / `main`. Without a Device Builder config: which channel to compare the device with. With a template config: rewrites `ref:` in the config, the next install builds from it. Unavailable for a custom config: change its `ref:` yourself |
| **Device Builder config** | The config file the device is built from |
| **Config type** | `original` / `xiao_c3` / `c3` / `s3`: made from a template; `custom`: your own config |

A newer **ESPHome** version is already offered by Home Assistant's own ESPHome
firmware update; this integration adds the component version.

Component updates show in **Settings → Updates** under *Levoit ESPHome*, like
other firmware updates: install them one by one or with *Update all*. A device
without a Device Builder config is not listed there, as there is nothing to
install yet.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/updates-page.png" width="560" alt="Settings, Updates: the Levoit ESPHome card with Update all and four purifiers on component 1.7.2, one installing">

Each update shows the installed and the latest version, with the release notes
(stable) or a link to the new commits (main):

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/update-dialog.png" width="380" alt="The Component firmware update of a purifier: installed 1.3.0, latest 1.7.2, with the release notes, installing">

### Add device

**Settings → Devices & services → Levoit ESPHome → Add device** makes a Device
Builder config from a template of tuct/levoit
([`devices/templates.json`](https://github.com/tuct/levoit/blob/main/devices/templates.json)):
pick the model and the ESP (original, Seeed XIAO ESP32-C3, ESP32-C3, Seeed XIAO ESP32-S3),
or **Other ESP** for a board or pins without a template: enter the ESPHome board
name (e.g. `seeed_xiao_esp32s3`, `esp32dev`, `esp32-c6-devkitc-1`) and the RX / TX
pins, and the config is made from the model's builder file with those.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/add-device-model.png" width="420" alt="Add device: pick the model">

* **New device:** a name is suggested; a new API encryption key is
  generated and stored in the Device Builder's `secrets.yaml` as
  `<name>_api_key`, and OTA updates are encrypted with it (a Device Builder
  older than ESPHome 2026.9.0 gets an OTA password instead, as
  `<name>_ota_password`). Flash it once over USB from the Device Builder;
  after that, updates come over the air. As soon as the
  flashed ESP is on the network (every 30 s it looks for `<name>.local`), the
  integration adds it to the ESPHome integration with the key from the Device
  Builder, so there is no discovered device to confirm. If the ESP needs
  input it cannot give (a different key, a name clash), it is left to Home
  Assistant's usual discovery
* **Device already in Home Assistant without a config:** it keeps its name
  and its API encryption key, which is taken from Home Assistant's ESPHome
  connection to the device (none there: no encryption) and stored as
  `<name>_api_key`. Home Assistant does not know the OTA password, so the
  flow asks for it (leave it empty if the device has none)
* Wi-Fi comes from the shared `wifi_ssid`, `wifi_password` and
  `wifi_ap_password` secrets, which must exist. The integration reads secret
  **names** only, never values, and never overwrites an existing secret

**Template configs follow the templates.** A config made from a template (or a
pasted builder file) is recognised by its first line,
`# levoit-esphome-ha: template=...`. Every update rewrites it from the newest
builder file first, keeping its name, secrets and channel, then compiles and
uploads. The header under that line says so. **To customise such a config,
delete its first line first**: otherwise the next update overwrites your
changes. Without it the config is **custom**, like one made with *Other ESP*:
it is never rewritten, and updates only build the newer component it pulls
through its `ref:`.

#### Encrypted native OTA

New configs encrypt OTA updates with the device's API key (`ota: encryption:`
without a key of its own). Template refreshes preserve the native ESPHome OTA
encryption key and API key, whether inline or referenced by `!secret`. If
`ota.encryption` is left empty, OTA continues to use the API encryption key.
An explicit OTA key must resolve to the same value as a configured API key.
The integration inspects the YAML without loading packages or looking up
secret values. Refresh supports a standalone template with the native API,
one native OTA transport, and an upstream Main or Stable source. Other layouts
stop before writing or building. Key rotation (`old_key`) and migration that
permits a plaintext upload (`allow_plaintext_upload`) also require a custom
config. Remove the template marker to manage that file manually. Use a Device
Builder version that supports native OTA encryption for an encrypted device.

**From an OTA password to encryption.** A template config made before this
version has `password: !secret <name>_ota_password`. It migrates over two
updates, as the [ESPHome documentation](https://esphome.io/components/ota/esphome/)
describes: the next update installs with the password as before, and the
firmware it installs (ESPHome 2026.9.0 or newer, with an API key) offers
encryption; right after that upload the integration swaps the password line
for `encryption:`, a text change, and the row says *OTA encrypted from the
next update on*. The update after that is encrypted. Nothing to do; the
`<name>_ota_password` secret stays in `secrets.yaml`, unused (the integration
never deletes a secret). Should an encrypted upload be refused because the
device does not offer encryption, the password line comes back while the
secret exists, and the row says so. A custom config is not touched. ESPHome
removes the plain password path in 2027.3.0: update every device once before
then.

### How it works

* Devices: every ESPHome device whose Device Builder config loads `levoit` or
  `philips`, or that has an `esp_version` sensor reporting a component version
  or a `model` sensor reporting a known model (both matched by their state, so
  their names do not matter). A device found once stays listed while
  it is offline (*Offline* on the sidebar page, its entities unavailable) and
  is back as soon as it reports again. One that is gone for good can be
  deleted on its device page (*⋮ → Delete*), if it has no Device Builder
  config
* Model and channel come from the resolved config (`esphome config` in the
  Device Builder). That output contains resolved secrets; the integration keeps
  only the model and the source, and reads each config at most every 6 hours
  or after a build
* Newest versions: the latest release and the `stable` / `main` heads of
  tuct/levoit on GitHub, every 6 hours
* Behind on `stable`: a newer release is out (a build from `main` after that
  release is not behind). Behind on `main`: it runs another commit than the
  head of `main`; a build without a commit in its version (1.7.0 and older) is
  compared by release number. A local `.dirty` build is never offered an update

#### How an update reaches the purifier

Everything runs on your Home Assistant host; the purifier only receives the
finished firmware over Wi-Fi.

1. **Config** (template configs only): the integration rewrites the config in
   the Device Builder from the newest builder file, through the Device
   Builder's API, keeping the name, secrets and channel. A custom config is
   left as it is.
2. **Compile:** the integration asks the Device Builder (the ESPHome add-on) to
   compile the config. It fetches the component from GitHub at the config's
   `ref:` (`stable` or `main`) and builds the firmware on the Home Assistant
   host. The first build takes a few minutes; later ones are faster. If the
   compile fails, nothing is uploaded.
3. **Upload over Wi-Fi:** the Device Builder connects to the purifier's ESP
   with ESPHome's own OTA protocol (TCP port 3232), finds it by its name
   (`<name>.local`, mDNS), authenticates with the configured OTA encryption key
   or legacy password, and sends the firmware. The ESP
   writes it into its **second app partition** while the current firmware keeps
   running, checks it (SHA-256), switches the boot partition to it and restarts.
   A connection that drops halfway leaves the old firmware running.
4. **Back online:** the ESP reconnects to Wi-Fi and to Home Assistant (with its
   API key), and reports the new version through its `esp_version` sensor. The
   update entity shows *Up to date*, the sidebar page *Uploaded HH:MM*.

What the upload needs, and what goes wrong otherwise:

| Needed | If not |
|--------|--------|
| The Home Assistant host reaches the ESP on TCP 3232 (same network, or routed without a firewall in between) | *Upload failed*; the device keeps its firmware |
| `<name>.local` resolves from the host (mDNS). Across VLANs or subnets mDNS often doesn't pass | *Upload failed*. Make mDNS pass (a reflector), or give the device a fixed address in a custom config (`wifi: use_address:`) |
| The OTA password in `secrets.yaml` matches the one the device was built with | *Upload failed*; fix the secret in the Device Builder (*Secrets*) and update again |
| The new firmware starts on this hardware (right board) | The ESP doesn't come back and needs a USB reflash. The configs don't enable ESPHome's `safe_mode`, so there is no automatic fallback |

The Device Builder streams the compile and upload output to the integration and
keeps none of it itself; it reports no progress of its own. The integration
reads the output into steps, *setup, compile, link and image, result, upload*,
each queued, running or done: for an ESP-IDF build the compile step counts the
files (`312 / 1065`, from the build tool's counter) and the upload step shows
its bar, the result step the Flash and RAM used. The device's row shows the
running step; **Log** shows all steps with the last 15 lines, or on request the
whole kept output (the last 400 lines), following a running build. The update
entity's progress bar follows the same counters. When a build fails, the
running step shows the reason (the last error line), the error message names
it, and the last 40 lines go into Home Assistant's log (*Settings → System →
Logs*).

## Requirements

* Home Assistant 2026.11 or newer
* The **ESPHome Device Builder add-on**, found by Home Assistant's ESPHome
  integration (Home Assistant OS or Supervised). A standalone Device Builder is
  not supported yet
* For installing updates: each device's config in that Device Builder, for
  example a pasted builder file from
  [tuct/levoit](https://github.com/tuct/levoit/tree/main/devices)
* The `esp_version` text sensor in the device config (the builder files have
  it); it is how the integration reads the installed version
* Optional, for devices without a Device Builder config: the `model` text sensor
  (`type: model`, tuct/levoit after 1.7.0)
* The channel comes from the component's source in the config:

  ```yaml
  external_components:
    - source:
        type: git
        url: https://github.com/tuct/levoit
        ref: stable      # or main
      components: [levoit]
      refresh: always    # fetch on every build; the default (1d) can rebuild an old commit
  ```

## Installation

Not in the default Marketplace catalog yet. Add it as a custom repository:
**Settings → Marketplace → ⋮ → Custom repositories**, enter
`https://github.com/tuct/levoit-esphome-ha`, type *Integration* (needs a
one-time GitHub sign-in). Install it, then add **Levoit ESPHome** under
**Settings → Devices & services**.

## Development

Home Assistant does not run on Windows; run the tests on Linux, macOS or in
WSL:

```bash
pip install -r requirements_test.txt
ruff check . && ruff format --check .
pytest
```

The README screenshots come from a running Home Assistant with the sidebar
page on, through [`scripts/screenshots.py`](scripts/screenshots.py) (headless
Edge or Chrome, with a long-lived access token of an admin):

```bash
pip install playwright
HA_URL=http://homeassistant.local:8123 HA_TOKEN=<token> python scripts/screenshots.py
```

It saves `overview.png`, `device-page.png`, `groups.png`, `group-page.png`,
`group-editor.png` and `panel-updates.png` to `images/`, and the dashboard cards
in their sizes as `cards-purifier.png`, `cards-group.png` and `cards-list.png`
(drawn on the page as a sections view would, nothing is added to a dashboard).
Home Assistant has to run the version in the manifest. `--device` and `--group`
pick which device and group, `--only overview groups` takes some, `--dark` uses the dark theme,
`--sidebar` keeps Home Assistant's sidebar and `--scale 2` makes them
sharper.
