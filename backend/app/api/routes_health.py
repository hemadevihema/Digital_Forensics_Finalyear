# pyrefly: ignore [missing-import]
from fastapi import APIRouter
from app.config import settings
from app.database.mongodb import db_client
from app.rag.vector_store import faiss_manager
from app.rag.embeddings import EmbeddingFactory

router = APIRouter(tags=["Health"])

@router.get("/health")
def get_health():
    db_status = db_client.get_health_status()
    has_gemini_key = bool(settings.gemini_api_key.strip())

    return {
        "status": "healthy",
        "service": "Prompt Injection Forensics - RAG Foundation",
        "database": db_status,
        "vector_store": {
            "type": "FAISS",
            "directory": str(settings.faiss_dir),
            "initialized": faiss_manager.vector_store is not None,
            "embedding_model": settings.embedding_model,
            "embedding_provider": settings.embedding_provider,
            "dimension": EmbeddingFactory.get_dimension()
        },
        "llm": {
            "model": settings.gemini_model,
            "api_key_configured": has_gemini_key
        },
        "config": {
            "chunk_size": settings.chunk_size,
            "chunk_overlap": settings.chunk_overlap,
            "top_k": settings.top_k,
            "debug_mode": settings.debug_mode
        }
    }
