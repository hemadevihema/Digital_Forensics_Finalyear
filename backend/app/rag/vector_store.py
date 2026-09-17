import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.config import settings
from app.logger import logger
from app.rag.embeddings import EmbeddingFactory
from app.database.models import ChunkMetadata

class FAISSVectorStore:
    def __init__(self):
        self.index_dir = settings.faiss_dir
        self.vector_store: Optional[FAISS] = None
        self.embeddings = EmbeddingFactory.get_embeddings()

    def load_or_create(self):
        index_file = self.index_dir / "index.faiss"
        pkl_file = self.index_dir / "index.pkl"

        if index_file.exists() and pkl_file.exists():
            try:
                self.vector_store = FAISS.load_local(
                    folder_path=str(self.index_dir),
                    embeddings=self.embeddings,
                    allow_dangerous_deserialization=True
                )
                logger.info("Loaded existing FAISS index from disk", path=str(self.index_dir))
                return
            except Exception as e:
                logger.warning("Failed to load FAISS index from disk. Creating fresh index.", error=str(e))

        # Create empty FAISS store
        logger.info("Initializing new FAISS vector store")
        dummy_doc = Document(
            page_content="__INIT_SENTINEL__",
            metadata={"document_id": "__INIT__", "chunk_id": "__INIT__"}
        )
        self.vector_store = FAISS.from_documents([dummy_doc], self.embeddings)
        self.save()

    def save(self):
        if self.vector_store:
            self.index_dir.mkdir(parents=True, exist_ok=True)
            self.vector_store.save_local(str(self.index_dir))
            logger.info("FAISS index saved to disk", path=str(self.index_dir))

    def add_chunks(self, chunks: List[ChunkMetadata]):
        if not chunks:
            return

        if self.vector_store is None:
            self.load_or_create()

        documents = [
            Document(
                page_content=c.text,
                metadata={
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "chunk_index": c.chunk_index,
                    "page": c.page,
                    **c.metadata
                }
            )
            for c in chunks
        ]

        self.vector_store.add_documents(documents)
        self.save()
        logger.info("Added chunks to FAISS index", count=len(chunks))

    def delete_document(self, document_id: str, remaining_chunks: List[ChunkMetadata]):
        """
        Reconstructs index from remaining chunks to cleanly remove a deleted document.
        """
        if self.index_dir.exists():
            for f in self.index_dir.iterdir():
                if f.is_file():
                    f.unlink()

        if not remaining_chunks:
            dummy_doc = Document(
                page_content="__INIT_SENTINEL__",
                metadata={"document_id": "__INIT__", "chunk_id": "__INIT__"}
            )
            self.vector_store = FAISS.from_documents([dummy_doc], self.embeddings)
        else:
            documents = [
                Document(
                    page_content=c.text,
                    metadata={
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "chunk_index": c.chunk_index,
                        "page": c.page,
                        **c.metadata
                    }
                )
                for c in remaining_chunks
            ]
            self.vector_store = FAISS.from_documents(documents, self.embeddings)

        self.save()
        logger.info("Rebuilt FAISS index after document deletion", deleted_doc=document_id, remaining_chunks=len(remaining_chunks))

    def similarity_search_with_score(
        self, query: str, k: int = 5
    ) -> List[Tuple[Document, float]]:
        if self.vector_store is None:
            self.load_or_create()

        results = self.vector_store.similarity_search_with_score(query, k=k)
        # Filter out the sentinel initialization document if present
        valid_results = [
            (doc, score) for doc, score in results
            if doc.metadata.get("document_id") != "__INIT__"
        ]
        return valid_results

faiss_manager = FAISSVectorStore()
