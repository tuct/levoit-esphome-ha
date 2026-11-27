# Guided onboarding: plan

*Add device* today is a Home Assistant config flow: five plain forms on the
integration page, then "flash it in the Device Builder" and a row on the
sidebar page that waits. It works, but it cannot show a photo, a wiring
note or progress, and it ends before the device is on the network.

This plan moves onboarding into the sidebar panel as a wizard with the same
backend: pick the model, pick the ESP, name it, and the integration makes the
config, compiles it, flashes it where it can, and waits for the device. The
screens can carry photos and notes per model and ESP, added later without
touching the flow. The config flow stays as the plain route.

## What exists and stays

| Piece | Where | Reused as |
|---|---|---|
| Templates: model × ESP from `devices/templates.json` of tuct/levoit | `templates.py` | the model and ESP lists |
| Rendering a builder file with name, API key, OTA credential, channel | `templates.py` `render`, `render_custom`, `_apply_values` | unchanged; already writes both an OTA password and OTA encryption |
| Secrets: names read, never values; never overwritten | `device_builder.py` | unchanged |
| Create config, pending list, auto-add when `<name>.local` answers (every 30 s) | `config_flow.py` `_async_create`, `coordinator.py` | the create and connect steps |
| Compile and upload through the Device Builder, with the build steps | `coordinator.py` `async_build`, `build_log.py` | the build and flash steps |
| The config flow forms | `config_flow.py` | kept, thin, as the fallback |

## The wizard

Entry: the panel's **Add device** button (today it links to the integration
page). Route `/levoit-esphome/add`, one screen per step, back and forward,
the state kept in the panel until the config is created.

| Step | Shows | Picks | Source |
|---|---|---|---|
| 1 Model | a card per model with a photo, the family (Core, Vital / Everest / Sprout / Eleva, humidifiers, Philips), one line on what the conversion takes | the model | `templates.json`; photos and notes from the content file (below), the line drawings as fallback |
| 2 ESP | the ESPs with a template for that model: original ESP, Seeed XIAO ESP32-C3, ESP32-C3, Seeed XIAO ESP32-S3, and Other; each with a photo, where it goes, a link to the device's wiring notes | the variant, or board and pins for Other | `templates.json`; `COMMON_BOARDS` and `builder_esp()` for Other |
| 3 Device | new, or one Home Assistant already knows without a config (listed with model and name) | new or existing | `coordinator.data.devices` without a configuration |
| 4 Name and channel | a suggested name, the channel; for an existing device its name, fixed | name, channel | `suggest_name`, the Device Builder listing for taken names |
| 5 Protection | what will be written (below), no input for a new device; for an existing device the OTA password field if it has one | the OTA password, if any | the rule below |
| 6 Create | the secrets and the config written, the pending row appears | | `_async_create`, moved to `onboarding.py` |
| 7 Build | the compile with its steps and counter, as *Updates & config* shows it | | `async_build(upload=False)` |
| 8 Flash | see below: over the air when the ESP already runs ESPHome, else USB | | `async_build(upload=True)`, or the Device Builder |
| 9 Connect | "waiting for `<name>.local`", then the device with its page link | | the pending watcher; done when the device appears in the snapshot |

The wizard never asks for Wi-Fi: it comes from the shared `wifi_ssid`,
`wifi_password` and `wifi_ap_password` secrets, as today. Missing ones stop
step 6 with the secret names to add, with a link to the Device Builder's
secrets editor.

## Protection: OTA encryption, a password only where one exists

New configs get the native API encryption key and encrypted OTA that
inherits it (`ota: - platform: esphome` with `encryption:` and no key), the
form #63 made the template refresh keep. A password stays only where a
device already has one, so an existing device keeps updating.

| Device | API | OTA | Secret written |
|---|---|---|---|
| New | new key, `<name>_api_key` | `encryption:` inheriting the API key | `<name>_api_key` |
| Existing, Home Assistant has its key, no OTA password given | that key, `<name>_api_key` | `encryption:` inheriting it | `<name>_api_key` |
| Existing, an OTA password given | that key if known | `password: !secret <name>_ota_password` | both |
| Existing, no key known, no password | none | `encryption:` cannot inherit: none; the wizard says the first update will be over USB | none |

The rendering already refuses encryption and password together, and
inherited encryption without an API key. New: the Device Builder has to be
new enough for encrypted OTA; the wizard reads `esphome_current` from the
snapshot and falls back to a password with a note when it is not.

### Migrating devices that have an OTA password

Every template device made so far has `password: !secret <name>_ota_password`
and an API key. ESPHome's rules (2026.11, `espota2.py` and the `ota`
component) make the move to encryption a normal update:

- `password:` and `encryption:` cannot be combined in one `ota:` block.
- A firmware built with ESPHome 2026.9.0 or newer that has an
  `api: encryption: key` offers OTA encryption by itself, also when it was
  built with `password:`; the uploader then authenticates over noise with
  the API key and never needs the password.
- Only a firmware older than 2026.9.0 does not offer it. ESPHome's advice for
  that case is "install once without the `ota: encryption:` block, then
  restore it", which is a plain password update with a current Device
  Builder; the build it installs offers encryption from then on.

So the migration is two updates, and the integration does the step between
them:

1. The next update of a template device with `password:` runs as today: the
   refresh keeps the password, the build is installed with it. Built by a
   Device Builder of 2026.9.0 or newer, that firmware offers encryption.
2. Right after that upload succeeds, the integration rewrites the config to
   `encryption:` (inheriting the API key) in place of the password line, a
   text change, no build. The device row says so.
3. The next update uses encryption: the refresh keeps `encryption:`, the
   uploader authenticates with the API key, and from then on the device
   requires it.

The only condition is the Device Builder's version, `esphome_current` of
2026.9.0 or newer; the device's own version does not matter, since step 1
always installs a current build. No user input, no `allow_plaintext_upload`,
no `old_key`. Should the encrypted upload in step 3 be refused all the same
("Refusing to send the image in plaintext"), the refresh writes the password
line back and reports it, so the next update is a password update again.

The `<name>_ota_password` secret stays in `secrets.yaml`, unused: the
integration never deletes a secret. The README says so, and that the config
of a migrated device can be reverted by hand to the password line while the
secret exists. Custom configs are never rewritten, as before.

New configs from the config flow get `encryption:` at once, with the same
Device Builder version check; this does not wait for the wizard.

## Flash: over the air where possible, USB where not

Two cases, told apart by whether the ESP already runs ESPHome and answers on
the network:

- **Existing device** (step 3), or a new config whose ESP comes up with an
  older firmware: `async_build(upload=True)` through the Device Builder's
  API, with the upload bar. This is the "via the API" path and it exists.
- **Fresh ESP**: a first flash needs USB, which the Device Builder's API
  cannot do; its web UI does it with esp-web-tools in the browser. Two
  options, in order:
  1. **Link**, as today: open the Device Builder on this config, *Install*,
     *Plug into this computer*. Phase 3 ships this.
  2. **In the wizard**: esp-web-tools (`<esp-web-install-button>`) in the
     panel, with a manifest and the `firmware.factory.bin` served by a small
     `HomeAssistantView` that proxies the Device Builder's
     `download.bin?configuration=…&file=…` under Home Assistant's auth.
     Web Serial needs a secure context (HTTPS or localhost) and Chrome or
     Edge, the same limits the Device Builder has; the wizard offers it only
     when `isSecureContext && navigator.serial`, else the link. To verify
     first: that `download.bin` is reachable through the add-on's trusted
     address like `/compile` is, and the size of the vendored script
     (esp-web-tools is MIT, one file). Phase 5.

Either way the wizard ends in step 9 waiting for the device; the pending
watcher already adds it to the ESPHome integration with its key.

## Content: photos and notes per model and ESP

A file in tuct/levoit next to the templates, `devices/onboarding.json`,
fetched and cached like `templates.json` (from `main`), with per model:
title, family, photo, one line on the conversion, a link to the device
folder; per ESP variant of that model: photo, placement note, wiring link.
Photos are the existing ones under `devices/<model>/images/`, hotlinked from
`raw.githubusercontent.com`; the panel's line drawings stand in when the
browser cannot reach GitHub. The file is the editable part: adding a note or
a better photo is a PR in tuct/levoit, no release here. Models without a
template (LV600S until it is a `levoit` model; LV131, LV131S, Mini with
their hardware hacks) are listed with a link to their folder and no wizard.

## Architecture

- `onboarding.py`, new: the logic now inside `AddDeviceFlow` (templates,
  taken names, secrets, rendering, create config, pending), plain functions
  the config flow and the panel share. The config flow shrinks to forms over
  it.
- WebSocket commands for the panel, in `websocket.py`:
  `levoit_esphome/onboarding/options` (models, variants, existing devices,
  content, what the Device Builder supports),
  `levoit_esphome/onboarding/check_name`,
  `levoit_esphome/onboarding/create` (the whole step 6, returns the config
  name), then the existing `build` and `build_log`. Driving the config flow
  through `/api/config/config_entries/subentries/flow` was considered: it
  returns form schemas the panel would render as plain forms again, which
  is the thing to leave behind.
- The panel: a `_wizard()` view with the step state in `this._add`; photos
  as `<img>` with the drawing as fallback; steps 7 to 9 reuse `_buildChip`,
  `_stepsList` and the snapshot.
- Tests: `onboarding.py` with the fake Device Builder (names, secrets,
  rendered YAML for every protection case); the WS commands; the wizard's
  screens in quickjs per step and state, as the panel is tested now.

## Steps

0. **Encrypted OTA first**: new configs get `encryption:`; password devices
   migrate over two updates, the config rewritten after the first upload,
   with the write-back on a refused upload. Tests for every row of the
   protection table and the Device Builder version gate. Independent of the
   wizard, so it ships on its own.
1. **Extract**: `onboarding.py` and the WS commands, the config flow on top
   of it, no UI change. Tests moved and extended with the protection table.
2. **The wizard, to the config**: steps 1 to 6 in the panel, plain screens,
   the panel's Add device button opens it. The integration page flow stays.
3. **Build and flash**: steps 7 to 9, compile with the counter, OTA for an
   existing device, the Device Builder link for a fresh ESP, waiting for the
   device, done with the page link.
4. **Content**: `devices/onboarding.json` in tuct/levoit with the photos and
   notes that exist, the wizard shows them. From here the screens grow by
   editing that file.
5. **USB in the wizard** (optional): the firmware view and esp-web-tools,
   offered in a secure context.

Each step is one PR; 0 can release alone, 1 to 3 make a release, 4 and 5
follow.

## Open

- Keep the HA config flow as the plain route, or point the integration page's
  *Add device* at the panel too? Plan: keep it, thin.
- OTA password for an existing device: ask (today), or look it up in the
  device's current config when it has one (`config_values()` reads it)? Plan:
  look it up, ask only when there is none.
- esp-web-tools vendored into the integration, or loaded from a CDN? Plan:
  vendored; Home Assistant installs should not depend on a CDN.
- The LV600S enters the model list when it is a `levoit` model (humidifier
  plan step 3); until then it is a link.
