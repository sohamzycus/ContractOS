"""LLM provider abstraction — supports Anthropic Claude and mock for testing."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class LLMMessage(BaseModel):
    """A single message in a conversation."""

    role: str = Field(pattern=r"^(system|user|assistant)$")
    content: str = Field(min_length=1)


class LLMResponse(BaseModel):
    """Response from an LLM provider."""

    content: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """Send messages to the LLM and get a completion."""

    @abstractmethod
    async def complete_json(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send messages and parse the response as JSON."""


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider using the official SDK."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        base_url: str | None = None,
    ) -> None:
        try:
            import anthropic
        except ImportError as e:
            msg = "anthropic package required: pip install anthropic"
            raise ImportError(msg) from e
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = anthropic.AsyncAnthropic(**kwargs)
        self._model = model

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if system:
            kwargs["system"] = system
        response = await self._client.messages.create(**kwargs)
        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason,
        )

    async def complete_json(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        response = await self.complete(
            messages, system=system, temperature=temperature, max_tokens=max_tokens,
        )
        text = response.content.strip()
        # Handle markdown code fences
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]) if len(lines) > 2 else text
        return json.loads(text)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for deterministic testing.

    Accepts a list of canned responses that are returned in order.
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses: list[str] = responses or []
        self._call_count = 0
        self.call_log: list[dict[str, Any]] = []

    def add_response(self, response: str) -> None:
        self._responses.append(response)

    async def complete(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        self.call_log.append({
            "messages": [m.model_dump() for m in messages],
            "system": system,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        if self._call_count >= len(self._responses):
            msg = f"MockLLMProvider: no response for call #{self._call_count}"
            raise IndexError(msg)
        content = self._responses[self._call_count]
        self._call_count += 1
        return LLMResponse(
            content=content,
            model="mock-model",
            input_tokens=100,
            output_tokens=50,
            stop_reason="end_turn",
        )

    async def complete_json(
        self,
        messages: list[LLMMessage],
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        response = await self.complete(
            messages, system=system, temperature=temperature, max_tokens=max_tokens,
        )
        return json.loads(response.content)
