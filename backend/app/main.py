from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.logger import logger
from app.database.mongodb import db_client
from app.rag.vector_store import faiss_manager
from app.api.routes_health import router as health_router
from app.api.routes_documents import router as documents_router
from app.api.routes_chat import router as chat_router
from app.api.routes_events import router as events_router
from app.api.routes_retrievals import router as retrievals_router
from app.api.routes_forensics import router as forensics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Prompt Injection Forensics - RAG Foundation API")
    db_client.connect()
    # Initialize / load persistent FAISS index
    faiss_manager.load_or_create()
    yield
    # Shutdown
    logger.info("Shutting down API server")
    db_client.close()

app = FastAPI(
    title="Prompt Injection Forensics - RAG Foundation API",
    description="Observable and traceable RAG backend providing document indexing, FAISS vector retrieval, Gemini generation, and structured forensic event logging.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(events_router)
app.include_router(retrievals_router)
app.include_router(forensics_router)

@app.get("/")
def root():
    return {
        "service": "Prompt Injection Forensics - RAG Foundation",
        "version": "1.0.0",
        "docs_url": "/docs",
        "health_url": "/health"
    }
