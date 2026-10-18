"""Console UI for Knoc8 — a live, Claude-Code-style transcript of what the
agent is doing. Falls back to plain print() if `rich` is unavailable."""

import os
import sys
import threading
import time


def _prepare_windows_console() -> bool:
    """UTF-8 output + VT escape sequences in the Windows console.

    Without this the legacy console is cp1252 and every box/check glyph
    raises UnicodeEncodeError.  Returns True if VT mode is available.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name != "nt":
        return True
    try:
        import ctypes

        k32 = ctypes.windll.kernel32
        k32.SetConsoleOutputCP(65001)          # UTF-8 code page
        k32.SetConsoleCP(65001)
        handle = k32.GetStdHandle(-11)         # STD_OUTPUT_HANDLE
        mode = ctypes.c_uint32()
        if not k32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(k32.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


_VT = _prepare_windows_console()

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.spinner import Spinner
    from rich.text import Text
    _RICH = True
except ImportError:  # degraded but functional
    _RICH = False

import config

_console = Console(highlight=False, soft_wrap=False,
                   legacy_windows=False if _VT else None) if _RICH else None
_lock = threading.Lock()


def _can_encode(sample: str) -> bool:
    enc = getattr(sys.stdout, "encoding", None) or "ascii"
    try:
        sample.encode(enc)
        return True
    except Exception:
        return False


_UNI = _can_encode("✻✓✗●○→⊘❯")


def _g(fancy: str, plain: str) -> str:
    """Pick a glyph the current console can actually print."""
    return fancy if _UNI else plain


LOGO = _g("✻", "*")
CHECK = _g("✓", "+")
CROSS = _g("✗", "x")
DOT = _g("·", "-")
BANG = "!"
FILLED = _g("●", "*")
HOLLOW = _g("○", "o")
ARROW = _g("→", ">")
BLOCK = _g("⊘", "!")
CHEV = _g("❯", ">")
SEP = _g("·", "-")

# palette
DIM = "grey50"
ACCENT = "bright_magenta"
OK = "green"
BAD = "red"
WARN = "yellow"
USER = "bright_cyan"

_live: "Live | None" = None
_live_started = 0.0


# ------------------------------------------------------------------ helpers

def _p(*args, **kwargs) -> None:
    if _RICH:
        _console.print(*args, **kwargs)
    else:
        text = " ".join(str(a) for a in args)
        for tag in ("[/]", "[bold]", "[/bold]", "[dim]", "[/dim]"):
            text = text.replace(tag, "")
        print(text)


def _plain(s: str) -> str:
    """Escape rich markup in untrusted text (transcripts, tool output)."""
    return s.replace("[", r"\[") if _RICH else s


def clear() -> None:
    if _RICH:
        _console.clear()


# ------------------------------------------------------------------ banner

def banner() -> None:
    clear()
    if not _RICH:
        print(f"\n  {config.ASSISTANT_NAME} Desktop Agent\n")
        return
    body = Text()
    body.append(f"{LOGO} ", style=ACCENT)
    body.append(f"{config.ASSISTANT_NAME} Desktop Agent", style="bold")
    body.append("\n  voice-controlled Windows automation", style=DIM)
    _console.print(Panel(body, border_style=DIM, padding=(0, 2), expand=False))
    _console.print()


# ------------------------------------------------------------------ setup

def section(title: str) -> None:
    _p(f"  [bold]{title}[/bold]")


def setup_step(label: str, detail: str = "", state: str = "ok") -> None:
    """state: ok | fail | warn | info"""
    mark, style = {
        "ok":   (CHECK, OK),
        "fail": (CROSS, BAD),
        "warn": (BANG, WARN),
        "info": (DOT, DIM),
    }.get(state, (DOT, DIM))
    pad = " " * max(1, 26 - len(label))
    line = f"  [{style}]{mark}[/{style}] {label}"
    if detail:
        line += f"{pad}[{DIM}]{_plain(detail)}[/{DIM}]"
    _p(line)


class task:
    """Spinner for a slow step:  with ui.task("Downloading model") as t: ..."""

    def __init__(self, label: str, detail: str = "") -> None:
        self.label = label
        self.detail = detail
        self._live = None
        self._start = 0.0

    def __enter__(self):
        self._start = time.time()
        if _RICH:
            spinner = Spinner("dots", text=Text.from_markup(
                f" {self.label}" + (f"  [{DIM}]{_plain(self.detail)}[/{DIM}]"
                                    if self.detail else "")))
            self._live = Live(spinner, console=_console, refresh_per_second=12,
                              transient=True)
            self._live.start()
        else:
            print(f"  · {self.label} ...")
        return self

    def update(self, detail: str) -> None:
        self.detail = detail
        if self._live:
            self._live.update(Spinner("dots", text=Text.from_markup(
                f" {self.label}  [{DIM}]{_plain(detail)}[/{DIM}]")))

    def __exit__(self, exc_type, exc, tb):
        if self._live:
            self._live.stop()
        took = time.time() - self._start
        suffix = self.detail or (f"{took:.0f}s" if took >= 2 else "")
        setup_step(self.label, suffix, "fail" if exc_type else "ok")
        return False


def ready(hint: str = "Tap the button on your device to talk") -> None:
    _p()
    if _RICH:
        _console.print(f"  [{OK}]{FILLED}[/{OK}] [bold]Ready[/bold]  [{DIM}]{SEP} {hint}[/{DIM}]")
    else:
        print(f"  Ready — {hint}")
    _p()


# ------------------------------------------------------------------ runtime

def listening() -> None:
    _p(f"  [{USER}]{FILLED}[/{USER}] [bold]Listening[/bold][{DIM}]  {SEP} speak now[/{DIM}]")


def cancelled(what: str = "Recording cancelled") -> None:
    _p(f"  [{DIM}]{HOLLOW} {what}[/{DIM}]")
    _p()


def _wrap(text: str, indent: int) -> list[str]:
    import textwrap

    width = (_console.width if _RICH else 80) - indent - 2
    out: list[str] = []
    for para in text.splitlines() or [""]:
        out.extend(textwrap.wrap(para, max(20, width)) or [""])
    return out


def heard(text: str) -> None:
    _stop_step_live()
    _p()
    lines = _wrap(text, 4)
    _p(f"  [{USER}]{CHEV}[/{USER}] [bold]{_plain(lines[0])}[/bold]")
    for extra in lines[1:]:
        _p(f"    [bold]{_plain(extra)}[/bold]")


def thinking_start() -> None:
    global _live, _live_started
    if not _RICH:
        print(f"  · thinking ...")
        return
    _live_started = time.time()
    _live = Live(Spinner("dots", text=Text(" thinking...", style=DIM)),
                 console=_console, refresh_per_second=12, transient=True)
    _live.start()


def thinking_stop() -> None:
    global _live
    if _live is not None:
        _live.stop()
        _live = None


_step_live: "Live | None" = None


def _step_line(mark: str, style: str, tool: str, action: str, detail: str) -> str:
    name = f"{tool}.{action}"
    pad = " " * max(1, 26 - len(name))
    line = f"    [{style}]{mark}[/{style}] {name}"
    if detail:
        line += f"{pad}[{DIM}]{_plain(detail[:64])}[/{DIM}]"
    return line


def step(tool: str, action: str, detail: str = "", state: str = "run") -> None:
    """A running step shows a spinner that is replaced by its result.

    state: run | ok | fail | denied | skip
    """
    global _step_live

    if state == "run":
        if not _RICH:
            print(f"    {ARROW} {tool}.{action}  {detail[:64]}")
            return
        _stop_step_live()
        name = f"{tool}.{action}"
        pad = " " * max(1, 26 - len(name))
        label = f" {name}" + (f"{pad}[{DIM}]{_plain(detail[:64])}[/{DIM}]"
                              if detail else "")
        _step_live = Live(
            Spinner("dots", text=Text.from_markup(f"   {label}")),
            console=_console, refresh_per_second=12, transient=True)
        _step_live.start()
        return

    _stop_step_live()
    mark, style = {
        "ok":     (CHECK, OK),
        "fail":   (CROSS, BAD),
        "denied": (BLOCK, WARN),
        "skip":   (DOT, DIM),
    }.get(state, (DOT, DIM))
    _p(_step_line(mark, style, tool, action, detail))


def _stop_step_live() -> None:
    global _step_live
    if _step_live is not None:
        _step_live.stop()
        _step_live = None


def reply(text: str) -> None:
    _stop_step_live()
    _p()
    _p(f"  [{ACCENT}]{LOGO}[/{ACCENT}] [bold]{config.ASSISTANT_NAME}[/bold]")
    for line in _wrap(text, 4):
        _p(f"    {_plain(line)}")
    _p()


def info(text: str) -> None:
    _p(f"  [{DIM}]{_plain(text)}[/{DIM}]")


def warn(text: str) -> None:
    _stop_step_live()
    _p(f"  [{WARN}]{BANG}[/{WARN}] {_plain(text)}")


def error(text: str) -> None:
    _p(f"  [{BAD}]{CROSS}[/{BAD}] {_plain(text)}")


def rule() -> None:
    if _RICH:
        _console.rule(style=DIM)
    else:
        print("-" * 60)


def bye() -> None:
    _p()
    _p(f"  [{DIM}]Knoc8 stopped.[/{DIM}]")
    _p()
