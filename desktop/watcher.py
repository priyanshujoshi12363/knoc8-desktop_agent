import subprocess
import sys
import time
from pathlib import Path

from serial.tools import list_ports

DESKTOP_DIR = Path(__file__).resolve().parent
ESP32_VIDS = {0x303A, 0x10C4, 0x1A86, 0x0403}
POLL_SECONDS = 3


def device_connected() -> bool:
    return any(p.vid in ESP32_VIDS for p in list_ports.comports())


def main() -> None:
    agent: subprocess.Popen | None = None
    while True:
        connected = device_connected()
        running = agent is not None and agent.poll() is None
        if connected and not running:
            time.sleep(2)
            agent = subprocess.Popen(
                [sys.executable.replace("pythonw.exe", "python.exe"), "main.py"],
                cwd=str(DESKTOP_DIR),
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        elif not connected and running:
            agent.terminate()
            agent = None
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
