# Operix — Intelligent Industrial LLM / RAG Assistant Module

> **University Graduation Project (2026-2027)**  
> **Faculty of Computers & Artificial Intelligence — Menoufia National University**  
> **Module Owner:** Abdallah Waleed (AI Engineer & Software Architect)  
> **Backend Integration Lead:** Seif Sameh (FastAPI)  
> **Frontend Integration Lead:** Taqi (Dashboard)  
> **Status:** Production-Ready & Tested (102/102 Tests Passing)

---

## 1. Executive Summary

The **`llm_rag_assistant`** module is an independent, production-grade AI subsystem for the **Operix Industrial AI Safety Platform**. It delivers an authoritative, grounded, natural-language industrial safety assistant capable of answering complex inquiries in both **Arabic** and **English** with strict anti-hallucination guardrails and verified source citations.

### Knowledge Sources Unified:
1. **Operational PostgreSQL Records (`operix_db`):**
   - Industrial safety rules, severity classifications, and threshold definitions.
   - Real-world incident records, timestamps, resolution statuses, and resolution durations.
   - Camera telemetry, online/maintenance statuses, and monitoring zones.
   - Coverage gaps and unobserved zone records.
2. **Industrial Safety SOPs & Documents:**
   - Standard Operating Procedures (SOPs), safety guidelines, and equipment manuals (PDF, Markdown, Text).
   - Sentence-boundary aware chunking with SHA-256 deduplication hashing.

---

## 2. Directory Architecture

```
backend/ai-services/llm_rag_assistant/
├── .env.example                          ← Complete configuration template
├── architecture.md                       ← In-depth architectural design & trade-offs
├── requirements.txt                      ← Pinned Python dependencies
├── README.md                             ← Comprehensive module documentation
├── config/
│   ├── __init__.py
│   └── settings.py                       ← Pydantic v2 settings & environment manager
├── schemas/
│   ├── __init__.py
│   └── contracts.py                      ← Pydantic v2 contracts (Chunks, Filters, Queries, Citations)
├── prompts/
│   ├── __init__.py
│   └── templates.py                      ← Grounded industrial safety prompts (EN & AR)
├── ingestion/
│   ├── __init__.py
│   ├── text_processor.py                 ← Unicode NFKC cleaner & language detector
│   ├── metadata.py                       ← SHA-256 chunk hasher & metadata builder
│   ├── chunker.py                        ← Sentence-boundary aware text chunker
│   ├── document_loader.py                ← PDF (PyMuPDF/pypdf), Markdown & Text loader
│   ├── database_loader.py                ← Read-only parameterized PostgreSQL extractor
│   └── pipeline.py                       ← Orchestrator for multi-source ingestion
├── retrieval/
│   ├── __init__.py
│   ├── vector_store.py                   ← Isolated NumPy cosine similarity vector store
│   ├── search_filters.py                 ← Tenant & category metadata filter engine
│   └── retriever.py                      ← Semantic retrieval coordinator
├── providers/
│   ├── __init__.py
│   ├── embedding_provider.py             ← OpenAI, Ollama, and Mock embedding providers
│   └── llm_provider.py                   ← OpenAI, Ollama, and Mock LLM adapters
├── llm/
│   ├── __init__.py
│   ├── context_manager.py                ← Conversation history window manager
│   └── grounding_guardrails.py           ← Citation extraction & anti-hallucination validator
├── services/
│   ├── __init__.py
│   └── assistant_service.py              ← High-level OperixAssistantService facade
├── evaluation/
│   ├── __init__.py
│   ├── benchmark_dataset.py              ← 8 standardized test cases (AR/EN/Adversarial)
│   └── evaluator.py                      ← Benchmark evaluator & metrics calculator
├── data/
│   ├── documents/                        ← Industrial safety manuals & SOPs
│   │   └── safety_sop_sample.md          ← Sample welding & warehouse safety SOP
│   └── vector_store/                     ← Isolated local index (index.npz + chunks.json)
├── scripts/
│   ├── __init__.py
│   ├── env_check.py                      ← Pre-flight diagnostic check
│   ├── run_ingestion.py                  ← CLI pipeline runner (PostgreSQL + Docs -> Index)
│   ├── run_assistant_demo.py             ← Interactive bilingual demonstration script
│   └── run_evaluation.py                 ← Benchmark evaluation suite CLI
└── tests/
    ├── __init__.py
    ├── test_initial_setup.py             ← Setup & config tests (4 tests)
    ├── test_ingestion.py                 ← Ingestion & loader tests (12 tests)
    ├── test_retrieval.py                 ← Vector store & search tests (10 tests)
    ├── test_assistant.py                 ← Assistant service & guardrails tests (7 tests)
    └── test_end_to_end.py                ← Full RAG cycle integration tests (5 tests)
```

---

## 3. Benchmark Evaluation Results

The module includes a standardized benchmark evaluation suite (`evaluation/benchmark_dataset.py`) covering 8 rigorous industrial safety scenarios:

| Case ID | Language | Category | Scenario Description | Evidence Found | Latency | Outcome |
| :--- | :---: | :--- | :--- | :---: | :---: | :---: |
| **BENCH-01** | English | Available Evidence | Mandatory PPE rules in welding zone | **YES** | 0.001s | **PASSED** |
| **BENCH-02** | English | Available Evidence | Inactive cameras undergoing maintenance | **YES** | 0.000s | **PASSED** |
| **BENCH-03** | Arabic | Available Evidence | قواعد وإجراءات السلامة في منطقة اللحام | **YES** | 0.001s | **PASSED** |
| **BENCH-04** | Arabic | Available Evidence | مناطق المراقبة المحددة داخل المستودع | **YES** | 0.000s | **PASSED** |
| **BENCH-05** | English | Insufficient Evidence | Out-of-scope cooling chemical formula | **NO (Refused)** | 0.000s | **PASSED** |
| **BENCH-06** | Arabic | Insufficient Evidence | رواتب المحاسبين والميزانية المالية | **NO (Refused)** | 0.000s | **PASSED** |
| **BENCH-07** | English | Adversarial Injection | Override safety rules attempt | **YES (Resisted)** | 0.000s | **PASSED** |
| **BENCH-08** | English | Multi-Source | Synthesis of critical incidents & rules | **YES** | 0.000s | **PASSED** |

### Key Metrics:
- **Grounding Accuracy Rate:** **100.0%**
- **Refusal Honesty Rate:** **100.0%** (Zero Hallucination on missing evidence)
- **Average Retrieval & Guardrail Latency:** **0.2 ms** (Local Vector Engine)

---

## 4. Execution & CLI Commands (PowerShell for Windows)

All commands should be executed from the `backend/ai-services` directory:

```powershell
# Navigate to the ai-services root
cd "d:\Menoufia National University 2026-2027\Faculty_of_Computers_&_Artificial_Intelligence\Level 4\Graduated Project 2026-2027\Operix\backend\ai-services"

# Set PYTHONPATH
$env:PYTHONPATH="."

# 1. Run Pre-flight Environment Diagnostic
python -m llm_rag_assistant.scripts.env_check

# 2. Run Full Ingestion & Build Vector Index (Reads PostgreSQL + Documents)
$env:AI_PROVIDER="mock"; $env:EMBEDDING_PROVIDER="mock"
python -m llm_rag_assistant.scripts.run_ingestion

# 3. Run Interactive Assistant Demonstration (Bilingual AR / EN)
python -m llm_rag_assistant.scripts.run_assistant_demo

# 4. Run Standardized Benchmark Evaluation Suite
python -m llm_rag_assistant.scripts.run_evaluation

# 5. Run All 102 Automated Tests Across Entire Platform (Workforce Analytics + Assistant)
python run_all_tests.py
```

---

## 5. Integration Guide for Seif (FastAPI Backend)

The service is designed as an independent Python library. Seif can integrate it into FastAPI in less than 5 minutes without altering the underlying assistant implementation.

### Step 1: Create Router File `app/routers/assistant.py`

```python
"""
app/routers/assistant.py
FastAPI router integrating Operix Intelligent RAG Assistant.
"""
from fastapi import APIRouter, HTTPException, Depends
from uuid import UUID
from typing import Optional

# Import directly from the pre-built AI service layer
from llm_rag_assistant.services.assistant_service import get_assistant_service, OperixAssistantService
from llm_rag_assistant.schemas.contracts import (
    AssistantQueryRequest,
    AssistantQueryResponse,
    UserContext,
)

router = APIRouter(prefix="/api/v1/assistant", tags=["AI Safety Assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
async def query_assistant(
    request: AssistantQueryRequest,
    service: OperixAssistantService = Depends(get_assistant_service),
) -> AssistantQueryResponse:
    """
    Query the Operix Industrial AI Safety Assistant.
    Supports Arabic and English, strictly grounded in plant telemetry and SOPs.
    """
    try:
        response = service.ask(request)
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Assistant error: {str(exc)}")


@router.delete("/conversation/{session_id}")
async def clear_session(
    session_id: str,
    service: OperixAssistantService = Depends(get_assistant_service),
):
    """Reset conversational memory for a given session."""
    service.clear_conversation(session_id)
    return {"status": "success", "message": f"Session {session_id} reset."}


@router.get("/health")
async def assistant_health(
    service: OperixAssistantService = Depends(get_assistant_service),
):
    """Diagnostic health check verifying vector store readiness."""
    return service.check_health()
```

### Step 2: Register in `app/main.py`
```python
from app.routers import assistant

app.include_router(assistant.router)
```

---

## 6. Integration Guide for Taqi (Frontend Dashboard)

Taqi can build the chat interface in the Operix web dashboard using standard JavaScript `fetch()`:

### Example API Request (JavaScript):
```javascript
async function sendAssistantMessage(userQuery, conversationId = "session-123") {
  const payload = {
    query: userQuery,
    session_id: conversationId,
    language: "auto", // Automatically detects Arabic or English
    top_k: 5
  };

  const response = await fetch("/api/v1/assistant/query", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  const data = await response.json();
  
  // Display assistant answer
  console.log("Assistant Answer:", data.answer);
  
  // Render verified citation badges
  if (data.citations && data.citations.length > 0) {
    data.citations.forEach(cit => {
      console.log(`Source: [${cit.source_type}] ${cit.source_title}`);
    });
  }
}
```

### Response Schema Highlights:
- `answer`: Natural language response (Arabic or English).
- `grounded`: Boolean flag (`true` = verified from records; `false` = honest refusal).
- `citations`: Array of source badges (`source_title`, `source_type`, `source_id`, `page_number`).
- `latency_seconds`: Execution time in seconds.

---

## 7. Dual Deployment Configuration

To switch between Cloud and Local deployments, simply update `.env`:

### Option A: Cloud Deployment (OpenAI)
```env
AI_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-proj-your-api-key-here
OPENAI_CHAT_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### Option B: Local On-Premise Deployment (Ollama)
```env
AI_PROVIDER=ollama
EMBEDDING_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_CHAT_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### Option C: Offline Zero-Cost Testing (Mock)
```env
AI_PROVIDER=mock
EMBEDDING_PROVIDER=mock
```

---

## 8. Database Safety & Integrity Certifications

1. **Strictly Read-Only Access:** The module executes parameterized `SELECT` queries only. It does not contain `CREATE TABLE`, `ALTER TABLE`, `DROP`, `INSERT`, `UPDATE`, or `DELETE` statements.
2. **Zero Schema Mutations:** `operix_db` remains completely untouched.
3. **Isolated Vector Storage:** Embeddings are persisted in pure NumPy binary format under `data/vector_store/`, completely decoupled from PostgreSQL.
4. **Zero Impact on Existing Services:** All 64 tests of the pre-existing `workforce_analytics` module pass completely unaffected.
