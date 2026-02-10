"""Unit tests for LLM provider abstraction."""

from __future__ import annotations

import json

import pytest

from contractos.llm.provider import LLMMessage, LLMResponse, MockLLMProvider


# ── LLMMessage / LLMResponse models ───────────────────────────────


class TestLLMMessage:
    def test_valid_roles(self) -> None:
        for role in ("system", "user", "assistant"):
            msg = LLMMessage(role=role, content="hello")
            assert msg.role == role

    def test_invalid_role_rejected(self) -> None:
        with pytest.raises(Exception):
            LLMMessage(role="tool", content="hello")

    def test_empty_content_rejected(self) -> None:
        with pytest.raises(Exception):
            LLMMessage(role="user", content="")


class TestLLMResponse:
    def test_basic_response(self) -> None:
        resp = LLMResponse(content="Hello", model="claude-3", input_tokens=10, output_tokens=5)
        assert resp.content == "Hello"
        assert resp.model == "claude-3"

    def test_defaults(self) -> None:
        resp = LLMResponse(content="Hi", model="m")
        assert resp.input_tokens == 0
        assert resp.output_tokens == 0
        assert resp.stop_reason is None


# ── MockLLMProvider ────────────────────────────────────────────────


class TestMockLLMProvider:
    @pytest.mark.asyncio
    async def test_returns_canned_responses_in_order(self) -> None:
        mock = MockLLMProvider(responses=["first", "second"])
        msgs = [LLMMessage(role="user", content="hi")]

        r1 = await mock.complete(msgs)
        assert r1.content == "first"
        assert r1.model == "mock-model"

        r2 = await mock.complete(msgs)
        assert r2.content == "second"

    @pytest.mark.asyncio
    async def test_raises_when_no_more_responses(self) -> None:
        mock = MockLLMProvider(responses=["only-one"])
        msgs = [LLMMessage(role="user", content="hi")]
        await mock.complete(msgs)
        with pytest.raises(IndexError, match="no response for call #1"):
            await mock.complete(msgs)

    @pytest.mark.asyncio
    async def test_add_response(self) -> None:
        mock = MockLLMProvider()
        mock.add_response("dynamic")
        msgs = [LLMMessage(role="user", content="hi")]
        r = await mock.complete(msgs)
        assert r.content == "dynamic"

    @pytest.mark.asyncio
    async def test_call_log_records_all_calls(self) -> None:
        mock = MockLLMProvider(responses=["ok"])
        msgs = [LLMMessage(role="user", content="test")]
        await mock.complete(msgs, system="sys prompt", temperature=0.5)
        assert len(mock.call_log) == 1
        assert mock.call_log[0]["system"] == "sys prompt"
        assert mock.call_log[0]["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_complete_json_parses_response(self) -> None:
        payload = {"facts": [{"id": "f-001", "value": "Net 90"}]}
        mock = MockLLMProvider(responses=[json.dumps(payload)])
        msgs = [LLMMessage(role="user", content="extract")]
        result = await mock.complete_json(msgs)
        assert result == payload

    @pytest.mark.asyncio
    async def test_complete_json_invalid_json_raises(self) -> None:
        mock = MockLLMProvider(responses=["not json"])
        msgs = [LLMMessage(role="user", content="extract")]
        with pytest.raises(json.JSONDecodeError):
            await mock.complete_json(msgs)

    @pytest.mark.asyncio
    async def test_token_counts_in_mock(self) -> None:
        mock = MockLLMProvider(responses=["ok"])
        msgs = [LLMMessage(role="user", content="hi")]
        r = await mock.complete(msgs)
        assert r.input_tokens == 100
        assert r.output_tokens == 50
        assert r.stop_reason == "end_turn"
