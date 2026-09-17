# Prompt Injection Forensics: Observable RAG Foundation

An observable, traceable, and modular Retrieval-Augmented Generation (RAG) system built as the core foundational layer for the **Prompt Injection Forensics Framework**.

> **Design Principle**: Build an **observable and traceable RAG system** rather than a black-box RAG system. Every stage—document parsing, chunking, vector embedding, FAISS indexing, query embedding, Top-K retrieval, prompt quarantine, Gemini generation, and source citation—is correlated with unique session, request, and event identifiers, measured in milliseconds, and persisted in MongoDB Atlas.

---

## 1. Architecture & Pipeline

```text
                           REACT FRONTEND (Vite + React)
        [ Chat & Citations ]   [ Document Manager ]   [ Forensic Timeline Inspector ]
                                       │
                                 REST API (HTTP)
                                       ▼
                             FASTAPI BACKEND
     ┌─────────────────────────────────┼─────────────────────────────────┐
     ▼                                 ▼                                 ▼
[ Document Service ]          [ RAG Orchestrator ]              [ Event Service ]
  • File Validator              • Query Embedder                  • Structured Logger (structlog)
  • Parsers (PDF, TXT, MD, DOCX)• FAISS Top-K Retriever           • MongoDB Atlas Persister
  • LangChain Text Splitter     • Grounded Prompt Builder         • Correlation Engine
  • Embeddings Factory          • Gemini LLM Client               • Latency Tracker (ms)
     │                                 │                                 │
     ▼                                 ▼                                 ▼
[ FAISS Vector Store ]         [ Google Gemini ]                [ MongoDB Atlas ]
  • Disk Persistence             • Untrusted Data Boundary        • Collections:
  • Similarity Scores & Ranks    • Grounded Answers                 documents, chunks,
  • Metadata Preservation        • Insufficient-Info Fallback       sessions, requests, events
```

---

## 2. Technology Stack

* **Frontend**: React (Vite, vanilla CSS design system with modern dark/glassmorphic styling)
* **Backend**: Python 3.12 + FastAPI with Pydantic v2 schemas
* **LLM**: Google Gemini (`gemini-1.5-flash` or configurable)
* **RAG & Vector Store**: LangChain, FAISS (`faiss-cpu`) with disk persistence
* **Embeddings**: `sentence-transformers` (`all-MiniLM-L6-v2` for fast, free, local CPU embeddings; optional Gemini embeddings configurable)
* **Document Parsers**: `pypdf`, `python-docx`, `markdown`
* **Database**: MongoDB Atlas (`pymongo`/`motor` with automatic fallback for standalone mock operation)
* **Logging & Tracing**: Python Structured Logging (`structlog`) emitting standardized JSON logs

---

## 3. Key Features & Forensic Traceability

### 3.1 Untrusted Data Boundary
Retrieved documents are treated strictly as **untrusted external DATA, not instructions**. The prompt builder enforces quarantine:
$$\text{Trusted System Instructions} \quad\Vert\quad \text{Retrieved Untrusted Data} \quad\Vert\quad \text{User Question}$$

### 3.2 Correlated Structured Event Logging
Every request generates a sequence of correlated events linked by `session_id`, `request_id`, `event_id`, and timestamps:
1. `USER_PROMPT_RECEIVED`
2. `QUERY_EMBEDDING_STARTED`
3. `QUERY_EMBEDDED`
4. `RETRIEVAL_STARTED`
5. `DOCUMENT_RETRIEVED` (for each chunk with rank and similarity score)
6. `RETRIEVAL_COMPLETED`
7. `CONTEXT_BUILT`
8. `LLM_REQUEST_STARTED`
9. `LLM_RESPONSE_RECEIVED`
10. `RESPONSE_VALIDATED`
11. `RESPONSE_SENT`

### 3.3 Millisecond Latency Tracking
Calculates:
* `embedding_time_ms`
* `retrieval_time_ms`
* `prompt_construction_time_ms`
* `llm_latency_ms`
* `total_request_latency_ms`

---

## 4. Getting Started

### Prerequisites
* Python 3.12+
* Node.js 18+ and npm

### 4.1 Backend Setup

1. Open a terminal in the project directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # On Windows:
   py -3.12 -m venv venv
   .\venv\Scripts\activate

   # On Linux/macOS:
   python3.12 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables in `backend/.env`:
   ```env
   # Gemini API Key (Optional for simulated offline testing, required for live Gemini)
   GEMINI_API_KEY=your_gemini_api_key_here
   GEMINI_MODEL=gemini-1.5-flash

   # MongoDB Atlas URI (Optional; falls back to in-memory mock if blank)
   MONGODB_URI=
   MONGODB_DATABASE=rag_forensics

   # Embeddings
   EMBEDDING_PROVIDER=local
   EMBEDDING_MODEL=all-MiniLM-L6-v2

   # RAG Settings
   CHUNK_SIZE=800
   CHUNK_OVERLAP=100
   TOP_K=5
   ```

5. Generate synthetic sample documents:
   ```bash
   python scripts/generate_sample_docs.py
   ```

6. Start the FastAPI backend server:
   ```bash
   python run.py
   # Or: uvicorn app.main:app --reload --port 8000
   ```
   The backend will be live at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

---

### 4.2 Frontend Setup

1. In a separate terminal, navigate to the `frontend` folder:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173` in your browser.

---

## 5. API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health status of MongoDB Atlas, FAISS, embeddings, and LLM |
| `POST` | `/documents/upload` | Upload and process PDF, TXT, MD, or DOCX document |
| `GET` | `/documents` | List all indexed documents with page and chunk counts |
| `GET` | `/documents/{document_id}/chunks` | Inspect all chunks belonging to a document |
| `DELETE` | `/documents/{document_id}` | Remove document, chunks, and update FAISS index |
| `POST` | `/chat` | Submit question, retrieve chunks, and generate grounded answer |
| `GET` | `/events/request/{request_id}` | Retrieve chronological correlated event trail for a request |
| `GET` | `/requests/{request_id}/retrievals` | Detailed retrieval scores, ranks, chunks, and prompt boundary |

---

## 6. Running Automated Tests

Run the full automated test suite covering all 8 verification scenarios:
```bash
cd backend
pytest -v
```

### Verified Test Cases
1. **Direct Factual Question**: Verifies grounded answers and citations for known facts (e.g. annual leave policy).
2. **Multi-Document Question**: Verifies cross-document chunk retrieval and multi-source citations.
3. **Irrelevant Question**: Tests unanswerable questions (e.g. "What is the capital of France?"), asserting strict fallback behavior.
4. **No Useful Retrieval**: Confirms fallback when context is absent.
5. **Multiple Relevant Chunks**: Validates Top-K ranking, similarity score calculations, and chunk metadata.
6. **Duplicate Document**: Ensures re-uploading an existing file replaces older entries without corruption.
7. **Invalid File Rejection**: Asserts graceful rejection of unsupported file types (e.g. `.exe`).
8. **Large Document Processing**: Validates chunking across large multi-page texts.

---

## 7. Future Forensic Layer Roadmap

The data structures and events implemented in this RAG foundation are designed to integrate directly with:
* **Attack Graph Construction**: Generating NetworkX DAGs from event correlations (`session_id`, `request_id`, `event_id`).
* **Source Attribution**: Tracing whether malicious directives originated from `USER`, `DOCUMENT`, `RAG_RESULT`, or `EXTERNAL`.
* **Impact Analysis**: Quantifying prompt injection impact (`BLOCKED`, `MODEL_MANIPULATION`, `UNAUTHORIZED_DATA_ACCESS`).
* **React Flow Visualization**: Interactive visual attack graph rendering in the forensic dashboard.
