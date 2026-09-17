from fastapi import APIRouter, HTTPException
from app.database.models import ChatRequest, ChatResponse
from app.services.rag_service import rag_service

router = APIRouter(tags=["Chat"])

@router.post("/chat", response_model=ChatResponse)
def ask_question(request: ChatRequest):
    question = request.user_question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Please enter a question.")

    try:
        response = rag_service.query(
            user_question=question,
            session_id=request.session_id,
            top_k=request.top_k
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG query failed: {str(e)}")
