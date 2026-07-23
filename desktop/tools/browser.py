import json
import os
import subprocess
import urllib.parse
import webbrowser

import config
from logger import get_logger
from tools.base import Action

log = get_logger("browser")

_profiles_cache: dict[str, str] | None = None


def chrome_profiles() -> dict[str, str]:
    global _profiles_cache
    if _profiles_cache is None:
        _profiles_cache = {}
        try:
            path = os.path.join(
                os.environ.get("LOCALAPPDATA", ""),
                "Google", "Chrome", "User Data", "Local State",
            )
            with open(path, encoding="utf-8") as fh:
                state = json.load(fh)
            for dirname, meta in state.get("profile", {}).get("info_cache", {}).items():
                _profiles_cache[dirname] = meta.get("name") or dirname
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Could not read Chrome profiles: %s", exc)
    return _profiles_cache


def _open(url: str) -> None:
    profile = _resolve_profile(config.CHROME_PROFILE)
    cmd = 'start "" chrome '
    if profile:
        cmd += f'--profile-directory="{profile}" '
    cmd += f'"{url}"'
    result = subprocess.run(cmd, shell=True, capture_output=True)
    if result.returncode != 0:
        log.warning("Chrome launch failed, falling back to default browser.")
        webbrowser.open(url)


def _resolve_profile(profile: str) -> str:
    profiles = chrome_profiles()
    wanted = profile.lower().strip()
    if not wanted:
        return ""
    for dirname, name in profiles.items():
        if wanted in (dirname.lower(), name.lower()):
            return dirname
    for dirname, name in profiles.items():
        if wanted in name.lower():
            return dirname
    return ""


def open_chrome(profile: str = "") -> str:
    dirname = _resolve_profile(profile or config.CHROME_PROFILE)
    cmd = 'start "" chrome'
    if dirname:
        cmd += f' --profile-directory="{dirname}"'
    subprocess.run(cmd, shell=True)
    if dirname:
        name = chrome_profiles().get(dirname, dirname)
        return f"Chrome opened with the {name} profile."
    if profile:
        return (f"Profile '{profile}' was not found, opened Chrome with the "
                f"last used profile instead.")
    return "Chrome opened with the last used profile."


def list_chrome_profiles() -> str:
    profiles = chrome_profiles()
    if not profiles:
        return "No Chrome profiles found."
    return "Chrome profiles:\n" + "\n".join(
        f"- {name}" for name in profiles.values()
    )


def open_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    log.info("Opening URL: %s", url)
    _open(url)
    return f"Opened {url} in Chrome."


def search_google(query: str) -> str:
    url = "https://www.google.com/search?q=" + urllib.parse.quote_plus(query)
    _open(url)
    return f"Searching Google for: {query}"


def search_youtube(query: str) -> str:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    _open(url)
    return f"Searching YouTube for: {query}"


def play_youtube(query: str) -> str:
    import re

    import requests

    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    try:
        html = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }).text
        match = re.search(r'"videoId":"([\w-]{11})"', html)
    except requests.RequestException as exc:
        log.warning("YouTube lookup failed: %s", exc)
        match = None
    if not match:
        _open(url)
        return f"Could not find a video directly, opened YouTube search for: {query}"
    video = f"https://www.youtube.com/watch?v={match.group(1)}"
    _open(video)
    return f"Playing the top YouTube result for: {query}"


ACTIONS = {
    "open_chrome": Action(open_chrome,
                          "Open Google Chrome, optionally with a specific profile.",
                          {"profile": "profile name, or empty for last used"}),
    "list_chrome_profiles": Action(list_chrome_profiles,
                                   "List the available Chrome profiles."),
    "open_url": Action(open_url, "Open a website in the default browser.",
                       {"url": "the website URL or domain"}),
    "search_google": Action(search_google, "Search Google.",
                            {"query": "the search text"}),
    "search_youtube": Action(search_youtube, "Open YouTube search results.",
                             {"query": "the search text"}),
    "play_youtube": Action(play_youtube,
                           "Find and PLAY the top YouTube video for a query "
                           "(use this when the user wants to hear/watch, not "
                           "just search).",
                           {"query": "song or video to play"}),
}
