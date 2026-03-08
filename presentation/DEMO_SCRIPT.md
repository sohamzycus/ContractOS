# ContractOS Demo Script & Storyboard

> Voiceover-ready script for capstone video recording.
> Estimated total runtime: 12-15 minutes.

---

## Pre-Recording Setup

1. Start the server:
   ```bash
   cd /path/to/ContractOS
   source .venv/bin/activate
   export ANTHROPIC_API_KEY="your-key"
   export ANTHROPIC_BASE_URL="https://your-proxy/"
   export ANTHROPIC_MODEL="claude-sonnet-4-5-global"
   python -m uvicorn contractos.api.app:create_app --host 127.0.0.1 --port 8742 --factory
   ```

2. Open browser tabs:
   - Tab 1: `http://127.0.0.1:8742/demo/copilot.html` (Document Copilot)
   - Tab 2: `http://127.0.0.1:8742/demo/graph.html` (TrustGraph — optional)
   - Tab 3: Cursor IDE with ContractOS project open (for MCP demo)

3. Have contracts ready:
   - `demo/samples/complex_procurement_framework.pdf`
   - `demo/samples/complex_it_outsourcing.docx`

4. Clear any previous data: Click "Clear All" in the Copilot or run `DELETE /contracts/clear`

---

## INTRO (30 seconds)

### Voiceover:
> "Contracts are the backbone of every business relationship — but they're also one of the most misunderstood documents in any organization. A 50-page outsourcing agreement contains obligations buried in tables, definitions that transform meaning, and cross-references that create invisible dependencies.
>
> Today I'm going to show you ContractOS — an AI-powered system that transforms static legal documents into structured, queryable, explainable legal knowledge. Every answer is grounded in source text. Every claim is traceable. Let me show you what that looks like in practice."

### Screen:
- Show the presentation title slide briefly, then switch to the Copilot UI

---

## ACT 1: Complex Procurement Framework (5-6 minutes)

### Scene 1.1: Upload & Extraction (60 seconds)

#### Voiceover:
> "Let's start with a real-world scenario. I have here a Procurement Framework Agreement — an 85 million pound contract between Pinnacle Manufacturing in the UK and GlobalSource Industrial Supply in Singapore. This is a multi-category procurement framework covering 14 delivery points across 10 countries."

#### Screen Action:
- Drag and drop `complex_procurement_framework.pdf` into the Copilot
- Wait for upload and extraction to complete

#### Voiceover (while loading):
> "ContractOS is now running its three-phase extraction pipeline. Phase one uses regex patterns and structural parsing to extract facts deterministically — dates, amounts, definitions, party names. Phase two builds a FAISS vector index for semantic search. All of this happens in seconds, with zero LLM calls."

#### Voiceover (when complete):
> "And there we go — [read the extraction summary numbers]. The document is now fully rendered on the left, and our AI copilot is ready on the right. Let me click through some of the quick-action buttons to show you what was extracted."

#### Screen Action:
- Click "Parties" button — show the extracted parties
- Click "Definitions" — show resolved bindings
- Briefly scroll through the rendered document

---

### Scene 1.2: The Lorry Strike Scenario (90 seconds)

#### Voiceover:
> "Now here's where it gets interesting. Let me paint you a real-world scenario.
>
> Imagine you're a procurement manager at Pinnacle Manufacturing. There's been an interstate transport strike. A lorry carrying raw materials from GlobalSource got delayed — the goods arrived at your godown 10 days late. To keep your production line running, you had to emergency-procure from a local vendor at a higher cost. Now the original shipment has finally arrived.
>
> The question is: What are your legal options? Can you reject the late delivery? Can you cancel the order and claim your money back? Are you entitled to liquidated damages?"

#### Screen Action:
- Type into the Copilot chat:
  ```
  Due to a recent interstate transport strike, a lorry carrying goods from our supplier was delayed by 10 days. We had to procure from a local vendor at higher cost. The original shipment has now arrived at our godown. What are my legal options under this contract? Can I reject the late delivery, cancel the order, and claim my money back?
  ```
- Wait for the response

#### Voiceover (reading response):
> "Look at this response. ContractOS has identified the relevant provisions — [read key points from the answer]. Notice the confidence score and the provenance chain. Each cited fact links back to a specific section of the contract. If I click on any of these references, the document scrolls to and highlights the exact source text."

#### Screen Action:
- Click on a provenance reference to show document highlighting
- Point out the confidence label

---

### Scene 1.3: Follow-Up — Liquidated Damages (60 seconds)

#### Voiceover:
> "Let me dig deeper. What about liquidated damages specifically?"

#### Screen Action:
- Type: `What are the liquidated damages provisions if delivery is late by 10 days? How is the penalty calculated?`
- Wait for response

#### Voiceover:
> "ContractOS retains conversation context across turns — it knows we're still talking about the same contract and the same scenario. [Read key points about liquidated damages from the response]. Again, every figure cited traces back to specific contract text."

---

### Scene 1.4: Playbook Review (90 seconds)

#### Voiceover:
> "Now let me show you something powerful. Instead of asking individual questions, let's run a full playbook compliance review. This compares the contract against our organization's standard positions across 10 key clause types."

#### Screen Action:
- Click "Review Against Playbook" button
- Watch the streaming SSE updates as each clause is evaluated

#### Voiceover (while streaming):
> "Watch this — ContractOS is evaluating each clause type in real time. You can see the progress: GREEN means the clause meets our standard, YELLOW means it deviates and needs negotiation, RED means it's missing or unacceptable.
>
> [As results appear] We've got [X] GREEN findings, [Y] YELLOW, and [Z] RED. For each YELLOW and RED finding, ContractOS has generated automated redline suggestions — alternative language with a rationale and fallback position.
>
> And look at this risk matrix — a 5-by-5 severity times likelihood grid showing the overall risk profile of this contract."

#### Screen Action:
- Expand a YELLOW or RED finding to show the redline suggestion
- Point out the risk matrix visualization

---

## ACT 2: IT Outsourcing Agreement (5-6 minutes)

### Scene 2.1: Upload & Multi-Document Workspace (45 seconds)

#### Voiceover:
> "Now let's add a completely different type of contract to our workspace. This is a 47.5 million dollar IT Outsourcing Services Agreement between Meridian Global Holdings in New York and TechServe Solutions in India. It covers 350 full-time equivalents across 12 locations, with a detailed SLA framework, data protection requirements, and complex liability provisions.
>
> Notice the workspace sidebar on the left — it already shows our Procurement Framework. I'll upload the IT Outsourcing agreement alongside it."

#### Screen Action:
- Click "Upload Contract" button
- Upload `complex_it_outsourcing.docx`
- Wait for extraction
- Point out the workspace sidebar now showing **2 contracts**

#### Voiceover (when complete):
> "[Read extraction numbers] — notice how much richer this document is. And look at the workspace sidebar — we now have two contracts loaded. I can click between them to switch the document view, or I can enable cross-contract Q&A to query across both simultaneously."

---

### Scene 2.2: The Data Breach Scenario (90 seconds)

#### Voiceover:
> "Here's our second scenario. TechServe, our outsourcing vendor, has experienced a data breach. 50,000 customer records have been compromised — including personally identifiable information. Their SLA specifies a 15-minute response time for Severity 1 incidents, but they took 3 full days to notify us. That's a violation of both the SLA and the 24-hour breach notification requirement in the data protection clause.
>
> We want to know: Can we terminate this contract for cause? What damages can we claim? And critically — does the liability cap apply to data breaches?"

#### Screen Action:
- Type into the Copilot:
  ```
  Our vendor TechServe had a data breach affecting 50,000 customer records with PII. Their SLA requires 15-minute response for Severity 1 incidents but they took 3 days to notify us, violating the 24-hour breach notification requirement. Can we terminate for cause? What damages can we claim? Does the liability cap apply to data breaches?
  ```
- Wait for response

#### Voiceover (reading response):
> "This is exactly why ContractOS is powerful. Look at the answer — [read key points]. The system has traced through multiple interconnected provisions: the SLA table showing the 15-minute response time, the data protection clause requiring 24-hour notification, the termination-for-cause provision, AND the liability section — specifically the carve-out that says the liability cap does NOT apply to data breaches. That's Section 9.2.
>
> A human lawyer would need to cross-reference at least 4 different sections to reach this conclusion. ContractOS did it in seconds, with full provenance."

#### Screen Action:
- Click provenance references to highlight source text in the document
- Show how the answer traces through multiple sections

---

### Scene 2.3: Liability Deep-Dive (60 seconds)

#### Voiceover:
> "Let me ask a targeted follow-up about the liability structure."

#### Screen Action:
- Type: `What is the exact liability cap amount and what specific categories of liability are excluded from the cap? List each exclusion.`
- Wait for response

#### Voiceover:
> "[Read the response] — The general cap is 150% of annual fees, which is 14.25 million dollars. But data breaches, confidentiality breaches, IP infringement, willful misconduct, and regulatory non-compliance are all carved out — meaning unlimited liability. This is critical information for our breach scenario."

---

### Scene 2.4: NDA Triage or Risk Memo (60 seconds)

#### Voiceover:
> "Let me generate a comprehensive risk memo for this contract."

#### Screen Action:
- Click "Risk Memo" or trigger via the streaming endpoint
- Watch progressive results

#### Voiceover:
> "ContractOS is now generating a structured risk assessment — executive summary, key risks with severity and likelihood scoring, missing protections, and prioritized recommendations. [Read a few highlights as they stream in].
>
> This is the kind of analysis that would take a legal team hours to produce manually. ContractOS delivers it in under a minute, grounded in extracted evidence."

---

## ACT 3: Cross-Contract Intelligence (3 minutes)

### Scene 3.1: Compare Contracts via Workspace (90 seconds)

#### Voiceover:
> "Now for the finale — cross-contract intelligence. Both contracts are already in our workspace. Let me select them both and use the built-in comparison feature."

#### Screen Action:
- In the workspace sidebar, click the checkboxes on both contracts to select them
- Click the **"⚖️ Compare Selected"** button
- Wait for the comparison results

#### Voiceover:
> "ContractOS is now comparing both contracts clause by clause. [Read key differences as they appear]. Look at this side-by-side comparison — for each aspect, you can see exactly how the two contracts differ. The procurement framework has a 90-day threshold before termination rights kick in, while the IT outsourcing agreement has a 60-day threshold plus specific pandemic provisions.
>
> Each difference is rated by significance — high, medium, or low — with risk implications noted."

---

### Scene 3.2: Cross-Contract Q&A (60 seconds)

#### Voiceover:
> "But comparison isn't the only cross-contract capability. Let me enable cross-contract Q&A mode."

#### Screen Action:
- Click **"🔗 Cross-Contract Q&A"** button in the workspace sidebar
- Notice the input placeholder changes to "Ask across ALL contracts..."
- Type: `If our vendor's delivery is delayed due to a force majeure event like a transport strike, compare my options under both contracts. Which one gives me stronger termination rights?`
- Wait for response

#### Voiceover:
> "Now ContractOS is querying across BOTH contracts simultaneously. [Read key points from the response]. It's pulling facts from both the procurement framework and the IT outsourcing agreement, labeling each source so you know exactly which contract each provision comes from. This is true cross-contract intelligence."

---

### Scene 3.3: MCP in Cursor (Optional — 60 seconds)

#### Voiceover:
> "One last thing — ContractOS isn't just a web app. It's also an MCP server — that's Anthropic's Model Context Protocol. This means any AI assistant that supports MCP can use ContractOS as a tool."

#### Screen Action:
- Switch to Cursor IDE
- In the chat, type: `Load the simple NDA sample and run a full contract analysis`
- Show the MCP tools being called

#### Voiceover:
> "Watch — the AI assistant in Cursor is calling ContractOS MCP tools: load sample contract, triage NDA, review against playbook, extract obligations. All 13 tools are available. You can do everything we just demonstrated without ever leaving your IDE."

---

## CLOSING (30 seconds)

#### Voiceover:
> "That's ContractOS — the operating system for contract intelligence. 794 tests passing, 34 API endpoints, 13 MCP tools, tested against 50 real NDA documents from Stanford's ContractNLI dataset.
>
> Built entirely with test-driven development — 14,800 lines of test code, 1.5 times the production code.
>
> The core insight is simple: separate what a contract says from what it means, from what can be derived, from what someone thinks about it. That's the truth model. That's what makes every answer auditable and every claim traceable.
>
> Don't read contracts. Understand them. Thank you."

#### Screen:
- Show the final presentation slide: "Don't read contracts. Understand them."

---

## Post-Recording Notes

### Key Moments to Emphasize
1. **Provenance clicking** — Every time you click a source reference and the document highlights the exact text, pause briefly. This is the "wow" moment. The text_span now matches precisely.
2. **Streaming playbook review** — The real-time GREEN/YELLOW/RED updates are visually compelling. Let them play out.
3. **Liability carve-out** — The data breach scenario where the cap doesn't apply is the strongest "this is why you need AI" moment.
4. **Workspace sidebar** — Show the multi-document workspace with both contracts listed. Click between them to show document switching.
5. **Compare Selected** — The side-by-side comparison with significance ratings is visually impressive.
6. **Cross-Contract Q&A** — Toggle it on, ask a question, and show facts labeled from different contracts.

### Pacing Tips
- Speak slightly slower than conversational pace
- Pause after asking each scenario question — let the audience absorb the complexity
- When reading ContractOS responses, summarize rather than reading verbatim
- Let streaming animations play out — don't rush past them

### Backup Questions (if demo time allows)
- "What insurance coverage is required and what are the minimum amounts?"
- "If TechServe is acquired by a competitor, can they still perform under this contract?"
- "What happens if the Service Provider's employees go on strike — is that covered by force majeure?"
- "Compare the confidentiality obligations between both contracts"
- "What are all the deadlines and notice periods in this contract?"

### Technical Contingencies
- If the server is slow: Have pre-recorded responses ready as backup
- If upload fails: Use `load_sample_contract` MCP tool as fallback
- If LLM is unavailable: Show the extraction pipeline (facts, clauses, bindings) which works without LLM
