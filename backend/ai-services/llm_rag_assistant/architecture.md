# Operix LLM / RAG Assistant — Architectural Design Document

> **Project:** Operix — Industrial AI Safety Platform  
> **Module:** `llm_rag_assistant`  
> **Author:** Abdallah Waleed (AI Engineer & Software Architect)  
> **Status:** Phase 1 Architectural Blueprint  

---

## 1. Executive Summary & Purpose

The **Operix LLM / RAG Assistant** provides natural-language intelligence over industrial safety policies, incident records, monitoring zones, and camera telemetry. Factory supervisors and managers can query the platform in Arabic or English to understand historical safety events, investigate violations, and receive grounded guidance strictly anchored in verified operational records.

This module is completely decoupled from FastAPI web routing and existing operational database schemas, ensuring maximum portability, testability, and safety.

---

## 2. High-Level Architecture & Component Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        User Query (AR / EN)                            │
│                 "ما هي أكثر مخالفات السلامة تكراراً؟"                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼────────────────────────────────────┐
│                  OperixAssistantService (Facade)                       │
│    - Validates Tenant & User Context (Factory ID, Role)                │
│    - Loads & Manages Isolated Conversation History                     │
└───────────────────┬────────────────────────────────┬───────────────────┘
                    │                                │
    1. Retrieve Context              2. Format Grounded Prompt
                    │                                │
┌───────────────────▼──────────────┐  ┌──────────────▼───────────────────┐
│     Hybrid Retrieval Engine      │  │        Prompt Guardrails         │
│  - Query Embedding               │  │  - Strict Grounding Rules        │
│  - Vector Similarity (Top-K)     │  │  - Anti-Hallucination Filter     │
│  - Metadata Filtering (Factory)  │  │  - Injection Defense (Passive)   │
└───────────────────┬──────────────┘  └──────────────┬───────────────────┘
                    │                                │
┌───────────────────▼──────────────┐                 │
│      Isolated Vector Store       │                 │
│  (Pure NumPy / Local SQLite)     │                 │
│  - Zero modifications to Postgres│                 │
└──────────────────────────────────┘                 │
                                                     │ 3. Dispatch Grounded Request
                                      ┌──────────────▼───────────────────┐
                                      │       Unified LLM Provider       │
                                      │    ┌────────────┐ ┌────────────┐ │
                                      │    │   OpenAI   │ │   Ollama   │ │
                                      │    │  (Cloud)   │ │  (Local)   │ │
                                      │    └────────────┘ └────────────┘ │
                                      └──────────────┬───────────────────┘
                                                     │
┌────────────────────────────────────────────────────▼───────────────────┐
│                      AssistantQueryResponse                            │
│  - Grounded Answer (Arabic or English)                                 │
│  - Source Attribution & Evidence Citations (Rule ID, Incident #)       │
│  - Truthfulness & Evidence Completeness Indicator                      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Core Architectural Decisions & Rationale

### A. Zero Database Schema Modification & Read-Only Policy
- **Decision:** The operational PostgreSQL database (`operix_db`) is accessed in **strictly read-only mode** via parameterized `SELECT` queries.
- **Why:** The existing ERD is approved by the team and active in production. Creating tables or altering existing schemas in `operix_db` violates database safety rules and risks breaking ongoing development by team members (Seif / Backend).

### B. Isolated Vector Storage Architecture
- **Audit Finding:** PostgreSQL 18 on this environment does **not** have the `pgvector` extension installed (`SELECT * FROM pg_available_extensions WHERE name LIKE '%vector%'` returned 0 rows).
- **Decision:** Use an **isolated local vector storage adapter** located in `llm_rag_assistant/data/vector_store/` using a **NumPy-accelerated Cosine Similarity Index** (`numpy_local`), backed by JSON metadata persistence.
- **Why:**
  1. *Zero C-Compilation Issues on Windows:* Heavy libraries (like FAISS or LanceDB) frequently fail to compile on Windows without MSVC C++ build tools. Pure NumPy cosine similarity requires zero external tools.
  2. *Performance:* For factory-scale documentation (1,000 to 50,000 chunks), NumPy matrix vectorization ($\mathbf{Q} \cdot \mathbf{M}^T$) computes Top-K similarity in under **5 milliseconds**.
  3. *Pluggable Adapter:* The vector store adheres to an abstract interface (`VectorStoreBase`). If the team later adds a dedicated vector database or installs `pgvector`, swapping the store requires modifying only one adapter file.

### C. Dual-Provider AI Strategy (Cloud & Local)
- **Decision:** Abstract both LLM generation and Embedding generation behind unified provider interfaces:
  - **Cloud Mode:** OpenAI API (`gpt-4o-mini`, `text-embedding-3-small`).
  - **Local Mode:** Ollama (`llama3.2` / `qwen2.5`, `nomic-embed-text`).
  - **Mock Mode:** Deterministic Mock Provider for offline CI/CD automated tests without requiring paid tokens or running servers.
- **Why:** Provides full offline independence for university lab demonstrations while allowing high-accuracy cloud models when internet access and API keys are available.

### D. Grounding & Anti-Hallucination Framework
- **Decision:**
  1. If retrieved chunks have a similarity score below threshold ($\text{score} < 0.60$) or if no relevant documents are found, the engine **refuses to fabricate answers** and returns:
     > *"Based on the available Operix records, there is insufficient information to answer this question."*
  2. Treat all retrieved chunks as **untrusted data**, not system instructions, neutralizing Prompt Injection attacks.

---

## 4. Risk Analysis & Missing Resources Matrix

| # | Identified Risk / Gap | Impact | Mitigation Strategy |
|---|---|:---:|---|
| **1** | `pgvector` not installed in PostgreSQL 18 | High | Propose and implement an isolated local vector store in `data/vector_store/` with zero database schema alterations. |
| **2** | Internet DNS / Network restrictions on Windows sandbox | Medium | Implemented a Mock Provider for automated tests; support Ollama local provider for offline execution. |
| **3** | Safety rule text chunking breaking critical instructions | High | Implement sentence-boundary-aware and section-aware chunking with metadata inheritance (rule ID, severity, factory ID). |
| **4** | Missing external safety manual PDFs in repo | Low | Created structured loaders that synthesize knowledge chunks directly from live database tables (`safety_rules`, `incidents`, `monitoring_zones`, `cameras`, `departments`). |
| **5** | Multi-tenant data leakage across factories | Critical | Mandate `factory_id` scoping inside `RetrievalFilter` so chunks from Factory A can never be retrieved in Factory B context. |

---

## 5. Module Roadmap (Prompts 1 through 5)

- **Phase 1 (Current):** Project Audit, Architecture Blueprint, Folder Setup, Configurations, Contracts & Sanity Tests.
- **Phase 2:** Knowledge Ingestion Pipeline (Database Loader, Document Loader, Sentence-Aware Chunker, Metadata Manager).
- **Phase 3:** Vector Store Engine (NumPy-accelerated Cosine Index, Batch Embeddings, OpenAI & Ollama Embedding Providers).
- **Phase 4:** Assistant Service & RAG Orchestrator (Prompt Engine, OpenAI/Ollama Chat Providers, Conversation Isolation, Grounding Guardrails).
- **Phase 5:** End-to-End Evaluation, Accuracy Benchmarks, FastAPI Integration Docs for Seif, and Final Verification.
