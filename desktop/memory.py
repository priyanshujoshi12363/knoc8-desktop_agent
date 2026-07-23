import json
from datetime import datetime

import config
from logger import get_logger

log = get_logger("memory")


class Memory:
    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []
        self.facts: list[str] = []
        self.journal: list[str] = []
        self._load()

    def _load(self) -> None:
        if not config.MEMORY_FILE.exists():
            return
        try:
            data = json.loads(config.MEMORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not load memory file: %s", exc)
            return
        if isinstance(data, list):
            self.facts = data
        elif isinstance(data, dict):
            self.facts = data.get("facts", [])
            self.journal = data.get("journal", [])

    def _save(self) -> None:
        config.MEMORY_FILE.write_text(
            json.dumps(
                {"facts": self.facts, "journal": self.journal},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def remember(self, fact: str) -> str:
        self.facts.append(fact.strip())
        self._save()
        log.info("Remembered: %s", fact)
        return f"Stored in memory: {fact}"

    def recall(self) -> str:
        if not self.facts:
            return "Memory is empty."
        return "Stored facts:\n" + "\n".join(f"- {f}" for f in self.facts)

    def forget_all(self) -> str:
        self.facts.clear()
        self._save()
        return "All stored facts were erased."

    def log_activity(self, summary: str) -> None:
        stamp = datetime.now().strftime("%d %b %H:%M")
        self.journal.append(f"[{stamp}] {summary}")
        self.journal = self.journal[-30:]
        self._save()
        log.info("Journal: %s", summary)

    def recent_activity(self, n: int = 10) -> list[str]:
        return self.journal[-n:]

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        max_msgs = config.LLM_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def conversation(self) -> list[dict[str, str]]:
        return list(self.history)
