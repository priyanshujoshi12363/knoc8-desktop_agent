from logger import get_logger
from tools.base import Action

log = get_logger("settings")


def open_settings() -> str:
    import settings_web

    url = settings_web.launch()
    return f"Settings panel opened in your browser at {url}."


ACTIONS = {
    "open": Action(open_settings,
                   "Open the Knoc8 settings panel in the web browser (to change "
                   "the LLM provider, API keys, models, wake word, and more)."),
}
