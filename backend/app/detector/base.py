from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class RiskLevel(str, Enum):
    BENIGN = "BENIGN"
    SUSPICIOUS = "SUSPICIOUS"
    MALICIOUS_INJECTION = "MALICIOUS_INJECTION"

class SourceOrigin(str, Enum):
    NONE = "NONE"
    USER = "USER"
    DOCUMENT = "DOCUMENT"
    BOTH = "BOTH"

class DetectorResult(BaseModel):
    detector_name: str
    score: float = Field(ge=0.0, le=1.0, description="Normalized risk score from 0.0 to 1.0")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    triggered: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)
    latency_ms: float = 0.0

class EnsembleResult(BaseModel):
    risk_score: float = Field(ge=0.0, le=1.0)
    classification: RiskLevel = RiskLevel.BENIGN
    detector_results: Dict[str, DetectorResult] = Field(default_factory=dict)
    forensic_evidence: Dict[str, Any] = Field(default_factory=dict)
    total_latency_ms: float = 0.0

class SourceAttributionResult(BaseModel):
    attribution: SourceOrigin = SourceOrigin.NONE
    user_scan: Optional[EnsembleResult] = None
    document_scans: List[Dict[str, Any]] = Field(default_factory=list)
    culprit_chunk_ids: List[str] = Field(default_factory=list)
    culprit_document_ids: List[str] = Field(default_factory=list)
    summary: str = "No prompt injection detected."

class BaseInjectionDetector(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for the detector."""
        pass

    @abstractmethod
    def scan(self, text: str) -> DetectorResult:
        """Scan input text and return a structured DetectorResult."""
        pass
