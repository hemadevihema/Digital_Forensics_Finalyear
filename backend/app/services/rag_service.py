import time
import uuid
from typing import Any, Dict, List, Optional
from app.config import settings
from app.logger import EventType, logger
from app.database.mongodb import db_client
from app.database.models import ChatResponse, RequestRecord, RetrievalItem
from app.rag.retriever import retriever
from app.rag.prompt_builder import PromptBuilder, INSUFFICIENT_INFO_PHRASE
from app.rag.llm import gemini_llm
from app.services.event_service import event_service
from app.detector.source_attribution import source_attribution_engine
from app.detector.base import SourceOrigin, RiskLevel

class RAGService:
    def __init__(self):
        self._request_counter = 0

    def query(
        self,
        user_question: str,
        session_id: Optional[str] = None,
        top_k: Optional[int] = None
    ) -> ChatResponse:
        total_start = time.perf_counter()
        self._request_counter += 1

        # Session & Request Correlation IDs
        if not session_id or session_id == "null":
            session_id = f"SES-{uuid.uuid4().hex[:6].upper()}"
            db_client.create_session(session_id)
            event_service.record_event(
                event_type=EventType.SESSION_STARTED,
                component="session_manager",
                session_id=session_id,
                data={"session_id": session_id}
            )

        request_id = f"REQ-{self._request_counter:04d}-{uuid.uuid4().hex[:6].upper()}"

        # 1. USER_PROMPT_RECEIVED
        event_service.record_event(
            event_type=EventType.USER_PROMPT_RECEIVED,
            component="rag_service",
            session_id=session_id,
            request_id=request_id,
            data={"user_question": user_question, "char_count": len(user_question)}
        )

        # 2. QUERY_EMBEDDING_STARTED / QUERY_EMBEDDED
        embed_start = time.perf_counter()
        event_service.record_event(
            event_type=EventType.QUERY_EMBEDDING_STARTED,
            component="query_embedder",
            session_id=session_id,
            request_id=request_id,
            data={"query": user_question, "model": settings.embedding_model}
        )
        # embedding is performed inside FAISS search, but we log the step explicitly
        embedding_time_ms = (time.perf_counter() - embed_start) * 1000
        event_service.record_event(
            event_type=EventType.QUERY_EMBEDDED,
            component="query_embedder",
            session_id=session_id,
            request_id=request_id,
            data={"status": "completed"},
            duration_ms=embedding_time_ms
        )

        # 3. RETRIEVAL_STARTED
        retrieval_start = time.perf_counter()
        k_val = top_k or settings.top_k
        event_service.record_event(
            event_type=EventType.RETRIEVAL_STARTED,
            component="retriever",
            session_id=session_id,
            request_id=request_id,
            data={"requested_top_k": k_val}
        )

        # FAISS Top-K Retrieval
        retrieved_items: List[RetrievalItem] = retriever.retrieve(user_question, top_k=k_val)
        retrieval_time_ms = (time.perf_counter() - retrieval_start) * 1000

        # Emit DOCUMENT_RETRIEVED for each retrieved item
        for item in retrieved_items:
            event_service.record_event(
                event_type=EventType.DOCUMENT_RETRIEVED,
                component="faiss_retriever",
                session_id=session_id,
                request_id=request_id,
                data={
                    "document_id": item.document_id,
                    "chunk_id": item.chunk_id,
                    "source": item.source,
                    "page": item.page,
                    "rank": item.rank,
                    "score": item.score
                }
            )

        event_service.record_event(
            event_type=EventType.RETRIEVAL_COMPLETED,
            component="retriever",
            session_id=session_id,
            request_id=request_id,
            data={"chunks_retrieved": len(retrieved_items), "top_k": k_val},
            duration_ms=retrieval_time_ms
        )

        # 4. CONTEXT_BUILT
        prompt_start = time.perf_counter()
        system_instructions, formatted_context, full_prompt = PromptBuilder.build_prompt(
            user_question, retrieved_items
        )
        prompt_construction_ms = (time.perf_counter() - prompt_start) * 1000

        event_service.record_event(
            event_type=EventType.CONTEXT_BUILT,
            component="prompt_builder",
            session_id=session_id,
            request_id=request_id,
            data={
                "untrusted_blocks_count": len(retrieved_items),
                "total_prompt_chars": len(full_prompt)
            },
            duration_ms=prompt_construction_ms
        )

        # 5. INJECTION DETECTION & SOURCE ATTRIBUTION
        scan_start = time.perf_counter()
        event_service.record_event(
            event_type=EventType.INJECTION_SCAN_STARTED,
            component="source_attribution_engine",
            session_id=session_id,
            request_id=request_id,
            data={"layers": ["rule_regex", "tfidf", "semantic", "gemini_contextual"]}
        )

        attribution_res = source_attribution_engine.attribute(
            user_question=user_question,
            retrieved_items=retrieved_items,
            request_id=request_id
        )
        scan_duration_ms = (time.perf_counter() - scan_start) * 1000

        user_risk = attribution_res.user_scan.risk_score if attribution_res.user_scan else 0.0
        user_class = attribution_res.user_scan.classification.value if attribution_res.user_scan else "BENIGN"
        triggered_layers = attribution_res.user_scan.forensic_evidence.get("triggered_layers", []) if attribution_res.user_scan else []

        event_service.record_event(
            event_type=EventType.INJECTION_SCAN_COMPLETED,
            component="ensemble_detector",
            session_id=session_id,
            request_id=request_id,
            data={
                "user_risk_score": user_risk,
                "user_classification": user_class,
                "triggered_layers": triggered_layers
            },
            duration_ms=scan_duration_ms
        )

        event_service.record_event(
            event_type=EventType.INJECTION_ATTRIBUTED,
            component="source_attribution_engine",
            session_id=session_id,
            request_id=request_id,
            data={
                "attribution": attribution_res.attribution.value,
                "culprit_chunks": attribution_res.culprit_chunk_ids,
                "culprit_documents": attribution_res.culprit_document_ids,
                "summary": attribution_res.summary
            }
        )

        forensics_payload = {
            "attribution": attribution_res.attribution.value,
            "summary": attribution_res.summary,
            "culprit_chunk_ids": attribution_res.culprit_chunk_ids,
            "culprit_document_ids": attribution_res.culprit_document_ids,
            "user_scan": attribution_res.user_scan.model_dump() if attribution_res.user_scan else None,
            "document_scans": attribution_res.document_scans,
            "scan_latency_ms": round(scan_duration_ms, 2)
        }

        # 6. LLM GENERATION OR GUARDED BLOCK
        # If malicious injection originates directly from user, block generation to protect system integrity
        if attribution_res.attribution in {SourceOrigin.USER, SourceOrigin.BOTH} and attribution_res.user_scan and attribution_res.user_scan.classification == RiskLevel.MALICIOUS_INJECTION:
            answer_text = (
                f"🚨 Security Alert: Prompt Injection attack detected from USER input. "
                f"Attack Indicators: {', '.join(triggered_layers) or 'Rule Trigger'}. "
                f"The request has been quarantined by the forensic security engine."
            )
            llm_latency_ms = 0.0
            gen_status = "blocked_direct_injection"
        else:
            event_service.record_event(
                event_type=EventType.LLM_REQUEST_STARTED,
                component="gemini_llm",
                session_id=session_id,
                request_id=request_id,
                data={"model": gemini_llm.model_name}
            )

            answer_text, llm_latency_ms, gen_status = gemini_llm.generate(
                system_instructions=system_instructions,
                retrieved_context=formatted_context,
                user_question=user_question,
                request_id=request_id
            )

            # If indirect injection was retrieved from a document, append a forensic note
            if attribution_res.attribution == SourceOrigin.DOCUMENT:
                answer_text += (
                    f"\n\n🛡️ [Forensic Notice: Untrusted Data Quarantine neutralized an indirect prompt injection "
                    f"detected inside knowledge document chunk(s): {', '.join(attribution_res.culprit_chunk_ids)}]."
                )

            event_service.record_event(
                event_type=EventType.LLM_RESPONSE_RECEIVED,
                component="gemini_llm",
                session_id=session_id,
                request_id=request_id,
                data={"status": gen_status, "response_length": len(answer_text)},
                duration_ms=llm_latency_ms
            )

        # 7. Extract Grounded Citations
        citations = []
        seen_citations = set()
        is_greeting = user_question.lower().strip().rstrip("!?.").strip() in {
            "hi", "hello", "hey", "hi there", "hello there", "good morning", "good afternoon", "good evening", "greetings", "who are you"
        }
        if retrieved_items and INSUFFICIENT_INFO_PHRASE not in answer_text and not is_greeting and gen_status != "blocked_direct_injection":
            for item in retrieved_items:
                citation_key = f"{item.source}__p{item.page}"
                if citation_key not in seen_citations:
                    seen_citations.add(citation_key)
                    citations.append({
                        "document_id": item.document_id,
                        "source": item.source,
                        "page": item.page,
                        "chunk_id": item.chunk_id,
                        "score": item.score
                    })

        # 8. RESPONSE_VALIDATED
        event_service.record_event(
            event_type=EventType.RESPONSE_VALIDATED,
            component="grounding_validator",
            session_id=session_id,
            request_id=request_id,
            data={
                "grounded": len(citations) > 0 or INSUFFICIENT_INFO_PHRASE in answer_text or gen_status == "blocked_direct_injection",
                "citation_count": len(citations),
                "injection_status": attribution_res.attribution.value
            }
        )

        total_request_latency_ms = (time.perf_counter() - total_start) * 1000

        metrics = {
            "embedding_time_ms": round(embedding_time_ms, 2),
            "retrieval_time_ms": round(retrieval_time_ms, 2),
            "prompt_construction_time_ms": round(prompt_construction_ms, 2),
            "injection_scan_time_ms": round(scan_duration_ms, 2),
            "llm_latency_ms": round(llm_latency_ms, 2),
            "total_request_latency_ms": round(total_request_latency_ms, 2),
            "retrieved_chunk_count": len(retrieved_items),
            "citation_count": len(citations),
            "forensics": {
                "attribution": attribution_res.attribution.value,
                "risk_score": user_risk,
                "classification": user_class
            }
        }

        # 9. RESPONSE_SENT
        event_service.record_event(
            event_type=EventType.RESPONSE_SENT,
            component="rag_service",
            session_id=session_id,
            request_id=request_id,
            data={"total_latency_ms": round(total_request_latency_ms, 2)},
            duration_ms=total_request_latency_ms
        )

        # Persist Request Record
        req_record = RequestRecord(
            request_id=request_id,
            session_id=session_id,
            user_question=user_question,
            status="completed",
            metrics=metrics,
            retrieved_chunk_ids=[item.chunk_id for item in retrieved_items],
            answer=answer_text,
            citations=citations,
            forensics=forensics_payload
        )
        db_client.insert_request(req_record)

        return ChatResponse(
            request_id=request_id,
            session_id=session_id,
            user_question=user_question,
            answer=answer_text,
            citations=citations,
            retrieved_chunks=retrieved_items,
            metrics=metrics,
            forensics=forensics_payload
        )

rag_service = RAGService()
