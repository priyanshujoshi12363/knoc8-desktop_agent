import subprocess

from logger import get_logger
from tools.base import Action

log = get_logger("system")


def _volume_interface():
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    device = AudioUtilities.GetSpeakers()
    interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return interface.QueryInterface(IAudioEndpointVolume)


def set_volume(level: int) -> str:
    level = max(0, min(100, int(level)))
    _volume_interface().SetMasterVolumeLevelScalar(level / 100.0, None)
    return f"Volume set to {level}%."


def get_volume() -> str:
    current = round(_volume_interface().GetMasterVolumeLevelScalar() * 100)
    return f"Current volume is {current}%."


def mute(state: bool = True) -> str:
    _volume_interface().SetMute(1 if state else 0, None)
    return "Muted." if state else "Unmuted."


def set_brightness(level: int) -> str:
    import screen_brightness_control as sbc

    level = max(0, min(100, int(level)))
    sbc.set_brightness(level)
    return f"Brightness set to {level}%."


def lock() -> str:
    subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"])
    return "Workstation locked."


def shutdown() -> str:
    log.warning("SHUTDOWN requested")
    subprocess.run(["shutdown", "/s", "/t", "10"])
    return "Shutting down in 10 seconds. Run 'shutdown /a' to abort."


def restart() -> str:
    log.warning("RESTART requested")
    subprocess.run(["shutdown", "/r", "/t", "10"])
    return "Restarting in 10 seconds. Run 'shutdown /a' to abort."


ACTIONS = {
    "set_volume": Action(set_volume, "Set the system volume.",
                         {"level": "0-100"}),
    "get_volume": Action(get_volume, "Get the current system volume."),
    "mute": Action(mute, "Mute or unmute audio.",
                   {"state": "true to mute, false to unmute"}),
    "set_brightness": Action(set_brightness, "Set screen brightness.",
                             {"level": "0-100"}),
    "lock": Action(lock, "Lock the workstation."),
    "shutdown": Action(shutdown, "Shut the PC down.", dangerous=True),
    "restart": Action(restart, "Restart the PC.", dangerous=True),
}
