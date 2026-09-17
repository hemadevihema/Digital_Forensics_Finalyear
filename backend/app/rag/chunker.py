from typing import Any, Dict, List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings
from app.database.models import ChunkMetadata

class DocumentChunker:
    def __init__(self, chunk_size: Optional[int] = None, chunk_overlap: Optional[int] = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def chunk_document(
        self,
        document_id: str,
        filename: str,
        parsed_pages: List[Dict[str, Any]]
    ) -> List[ChunkMetadata]:
        chunks: List[ChunkMetadata] = []
        global_chunk_index = 0

        for page_data in parsed_pages:
            page_num = page_data.get("page", 1)
            text = page_data.get("text", "")
            if not text.strip():
                continue

            splits = self.splitter.split_text(text)
            for split_text in splits:
                if not split_text.strip():
                    continue

                chunk_id = f"{document_id}-CHUNK-{global_chunk_index:04d}"
                chunk_meta = ChunkMetadata(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    chunk_index=global_chunk_index,
                    page=page_num,
                    text=split_text,
                    metadata={
                        "document_id": document_id,
                        "chunk_id": chunk_id,
                        "chunk_index": global_chunk_index,
                        "page": page_num,
                        "source": filename,
                        "char_count": len(split_text)
                    }
                )
                chunks.append(chunk_meta)
                global_chunk_index += 1

        return chunks
