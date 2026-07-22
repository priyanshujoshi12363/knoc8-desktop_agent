from abc import ABC, abstractmethod

import requests

import config
from logger import get_logger

log = get_logger("llm")

Message = dict[str, str]


class LLMProvider(ABC):
    @abstractmethod
    def chat(self, messages: list[Message]) -> str: ...


class OllamaCloudProvider(LLMProvider):
    def __init__(
        self,
        model: str = config.LLM_MODEL,
        api_key: str = config.OLLAMA_API_KEY,
        base_url: str = config.OLLAMA_BASE_URL,
    ) -> None:
        if not api_key:
            raise ValueError("OLLAMA_API_KEY is not set (see desktop/.env)")
        self.model = model
        self._url = f"{base_url.rstrip('/')}/api/chat"
        self._headers = {"Authorization": f"Bearer {api_key}"}
        self._session = requests.Session()

    def chat(self, messages: list[Message]) -> str:
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        log.debug("LLM request (%d messages) -> %s", len(messages), self.model)
        resp = self._session.post(
            self._url, json=payload, headers=self._headers, timeout=config.LLM_TIMEOUT
        )
        resp.raise_for_status()
        content: str = resp.json()["message"]["content"]
        log.debug("LLM response: %s", content[:500])
        return content


def create_provider() -> LLMProvider:
    return OllamaCloudProvider()
