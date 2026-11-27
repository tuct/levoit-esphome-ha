<div align="center">

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/logo.png?v=0.8.0" width="112" alt="Levoit ESPHome logo: a blue house with the letters LE, the E's middle arm a wave of air">

# Levoit ESPHome

**The Home Assistant integration for purifiers running the [tuct/levoit](https://github.com/tuct/levoit) firmware.**<br>
Use them, run a room as one group, and update their firmware, all from Home Assistant.

[![HACS custom repository](https://img.shields.io/badge/HACS-custom-41BDF5)](#installation)
[![Home Assistant 2026.11 or newer](https://img.shields.io/badge/Home%20Assistant-%E2%89%A5%202026.11-18BCF2?logo=homeassistant&logoColor=white)](#requirements)
[![Release](https://img.shields.io/github/v/release/tuct/levoit-esphome-ha?label=release&color=0E8F8A)](https://github.com/tuct/levoit-esphome-ha/releases/latest)
[![License](https://img.shields.io/github/license/tuct/levoit-esphome-ha?color=6B7A83)](./LICENSE)

[![Support me on Ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/P4P721ETB5)

[Features](#features) · [Installation](#installation) · [Requirements](#requirements) · [Supported models](#supported-models) · [Documentation](#documentation)

</div>

## Features

### Your purifiers at a glance

A sidebar page with every purifier as a card: power, mode and speed, PM2.5,
AQI and CADR, an air quality dot, and the filter and timer left. A line on top
counts the purifiers running, off and offline, and names the one with the worst air.
[More](docs/sidebar-page.md#devices-tab)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/overview.png?v=0.8.1" width="720" alt="The sidebar page: purifiers as cards, each with power, mode and speed, PM2.5, AQI and CADR">

### A page per purifier

Power, mode and speed with PM2.5, AQI and CADR on top, the air quality history
over 12 hours to 30 days in one chart, and all the settings grouped:
automatic, sleep, timer, display, filter.
[More](docs/sidebar-page.md#device-page)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/device-page.png?v=0.8.1" width="720" alt="A purifier's page: power, mode and speed, PM2.5, AQI and CADR, the 24 hour history and the settings">

### Dashboard cards

Three cards for any dashboard and every user, not only admins. They load by
themselves, with no resource to add.
[More](docs/sidebar-page.md#dashboard-cards)

**Purifier card:** one purifier in four sizes, from large to compact.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-purifier.png?v=0.8.1" width="720" alt="The purifier card in its sizes: large with PM2.5, AQI, CADR, speeds and mode; medium; small with the speeds; compact with the state only">

**Group card:** a group with its level, its combined PM2.5 and AQI, the total CADR and a chip per purifier, in four sizes.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-group.png?v=0.8.1" width="720" alt="The group card in its sizes: large with the level bars, PM2.5, AQI index, CADR, its purifiers, Auto or Manual and the levels; medium; small with Auto and the levels in one row; compact">

**List card:** a row per group and purifier, the purifiers under their group, with PM2.5, mode, speed or level and power.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/cards-list.png?v=0.8.1" width="720" alt="The list card: a group with its two purifiers under it, then the other purifiers, each with PM2.5, mode, speed or level and power">

### Air purifier groups

Run two or more purifiers as one, for example everything in a room. Groups
run inside the integration, so they keep working with the page closed and
after a restart.

- **Auto from your air sensors.** PM1, PM2.5, PM10 and the purifiers' AQI
  give a level from 1 (very good) to 4 (poor), and the worst one counts. The
  level goes up at once and comes down one step at a time. A fast rise in
  PM2.5 jumps straight to 4.
- **Each purifier its own range.** Set a lowest and a highest step per
  purifier (Off, Sleep or a speed), and the levels are spread between them.
- **Hands off when you take over.** Change a purifier by hand and the group
  leaves it alone for 30 minutes. With no sensor value, it lets go entirely.
- **Manual** runs one level on every purifier in the group.
- **One fan entity per group**, for dashboards, voice and automations, with
  sensors for the level, the air quality, the combined PM values and the
  total CADR.
- **Rooms with two or more purifiers** are suggested as groups.

[More](docs/groups.md)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/groups.png?v=0.8.1" width="720" alt="Purifier groups: each group with its level, reason, sensors and purifiers">

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/group-page.png?v=0.8.1" width="720" alt="A group's page: power, Auto or Manual and level 1 to 4, tiles for PM2.5, AQI index and CADR, the history with the level as a band, and its purifiers">

### Firmware updates

Every ESPHome device built with the `levoit` or `philips` component is found
and linked to its config in the ESPHome Device Builder. When the device's
channel has a newer component version, an update shows up under *Settings →
Updates* with its release notes.
[More](docs/updates.md)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/panel-updates.png?v=0.8.1" width="720" alt="Updates and config: every device with its channel, installed and latest version, and Compile and Update">

*Install* compiles the config and uploads it over the air. You can follow
each step live: setup, compile with a file count, link, then the upload with
its percentage.

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/build-log-upload.png?v=0.7.1" width="720" alt="A build uploading: Setup, Compile with 107 files, Link and image with a 900 KB image and Result with RAM 30.3 % and Flash 50.2 % done, Upload at 74 % with its bar, and the upload's progress lines">

### Add a new purifier

*Add device* walks you through it, one step at a time. Pick the model, with
its photo and notes from [tuct/levoit](https://github.com/tuct/levoit), then
the ESP: the original one, a Seeed XIAO ESP32-S3 / C3, or your own board.
Give it a name and a channel, see exactly what gets written, and create the
config with its own keys. It compiles right away, with the build's steps
live; you flash it once over USB from the Device Builder, and after that,
updates come over the air.
[More](docs/updates.md#add-device)

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/add-device-1-model.png?v=0.8.1" width="720" alt="Which purifier: the models with a template, each with its photo, status, CADR, how easy it is to open and the ESPs it has a template for; below them the models with a guide but no template">

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/add-device-2-esp.png?v=0.8.1" width="720" alt="Which ESP for the Levoit Core 300S: original ESP, Seeed XIAO ESP32-S3, Seeed XIAO ESP32-C3, or Other ESP with your own board and pins">

<img src="https://raw.githubusercontent.com/tuct/levoit-esphome-ha/main/images/add-device-7-compile.png?v=0.8.1" width="720" alt="Compile: Setup done with ESP-IDF 5.5.6, Compile running at 40 of 936 files with its bar, and the build output below">

> **Early version.** Part of the
> [firmware update plan](https://github.com/tuct/levoit/blob/main/docs/firmware-updates.md).

## Installation

[![Open your Home Assistant instance and open this repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tuct&repository=levoit-esphome-ha&category=integration)

1. **Add the repository.** It is not in the default Marketplace catalog yet.
   Use the button above, or go to **Settings → Marketplace → ⋮ → Custom
   repositories**, enter `https://github.com/tuct/levoit-esphome-ha` and pick
   type *Integration* (needs a one-time GitHub sign-in).
2. **Install** *Levoit ESPHome* and restart Home Assistant.
3. **Add the integration** under **Settings → Devices & services**, or here:

   [![Add the Levoit ESPHome integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=levoit_esphome)
4. **Optional:** turn on **Configure → Show in the sidebar** for the
   *Levoit ESPHome* page.

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

## Supported models

The templates *Add device* offers per model (✓). **Other ESP** works for every
model, with your board and pins.

| Model | XIAO ESP32-C3 | XIAO ESP32-S3 | Original ESP: updates through this integration |
|---|---|---|---|
| Levoit Core 200S | ✓ | ✓ | not tested yet |
| Levoit Core 300S | ✓ | ✓ | not tested yet |
| Levoit Core 400S | ✓ | ✓ | **works**: 1.3.1 → 1.7.2 ([walkthrough](docs/updates.md#original-esp-already-flashed-keep-it-updated)) |
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

## Documentation

| Page | What is in it |
|---|---|
| [Sidebar page and dashboard cards](docs/sidebar-page.md) | The Devices tab, the device page with its history and settings, and the purifier, group and list cards |
| [Purifier groups](docs/groups.md) | Making a group, how *Auto* follows the air, and the group's fan entity |
| [Manage and update](docs/updates.md) | The Updates & config tab, extra or original ESP, *Add device*, encrypted OTA, and how an update reaches the purifier |
| [Entities per purifier](docs/entities.md) | What the integration adds for each purifier |
| [Development](docs/development.md) | Tests, and how the README screenshots are made |

The firmware, the device configs and the wiring guides live in
**[tuct/levoit](https://github.com/tuct/levoit)**.
