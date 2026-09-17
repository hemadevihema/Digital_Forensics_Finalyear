from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import BaseModel, Field
from app.config import settings
from app.detector.ensemble import ensemble_detector
from app.detector.evaluator import benchmark_evaluator
from app.detector.source_attribution import source_attribution_engine
from app.database.models import RetrievalItem
from app.services.attack_graph_service import attack_graph_service
from app.services.forensic_report_service import forensic_report_service

router = APIRouter(prefix="/forensics", tags=["Prompt Injection Forensics"])

class ScanRequest(BaseModel):
    text: str = Field(..., description="Text to analyze for prompt injection")
    include_llm: Optional[bool] = Field(default=True, description="Whether to include Gemini contextual layer")

class AttributeRequest(BaseModel):
    user_question: str
    chunks: List[Dict[str, Any]] = Field(default_factory=list)

@router.post("/scan")
def scan_text(request: ScanRequest):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")
    
    result = ensemble_detector.scan(text, include_llm=request.include_llm)
    return {
        "text_preview": text[:100],
        "risk_score": result.risk_score,
        "classification": result.classification.value,
        "total_latency_ms": result.total_latency_ms,
        "detector_results": {
            k: v.model_dump() for k, v in result.detector_results.items()
        },
        "forensic_evidence": result.forensic_evidence
    }

@router.post("/attribute")
def attribute_sources(request: AttributeRequest):
    retrieval_items = [
        RetrievalItem(
            document_id=c.get("document_id", "DOC-UNKNOWN"),
            chunk_id=c.get("chunk_id", f"CHUNK-{i}"),
            source=c.get("source", "Unknown"),
            page=int(c.get("page", 1)),
            rank=i + 1,
            score=float(c.get("score", 0.8)),
            text=c.get("text", "")
        )
        for i, c in enumerate(request.chunks)
    ]
    
    res = source_attribution_engine.attribute(
        user_question=request.user_question,
        retrieved_items=retrieval_items
    )
    return {
        "attribution": res.attribution.value,
        "summary": res.summary,
        "culprit_chunk_ids": res.culprit_chunk_ids,
        "culprit_document_ids": res.culprit_document_ids,
        "user_scan": res.user_scan.model_dump() if res.user_scan else None,
        "document_scans": res.document_scans
    }

@router.get("/evaluate")
def run_evaluation(include_llm: bool = False):
    try:
        report = benchmark_evaluator.run_benchmark(include_llm=include_llm)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Benchmark evaluation failed: {str(e)}")

@router.get("/config")
def get_forensics_config():
    return {
        "weights": {
            "rule": ensemble_detector.rule_weight,
            "tfidf": ensemble_detector.tfidf_weight,
            "semantic": ensemble_detector.semantic_weight,
            "llm": ensemble_detector.llm_weight
        },
        "thresholds": {
            "suspicious": ensemble_detector.suspicious_threshold,
            "malicious": ensemble_detector.malicious_threshold
        },
        "detectors": [d.name for d in ensemble_detector.detectors]
    }

@router.get("/graph/{request_id}")
def get_attack_graph(request_id: str):
    clean_id = request_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="request_id cannot be empty.")
    try:
        graph_data = attack_graph_service.build_attack_graph(clean_id)
        return graph_data
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate attack graph for request '{clean_id}': {str(e)}")

@router.get("/report/{request_id}")
def get_forensic_report(request_id: str, format: str = Query(default="json", description="Report format: 'json' or 'pdf'")):
    clean_id = request_id.strip()
    if not clean_id:
        raise HTTPException(status_code=400, detail="request_id cannot be empty.")
    
    report_format = format.strip().lower()
    if report_format not in {"json", "pdf"}:
        raise HTTPException(status_code=400, detail=f"Unsupported format '{format}'. Supported formats: 'json', 'pdf'.")

    try:
        if report_format == "pdf":
            pdf_bytes = forensic_report_service.generate_pdf_report(clean_id)
            filename = f"Forensic_Audit_Report_{clean_id}.pdf"
            return Response(
                content=pdf_bytes,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                }
            )
        else:
            return forensic_report_service.generate_json_report(clean_id)
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate forensic report for request '{clean_id}': {str(e)}")
