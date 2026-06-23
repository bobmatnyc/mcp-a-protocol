---
Status: DRAFT
Version: 1.0.1-beta
Date: 2026-06-18
---

# MCP-A Positioning: Naming, Landscape, & Relationship to Existing Standards

## Naming

MCP-A stands for **MCP Answers Profile**. The full name "MCP Answers Profile" clarifies that this is a specialization of MCP, not a standalone protocol.

---

## MCP-A vs. Related Approaches

### MCP-A vs. RAG (Retrieval-Augmented Generation)

| Aspect | RAG | MCP-A |
|--------|-----|-------|
| **Purpose** | Improve LLM answer quality by retrieving relevant documents before generation. | Orchestrate multi-source compiled answers with routing, fallback, and RBAC. |
| **Core Loop** | Retrieve → Embed/Search → Inject into context → LLM → Answer | Classify question → Route to domains → Fan out → Consolidate → Answer |
| **Determinism** | Deterministic retrieval + LLM (non-deterministic). Result depends on retrieval and model state. | Non-deterministic routing and source selection. Different calls can hit different sources. |
| **Trust Model** | Trust the LLM's fluency. May hallucinate even with good retrieval. | Trust routing decisions and source citations. Answers are source-factored. |
| **Composition** | Single-turn: retrieve, generate. | Multi-turn: classify → route → drill → refine. |
| **Access Control** | Not a first-class concern; implemented as filtering at retrieval time. | RBAC is first-class: every response is scoped to the user's permissions. |
| **Common Use Cases** | QA over a document corpus; knowledge-base search with LLM polish. | Enterprise data federation; compliance-driven multi-source answers; team/org-scoped intelligence. |

**Can they coexist?** Yes. MCP-A can use RAG internally: a domain might be backed by a RAG pipeline (retrieval + LLM). MCP-A is the *orchestration layer above* RAG and other techniques.

### MCP-A and Cache-Augmented Generation (LLM inference technique)

| Aspect | Cache-Augmented Generation | MCP-A |
|--------|---------------------------|-------|
| **Scope** | LLM inference only. Pre-compute and cache tokens/embeddings to reduce latency. | Tool orchestration. Multi-source answer compilation. |
| **Input/Output** | LLM input (context) → cached state → LLM output (text). | Question → routing → sources → consolidated answer. |
| **Determinism** | Deterministic given the cached state. | Non-deterministic; routing varies with context and source state. |
| **Relationship** | Orthogonal. You could use cache-augmented generation inside an MCP-A domain that's backed by an LLM. | Orthogonal. MCP-A doesn't mandate how domains generate answers (LLM, deterministic query, etc.). |

### MCP-A and Context-Augmented Generation (LLM inference technique)

| Aspect | Context-Augmented Generation | MCP-A |
|--------|------------------------------|-------|
| **Scope** | LLM inference. Stuff more context into the input window to improve fluency. | Tool orchestration. Multi-source answer compilation. |
| **Input/Output** | Larger LLM context → better answer. | Question + routing → consolidated, source-cited answer. |
| **Determinism** | Non-deterministic (LLM is non-deterministic). | Non-deterministic routing; compiled answers vary by source selection. |
| **Relationship** | Orthogonal. An MCP-A domain could use context-augmentation internally. | Orthogonal. MCP-A is source-agnostic. |

**Key point**: Cache-augmented and context-augmented generation are *how you implement a single inference step*. MCP-A is *how you orchestrate multiple sources to build an answer*. No conflict.

---

## Relationship to MCP (Model Context Protocol)

MCP is a **transport and tool-calling protocol**: it standardizes how agents call tools, how tools expose themselves, and how results flow back.

MCP-A is **not** a competitor or a sibling to MCP -- it is a **profile of MCP**. Every MCP-A server is an MCP server; every MCP-A client is an MCP client. MCP-A defines specific tools (the seven primitives) and result shapes designed to make LLM processing efficient.

**How they work together**:

```
Agent
  ↓
MCP-A Profile (compiled answers, routing, RBAC, explainability)
  = An MCP specialization
  ↓
MCP Base (tool calls, transport, schemas)
  ↓
Source Systems (JIRA, Salesforce, databases, etc.)
```

**The distinction**:
- **MCP** standardizes how tools are called (transport + schema).
- **MCP-A** standardizes how tool results are compiled so the LLM does less work.

**Concretely**:
1. Agent calls MCP-A `query("What are the open customer issues?")` -- an MCP-A tool.
2. MCP-A (an MCP server) classifies intent: "likely JIRA + Salesforce".
3. MCP-A internally calls MCP tools: `search_jira({"status": "Open", ...})` and `query_salesforce(...)`.
4. MCP-A consolidates the MCP results into a single answer.
5. MCP-A returns the answer + citations + `answer_id` to the agent -- still over MCP.

MCP-A wraps deterministic MCP tool-calling to provide dynamic, personalized, explainable compiled answers. It is an MCP profile, not a fork.

---

## Relationship to the Agentic AI Foundation & SEP Track

The [Agentic AI Foundation](https://www.agenticaifoundation.org/) is exploring standards for multi-agent systems, tool protocols, and orchestration.

**MCP-A's position**:

- **Primary venue** (near term): Standalone GitHub spec repo. Lowest friction, full authorial control, MAEP (MCP-A Enhancement Proposal) process mirrors MCP's SEP.
- **Secondary venue** (long term): Because MCP-A is an MCP profile, graduate the MAEPs into MCP's own SEP track at the AAIF/Linux Foundation, positioning MCP-A as the "MCP Answers Profile".
- **Community**: Publish spec, solicit feedback from Anthropic (Claude team), OpenAI (if applicable), and other MCP adopters.

**Why this sequencing**:

1. Spec is clearer when standalone. The MAEP process is lighter-weight than AAIF governance.
2. Once spec is proven (real implementations exist), proposing to AAIF is a stronger move.
3. AAIF SEP process may add requirements (e.g., reference implementation) that are not ready yet.

---

## Positioning Summary (For Public Writing)

**One-liner**: "MCP-A, the MCP Answers Profile -- a specialization of MCP for dynamic, multi-source, RBAC-aware compiled answers that returns structured, ontology-conformant results, where raw MCP returns whatever each tool returns."

**Three-sentence elevator pitch**:

Today's AI-data interfaces are brittle: agents call individual tools deterministically, and when answers require fanning out across multiple sources, classifying intent, or explaining why a route was chosen, the burden falls on the caller. MCP-A fixes this by defining seven primitives (discover, schema, query, action, follow_up, context, explain) that enable dynamic domain discovery, compiled non-deterministic answers, and routing explainability -- all while respecting user access scope (RBAC) at every step. It's a profile of MCP, designed to be vendor-neutral and publishable as a public standard.

**Key positioning contrasts**:

- **vs. RAG**: RAG retrieves + generates from a single corpus. MCP-A orchestrates answers across multiple domains and routes dynamically based on context.
- **vs. cache-/context-augmented generation (LLM techniques)**: Those are how you optimize inference. MCP-A is how you orchestrate multiple tools to build an answer.
- **vs. raw MCP**: MCP standardizes how tools are called. MCP-A standardizes how tool results are compiled -- structured, ontology-conformant output is part of what separates MCP-A from raw MCP, which returns whatever each tool returns. MCP-A is not a competitor -- it is an MCP profile.

---

## What MCP-A Is *Not*

- **Not a replacement for RAG.** MCP-A can use RAG internally.
- **Not an LLM inference optimization.** It's tool orchestration.
- **Not specific to any single vendor or organization.** It's a public standard, usable by any organization with multi-source data.
- **Not a competitor to MCP.** It's a profile of MCP.
- **Not a database query language.** Domains may be databases, but MCP-A is agnostic.
- **Not a new transport protocol.** MCP-A can be bound to HTTP, gRPC, MCP, or other transports.

---

## References

- [SPEC.md](./SPEC.md) — The formal specification.
- [RFC-PROCESS.md](./RFC-PROCESS.md) — MAEP governance and publication paths.
- [MCP Documentation](https://modelcontextprotocol.io/) — Transport and tool-calling standard.
