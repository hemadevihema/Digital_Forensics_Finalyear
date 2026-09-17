import shutil
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from app.config import settings
from app.logger import logger
from app.database.models import DocumentMetadata
from app.rag.parser import DocumentParser
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])

@router.post("/upload", response_model=DocumentMetadata)
async def upload_document(
    file: UploadFile = File(...),
    session_id: Optional[str] = Form("DEFAULT-SESSION")
):
    # 1. Validate extension
    filename = file.filename or "unnamed_file"
    if not DocumentParser.is_supported(filename):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported document format: '{filename}'. Supported formats: PDF, TXT, MD, DOCX"
        )

    # 2. Save uploaded file to uploads directory
    uploads_dir = settings.uploads_dir
    safe_path = uploads_dir / filename

    try:
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > settings.max_upload_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File size {file_size_mb:.1f}MB exceeds limit of {settings.max_upload_size_mb}MB"
            )

        with open(safe_path, "wb") as f:
            f.write(content)

        # 3. Process and index
        doc_meta = document_service.process_and_index_document(
            file_path=safe_path,
            original_filename=filename,
            session_id=session_id
        )
        return doc_meta

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process uploaded file", filename=filename, error=str(e))
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")

@router.get("", response_model=List[DocumentMetadata])
def list_documents():
    docs = document_service.list_documents()
    return [DocumentMetadata(**d) for d in docs]

@router.get("/{document_id}/chunks")
def get_document_chunks(document_id: str):
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    chunks = document_service.get_document_chunks(document_id)
    return {
        "document_id": document_id,
        "filename": doc.get("filename"),
        "chunk_count": len(chunks),
        "chunks": chunks
    }

@router.delete("/{document_id}")
def delete_document(document_id: str):
    doc = document_service.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    document_service.delete_document(document_id)
    return {"message": f"Document '{doc.get('filename')}' successfully removed from knowledge base and index"}
