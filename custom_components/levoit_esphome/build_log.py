"""The output of one build, as the Device Builder streams it, read into steps.

The Device Builder reports no progress of its own: it streams the output of
`esphome compile` and `esphome upload`. For an ESP-IDF build that output
says enough to show where the build is, so the panel can show steps instead
of a spinner over a wall of text:

* setup    the `INFO` lines before the first object file: reading the config,
           generating the source, checking the ESP-IDF framework
* compile  `[312/1065] Building CXX object .../levoit_device.cpp.obj`, one
           line per file with the counter ninja prints
* link     `Linking CXX executable <name>.elf`, the binary image, its size
* result   the `RAM:` and `Flash:` lines, then `Successfully compiled`
* upload   `INFO Uploading ... (820227 bytes)`, the `Uploading: [====] 50%`
           bar, `Upload took 12.3 seconds`, `OTA successful`

The steps come from the stream's order, not from the Device Builder's state:
the coordinator only says when the build moves to the upload. A line that
matches nothing changes nothing, so an Arduino build (no ninja counter) still
ends with every step done, it just shows less on the way. The formats are
ESPHome's own output, pinned here as regular expressions; when one changes,
the step stays running without its detail, nothing breaks.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any

from homeassistant.core import callback

BUILD_LOG_LINES = 2000  # kept per device: a first ESP-IDF build (~1,200 lines) fits whole
BUILD_LOG_HEAD = 200  # of those, the first lines, kept even when a build runs longer
BUILD_LOG_TAIL = 15  # sent to the panel with every snapshot, under the steps
BUILD_LOG_IN_HA_LOG = 40  # copied into Home Assistant's log when a build fails
BUILD_PUSH_INTERVAL = 1.0  # seconds between pushes of a running build to the panel

STEP_SETUP = "setup"
STEP_COMPILE = "compile"
STEP_LINK = "link"
STEP_RESULT = "result"
STEP_UPLOAD = "upload"
STEPS = (STEP_SETUP, STEP_COMPILE, STEP_LINK, STEP_RESULT, STEP_UPLOAD)

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"

# what the coordinator does before the Device Builder prints anything
STAGE_TEMPLATE = "template"
STAGE_WAITING = "waiting"
STAGE_COMPILE = "compile"
STAGE_UPLOAD = "upload"
_STAGE_DETAILS = {
    STAGE_TEMPLATE: "Updating the config from the template",
    STAGE_WAITING: "Waiting for another build",
}

# the update entity's progress bar: setup 10 %, the compile counter up to 80,
# link 80, result 82, the upload bar from 85 to 100
_PERCENT_SETUP = 10
_PERCENT_COMPILE_SPAN = 70
_PERCENT_LINK = 80
_PERCENT_RESULT = 82
_PERCENT_UPLOAD = 85
_PERCENT_UPLOAD_SPAN = 15

# colour codes, also written out as text: the Device Builder 2026.11 sends "\033[32m"
_ANSI = re.compile(r"(?:\x1b|\\033|\\x1b|\\u001b)\[[0-9;?]*[A-Za-z]")
# best first: an error line names the cause, "[FAILED]" only that it failed
_REASON_LINES = (re.compile(r"\bERROR\b|\berror:"), re.compile(r"\b(FAILED|Failed|failed)\b"))

_INFO = re.compile(r"^INFO (.+)$")
_INFO_CUT = re.compile(r" Build path:.*$")  # "Compiling app... Build path: /data/..."
_IDF_VERSION = re.compile(r"^Checking ESP-IDF (\S+) framework")
# ninja's counter: "[312/1065] Building CXX object esp-idf/.../levoit_device.cpp.obj"
_NINJA = re.compile(r"^\[(\d+)/(\d+)\] (.*)$")
_OBJECT = re.compile(r"^Building (?:CXX|C|ASM) object .*?([^/\\]+)\.(?:obj|o)$")
# the app's link, not the bootloader's (its own nested ninja run)
_LINK = re.compile(r"^Linking CXX executable (?!bootloader)(\S+)")
_IMAGE = re.compile(r"^Generating binary image")
_IMAGE_SIZE = re.compile(r"^Total image size: (\d+) bytes")
_SIZE = re.compile(r"^(RAM|Flash):\s+\[[= ]*\]\s+([\d.]+)% \(used (\d+) bytes from (\d+) bytes\)")
_COMPILED = re.compile(r"^INFO Successfully compiled program")
_UPLOADING = re.compile(r"^INFO Uploading .*\((\d+) bytes\)")
_UPLOAD_PERCENT = re.compile(r"Uploading: \[[= ]*\]\s*(\d+)%")
_UPLOAD_TOOK = re.compile(r"^INFO Upload took ([\d.]+) seconds")
_UPLOADED = re.compile(r"^INFO (?:OTA successful|Successfully uploaded program)")
# the first line of a compile or upload: the ESPHome that builds and uploads
_ESPHOME_VERSION = re.compile(r"^INFO ESPHome (\d+\.\d+\.\d+\S*)")
# the uploader with `ota: encryption:` against a firmware that cannot encrypt
_ENCRYPTION_REFUSED = re.compile(
    r"did not offer (?:OTA )?encryption|Refusing to send the image in plaintext"
)

STEP_FAILED_DETAIL = 160  # characters of the reason shown in the failed step


@dataclass
class Step:
    """One step of a build: what it does now, or how it ended."""

    key: str
    state: str = QUEUED
    detail: str | None = None  # running: what it does now; done: the summary
    done: int | None = None  # compile: files built so far, of total
    total: int | None = None
    percent: int | None = None  # upload: the bar

    def as_dict(self) -> dict[str, Any]:
        """For the panel; only what is set."""
        out: dict[str, Any] = {"key": self.key, "state": self.state}
        for name in ("detail", "done", "total", "percent"):
            if (value := getattr(self, name)) is not None:
                out[name] = value
        return out


def _kb(size: int) -> str:
    return f"{size / 1024:.0f} KB"


class BuildLog:
    """The compile / upload output of one build, as the Device Builder streams it."""

    def __init__(self, *, upload: bool, on_line: Callable[[], None] | None = None) -> None:
        """Initialize; `upload` adds the upload step, `on_line` hears every line."""
        self.upload = upload
        self._on_line = on_line
        # the first lines (setup, the config, ESP-IDF) and the newest; the middle
        # of a build longer than BUILD_LOG_LINES is dropped and counted
        self._head: list[str] = []
        self._lines: deque[str] = deque(maxlen=BUILD_LOG_LINES - BUILD_LOG_HEAD)
        self._skipped = 0
        self.steps: list[Step] = [Step(key) for key in STEPS if upload or key != STEP_UPLOAD]
        self._current: Step = self.steps[0]
        self._current.state = RUNNING
        self._files = 0
        self._idf: str | None = None
        self._image_size: int | None = None
        self._sizes: dict[str, float] = {}
        self._upload_seconds: float | None = None
        self.finished = False
        self.esphome_version: str | None = None  # "2026.11.0", from the output's first line
        self.encryption_refused = False  # the upload wanted encryption, the device had none
        self.note: str | None = None  # what the coordinator did after the build, for the row

    @callback
    def add(self, line: str) -> None:
        """One line of output (colour codes removed); read for the steps."""
        text = _ANSI.sub("", line)
        # the upload's bar comes as "\rUploading: [=  ] 10%\rUploading: [== ] 20%":
        # every part is read, the last one is kept
        parts = [part.rstrip() for part in text.split("\r") if part.strip()]
        for part in parts:
            self._read(part.strip())
        kept = parts[-1] if parts else ""
        if len(self._head) < BUILD_LOG_HEAD:
            self._head.append(kept)
        else:
            if len(self._lines) == self._lines.maxlen:
                self._skipped += 1
            self._lines.append(kept)
        if self._on_line is not None:
            self._on_line()

    @property
    def lines(self) -> list[str]:
        """The kept lines, oldest first, with a marker where the middle was dropped."""
        gap = [f"... {self._skipped} lines not kept ..."] if self._skipped else []
        return [*self._head, *gap, *self._lines]

    @property
    def tail(self) -> list[str]:
        """The newest lines, for the panel."""
        return [*self._head, *self._lines][-BUILD_LOG_TAIL:]

    def reason(self) -> str:
        """The last error line, else the last "failed" line, else the last line."""
        lines = [line.strip() for line in (*self._head, *self._lines) if line.strip()]
        for pattern in _REASON_LINES:
            for line in reversed(lines):
                if pattern.search(line):
                    return line[:300]
        return lines[-1][:300] if lines else "no output"

    # --- the coordinator's side ---------------------------------------------------

    def stage(self, stage: str) -> None:
        """What the coordinator does: before the output, and the move to the upload."""
        if stage == STAGE_UPLOAD:
            self._enter(STEP_UPLOAD)
        elif stage in _STAGE_DETAILS and self._current.key == STEP_SETUP:
            self._current.detail = _STAGE_DETAILS[stage]
        elif stage == STAGE_COMPILE and self._current.key == STEP_SETUP:
            self._current.detail = None

    def finish(self, ok: bool, reason: str | None = None) -> None:
        """The build ended: every step done, or the running one failed."""
        self.finished = True
        if ok:
            for step in self.steps:
                if step.state != DONE:
                    self._complete(step)
            return
        step = self._current
        step.state = FAILED
        step.detail = (reason or "failed")[:STEP_FAILED_DETAIL]

    def percent(self) -> int | None:
        """Progress for the update entity, 10 to 100; None before the output says anything."""
        step = self._current
        if step.key == STEP_COMPILE:
            if step.total:
                return _PERCENT_SETUP + round(_PERCENT_COMPILE_SPAN * (step.done or 0) / step.total)
            return _PERCENT_SETUP
        if step.key == STEP_LINK:
            return _PERCENT_LINK
        if step.key == STEP_RESULT:
            return _PERCENT_RESULT
        if step.key == STEP_UPLOAD:
            if step.percent is not None:
                return _PERCENT_UPLOAD + round(_PERCENT_UPLOAD_SPAN * step.percent / 100)
            return _PERCENT_UPLOAD
        return None

    def summary(self) -> dict[str, Any]:
        """The steps and the newest lines, for the panel."""
        return {
            "upload": self.upload,
            "steps": [step.as_dict() for step in self.steps],
            "tail": self.tail,
        }

    # --- reading the stream ---------------------------------------------------------

    def _step(self, key: str) -> Step | None:
        return next((step for step in self.steps if step.key == key), None)

    def _enter(self, key: str) -> Step:
        """Move to a step: the ones before it are done, it runs; already there: as is."""
        target = self._step(key)
        if target is None or target is self._current:
            return self._current
        for step in self.steps:
            if step is target:
                break
            if step.state != DONE:
                self._complete(step)
        target.state = RUNNING
        if target.key != STEP_COMPILE:
            target.detail = None  # the compile keeps its last file until a summary replaces it
        self._current = target
        return target

    def _complete(self, step: Step) -> None:
        """A step is done: its summary replaces what it was doing."""
        step.state = DONE
        step.detail = self._summary(step)

    def _summary(self, step: Step) -> str | None:
        if step.key == STEP_SETUP:
            return self._idf
        if step.key == STEP_COMPILE:
            return f"{self._files} files" if self._files else None
        if step.key == STEP_LINK:
            return f"{_kb(self._image_size)} image" if self._image_size else None
        if step.key == STEP_RESULT:
            return self._sizes_text()
        if step.key == STEP_UPLOAD:
            took = f" · {self._upload_seconds:.0f} s" if self._upload_seconds is not None else ""
            return f"OTA successful{took}"
        return None

    def _sizes_text(self) -> str | None:
        parts = [f"{name} {value:.1f} %" for name, value in self._sizes.items()]
        return " · ".join(parts) if parts else None

    def _read(self, text: str) -> None:
        if self.esphome_version is None and (match := _ESPHOME_VERSION.match(text)):
            self.esphome_version = match.group(1)
        if _ENCRYPTION_REFUSED.search(text):
            self.encryption_refused = True
        if match := _NINJA.match(text):
            self._read_ninja(int(match.group(1)), int(match.group(2)), match.group(3))
        elif match := _IMAGE_SIZE.match(text):
            if self._current.key == STEP_LINK:
                self._image_size = int(match.group(1))
        elif match := _SIZE.match(text):
            self._sizes[match.group(1)] = float(match.group(2))
            self._enter(STEP_RESULT).detail = self._sizes_text()
        elif _COMPILED.match(text):
            self._enter(STEP_RESULT)
            self._complete(self._current)
        elif match := _UPLOADING.match(text):
            self._enter(STEP_UPLOAD).detail = _kb(int(match.group(1)))
        elif match := _UPLOAD_PERCENT.search(text):
            # the bar says it all; the INFO line before it would stay next to it
            step = self._enter(STEP_UPLOAD)
            step.percent = int(match.group(1))
            step.detail = None
        elif match := _UPLOAD_TOOK.match(text):
            self._upload_seconds = float(match.group(1))
            step = self._enter(STEP_UPLOAD)
            step.percent = 100
            step.detail = "Waiting for the device"
        elif _UPLOADED.match(text):
            self._enter(STEP_UPLOAD)
            self._complete(self._current)
        elif match := _INFO.match(text):
            self._read_info(match.group(1))

    def _read_ninja(self, done: int, total: int, rest: str) -> None:
        if match := _OBJECT.match(rest):
            self._files += 1
            step = self._enter(STEP_COMPILE)
            # the bootloader is built in a nested run with its own, smaller total
            if step.total is None or total >= step.total:
                step.done, step.total = done, total
            step.detail = match.group(1)
        elif self._current.key == STEP_COMPILE:
            # the app's link; the bootloader's nested run links and images too
            if match := _LINK.match(rest):
                self._enter(STEP_LINK).detail = f"Linking {match.group(1)}"
        elif self._current.key == STEP_LINK and _IMAGE.match(rest):
            self._current.detail = "Generating the binary image"

    def _read_info(self, text: str) -> None:
        if match := _IDF_VERSION.match(text):
            self._idf = f"ESP-IDF {match.group(1)}"
        if self._current.key in (STEP_SETUP, STEP_UPLOAD):
            self._current.detail = _INFO_CUT.sub("", text).strip(" .") or None
