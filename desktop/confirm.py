import ctypes
import threading
import time
from typing import Callable, Optional

from logger import get_logger

log = get_logger("confirm")

_user32 = ctypes.windll.user32
_MB_YESNO = 0x00000004
_MB_ICONWARNING = 0x00000030
_MB_SYSTEMMODAL = 0x00001000
_MB_TOPMOST = 0x00040000
_IDYES = 6
_IDNO = 7
_WM_COMMAND = 0x0111
_TITLE = "Knoc8  —  Confirm action"


class _Dialog:
    """A native Yes/No message box running in its own thread so the caller
    can also watch for a voice decision and dismiss it programmatically."""

    def __init__(self, message: str) -> None:
        self._result: Optional[bool] = None
        self._hwnd = 0
        threading.Thread(target=self._run, args=(message,), daemon=True).start()

    def _run(self, message: str) -> None:
        flags = _MB_YESNO | _MB_ICONWARNING | _MB_SYSTEMMODAL | _MB_TOPMOST
        try:
            r = _user32.MessageBoxW(0, message, _TITLE, flags)
            self._result = (r == _IDYES)
        except Exception as exc:
            log.warning("Confirmation dialog failed: %s", exc)
            self._result = None

    def result(self) -> Optional[bool]:
        return self._result

    def _find(self) -> int:
        if not self._hwnd:
            self._hwnd = _user32.FindWindowW(None, _TITLE) or 0
        return self._hwnd

    def dismiss(self) -> None:
        hwnd = self._find()
        if hwnd:
            _user32.PostMessageW(hwnd, _WM_COMMAND, _IDNO, 0)


def confirm(
    message: str,
    timeout: float = 20.0,
    poll: Optional[Callable[[], Optional[str]]] = None,
) -> bool:
    """Ask the user to approve a dangerous action.

    Shows a native Yes/No popup and, if `poll` is given, checks it repeatedly
    for a spoken decision ('yes' / 'no'). Whichever answers first wins.
    Times out to a safe **No**.
    """
    log.info("Confirmation requested: %s", message)
    dlg = _Dialog(message)
    deadline = time.time() + timeout
    while time.time() < deadline:
        clicked = dlg.result()
        if clicked is not None:
            log.info("Confirmation via dialog: %s", "YES" if clicked else "NO")
            return clicked
        if poll is not None:
            spoken = poll()
            if spoken == "yes":
                dlg.dismiss()
                log.info("Confirmation via voice: YES")
                return True
            if spoken == "no":
                dlg.dismiss()
                log.info("Confirmation via voice: NO")
                return False
        time.sleep(0.05)
    dlg.dismiss()
    log.info("Confirmation timed out -> NO")
    return False
