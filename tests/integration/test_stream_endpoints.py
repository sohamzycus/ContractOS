"""Integration tests for SSE streaming endpoints (Phase 12).

Tests cover:
- /stream/{document_id}/review — playbook review streaming
- /stream/{document_id}/triage — NDA triage streaming
- /stream/{document_id}/discover — hidden fact discovery streaming
- /stream/{document_id}/obligations — obligation extraction streaming
- /stream/{document_id}/risk-memo — risk memo generation streaming
- /stream/{document_id}/report — HTML report download
- Error handling (404 for missing documents)

Each endpoint returns Server-Sent Events. We parse the event stream and verify
step/result/done events are emitted with the correct structure.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import get_state, init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig
from contractos.llm.provider import MockLLMProvider

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"


def _parse_sse_events(text: str) -> list[dict]:
    """Parse an SSE text stream into a list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = []

    for line in text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data.append(line[6:])
        elif line == "" and current_event is not None:
            data_str = "\n".join(current_data)
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                data = data_str
            events.append({"event": current_event, "data": data})
            current_event = None
            current_data = []
    return events


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    state = init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


@pytest.fixture
def sample_docx():
    """Path to a test DOCX fixture."""
    docx_files = list(FIXTURES_DIR.glob("*.docx"))
    if docx_files:
        return docx_files[0]
    return None


async def _upload_doc(client: AsyncClient, path: Path) -> str:
    """Upload a document and return its document_id."""
    with open(path, "rb") as f:
        mime = (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            if str(path).endswith(".docx")
            else "application/pdf"
        )
        r = await client.post(
            "/contracts/upload",
            files={"file": (path.name, f, mime)},
        )
    assert r.status_code == 201, f"Upload failed: {r.text}"
    return r.json()["document_id"]


# ── 404 Tests ─────────────────────────────────────────────────────


class TestStreamEndpoints404:
    """All streaming endpoints should return 404 for non-existent documents."""

    @pytest.mark.asyncio
    async def test_review_stream_404(self, client):
        r = await client.get("/stream/nonexistent/review")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_triage_stream_404(self, client):
        r = await client.get("/stream/nonexistent/triage")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_discover_stream_404(self, client):
        r = await client.get("/stream/nonexistent/discover")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_obligations_stream_404(self, client):
        r = await client.get("/stream/nonexistent/obligations")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_risk_memo_stream_404(self, client):
        r = await client.get("/stream/nonexistent/risk-memo")
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_report_download_404(self, client):
        r = await client.get("/stream/nonexistent/report?type=review")
        assert r.status_code == 404


# ── Obligation Extraction Stream ──────────────────────────────────


class TestObligationStream:
    """Tests for GET /stream/{document_id}/obligations."""

    @pytest.mark.asyncio
    async def test_obligations_stream_returns_events(self, client, sample_docx):
        """Obligation stream should emit step and result events."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        # Prepare mock LLM response for obligations
        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        mock_llm.add_response(json.dumps({
            "summary": "Contract contains 3 key obligations",
            "total_affirmative": 2,
            "total_negative": 1,
            "total_conditional": 0,
            "obligations": [
                {
                    "party": "Client",
                    "type": "affirmative",
                    "description": "Pay monthly fees within 30 days",
                    "trigger": "",
                    "deadline": "30 days from invoice",
                    "clause_reference": "Section 4.1",
                    "risk_if_breached": "Late payment penalties apply",
                },
                {
                    "party": "Vendor",
                    "type": "affirmative",
                    "description": "Deliver quarterly reports",
                    "trigger": "",
                    "deadline": "End of each quarter",
                    "clause_reference": "Section 6.2",
                    "risk_if_breached": "Service level breach",
                },
                {
                    "party": "Vendor",
                    "type": "negative",
                    "description": "Must not share confidential information",
                    "trigger": "",
                    "deadline": "",
                    "clause_reference": "Section 8.1",
                    "risk_if_breached": "Material breach, termination",
                },
            ],
        }))

        r = await client.get(f"/stream/{doc_id}/obligations")
        assert r.status_code == 200

        events = _parse_sse_events(r.text)
        assert len(events) >= 3  # At least: gather step, extract step, result/done

        # Check for step events
        step_events = [e for e in events if e["event"] == "step"]
        assert len(step_events) >= 2  # gather + extract at minimum

        # Check for result event
        result_events = [e for e in events if e["event"] == "result"]
        assert len(result_events) == 1
        result = result_events[0]["data"]
        assert "obligations" in result
        assert len(result["obligations"]) == 3
        assert result["total_affirmative"] == 2
        assert result["total_negative"] == 1

        # Check for done event
        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) == 1
        assert "elapsed_ms" in done_events[0]["data"]

    @pytest.mark.asyncio
    async def test_obligations_handles_truncated_response(self, client, sample_docx):
        """Should handle truncated LLM response gracefully."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        # Simulate truncated response (as if max_tokens was hit)
        mock_llm.add_response(
            '{"summary": "Many obligations found", '
            '"total_affirmative": 3, "total_negative": 1, "total_conditional": 0, '
            '"obligations": ['
            '{"party": "Client", "type": "affirmative", "description": "Pay fees", '
            '"trigger": "", "deadline": "30 days", "clause_reference": "S4", "risk_if_breached": "Penalty"},'
            '{"party": "Vendor", "type": "negative", "description": "No subcontract'
        )

        r = await client.get(f"/stream/{doc_id}/obligations")
        assert r.status_code == 200

        events = _parse_sse_events(r.text)
        result_events = [e for e in events if e["event"] == "result"]
        assert len(result_events) == 1
        result = result_events[0]["data"]
        # Should have salvaged at least 1 complete obligation
        assert len(result["obligations"]) >= 1
        assert result["obligations"][0]["party"] == "Client"


# ── Risk Memo Stream ─────────────────────────────────────────────


class TestRiskMemoStream:
    """Tests for GET /stream/{document_id}/risk-memo."""

    @pytest.mark.asyncio
    async def test_risk_memo_stream_returns_events(self, client, sample_docx):
        """Risk memo stream should emit step, risk_item, and result events."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        mock_llm.add_response(json.dumps({
            "executive_summary": "This is a high-risk outsourcing agreement.",
            "overall_risk_rating": "high",
            "missing_protections": ["No force majeure clause", "No audit rights"],
            "escalation_items": ["IP ownership unclear"],
            "recommendations": [
                {"priority": "high", "action": "Add force majeure clause", "owner": "Legal"},
                {"priority": "medium", "action": "Negotiate audit rights", "owner": "Procurement"},
            ],
            "key_risks": [
                {
                    "risk": "Unlimited liability exposure",
                    "severity": 5,
                    "likelihood": 3,
                    "category": "financial",
                    "mitigation": "Add liability cap at 2x annual fees",
                },
                {
                    "risk": "Data protection gaps",
                    "severity": 4,
                    "likelihood": 4,
                    "category": "regulatory",
                    "mitigation": "Add GDPR/data processing addendum",
                },
            ],
        }))

        r = await client.get(f"/stream/{doc_id}/risk-memo")
        assert r.status_code == 200

        events = _parse_sse_events(r.text)
        step_events = [e for e in events if e["event"] == "step"]
        result_events = [e for e in events if e["event"] == "result"]
        done_events = [e for e in events if e["event"] == "done"]

        assert len(step_events) >= 2  # gather + analyze
        assert len(result_events) == 1
        assert len(done_events) == 1

        result = result_events[0]["data"]
        assert result["overall_risk_rating"] == "high"
        assert len(result["key_risks"]) == 2
        assert len(result["missing_protections"]) == 2
        assert len(result["recommendations"]) == 2
        assert result["executive_summary"] != ""


# ── Review Stream ─────────────────────────────────────────────────


class TestReviewStream:
    """Tests for GET /stream/{document_id}/review."""

    @pytest.mark.asyncio
    async def test_review_stream_returns_200(self, client, sample_docx):
        """Review stream should return 200 with SSE events."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        r = await client.get(f"/stream/{doc_id}/review")
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")

        events = _parse_sse_events(r.text)
        # Should have at least a done event
        done_events = [e for e in events if e["event"] == "done"]
        assert len(done_events) >= 1


# ── Triage Stream ────────────────────────────────────────────────


class TestTriageStream:
    """Tests for GET /stream/{document_id}/triage."""

    @pytest.mark.asyncio
    async def test_triage_stream_returns_200(self, client, sample_docx):
        """Triage stream should return 200 with SSE events."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        # The triage agent uses the mock LLM which may need responses
        # For mock, it will return default responses or raise — both are acceptable
        # as long as the endpoint doesn't crash
        r = await client.get(f"/stream/{doc_id}/triage")
        assert r.status_code == 200

        events = _parse_sse_events(r.text)
        # Should always have at least the load_checklist step
        step_events = [e for e in events if e["event"] == "step"]
        assert len(step_events) >= 1


# ── Discover Stream ──────────────────────────────────────────────


class TestDiscoverStream:
    """Tests for GET /stream/{document_id}/discover."""

    @pytest.mark.asyncio
    async def test_discover_stream_returns_events(self, client, sample_docx):
        """Discover stream should emit step events and results."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        mock_llm.add_response(json.dumps({
            "discovered_facts": [
                {
                    "type": "hidden_risk",
                    "claim": "No force majeure clause",
                    "evidence": "Agreement lacks FM provisions",
                    "risk_level": "high",
                    "explanation": "No protection for extraordinary events",
                },
            ],
            "summary": "Found 1 hidden fact",
            "categories_found": "hidden_risk",
        }))

        r = await client.get(f"/stream/{doc_id}/discover")
        assert r.status_code == 200

        events = _parse_sse_events(r.text)
        step_events = [e for e in events if e["event"] == "step"]
        assert len(step_events) >= 2  # gather_context + build_prompt at minimum

        result_events = [e for e in events if e["event"] == "result"]
        if result_events:
            result = result_events[0]["data"]
            assert "discovered_facts" in result


# ── Report Download ───────────────────────────────────────────────


class TestReportDownload:
    """Tests for GET /stream/{document_id}/report."""

    @pytest.mark.asyncio
    async def test_report_requires_type_param(self, client, sample_docx):
        """Report endpoint needs a ?type= parameter."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)
        # Missing 'type' param — should get a 422 or handle gracefully
        r = await client.get(f"/stream/{doc_id}/report")
        # FastAPI will treat missing required query param as 422
        assert r.status_code in (422, 400, 200)  # depends on default

    @pytest.mark.asyncio
    async def test_report_review_type_returns_html(self, client, sample_docx):
        """Report download with type=review returns HTML content."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)
        r = await client.get(f"/stream/{doc_id}/report?type=review")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")
        assert "<!DOCTYPE html>" in r.text or "<html" in r.text

    @pytest.mark.asyncio
    async def test_report_triage_type_returns_html(self, client, sample_docx):
        """Report download with type=triage returns HTML content."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)
        r = await client.get(f"/stream/{doc_id}/report?type=triage")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_report_discovery_type_returns_html(self, client, sample_docx):
        """Report download with type=discovery returns HTML content."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)
        r = await client.get(f"/stream/{doc_id}/report?type=discovery")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")


# ── SSE Event Format ──────────────────────────────────────────────


class TestSSEEventFormat:
    """Verify SSE events follow the correct format."""

    @pytest.mark.asyncio
    async def test_events_have_correct_structure(self, client, sample_docx):
        """Every SSE event should have 'event:' and 'data:' lines."""
        if sample_docx is None:
            pytest.skip("No DOCX fixture available")

        doc_id = await _upload_doc(client, sample_docx)

        state = get_state()
        mock_llm = state.llm
        assert isinstance(mock_llm, MockLLMProvider)

        mock_llm.add_response(json.dumps({
            "summary": "Test",
            "total_affirmative": 0,
            "total_negative": 0,
            "total_conditional": 0,
            "obligations": [],
        }))

        r = await client.get(f"/stream/{doc_id}/obligations")
        assert r.status_code == 200

        # Check raw SSE format
        text = r.text
        assert "event: step" in text
        assert "event: result" in text
        assert "event: done" in text
        # Every 'data:' line should be valid JSON
        for line in text.split("\n"):
            if line.startswith("data: "):
                data_str = line[6:]
                parsed = json.loads(data_str)
                assert isinstance(parsed, dict)
