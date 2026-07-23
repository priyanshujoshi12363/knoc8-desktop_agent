import time

from logger import get_logger
from tools.base import Action

log = get_logger("wait")


def wait(seconds: float) -> str:
    seconds = max(0.0, min(300.0, float(seconds)))
    log.info("Waiting %.0f seconds...", seconds)
    time.sleep(seconds)
    return f"Waited {seconds:.0f} seconds."


ACTIONS = {
    "wait": Action(wait, "Pause between steps (e.g. let a song play, let an "
                         "app finish loading).",
                   {"seconds": "how long to wait, max 300"}),
}
