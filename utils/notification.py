import requests
from rss_translator.utils.config_reader import read_config


def pushover_notify(message: str) -> None:
    requests.post(
        "https://api.pushover.net/1/messages.json",
        data={
            "token": read_config("Pushover", "Pushover_APP_Key"),
            "user": read_config("Pushover", "Pushover_USER_Key"),
            "message": message,
        },
        timeout=10,
    )
