from typing import Any, Dict, List, Optional
from app.database.models import RetrievalItem
from app.detector.base import (
    EnsembleResult, RiskLevel, SourceAttributionResult, SourceOrigin
)
from app.detector.ensemble import ensemble_detector

class SourceAttributionEngine:
    """
    Source Attribution Engine.
    Correlates detected prompt injection indicators with pipeline provenance metadata
    to trace the origin of an attack back to USER, DOCUMENT, or BOTH.
    """
    def attribute(
        self,
        user_question: str,
        retrieved_items: List[RetrievalItem],
        request_id: Optional[str] = None,
        include_llm: Optional[bool] = None
    ) -> SourceAttributionResult:
        # 1. Scan User Query (include_llm configurable, defaults to ensemble setting)
        user_scan: EnsembleResult = ensemble_detector.scan(user_question, include_llm=include_llm)
        user_has_injection = user_scan.classification in {
            RiskLevel.SUSPICIOUS,
            RiskLevel.MALICIOUS_INJECTION
        }

        # 2. Scan Each Retrieved Document Chunk (fast layers 1-3 to avoid latency blowup)
        document_scans: List[Dict[str, Any]] = []
        culprit_chunks: List[str] = []
        culprit_docs: List[str] = []

        for item in retrieved_items:
            chunk_scan: EnsembleResult = ensemble_detector.scan(item.text, include_llm=False)
            is_malicious = chunk_scan.classification in {
                RiskLevel.SUSPICIOUS,
                RiskLevel.MALICIOUS_INJECTION
            }

            if is_malicious:
                culprit_chunks.append(item.chunk_id)
                if item.document_id not in culprit_docs:
                    culprit_docs.append(item.document_id)

            document_scans.append({
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "source": item.source,
                "page": item.page,
                "rank": item.rank,
                "score": item.score,
                "risk_score": chunk_scan.risk_score,
                "classification": chunk_scan.classification.value,
                "triggered_layers": chunk_scan.forensic_evidence.get("triggered_layers", []),
                "matched_patterns": chunk_scan.detector_results.get("rule_regex_detector", {}).details.get("matched_patterns", [])
            })

        doc_has_injection = len(culprit_chunks) > 0

        # 3. Determine Provenance Attribution
        if user_has_injection and doc_has_injection:
            attribution = SourceOrigin.BOTH
            summary = (
                f"Multi-vector injection detected: Direct USER injection coordinating with "
                f"poisoned content in {len(culprit_chunks)} retrieved DOCUMENT chunk(s)."
            )
        elif user_has_injection:
            attribution = SourceOrigin.USER
            summary = (
                f"Direct Prompt Injection detected originating from USER query "
                f"(Risk: {user_scan.risk_score}, Class: {user_scan.classification.value})."
            )
        elif doc_has_injection:
            attribution = SourceOrigin.DOCUMENT
            summary = (
                f"Indirect Prompt Injection detected originating from {len(culprit_chunks)} "
                f"retrieved DOCUMENT chunk(s) across document(s): {', '.join(culprit_docs)}."
            )
        else:
            attribution = SourceOrigin.NONE
            summary = "No prompt injection detected in user query or retrieved documents."

        return SourceAttributionResult(
            attribution=attribution,
            user_scan=user_scan,
            document_scans=document_scans,
            culprit_chunk_ids=culprit_chunks,
            culprit_document_ids=culprit_docs,
            summary=summary
        )

source_attribution_engine = SourceAttributionEngine()
