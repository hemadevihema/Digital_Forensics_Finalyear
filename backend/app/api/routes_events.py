from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException
from app.services.event_service import event_service
from app.database.mongodb import db_client

router = APIRouter(prefix="/events", tags=["Events & Forensics"])

@router.get("/request/{request_id}")
def get_request_events(request_id: str):
    events = event_service.get_request_timeline(request_id)
    if not events:
        req = db_client.get_request(request_id)
        if not req:
            raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")
    return {
        "request_id": request_id,
        "event_count": len(events),
        "events": events
    }

@router.get("/session/{session_id}")
def get_session_events(session_id: str):
    events = event_service.get_session_timeline(session_id)
    return {
        "session_id": session_id,
        "event_count": len(events),
        "events": events
    }

@router.get("/requests")
def get_recent_requests(limit: int = 20):
    return db_client.get_requests(limit=limit)
