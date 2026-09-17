import asyncio
from typing import Any, Dict, List, Optional
import pymongo
from pymongo import MongoClient
import mongomock
from app.config import settings
from app.logger import logger
from app.database.models import (
    DocumentMetadata, ChunkMetadata, SessionRecord, RequestRecord, EventRecord
)

class MongoDBClient:
    def __init__(self):
        self.client: Optional[Any] = None
        self.db: Optional[Any] = None
        self.is_atlas: bool = False
        self.connected: bool = False

    def connect(self):
        uri = settings.mongodb_uri.strip()
        # Clean any accidental <...> placeholder brackets around password
        import re
        uri = re.sub(r':<([^>]+)>@', r':\1@', uri)
        if uri and ("mongodb://" in uri or "mongodb+srv://" in uri):
            try:
                # 5 second timeout for Atlas connection check
                self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
                self.client.admin.command('ping')
                self.db = self.client[settings.mongodb_database]
                self.is_atlas = True
                self.connected = True
                logger.info("MongoDB Atlas connected successfully", database=settings.mongodb_database)
                self._create_indexes()
                return
            except Exception as e:
                logger.warning(
                    "Failed to connect to MongoDB Atlas URI. Falling back to local mock database.",
                    error=str(e)
                )

        # Fallback to in-memory mongomock
        logger.info("Using in-memory MongoDB mock storage")
        self.client = mongomock.MongoClient()
        self.db = self.client[settings.mongodb_database]
        self.is_atlas = False
        self.connected = True
        self._create_indexes()

    def _create_indexes(self):
        try:
            self.db.documents.create_index("document_id", unique=True)
            self.db.chunks.create_index("chunk_id", unique=True)
            self.db.chunks.create_index("document_id")
            self.db.sessions.create_index("session_id", unique=True)
            self.db.requests.create_index("request_id", unique=True)
            self.db.events.create_index("event_id", unique=True)
            self.db.events.create_index([("request_id", 1), ("timestamp", 1)])
        except Exception as e:
            logger.warning("Could not create database indexes", error=str(e))

    def close(self):
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.connected = False
            self.client = None
            self.db = None

    def _ensure_connected(self):
        if self.db is None or not self.connected:
            self.connect()

    # Documents
    def insert_document(self, doc: DocumentMetadata) -> bool:
        self._ensure_connected()
        doc_dict = doc.model_dump()
        self.db.documents.update_one(
            {"document_id": doc.document_id},
            {"$set": doc_dict},
            upsert=True
        )
        return True

    def get_documents(self) -> List[Dict[str, Any]]:
        self._ensure_connected()
        docs = list(self.db.documents.find({}, {"_id": 0}))
        return docs

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        doc = self.db.documents.find_one({"document_id": document_id}, {"_id": 0})
        return doc

    def delete_document(self, document_id: str) -> bool:
        self._ensure_connected()
        self.db.documents.delete_one({"document_id": document_id})
        self.db.chunks.delete_many({"document_id": document_id})
        return True

    # Chunks
    def insert_chunks(self, chunks: List[ChunkMetadata]) -> int:
        self._ensure_connected()
        if not chunks:
            return 0
        chunk_dicts = [c.model_dump() for c in chunks]
        for cd in chunk_dicts:
            self.db.chunks.update_one(
                {"chunk_id": cd["chunk_id"]},
                {"$set": cd},
                upsert=True
            )
        return len(chunks)

    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return list(self.db.chunks.find({"document_id": document_id}, {"_id": 0}).sort("chunk_index", 1))

    def get_chunk(self, chunk_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        return self.db.chunks.find_one({"chunk_id": chunk_id}, {"_id": 0})

    # Sessions
    def create_session(self, session_id: str) -> bool:
        self._ensure_connected()
        self.db.sessions.update_one(
            {"session_id": session_id},
            {"$setOnInsert": {"session_id": session_id, "created_at": SessionRecord(session_id=session_id).created_at}},
            upsert=True
        )
        return True

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        return self.db.sessions.find_one({"session_id": session_id}, {"_id": 0})

    # Requests
    def insert_request(self, req: RequestRecord) -> bool:
        self._ensure_connected()
        self.db.requests.update_one(
            {"request_id": req.request_id},
            {"$set": req.model_dump()},
            upsert=True
        )
        return True

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        self._ensure_connected()
        return self.db.requests.find_one({"request_id": request_id}, {"_id": 0})

    def get_requests(self, limit: int = 50) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return list(self.db.requests.find({}, {"_id": 0}).sort("timestamp", -1).limit(limit))

    def get_requests_by_session(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return list(self.db.requests.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1).limit(limit))

    # Events
    def insert_event(self, event: EventRecord) -> bool:
        self._ensure_connected()
        self.db.events.insert_one(event.model_dump())
        return True

    def get_events_by_request(self, request_id: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return list(self.db.events.find({"request_id": request_id}, {"_id": 0}).sort("timestamp", 1))

    def get_events_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        self._ensure_connected()
        return list(self.db.events.find({"session_id": session_id}, {"_id": 0}).sort("timestamp", 1))

    def get_health_status(self) -> Dict[str, Any]:
        self._ensure_connected()
        return {
            "connected": self.connected,
            "storage_type": "MongoDB Atlas" if self.is_atlas else "In-Memory Database",
            "database": settings.mongodb_database,
            "document_count": self.db.documents.count_documents({}),
            "chunk_count": self.db.chunks.count_documents({}),
            "request_count": self.db.requests.count_documents({}),
            "event_count": self.db.events.count_documents({}),
        }

db_client = MongoDBClient()
