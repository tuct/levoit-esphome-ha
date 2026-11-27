# Entities per purifier

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

[← Back to the README](../README.md)
