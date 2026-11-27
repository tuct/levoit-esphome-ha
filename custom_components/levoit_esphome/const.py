"""Constants for Levoit ESPHome."""

from datetime import timedelta

DOMAIN = "levoit_esphome"

# ESPHome components from tuct/levoit that make a device ours.
COMPONENTS = frozenset({"levoit", "philips", "lv600s_humidifier"})

# `model:` values of those components (VALID_MODELS in components/levoit and
# components/philips __init__.py). The `model` text sensor is recognised by its
# state being one of these; add new models here when the components get them.
KNOWN_MODELS = frozenset(
    {
        "CORE200S",
        "CORE300S",
        "CORE400S",
        "CORE600S",
        "LV600S",
        "ELEVA300X",
        "EVERESTAIR",
        "SPROUT",
        "SUPERIOR6000S",
        "VITAL100S",
        "VITAL200S",
        "AC0650",
        "AC0651",
        "AC0950",
        "AC0951",
    }
)

GITHUB_REPO = "tuct/levoit"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}"
VERSION_FILE = "components/levoit/VERSION"

CHANNEL_STABLE = "stable"
CHANNEL_MAIN = "main"
# A ref that is neither: a tag, a fork, a local path. No updates offered.
CHANNEL_PINNED = "pinned"
CHANNEL_LOCAL = "local"

# Device Builder device list and Home Assistant states.
SCAN_INTERVAL = timedelta(minutes=5)
# how often to look for a device made by Add device after its first flash
AUTO_ADD_INTERVAL = timedelta(seconds=30)
# Releases and branch heads on GitHub (unauthenticated API: 60 requests/hour).
GITHUB_INTERVAL = timedelta(hours=6)
# Model and channel read from each config. Every read runs `esphome config` in
# the Device Builder, so it is cached.
CONFIG_INTERVAL = timedelta(hours=6)

# Options
CONF_SHOW_PANEL = "show_panel"

# Sidebar panel (admins only, behind the show_panel option)
PANEL_URL_PATH = "levoit-esphome"
PANEL_COMPONENT = "levoit-esphome-panel"
PANEL_STATIC_URL = "/levoit_esphome_static"
# Coordinator replaced (entry set up again): panel subscriptions re-attach
SIGNAL_COORDINATOR = f"{DOMAIN}_coordinator"
