"""Launches the agent when the ESP32 is plugged in, stops it when unplugged.

Runs from the Windows Startup folder via pythonw (no console of its own).
Because it starts before the agent's own bootstrap has ever run, it has to be
able to install its own dependency instead of dying silently at import time.
"""

import subprocess
import sys
import time
from pathlib import Path

DESKTOP_DIR = Path(__file__).resolve().parent
ESP32_VIDS = {0x303A, 0x10C4, 0x1A86, 0x0403}
POLL_SECONDS = 3
LOG = DESKTOP_DIR / "logs" / "watcher.log"


def _note(message: str) -> None:
    """pythonw has no console, so leave a breadcrumb on disk."""
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {message}\n")
    except OSError:
        pass


def _import_list_ports():
    """pyserial may not be installed yet on a fresh machine — install it."""
    try:
        from serial.tools import list_ports

        return list_ports
    except ImportError:
        _note("pyserial missing, installing dependencies...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r",
                 str(DESKTOP_DIR / "requirements.txt"), "--quiet",
                 "--disable-pip-version-check"],
                timeout=1800, capture_output=True,
            )
            from serial.tools import list_ports

            _note("dependencies installed")
            return list_ports
        except Exception as exc:
            _note(f"could not install dependencies: {exc}")
            return None


list_ports = _import_list_ports()


def device_connected() -> bool:
    if list_ports is None:
        return False
    try:
        return any(p.vid in ESP32_VIDS for p in list_ports.comports())
    except Exception as exc:
        _note(f"port scan failed: {exc}")
        return False


def is_paused() -> bool:
    """Read .env fresh every poll — config.py caches at import, so it can't
    see a toggle flipped while the watcher is already running."""
    try:
        from settings import load_env

        return load_env().get("KNOC8_PAUSED", "0").strip() == "1"
    except Exception:
        return False


def main() -> None:
    if list_ports is None:
        _note("no pyserial - watcher cannot run")
        return
    _note("watcher started")
    agent: subprocess.Popen | None = None
    was_paused = False

    while True:
        paused = is_paused()
        connected = device_connected()
        running = agent is not None and agent.poll() is None

        if paused != was_paused:
            _note("PAUSED - releasing the COM port" if paused
                  else "resumed - watching for the device")
            was_paused = paused

        if paused:
            if running:
                _note("stopping agent so the port is free for flashing")
                agent.terminate()
                agent = None
        elif connected and not running:
            time.sleep(2)
            _note("device connected - launching agent")
            agent = subprocess.Popen(
                [sys.executable.replace("pythonw.exe", "python.exe"), "main.py"],
                cwd=str(DESKTOP_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        elif not connected and running:
            _note("device unplugged - stopping agent")
            agent.terminate()
            agent = None

        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
