import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings
from app.logger import EventType, logger
from app.database.mongodb import db_client
from app.database.models import DocumentMetadata, ChunkMetadata
from app.rag.parser import DocumentParser
from app.rag.chunker import DocumentChunker
from app.rag.vector_store import faiss_manager
from app.services.event_service import event_service

class DocumentService:
    def __init__(self):
        self.chunker = DocumentChunker()

    def process_and_index_document(
        self,
        file_path: Path,
        original_filename: str,
        session_id: str
    ) -> DocumentMetadata:
        total_start_time = time.perf_counter()
        doc_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"
        file_size = file_path.stat().st_size
        file_type = file_path.suffix.lower().replace(".", "")

        # Check for duplicate filename
        existing_docs = db_client.get_documents()
        for doc in existing_docs:
            if doc["filename"] == original_filename:
                logger.info("Re-indexing existing document name", filename=original_filename, old_id=doc["document_id"])
                # Remove prior version to keep index clean
                self.delete_document(doc["document_id"], session_id=session_id)

        # 1. DOCUMENT_UPLOAD_STARTED / DOCUMENT_UPLOADED
        event_service.record_event(
            event_type=EventType.DOCUMENT_UPLOAD_STARTED,
            component="document_service",
            session_id=session_id,
            data={"document_id": doc_id, "filename": original_filename, "size_bytes": file_size}
        )

        doc_meta = DocumentMetadata(
            document_id=doc_id,
            filename=original_filename,
            file_type=file_type,
            file_size=file_size,
            status="parsing",
            page_count=1,
            chunk_count=0
        )
        db_client.insert_document(doc_meta)

        event_service.record_event(
            event_type=EventType.DOCUMENT_UPLOADED,
            component="document_service",
            session_id=session_id,
            data={"document_id": doc_id, "filename": original_filename, "size_bytes": file_size}
        )

        try:
            # 2. DOCUMENT_PARSE_STARTED / DOCUMENT_PARSED
            parse_start = time.perf_counter()
            event_service.record_event(
                event_type=EventType.DOCUMENT_PARSE_STARTED,
                component="parser",
                session_id=session_id,
                data={"document_id": doc_id, "file_path": str(file_path)}
            )

            parsed_pages, page_count = DocumentParser.parse_file(file_path, original_filename)
            parse_duration_ms = (time.perf_counter() - parse_start) * 1000

            doc_meta.page_count = page_count
            doc_meta.status = "chunking"
            db_client.insert_document(doc_meta)

            event_service.record_event(
                event_type=EventType.DOCUMENT_PARSED,
                component="parser",
                session_id=session_id,
                data={"document_id": doc_id, "page_count": page_count, "sections": len(parsed_pages)},
                duration_ms=parse_duration_ms
            )

            # 3. DOCUMENT_CHUNKED
            chunk_start = time.perf_counter()
            chunks = self.chunker.chunk_document(doc_id, original_filename, parsed_pages)
            chunk_duration_ms = (time.perf_counter() - chunk_start) * 1000

            doc_meta.chunk_count = len(chunks)
            doc_meta.status = "embedding"
            db_client.insert_document(doc_meta)

            event_service.record_event(
                event_type=EventType.DOCUMENT_CHUNKED,
                component="chunker",
                session_id=session_id,
                data={"document_id": doc_id, "chunk_count": len(chunks), "chunk_size": settings.chunk_size, "chunk_overlap": settings.chunk_overlap},
                duration_ms=chunk_duration_ms
            )

            # 4. DOCUMENT_EMBEDDED
            embed_start = time.perf_counter()
            db_client.insert_chunks(chunks)

            # 5. DOCUMENT_INDEXED
            doc_meta.status = "indexing"
            db_client.insert_document(doc_meta)

            faiss_manager.add_chunks(chunks)
            embed_index_duration_ms = (time.perf_counter() - embed_start) * 1000

            event_service.record_event(
                event_type=EventType.DOCUMENT_EMBEDDED,
                component="embedding_engine",
                session_id=session_id,
                data={"document_id": doc_id, "model": settings.embedding_model, "chunk_count": len(chunks)},
                duration_ms=embed_index_duration_ms
            )

            total_duration_ms = (time.perf_counter() - total_start_time) * 1000
            doc_meta.status = "indexed"
            db_client.insert_document(doc_meta)

            event_service.record_event(
                event_type=EventType.DOCUMENT_INDEXED,
                component="faiss_vector_store",
                session_id=session_id,
                data={
                    "document_id": doc_id,
                    "total_chunks": len(chunks),
                    "total_pages": page_count,
                    "total_processing_time_ms": round(total_duration_ms, 2)
                },
                duration_ms=total_duration_ms
            )

            return doc_meta

        except Exception as e:
            doc_meta.status = "failed"
            doc_meta.error_message = str(e)
            db_client.insert_document(doc_meta)

            event_service.record_event(
                event_type=EventType.ERROR,
                component="document_service",
                session_id=session_id,
                data={"document_id": doc_id, "error": str(e)},
                level="error"
            )
            raise

    def list_documents(self) -> List[Dict[str, Any]]:
        return db_client.get_documents()

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        return db_client.get_document(document_id)

    def get_document_chunks(self, document_id: str) -> List[Dict[str, Any]]:
        return db_client.get_chunks_by_document(document_id)

    def delete_document(self, document_id: str, session_id: str = "SYSTEM") -> bool:
        # Delete from MongoDB
        db_client.delete_document(document_id)

        # Collect all remaining chunks from other documents to rebuild FAISS index
        all_docs = db_client.get_documents()
        remaining_chunks: List[ChunkMetadata] = []
        for doc in all_docs:
            if doc["document_id"] != document_id:
                raw_chunks = db_client.get_chunks_by_document(doc["document_id"])
                for rc in raw_chunks:
                    remaining_chunks.append(ChunkMetadata(**rc))

        faiss_manager.delete_document(document_id, remaining_chunks)

        logger.info("Document deleted successfully", document_id=document_id)
        return True

document_service = DocumentService()
