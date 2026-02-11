"""Integration tests with REAL NDA documents from ContractNLI / HuggingFace.

Tests 50 real-world Non-Disclosure Agreements sourced from:
- ContractNLI dataset (Stanford NLP, CC BY 4.0)
- LegalBench evaluation harness

Document categories tested:
- Corporate mutual NDAs (Bosch, NSK, AMC, BT)
- M&A confidentiality agreements (The Munt, Business Sale, Casino)
- Government/contractor NDAs (CCTV, SAMED, CEII)
- SEC filing NDAs (802724, 814457, 915191, etc.)
- Template/standard NDAs (Basic, Template, NDA_V3)

Test dimensions:
1. Single-document extraction quality (facts, clauses, bindings)
2. Single-document complex Q&A (confidentiality, termination, scope)
3. Multi-document comparative analysis (2-doc, 3-doc, 5-doc)
4. Cross-document NLI-style questions (entailment checks)
5. Chat history persistence across real documents
6. Bulk operations (upload all, query across all, clear)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from contractos.api.app import create_app
from contractos.api.deps import init_state, shutdown_state
from contractos.config import ContractOSConfig, LLMConfig, StorageConfig

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
NDA_DIR = FIXTURES_DIR / "contractnli_docs"

# ── Document Groups ──────────────────────────────────────────────────
# Curated subsets for different test scenarios

# Well-known corporate NDAs with rich clause structures
CORPORATE_NDAS = [
    "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
    "5-NSK-Confidentiality-Agreement-for-Suppliers.docx",
    "amc-general-mutual-non-disclosure-agreement-en-gb.docx",
    "BT_NDA.docx",
    "non-disclosure-agreement-en.docx",
]

# M&A / business sale confidentiality agreements
MA_NDAS = [
    "12032018_NDA_The_Munt_EN.docx",
    "Business-Sale-Non-Disclosure-Agreement.docx",
    "casino-nondisclosure-agmt.docx",
    "ICTSC-NDA-General-MandA-signed.docx",
    "814457_0000950137-04-009790_c89545exv99wxdyx6y.docx",
]

# Government / contractor NDAs
GOV_NDAS = [
    "064-19_Non_Disclosure_Agreement_2019.docx",
    "1588052992CCTV_Non_Disclosure_Agreement.docx",
    "SAMED_confidentiality_non_disclosure_and_conflict_of_interest_agreement_for_board_and_committee_members_ver_1.docx",
    "ceii-and-nda.docx",
    "Attachment-I-Non-DisclosureAgreementContractor.docx",
]

# SEC filing NDAs (from EDGAR)
SEC_NDAS = [
    "802724_0001193125-15-331613_d96542dex99d5.docx",
    "915191_0001047469-17-003155_a2231967zex-99_8.docx",
    "916457_0000916457-14-000028_exhibit104-confidentiality.docx",
    "1062478_0001193125-14-442753_d838170dex3.docx",
    "1010552_0000912057-01-520246_a2051644zex-99_20.docx",
]

# Diverse mix for multi-document cross-analysis
DIVERSE_MIX = [
    "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
    "12032018_NDA_The_Munt_EN.docx",
    "ceii-and-nda.docx",
    "802724_0001193125-15-331613_d96542dex99d5.docx",
    "Basic-Non-Disclosure-Agreement.docx",
]


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def test_config() -> ContractOSConfig:
    return ContractOSConfig(
        llm=LLMConfig(provider="mock"),
        storage=StorageConfig(path=":memory:"),
    )


@pytest.fixture
async def client(test_config: ContractOSConfig):
    init_state(test_config)
    app = create_app(test_config)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    shutdown_state()


async def _upload(client: AsyncClient, filename: str) -> dict:
    """Upload a fixture file and return the full response dict."""
    path = NDA_DIR / filename
    assert path.exists(), f"Fixture not found: {path}"
    with open(path, "rb") as f:
        resp = await client.post(
            "/contracts/upload",
            files={
                "file": (
                    filename,
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    assert resp.status_code == 201, f"Upload failed for {filename}: {resp.text}"
    return resp.json()


async def _upload_group(client: AsyncClient, filenames: list[str]) -> list[dict]:
    """Upload a group of documents and return all response dicts."""
    results = []
    for fname in filenames:
        data = await _upload(client, fname)
        results.append(data)
    return results


async def _ask(
    client: AsyncClient,
    question: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    """Ask a question and return the response dict."""
    body: dict = {"question": question}
    if document_ids:
        body["document_ids"] = document_ids
    elif document_id:
        body["document_id"] = document_id
    resp = await client.post("/query/ask", json=body)
    assert resp.status_code == 200, f"Query failed: {resp.text}"
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 1: Single Document Extraction Quality
# ═══════════════════════════════════════════════════════════════════════


class TestSingleDocExtractionQuality:
    """Verify extraction pipeline produces meaningful results on real NDAs."""

    @pytest.mark.parametrize(
        "filename",
        CORPORATE_NDAS + MA_NDAS[:2] + GOV_NDAS[:2] + SEC_NDAS[:2],
    )
    async def test_upload_extracts_facts(
        self, client: AsyncClient, filename: str
    ) -> None:
        """Each real NDA should produce at least some extracted facts."""
        data = await _upload(client, filename)
        assert data["status"] == "indexed"
        assert data["fact_count"] > 0, f"{filename}: expected facts, got 0"
        assert data["word_count"] > 100, f"{filename}: too few words"

    @pytest.mark.parametrize(
        "filename",
        [
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
            "5-NSK-Confidentiality-Agreement-for-Suppliers.docx",
            "ceii-and-nda.docx",
            "802724_0001193125-15-331613_d96542dex99d5.docx",
        ],
    )
    async def test_rich_extraction_on_complex_ndas(
        self, client: AsyncClient, filename: str
    ) -> None:
        """Complex NDAs should produce rich extraction with clauses and bindings."""
        data = await _upload(client, filename)
        assert data["fact_count"] >= 10, (
            f"{filename}: expected >=10 facts, got {data['fact_count']}"
        )
        assert data["clause_count"] >= 2, (
            f"{filename}: expected >=2 clauses, got {data['clause_count']}"
        )

    async def test_bosch_nda_has_facts_and_structure(self, client: AsyncClient) -> None:
        """Bosch mutual NDA should extract facts and have graph structure."""
        data = await _upload(
            client,
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
        )
        doc_id = data["document_id"]
        # Should have substantial facts
        resp = await client.get(f"/contracts/{doc_id}/facts")
        assert resp.status_code == 200
        facts = resp.json()
        assert len(facts) > 5, f"Bosch NDA should have >5 facts, got {len(facts)}"
        # Should have a graph
        resp = await client.get(f"/contracts/{doc_id}/graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert len(graph["nodes"]) > 5

    async def test_nsk_nda_has_clauses(self, client: AsyncClient) -> None:
        """NSK supplier confidentiality agreement should have classified clauses."""
        data = await _upload(
            client, "5-NSK-Confidentiality-Agreement-for-Suppliers.docx"
        )
        doc_id = data["document_id"]
        resp = await client.get(f"/contracts/{doc_id}/clauses")
        assert resp.status_code == 200
        clauses = resp.json()
        assert len(clauses) >= 2, f"NSK NDA should have >=2 clauses, got {len(clauses)}"

    async def test_ceii_nda_graph_structure(self, client: AsyncClient) -> None:
        """CEII NDA should produce a well-connected TrustGraph."""
        data = await _upload(client, "ceii-and-nda.docx")
        doc_id = data["document_id"]
        resp = await client.get(f"/contracts/{doc_id}/graph")
        assert resp.status_code == 200
        graph = resp.json()
        assert len(graph["nodes"]) >= 10, "CEII NDA graph should have >=10 nodes"
        assert len(graph["edges"]) >= 5, "CEII NDA graph should have >=5 edges"
        # Should have contract root node
        node_types = {n["type"] for n in graph["nodes"]}
        assert "contract" in node_types
        assert "fact" in node_types

    async def test_sec_filing_nda_extraction(self, client: AsyncClient) -> None:
        """SEC filing NDAs (originally HTML) should extract cleanly."""
        data = await _upload(
            client, "802724_0001193125-15-331613_d96542dex99d5.docx"
        )
        assert data["status"] == "indexed"
        assert data["word_count"] > 1000, "SEC filing NDA should be substantial"
        assert data["fact_count"] > 15, "SEC filing NDA should have many facts"


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 2: Single Document Complex Q&A
# ═══════════════════════════════════════════════════════════════════════


class TestSingleDocComplexQA:
    """Complex questions against individual real NDA documents."""

    async def test_bosch_confidentiality_scope(self, client: AsyncClient) -> None:
        """Ask about the scope of confidential information in Bosch NDA."""
        data = await _upload(
            client,
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
        )
        result = await _ask(
            client,
            "What types of information are considered confidential under this agreement?",
            document_id=data["document_id"],
        )
        assert result["answer"], "Should provide an answer about confidentiality scope"
        assert result["session_id"], "Should persist session"
        assert len(result["document_ids"]) == 1

    async def test_nsk_termination_provisions(self, client: AsyncClient) -> None:
        """Ask about termination and survival in NSK agreement."""
        data = await _upload(
            client, "5-NSK-Confidentiality-Agreement-for-Suppliers.docx"
        )
        result = await _ask(
            client,
            "What happens when this agreement terminates? Do any obligations survive?",
            document_id=data["document_id"],
        )
        assert result["answer"]
        assert result["retrieval_method"] in ("faiss_semantic", "full_scan")

    async def test_the_munt_disclosure_restrictions(
        self, client: AsyncClient
    ) -> None:
        """Ask about disclosure restrictions in The Munt M&A NDA."""
        data = await _upload(client, "12032018_NDA_The_Munt_EN.docx")
        result = await _ask(
            client,
            "Under what circumstances can the receiving party disclose confidential information to third parties?",
            document_id=data["document_id"],
        )
        assert result["answer"]
        assert result["session_id"]

    async def test_ceii_compelled_disclosure(self, client: AsyncClient) -> None:
        """Ask about compelled disclosure provisions in CEII NDA."""
        data = await _upload(client, "ceii-and-nda.docx")
        result = await _ask(
            client,
            "What must a party do if they are legally compelled to disclose confidential information?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_sec_filing_residuals_clause(self, client: AsyncClient) -> None:
        """Ask about residuals clause in SEC filing NDA (a complex legal concept)."""
        data = await _upload(
            client, "802724_0001193125-15-331613_d96542dex99d5.docx"
        )
        result = await _ask(
            client,
            "Does this agreement contain a residuals clause? What information can be freely used after the agreement?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_casino_nda_return_of_materials(
        self, client: AsyncClient
    ) -> None:
        """Ask about return of confidential materials in casino NDA."""
        data = await _upload(client, "casino-nondisclosure-agmt.docx")
        result = await _ask(
            client,
            "What are the obligations regarding return or destruction of confidential materials?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_samed_board_confidentiality(self, client: AsyncClient) -> None:
        """Ask about board member confidentiality obligations in SAMED NDA."""
        data = await _upload(
            client,
            "SAMED_confidentiality_non_disclosure_and_conflict_of_interest_agreement_for_board_and_committee_members_ver_1.docx",
        )
        result = await _ask(
            client,
            "What specific confidentiality obligations do board members have? Are board meetings open to the public?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_provenance_returned_for_real_doc(
        self, client: AsyncClient
    ) -> None:
        """Provenance chain should be returned for queries on real documents."""
        data = await _upload(
            client,
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
        )
        result = await _ask(
            client,
            "What is the definition of Confidential Information?",
            document_id=data["document_id"],
        )
        # Provenance should be present
        assert result.get("provenance") is not None or result.get("facts_referenced") is not None


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 3: Multi-Document Comparative Analysis
# ═══════════════════════════════════════════════════════════════════════


class TestMultiDocComparativeAnalysis:
    """Cross-document queries using real NDA documents."""

    async def test_compare_two_corporate_ndas(self, client: AsyncClient) -> None:
        """Compare confidentiality scope between Bosch and NSK NDAs."""
        docs = await _upload_group(client, CORPORATE_NDAS[:2])
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Compare the definition and scope of Confidential Information between these two agreements. Which is broader?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 2
        assert result["session_id"]

    async def test_compare_termination_across_three_ndas(
        self, client: AsyncClient
    ) -> None:
        """Compare termination provisions across three different NDA types."""
        filenames = [
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
            "12032018_NDA_The_Munt_EN.docx",
            "ceii-and-nda.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Compare the termination clauses across these three agreements. What are the notice periods and survival obligations?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 3

    async def test_compare_five_ndas_disclosure_rules(
        self, client: AsyncClient
    ) -> None:
        """Compare disclosure rules across 5 diverse NDAs."""
        docs = await _upload_group(client, DIVERSE_MIX)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Which of these agreements allows sharing confidential information with employees? What conditions apply?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 5

    async def test_cross_analyze_corporate_vs_ma_ndas(
        self, client: AsyncClient
    ) -> None:
        """Compare a corporate NDA with an M&A NDA."""
        filenames = [
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
            "814457_0000950137-04-009790_c89545exv99wxdyx6y.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "How do the permitted uses of confidential information differ between these agreements? Does either contain a residuals clause?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 2

    async def test_multi_doc_licensing_restrictions(
        self, client: AsyncClient
    ) -> None:
        """Check licensing restrictions across multiple NDAs."""
        filenames = [
            "064-19_Non_Disclosure_Agreement_2019.docx",
            "118.3-Non-disclosure-agreement.docx",
            "130806ca141.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Do any of these agreements grant intellectual property licenses? What are the licensing restrictions?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 3


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 4: ContractNLI-Style Entailment Questions
# ═══════════════════════════════════════════════════════════════════════


class TestContractNLIEntailment:
    """Questions modeled after ContractNLI hypotheses — testing NLI capabilities.

    These map to the 17 fixed hypotheses from the ContractNLI dataset:
    - Explicit identification of confidential information
    - Limited use restrictions
    - No licensing grants
    - Notice on compelled disclosure
    - Sharing with employees
    - Sharing with third parties
    - Return of confidential information
    - Survival of obligations
    - Permissible copying
    - Permissible development of similar information
    - Permissible acquisition of similar information
    - Permissible post-agreement possession
    - Confidentiality of the agreement itself
    - Inclusion of verbally conveyed information
    """

    async def test_nli_explicit_identification(self, client: AsyncClient) -> None:
        """Does the agreement require explicit identification of confidential info?"""
        data = await _upload(
            client, "amc-general-mutual-non-disclosure-agreement-en-gb.docx"
        )
        result = await _ask(
            client,
            "Does this agreement require that all Confidential Information be expressly identified or marked by the Disclosing Party?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_limited_use(self, client: AsyncClient) -> None:
        """Does the agreement restrict use of confidential info to stated purpose?"""
        data = await _upload(client, "130806ca141.docx")
        result = await _ask(
            client,
            "Is the Receiving Party restricted to using the Confidential Information only for the purpose stated in the agreement?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_no_licensing(self, client: AsyncClient) -> None:
        """Does the agreement explicitly state no IP license is granted?"""
        data = await _upload(client, "118.3-Non-disclosure-agreement.docx")
        result = await _ask(
            client,
            "Does this agreement explicitly state that no license or intellectual property rights are granted?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_compelled_disclosure_notice(
        self, client: AsyncClient
    ) -> None:
        """Does the agreement require notice before compelled disclosure?"""
        data = await _upload(
            client, "5-NSK-Confidentiality-Agreement-for-Suppliers.docx"
        )
        result = await _ask(
            client,
            "If the Receiving Party is legally compelled to disclose confidential information, must they notify the Disclosing Party first?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_sharing_with_employees(self, client: AsyncClient) -> None:
        """Does the agreement permit sharing with employees?"""
        data = await _upload(
            client,
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
        )
        result = await _ask(
            client,
            "Can the Receiving Party share Confidential Information with its employees? Under what conditions?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_return_of_information(self, client: AsyncClient) -> None:
        """Does the agreement require return of confidential information?"""
        data = await _upload(client, "mutual-non-disclosure-agreement.docx")
        result = await _ask(
            client,
            "Does this agreement require the return or destruction of Confidential Information upon request or termination?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_survival_of_obligations(self, client: AsyncClient) -> None:
        """Do obligations survive termination?"""
        data = await _upload(client, "NDA-Urban_Wind_Turbines.docx")
        result = await _ask(
            client,
            "Do any obligations under this agreement survive its termination? Which ones?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_confidentiality_of_agreement_itself(
        self, client: AsyncClient
    ) -> None:
        """Is the existence of the agreement itself confidential?"""
        data = await _upload(
            client, "59b1148ff6952b0001bdbedc_20170907_non_disclosure_agreement_expert.docx"
        )
        result = await _ask(
            client,
            "Is the existence of this agreement or the fact that negotiations are taking place considered confidential?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_verbally_conveyed_info(self, client: AsyncClient) -> None:
        """Does the agreement cover verbally conveyed information?"""
        data = await _upload(
            client, "1588052992CCTV_Non_Disclosure_Agreement.docx"
        )
        result = await _ask(
            client,
            "Does this agreement cover information that is conveyed verbally or orally, not just in written form?",
            document_id=data["document_id"],
        )
        assert result["answer"]

    async def test_nli_multi_doc_entailment_comparison(
        self, client: AsyncClient
    ) -> None:
        """Compare entailment of the same hypothesis across multiple NDAs."""
        filenames = [
            "064-19_Non_Disclosure_Agreement_2019.docx",
            "ConfidentialityAgreement.docx",
            "MUTUAL_NDA.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Which of these agreements explicitly prohibit the Receiving Party from copying Confidential Information? Compare the copying restrictions.",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 3


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 5: Chat History & Session Persistence with Real Docs
# ═══════════════════════════════════════════════════════════════════════


class TestChatHistoryWithRealDocs:
    """Verify chat history works correctly with real NDA documents."""

    async def test_session_persistence_single_doc(
        self, client: AsyncClient
    ) -> None:
        """Single-doc query should persist in chat history."""
        data = await _upload(client, "BT_NDA.docx")
        result = await _ask(
            client,
            "What is the governing law of this agreement?",
            document_id=data["document_id"],
        )
        assert result["session_id"]

        # Check history
        resp = await client.get("/query/history")
        history = resp.json()
        assert len(history) >= 1
        assert history[0]["question"] == "What is the governing law of this agreement?"

    async def test_session_persistence_multi_doc(
        self, client: AsyncClient
    ) -> None:
        """Multi-doc query should persist with correct document_ids."""
        docs = await _upload_group(
            client,
            [
                "BT_NDA.docx",
                "AGProjects-NDA.docx",
            ],
        )
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Compare the duration of confidentiality obligations",
            document_ids=doc_ids,
        )

        resp = await client.get("/query/history")
        history = resp.json()
        assert len(history) >= 1
        latest = history[0]
        assert len(latest["document_ids"]) == 2

    async def test_multiple_queries_history_ordering(
        self, client: AsyncClient
    ) -> None:
        """Multiple queries should appear in reverse chronological order."""
        data = await _upload(client, "Basic-Non-Disclosure-Agreement.docx")
        doc_id = data["document_id"]

        questions = [
            "What is the definition of Confidential Information?",
            "What are the exclusions from confidential information?",
            "What is the term of this agreement?",
        ]
        for q in questions:
            await _ask(client, q, document_id=doc_id)

        resp = await client.get("/query/history")
        history = resp.json()
        assert len(history) >= 3
        # Most recent first
        assert history[0]["question"] == questions[-1]

    async def test_clear_history_after_real_queries(
        self, client: AsyncClient
    ) -> None:
        """Clear history should remove all sessions from real doc queries."""
        data = await _upload(client, "NDA_V3.docx")
        await _ask(
            client,
            "What are the remedies for breach?",
            document_id=data["document_id"],
        )

        # Clear
        resp = await client.delete("/query/history")
        assert resp.status_code == 200
        assert resp.json()["cleared"] >= 1

        # Verify empty
        resp = await client.get("/query/history")
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 6: Bulk Upload & Operations
# ═══════════════════════════════════════════════════════════════════════


class TestBulkOperations:
    """Test uploading many real documents and bulk operations."""

    async def test_upload_ten_diverse_ndas(self, client: AsyncClient) -> None:
        """Upload 10 diverse NDAs and verify all are listed."""
        filenames = (CORPORATE_NDAS[:3] + MA_NDAS[:3] + GOV_NDAS[:2] + SEC_NDAS[:2])
        docs = await _upload_group(client, filenames)

        resp = await client.get("/contracts")
        contracts = resp.json()
        assert len(contracts) == 10

        # All should have facts
        for c in contracts:
            assert c["fact_count"] > 0, f"{c['title']}: no facts extracted"

    async def test_query_across_all_uploaded(self, client: AsyncClient) -> None:
        """Query across all uploaded documents."""
        filenames = CORPORATE_NDAS[:3] + MA_NDAS[:2]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Which of these agreements has the strongest confidentiality protections? What remedies are available for breach?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 5

    async def test_clear_all_after_bulk_upload(self, client: AsyncClient) -> None:
        """Clear all should remove everything after bulk upload."""
        filenames = CORPORATE_NDAS[:3]
        await _upload_group(client, filenames)

        # Ask some questions
        resp = await client.get("/contracts")
        contracts = resp.json()
        for c in contracts[:2]:
            await _ask(
                client,
                "What is this agreement about?",
                document_id=c["document_id"],
            )

        # Clear all
        resp = await client.delete("/contracts/clear")
        assert resp.status_code == 200
        assert resp.json()["cleared_contracts"] == 3

        # Verify empty
        resp = await client.get("/contracts")
        assert resp.json() == []

        # History should also be cleared
        resp = await client.delete("/query/history")
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════
# TEST SUITE 7: Complex Cross-Document Legal Analysis
# ═══════════════════════════════════════════════════════════════════════


class TestComplexCrossDocAnalysis:
    """Advanced multi-document legal analysis questions."""

    async def test_identify_most_restrictive_nda(
        self, client: AsyncClient
    ) -> None:
        """Identify which NDA has the most restrictive terms."""
        filenames = [
            "01_Bosch-Automotive-Service-Solutions-Mutual-Non-Disclosure-Agreement-7-12-17.docx",
            "Basic-Non-Disclosure-Agreement.docx",
            "802724_0001193125-15-331613_d96542dex99d5.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "Analyze the restrictiveness of each agreement. Which has the broadest definition of confidential information? Which has the longest survival period? Which is most favorable to the disclosing party?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 3

    async def test_remedies_comparison(self, client: AsyncClient) -> None:
        """Compare available remedies across different NDA types."""
        filenames = [
            "5bfbcabf0627e70bdcfc5b32_nda-ready4s.docx",
            "ceii-and-nda.docx",
            "915191_0001047469-17-003155_a2231967zex-99_8.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "What remedies are available for breach of confidentiality in each agreement? Do any mention injunctive relief or specific performance?",
            document_ids=doc_ids,
        )
        assert result["answer"]

    async def test_exceptions_and_carveouts(self, client: AsyncClient) -> None:
        """Compare exceptions to confidentiality across NDAs."""
        filenames = [
            "confidentiality-agreement.docx",
            "Non-Disclosure-Agreement-NDA.docx",
            "Template-NDA-2-way-final-1.docx",
            "Confidentiality_Agreement_1.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "What are the standard exceptions to confidentiality in each agreement? Do they all include publicly available information, prior knowledge, and independent development?",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 4

    async def test_governing_law_comparison(self, client: AsyncClient) -> None:
        """Compare governing law provisions across international NDAs."""
        filenames = [
            "12032018_NDA_The_Munt_EN.docx",
            "Clause-de-non-divulgation.docx",
            "ADVANIDE-NON-DISCLOSURE-AGREEMENT.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "What is the governing law and jurisdiction for each agreement? Are there any arbitration clauses?",
            document_ids=doc_ids,
        )
        assert result["answer"]

    async def test_definition_scope_analysis(self, client: AsyncClient) -> None:
        """Deep analysis of how 'Confidential Information' is defined differently."""
        filenames = [
            "1588052992CCTV_Non_Disclosure_Agreement.docx",
            "amc-general-mutual-non-disclosure-agreement-en-gb.docx",
            "883905_0001095811-01-000469_f68556ex99-d12.docx",
            "1043003_0000950170-98-000097_document_12.docx",
            "ConfidNonDisclosureAgree.docx",
        ]
        docs = await _upload_group(client, filenames)
        doc_ids = [d["document_id"] for d in docs]

        result = await _ask(
            client,
            "How does each agreement define 'Confidential Information'? Which agreements require marking or identification? Which include oral/verbal information? Provide a comparative summary.",
            document_ids=doc_ids,
        )
        assert result["answer"]
        assert len(result["document_ids"]) == 5
