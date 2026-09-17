import os
import tempfile
from pathlib import Path
import pytest
from app.rag.parser import DocumentParser
from app.rag.chunker import DocumentChunker
from app.rag.prompt_builder import PromptBuilder, INSUFFICIENT_INFO_PHRASE
from app.services.document_service import document_service
from app.services.rag_service import rag_service
from app.database.mongodb import db_client
from app.rag.vector_store import faiss_manager

@pytest.fixture(scope="module", autouse=True)
def setup_test_environment():
    # Connect in-memory DB and init FAISS
    db_client.connect()
    faiss_manager.load_or_create()
    yield
    db_client.close()

# Test 7: Invalid file
def test_7_invalid_file_rejected():
    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
        f.write(b"BINARY_DATA")
        tmp_path = Path(f.name)

    try:
        assert not DocumentParser.is_supported(tmp_path.name)
        with pytest.raises(ValueError, match="Unsupported file format"):
            DocumentParser.parse_file(tmp_path, tmp_path.name)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

# Test 8: Large document chunking
def test_8_large_document_chunking():
    chunker = DocumentChunker(chunk_size=200, chunk_overlap=20)
    large_text = "The annual company policy provides extensive information. " * 50
    pages_data = [{"text": large_text, "page": 1, "source": "large_doc.txt"}]

    chunks = chunker.chunk_document("DOC-TEST-LG", "large_doc.txt", pages_data)
    assert len(chunks) > 10
    assert chunks[0].chunk_id.startswith("DOC-TEST-LG-CHUNK-")
    assert chunks[0].metadata["source"] == "large_doc.txt"

# Test 6: Duplicate document handling
def test_6_duplicate_document_handling():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Company Policy: Employees are entitled to 20 days of annual leave.")
        tmp_path = Path(f.name)

    try:
        doc1 = document_service.process_and_index_document(tmp_path, "dup_policy.txt", session_id="TEST-SES")
        assert doc1.status == "indexed"
        assert doc1.chunk_count > 0

        # Upload again with same filename
        doc2 = document_service.process_and_index_document(tmp_path, "dup_policy.txt", session_id="TEST-SES")
        assert doc2.status == "indexed"

        # Check only one document with this name exists in active listing
        docs = [d for d in document_service.list_documents() if d["filename"] == "dup_policy.txt"]
        assert len(docs) == 1
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

# Test 1: Direct factual question
def test_1_direct_factual_question():
    resp = rag_service.query("What is the annual leave allowance?", session_id="TEST-SES")
    assert resp.request_id.startswith("REQ-")
    assert resp.session_id == "TEST-SES"
    assert resp.answer != ""
    assert len(resp.retrieved_chunks) > 0
    # Check similarity score is preserved
    assert resp.retrieved_chunks[0].score > 0.0
    assert resp.retrieved_chunks[0].chunk_id != ""

# Test 2: Multi-document question
def test_2_multi_document_indexing_and_query():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("Benefits Guide: Acme Global matches 401(k) retirement contributions up to 4 percent.")
        f_path = Path(f.name)

    try:
        document_service.process_and_index_document(f_path, "benefits_test.txt", session_id="TEST-SES")
        resp = rag_service.query("Tell me about leave allowance and 401k benefits", session_id="TEST-SES", top_k=5)
        assert len(resp.retrieved_chunks) >= 2
    finally:
        if f_path.exists():
            f_path.unlink()

# Test 3: Irrelevant question
def test_3_irrelevant_question():
    resp = rag_service.query("What is the capital of France?", session_id="TEST-SES")
    # Grounded response behavior must indicate insufficient information
    assert INSUFFICIENT_INFO_PHRASE in resp.answer

# Test 4: No useful retrieval (empty context fallback)
def test_4_no_useful_retrieval():
    from app.rag.llm import gemini_llm
    sys_inst, ctx, prompt = PromptBuilder.build_prompt("Unknown concept", [])
    assert "[No relevant documents retrieved" in ctx
    answer, latency, status = gemini_llm.generate(sys_inst, ctx, "Unknown concept", "REQ-TEST")
    assert INSUFFICIENT_INFO_PHRASE in answer

# Test 5: Multiple relevant chunks
def test_5_multiple_relevant_chunks():
    resp = rag_service.query("leave and vacation policy details", session_id="TEST-SES", top_k=3)
    assert len(resp.retrieved_chunks) <= 3
    for i, c in enumerate(resp.retrieved_chunks):
        assert c.rank == i + 1
        assert 0.0 <= c.score <= 1.0
