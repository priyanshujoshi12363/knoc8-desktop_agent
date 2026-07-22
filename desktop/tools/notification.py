from plyer import notification as plyer_notification

import config
from tools.base import Action


def show(title: str, message: str = "") -> str:
    plyer_notification.notify(
        title=title,
        message=message or " ",
        app_name=config.ASSISTANT_NAME,
        timeout=6,
    )
    return f"Notification shown: {title}"


ACTIONS = {
    "show": Action(show, "Show a desktop notification.",
                   {"title": "notification title", "message": "notification body"}),
}
