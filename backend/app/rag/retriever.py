from typing import List, Optional
from app.config import settings
from app.database.models import RetrievalItem
from app.rag.vector_store import faiss_manager
from app.logger import logger

class StructuredRetriever:
    def __init__(self, top_k: Optional[int] = None):
        self.top_k = top_k or settings.top_k

    def retrieve(self, query: str, top_k: Optional[int] = None) -> List[RetrievalItem]:
        k = top_k or self.top_k
        results = faiss_manager.similarity_search_with_score(query, k=k)

        retrieval_items: List[RetrievalItem] = []
        for rank, (doc, raw_score) in enumerate(results, start=1):
            # FAISS L2 distance: lower is more similar.
            # Convert to a normalized 0-1 similarity score: 1 / (1 + distance)
            sim_score = round(1.0 / (1.0 + float(raw_score)), 4)

            item = RetrievalItem(
                document_id=doc.metadata.get("document_id", "UNKNOWN"),
                chunk_id=doc.metadata.get("chunk_id", f"CHUNK-{rank}"),
                source=doc.metadata.get("source", "Unknown Document"),
                page=int(doc.metadata.get("page", 1)),
                rank=rank,
                score=sim_score,
                text=doc.page_content
            )
            retrieval_items.append(item)

        logger.info(
            "Retrieved chunks from FAISS",
            query=query[:60],
            requested_k=k,
            returned_count=len(retrieval_items)
        )
        return retrieval_items

retriever = StructuredRetriever()
