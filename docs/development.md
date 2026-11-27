# Development

Home Assistant does not run on Windows; run the tests on Linux, macOS or in
WSL:

```bash
pip install -r requirements_test.txt
ruff check . && ruff format --check .
pytest
```

The README screenshots come from a running Home Assistant with the sidebar
page on, through [`scripts/screenshots.py`](../scripts/screenshots.py) (headless
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

[← Back to the README](../README.md)
