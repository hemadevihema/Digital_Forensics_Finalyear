from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    file_type: str
    file_size: int
    upload_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "indexed"  # uploading, parsing, chunking, embedding, indexing, indexed, failed
    page_count: int = 1
    chunk_count: int = 0
    error_message: Optional[str] = None

class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    chunk_index: int
    page: int = 1
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionRecord(BaseModel):
    session_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RequestRecord(BaseModel):
    request_id: str
    session_id: str
    user_question: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "completed"  # processing, completed, failed
    metrics: Dict[str, Any] = Field(default_factory=dict)
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    answer: Optional[str] = None
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    forensics: Optional[Dict[str, Any]] = None

class EventRecord(BaseModel):
    event_id: str
    session_id: str
    request_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str
    component: str
    data: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[float] = None

class RetrievalItem(BaseModel):
    document_id: str
    chunk_id: str
    source: str
    page: int
    rank: int
    score: float
    text: str

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    user_question: str
    top_k: Optional[int] = None
    history: Optional[List[Dict[str, str]]] = None

class ChatResponse(BaseModel):
    request_id: str
    session_id: str
    user_question: str
    answer: str
    citations: List[Dict[str, Any]]
    retrieved_chunks: List[RetrievalItem]
    metrics: Dict[str, Any]
    forensics: Optional[Dict[str, Any]] = None
