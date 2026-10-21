from abc import ABC, abstractmethod

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
        import requests

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
        log.debug("Ollama request (%d messages) -> %s", len(messages), self.model)
        resp = self._session.post(
            self._url, json=payload, headers=self._headers, timeout=config.LLM_TIMEOUT
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class AnthropicProvider(LLMProvider):
    def __init__(
        self,
        model: str = config.ANTHROPIC_MODEL,
        api_key: str = config.ANTHROPIC_API_KEY,
    ) -> None:
        import anthropic

        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is not set (see desktop/.env)")
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key)
        self._not_given = anthropic.NOT_GIVEN

    def chat(self, messages: list[Message]) -> str:
        system_parts = [m["content"] for m in messages if m["role"] == "system"]
        convo = [m for m in messages if m["role"] != "system"]
        system_text = "\n\n".join(system_parts)

        log.debug("Anthropic request (%d messages) -> %s", len(convo), self.model)
        message = self._client.messages.create(
            model=self.model,
            max_tokens=config.LLM_MAX_TOKENS,
            system=system_text or self._not_given,
            messages=convo,
        )
        return "".join(b.text for b in message.content if b.type == "text")


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        model: str = config.OPENAI_MODEL,
        api_key: str = config.OPENAI_API_KEY,
        base_url: str = config.OPENAI_BASE_URL,
    ) -> None:
        from openai import OpenAI

        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set (see desktop/.env)")
        self.model = model
        self._client = OpenAI(api_key=api_key, base_url=base_url or None)

    def chat(self, messages: list[Message]) -> str:
        log.debug("OpenAI request (%d messages) -> %s", len(messages), self.model)
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
            timeout=config.LLM_TIMEOUT,
        )
        return resp.choices[0].message.content or ""


_PROVIDERS = {
    "ollama": OllamaCloudProvider,
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,
    "openai": OpenAIProvider,
}


def create_provider() -> LLMProvider:
    provider_cls = _PROVIDERS.get(config.LLM_PROVIDER)
    if provider_cls is None:
        raise ValueError(
            f"Unknown KNOC8_LLM_PROVIDER '{config.LLM_PROVIDER}' "
            f"(choose from: {', '.join(_PROVIDERS)})"
        )
    log.info("LLM provider: %s", config.LLM_PROVIDER)
    return provider_cls()
