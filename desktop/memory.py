import json

import config
from logger import get_logger

log = get_logger("memory")


class Memory:
    def __init__(self) -> None:
        self.history: list[dict[str, str]] = []
        self.facts: list[str] = self._load_facts()

    def _load_facts(self) -> list[str]:
        if config.MEMORY_FILE.exists():
            try:
                return json.loads(config.MEMORY_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError) as exc:
                log.warning("Could not load memory file: %s", exc)
        return []

    def _save_facts(self) -> None:
        config.MEMORY_FILE.write_text(
            json.dumps(self.facts, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def remember(self, fact: str) -> str:
        self.facts.append(fact.strip())
        self._save_facts()
        log.info("Remembered: %s", fact)
        return f"Stored in memory: {fact}"

    def recall(self) -> str:
        if not self.facts:
            return "Memory is empty."
        return "Stored facts:\n" + "\n".join(f"- {f}" for f in self.facts)

    def forget_all(self) -> str:
        self.facts.clear()
        self._save_facts()
        return "All stored facts were erased."

    def add_turn(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        max_msgs = config.LLM_HISTORY_TURNS * 2
        if len(self.history) > max_msgs:
            self.history = self.history[-max_msgs:]

    def conversation(self) -> list[dict[str, str]]:
        return list(self.history)
