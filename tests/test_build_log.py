"""The build output read into steps: an ESP-IDF compile, an OTA upload, a failure."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from custom_components.levoit_esphome.build_log import (
    BUILD_LOG_HEAD,
    BUILD_LOG_LINES,
    BUILD_LOG_TAIL,
    STAGE_COMPILE,
    STAGE_TEMPLATE,
    STAGE_UPLOAD,
    STAGE_WAITING,
    STEP_COMPILE,
    STEP_LINK,
    STEP_RESULT,
    STEP_SETUP,
    STEP_UPLOAD,
    BuildLog,
)

# a Device Builder compile of a Core 300S config on ESP-IDF 5.5.6 (ESPHome
# 2026.11), cut to the lines that matter: the counter, a nested bootloader
# build, the link, the sizes
FIXTURE = Path(__file__).parent / "fixtures" / "build-esp-idf.log"

UPLOAD_LINES = (
    "INFO Reading configuration /config/esphome/bedroom-purifier.yaml...",
    "INFO Resolving IP address of bedroom-purifier.local",
    "INFO Uploading /data/build/bedroom-purifier/build/firmware.ota.bin (820227 bytes)",
    "INFO Connecting to 192.168.1.50 port 3232...",
    "INFO Auth successful",
    # the bar is drawn with carriage returns, no line breaks
    "\rUploading: [=         ] 10% \rUploading: [=====     ] 50% ",
    "\rUploading: [==========] 100% Done...",
    "INFO Upload took 12.34 seconds, waiting for result...",
    "INFO OTA successful",
    "INFO Successfully uploaded program.",
)

SIZES = "RAM 29.2 % · Flash 44.7 %"


def _steps(log: BuildLog) -> dict[str, dict]:
    return {step["key"]: step for step in log.summary()["steps"]}


def _feed(log: BuildLog, lines: Iterator[str], until: str) -> None:
    """Add lines through the first one that contains `until`."""
    for line in lines:
        log.add(line)
        if until in line:
            return
    raise AssertionError(f"no line with {until!r}")


def _compile(until: str, *, upload: bool = False) -> tuple[BuildLog, Iterator[str]]:
    """A log fed with the fixture through the first line that contains `until`."""
    log = BuildLog(upload=upload)
    lines = iter(FIXTURE.read_text(encoding="utf-8").splitlines())
    _feed(log, lines, until)
    return log, lines


def test_setup() -> None:
    """Before the first object file: the setup runs, with the last INFO line."""
    log = BuildLog(upload=False)
    assert [s["key"] for s in log.summary()["steps"]] == [
        STEP_SETUP,
        STEP_COMPILE,
        STEP_LINK,
        STEP_RESULT,
    ]
    assert _steps(log)[STEP_SETUP] == {"key": STEP_SETUP, "state": "running"}
    assert log.percent() is None

    log, lines = _compile("Compiling app")
    # without its dots and the build path
    expected = {"key": STEP_SETUP, "state": "running", "detail": "Compiling app"}
    assert _steps(log)[STEP_SETUP] == expected
    _feed(log, lines, "Re-checking globbed")  # a ninja line without an object file
    assert _steps(log)[STEP_SETUP]["state"] == "running"
    assert _steps(log)[STEP_COMPILE] == {"key": STEP_COMPILE, "state": "queued"}


def test_compile_counter() -> None:
    """Ninja's counter and the file; the bootloader's nested run does not disturb it."""
    log, lines = _compile("[3/1065]")
    steps = _steps(log)
    assert steps[STEP_SETUP] == {"key": STEP_SETUP, "state": "done", "detail": "ESP-IDF 5.5.6"}
    assert steps[STEP_COMPILE] == {
        "key": STEP_COMPILE,
        "state": "running",
        "detail": "api_buffer.cpp",
        "done": 3,
        "total": 1065,
    }
    assert steps[STEP_LINK] == {"key": STEP_LINK, "state": "queued"}
    assert log.percent() == 10  # 10 + 70 * 3 / 1065

    # the nested run (total 97) neither moves the counter back nor, with its
    # own link and image, starts the link step
    _feed(log, lines, "Completed 'bootloader'")
    compile_ = _steps(log)[STEP_COMPILE]
    assert (compile_["done"], compile_["total"]) == (3, 1065)
    assert compile_["detail"] == "bootloader_common.c"
    assert _steps(log)[STEP_LINK]["state"] == "queued"

    _feed(log, lines, "[1062/1065]")
    compile_ = _steps(log)[STEP_COMPILE]
    assert (compile_["done"], compile_["total"], compile_["detail"]) == (1062, 1065, "main.cpp")
    assert log.percent() == 80  # 10 + 70 * 1062 / 1065, rounded


def test_link_and_result() -> None:
    """The app's link ends the compile; the sizes make the result; summaries when done."""
    log, lines = _compile("Linking CXX executable bedroom")
    steps = _steps(log)
    assert steps[STEP_COMPILE] == {
        "key": STEP_COMPILE,
        "state": "done",
        "detail": "7 files",  # object files in the fixture, the bootloader's included
        "done": 1062,
        "total": 1065,
    }
    assert steps[STEP_LINK] == {
        "key": STEP_LINK,
        "state": "running",
        "detail": "Linking bedroom-purifier.elf",
    }
    assert log.percent() == 80
    _feed(log, lines, "Generating binary image")
    assert _steps(log)[STEP_LINK]["detail"] == "Generating the binary image"

    _feed(log, lines, "RAM:")
    steps = _steps(log)
    assert steps[STEP_LINK] == {"key": STEP_LINK, "state": "done", "detail": "801 KB image"}
    assert steps[STEP_RESULT] == {"key": STEP_RESULT, "state": "running", "detail": "RAM 29.2 %"}
    _feed(log, lines, "Flash:")
    assert _steps(log)[STEP_RESULT]["detail"] == SIZES
    assert log.percent() == 82

    _feed(log, lines, "Successfully compiled")
    assert _steps(log)[STEP_RESULT] == {"key": STEP_RESULT, "state": "done", "detail": SIZES}
    assert not log.finished
    log.finish(True)
    assert log.finished
    assert all(step["state"] == "done" for step in log.summary()["steps"])


def test_upload_steps() -> None:
    """The coordinator moves to the upload; the bar comes with carriage returns."""
    log, _ = _compile("Successfully compiled", upload=True)
    assert log.summary()["upload"] is True
    assert _steps(log)[STEP_UPLOAD] == {"key": STEP_UPLOAD, "state": "queued"}

    log.stage(STAGE_UPLOAD)
    assert _steps(log)[STEP_UPLOAD] == {"key": STEP_UPLOAD, "state": "running"}
    assert log.percent() == 85
    lines = iter(UPLOAD_LINES)
    _feed(log, lines, "Resolving")
    # the upload's INFO lines are its detail, the compile's result stays
    assert _steps(log)[STEP_UPLOAD]["detail"] == "Resolving IP address of bedroom-purifier.local"
    assert _steps(log)[STEP_RESULT]["detail"] == SIZES
    _feed(log, lines, "Uploading /data")
    assert _steps(log)[STEP_UPLOAD]["detail"] == "801 KB"
    _feed(log, lines, "Auth successful")
    assert _steps(log)[STEP_UPLOAD]["detail"] == "Auth successful"
    _feed(log, lines, "50%")
    # the bar replaces the INFO text next to it
    assert _steps(log)[STEP_UPLOAD] == {"key": STEP_UPLOAD, "state": "running", "percent": 50}
    assert log.percent() == 85 + 8  # 85 + 15 * 0.5, rounded
    # only the last part of a line drawn with \r is kept
    assert log.lines[-1] == "Uploading: [=====     ] 50%"
    _feed(log, lines, "100%")
    assert _steps(log)[STEP_UPLOAD]["percent"] == 100
    _feed(log, lines, "Upload took")
    assert _steps(log)[STEP_UPLOAD]["detail"] == "Waiting for the device"
    assert log.percent() == 100
    _feed(log, lines, "OTA successful")
    assert _steps(log)[STEP_UPLOAD] == {
        "key": STEP_UPLOAD,
        "state": "done",
        "detail": "OTA successful · 12 s",
        "percent": 100,
    }
    log.add("INFO Successfully uploaded program.")
    log.finish(True)
    assert _steps(log)[STEP_UPLOAD]["detail"] == "OTA successful · 12 s"


def test_stages_before_output() -> None:
    """What the coordinator does before the Device Builder prints shows as the setup."""
    log = BuildLog(upload=True)
    log.stage(STAGE_TEMPLATE)
    assert _steps(log)[STEP_SETUP]["detail"] == "Updating the config from the template"
    log.stage(STAGE_WAITING)
    assert _steps(log)[STEP_SETUP]["detail"] == "Waiting for another build"
    log.stage(STAGE_COMPILE)
    assert "detail" not in _steps(log)[STEP_SETUP]
    assert log.percent() is None  # the coordinator's step value applies


def test_failure() -> None:
    """A failed build: the running step fails with the reason, the rest stays queued."""
    log = BuildLog(upload=True)
    for line in (
        "\033[32mINFO Compiling app...\033[0m",
        "[1/1065] Building CXX object esp-idf/src/CMakeFiles/__idf_src.dir/src/main.cpp.obj",
        "\x1b[31msrc/main.cpp:12: error: 'foo' was not declared\x1b[0m",
        "========== [FAILED] ==========",
    ):
        log.add(line)
    assert log.reason() == "src/main.cpp:12: error: 'foo' was not declared"
    log.finish(False, log.reason())
    steps = _steps(log)
    assert steps[STEP_SETUP]["state"] == "done"
    assert steps[STEP_COMPILE] == {
        "key": STEP_COMPILE,
        "state": "failed",
        "detail": "src/main.cpp:12: error: 'foo' was not declared",
        "done": 1,
        "total": 1065,
    }
    assert steps[STEP_LINK]["state"] == "queued"
    assert steps[STEP_UPLOAD]["state"] == "queued"
    assert log.lines == [
        "INFO Compiling app...",
        "[1/1065] Building CXX object esp-idf/src/CMakeFiles/__idf_src.dir/src/main.cpp.obj",
        "src/main.cpp:12: error: 'foo' was not declared",
        "========== [FAILED] ==========",
    ]

    # a build that fails before any output: the setup fails
    log = BuildLog(upload=False)
    log.finish(False, "Device Builder unavailable")
    assert _steps(log)[STEP_SETUP] == {
        "key": STEP_SETUP,
        "state": "failed",
        "detail": "Device Builder unavailable",
    }


def test_unknown_output() -> None:
    """Lines that match nothing (an Arduino build) change nothing; success ends all done."""
    log = BuildLog(upload=False)
    for line in (
        "Compiling .pioenvs/bedroom-purifier/src/main.cpp.o",
        "Linking .pioenvs/bedroom-purifier/firmware.elf",
        "RAM:   [=====     ]  45.6% (used 37312 bytes from 81920 bytes)",
        "INFO Successfully compiled program.",
    ):
        log.add(line)
    steps = _steps(log)
    assert steps[STEP_COMPILE] == {"key": STEP_COMPILE, "state": "done"}
    assert steps[STEP_LINK] == {"key": STEP_LINK, "state": "done"}
    assert steps[STEP_RESULT] == {"key": STEP_RESULT, "state": "done", "detail": "RAM 45.6 %"}
    log.finish(True)
    assert all(step["state"] == "done" for step in log.summary()["steps"])


def test_kept_lines() -> None:
    """A first build is kept whole, from its first line: the full log starts at the beginning."""
    log = BuildLog(upload=False)
    for i in range(1200):
        log.add(f"[{i}/1200] Building C object")
    assert len(log.lines) == 1200
    assert log.lines[0] == "[0/1200] Building C object"
    assert log.lines[-1] == "[1199/1200] Building C object"


def test_kept_lines_long_build() -> None:
    """The first and the newest lines, the middle counted; blank lines kept, a push per line."""
    pushes = 0

    def on_line() -> None:
        nonlocal pushes
        pushes += 1

    log = BuildLog(upload=False, on_line=on_line)
    for i in range(BUILD_LOG_LINES + 10):
        log.add(f"line {i}")
    log.add("")
    assert pushes == BUILD_LOG_LINES + 11
    assert len(log.lines) == BUILD_LOG_LINES + 1  # with the marker
    assert log.lines[0] == "line 0"
    assert log.lines[BUILD_LOG_HEAD - 1] == f"line {BUILD_LOG_HEAD - 1}"
    assert log.lines[BUILD_LOG_HEAD] == "... 11 lines not kept ..."
    assert log.lines[BUILD_LOG_HEAD + 1] == f"line {BUILD_LOG_HEAD + 11}"
    assert log.lines[-1] == ""
    assert log.summary()["tail"] == log.lines[-BUILD_LOG_TAIL:]
    assert log.reason() == f"line {BUILD_LOG_LINES + 9}"


def test_esphome_version_and_refusal() -> None:
    """The output's first line names the ESPHome at work; a refused encrypted upload is flagged."""
    log = BuildLog(upload=True)
    assert log.esphome_version is None and not log.encryption_refused
    log.add("\x1b[32mINFO ESPHome 2026.11.0\x1b[0m")
    log.add("INFO ESPHome 2025.1.0")  # a later mention does not replace it
    assert log.esphome_version == "2026.11.0"
    log.add("ERROR An OTA encryption key is configured but the device did not offer encryption")
    assert log.encryption_refused
    other = BuildLog(upload=True)
    other.add("ERROR Refusing to send the image in plaintext. The running firmware predates ...")
    assert other.encryption_refused
