import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.logger import EventType, log_structured_event
from app.database.mongodb import db_client
from app.database.models import EventRecord

class EventService:
    def __init__(self):
        self._event_counter = 0

    def record_event(
        self,
        event_type: EventType,
        component: str,
        session_id: str,
        request_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
        level: str = "info"
    ) -> EventRecord:
        self._event_counter += 1
        event_id = f"EVT-{self._event_counter:04d}-{uuid.uuid4().hex[:6].upper()}"

        # Structured JSON log
        payload = log_structured_event(
            event_id=event_id,
            session_id=session_id,
            request_id=request_id,
            event_type=event_type,
            component=component,
            data=data or {},
            duration_ms=duration_ms,
            level=level
        )

        event_record = EventRecord(
            event_id=event_id,
            session_id=session_id,
            request_id=request_id,
            timestamp=payload["timestamp"],
            event_type=event_type.value,
            component=component,
            data=data or {},
            duration_ms=duration_ms
        )

        # Store in MongoDB Atlas
        try:
            db_client.insert_event(event_record)
        except Exception as e:
            # Event logging should never crash execution
            pass

        return event_record

    def get_request_timeline(self, request_id: str) -> List[Dict[str, Any]]:
        return db_client.get_events_by_request(request_id)

    def get_session_timeline(self, session_id: str) -> List[Dict[str, Any]]:
        return db_client.get_events_by_session(session_id)

event_service = EventService()
