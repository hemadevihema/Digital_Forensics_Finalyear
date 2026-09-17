import logging
import sys
import structlog
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

class EventType(str, Enum):
    SESSION_STARTED = "SESSION_STARTED"
    DOCUMENT_UPLOAD_STARTED = "DOCUMENT_UPLOAD_STARTED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    DOCUMENT_PARSE_STARTED = "DOCUMENT_PARSE_STARTED"
    DOCUMENT_PARSED = "DOCUMENT_PARSED"
    DOCUMENT_CHUNKED = "DOCUMENT_CHUNKED"
    DOCUMENT_EMBEDDED = "DOCUMENT_EMBEDDED"
    DOCUMENT_INDEXED = "DOCUMENT_INDEXED"
    USER_PROMPT_RECEIVED = "USER_PROMPT_RECEIVED"
    QUERY_EMBEDDING_STARTED = "QUERY_EMBEDDING_STARTED"
    QUERY_EMBEDDED = "QUERY_EMBEDDED"
    RETRIEVAL_STARTED = "RETRIEVAL_STARTED"
    DOCUMENT_RETRIEVED = "DOCUMENT_RETRIEVED"
    RETRIEVAL_COMPLETED = "RETRIEVAL_COMPLETED"
    CONTEXT_BUILT = "CONTEXT_BUILT"
    INJECTION_SCAN_STARTED = "INJECTION_SCAN_STARTED"
    INJECTION_SCAN_COMPLETED = "INJECTION_SCAN_COMPLETED"
    INJECTION_ATTRIBUTED = "INJECTION_ATTRIBUTED"
    LLM_REQUEST_STARTED = "LLM_REQUEST_STARTED"
    LLM_RESPONSE_RECEIVED = "LLM_RESPONSE_RECEIVED"
    RESPONSE_VALIDATED = "RESPONSE_VALIDATED"
    RESPONSE_SENT = "RESPONSE_SENT"
    ERROR = "ERROR"

def configure_logger():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

configure_logger()
logger = structlog.get_logger("rag_forensics")

def log_structured_event(
    event_id: str,
    session_id: str,
    request_id: Optional[str],
    event_type: EventType,
    component: str,
    data: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
    level: str = "info"
):
    event_payload = {
        "event_id": event_id,
        "session_id": session_id,
        "request_id": request_id or "N/A",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type.value,
        "component": component,
        "data": data or {},
    }
    if duration_ms is not None:
        event_payload["duration_ms"] = round(duration_ms, 2)

    log_fn = getattr(logger, level, logger.info)
    log_fn(event_type.value, **event_payload)
    return event_payload
