import urllib.parse
import webbrowser

from logger import get_logger
from tools.base import Action

log = get_logger("browser")


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    log.info("Opening URL: %s", url)
    webbrowser.open(url)
    return f"Opened {url} in the default browser."


def search_google(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    webbrowser.open(url)
    return f"Searching Google for: {query}"


def search_youtube(query: str) -> str:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    webbrowser.open(url)
    return f"Searching YouTube for: {query}"


ACTIONS = {
    "open_url": Action(open_url, "Open a website in the default browser.",
                       {"url": "the website URL or domain"}),
    "search_google": Action(search_google, "Search Google.",
                            {"query": "the search text"}),
    "search_youtube": Action(search_youtube, "Search YouTube.",
                             {"query": "the search text"}),
}
