from fastapi import APIRouter, HTTPException
from app.database.mongodb import db_client
from app.rag.prompt_builder import PromptBuilder
from app.database.models import RetrievalItem

router = APIRouter(prefix="/requests", tags=["Retrieval Inspection"])

@router.get("/{request_id}/retrievals")
def get_request_retrievals(request_id: str):
    req = db_client.get_request(request_id)
    if not req:
        raise HTTPException(status_code=404, detail=f"Request '{request_id}' not found")

    chunk_ids = req.get("retrieved_chunk_ids", [])
    chunks_details = []
    retrieval_items = []

    for rank, cid in enumerate(chunk_ids, start=1):
        chunk_data = db_client.get_chunk(cid)
        if chunk_data:
            meta = chunk_data.get("metadata", {})
            # Match score from events if available
            score = meta.get("score", 0.90)
            item = RetrievalItem(
                document_id=chunk_data.get("document_id", "UNKNOWN"),
                chunk_id=cid,
                source=meta.get("source", "Unknown"),
                page=chunk_data.get("page", 1),
                rank=rank,
                score=score,
                text=chunk_data.get("text", "")
            )
            retrieval_items.append(item)
            chunks_details.append({
                "rank": rank,
                "chunk_id": cid,
                "document_id": chunk_data.get("document_id"),
                "source": meta.get("source", "Unknown"),
                "page": chunk_data.get("page", 1),
                "text": chunk_data.get("text", ""),
                "score": score
            })

    # Reconstruct prompt for inspection
    user_q = req.get("user_question", "")
    sys_inst, formatted_ctx, full_prompt = PromptBuilder.build_prompt(user_q, retrieval_items)

    return {
        "request_id": request_id,
        "session_id": req.get("session_id"),
        "user_question": user_q,
        "answer": req.get("answer"),
        "citations": req.get("citations", []),
        "metrics": req.get("metrics", {}),
        "retrieved_count": len(chunks_details),
        "retrieved_chunks": chunks_details,
        "prompt_inspection": {
            "system_instructions": sys_inst,
            "retrieved_untrusted_context": formatted_ctx,
            "full_constructed_prompt": full_prompt
        },
        "forensics": req.get("forensics")
    }
