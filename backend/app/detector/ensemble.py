import time
from typing import Any, Dict, List, Optional
from app.config import settings
from app.detector.base import (
    BaseInjectionDetector, DetectorResult, EnsembleResult, RiskLevel
)
from app.detector.rule_detector import rule_detector
from app.detector.tfidf_detector import tfidf_detector
from app.detector.semantic_detector import semantic_detector
from app.detector.llm_detector import llm_detector

class EnsembleRiskFusionEngine:
    """
    Ensemble Risk Fusion Engine.
    Combines outputs from 4 complementary detection layers:
    1. Rule / Regex Pattern Matching
    2. TF-IDF + Cosine Similarity Baseline
    3. Embedding-Based Semantic Similarity
    4. Gemini Contextual Classifier
    """
    def __init__(
        self,
        rule_weight: Optional[float] = None,
        tfidf_weight: Optional[float] = None,
        semantic_weight: Optional[float] = None,
        llm_weight: Optional[float] = None,
        suspicious_threshold: Optional[float] = None,
        malicious_threshold: Optional[float] = None,
        include_llm_by_default: bool = True
    ):
        self.rule_weight = rule_weight or getattr(settings, "detector_rule_weight", 0.35)
        self.tfidf_weight = tfidf_weight or getattr(settings, "detector_tfidf_weight", 0.20)
        self.semantic_weight = semantic_weight or getattr(settings, "detector_semantic_weight", 0.25)
        self.llm_weight = llm_weight or getattr(settings, "detector_llm_weight", 0.20)

        self.suspicious_threshold = suspicious_threshold or getattr(settings, "detector_suspicious_threshold", 0.35)
        self.malicious_threshold = malicious_threshold or getattr(settings, "detector_malicious_threshold", 0.70)
        self.include_llm_by_default = include_llm_by_default

        self.detectors: List[BaseInjectionDetector] = [
            rule_detector,
            tfidf_detector,
            semantic_detector,
            llm_detector
        ]

    def scan(self, text: str, include_llm: Optional[bool] = None) -> EnsembleResult:
        total_start = time.perf_counter()
        if not text or not text.strip():
            return EnsembleResult(
                risk_score=0.0,
                classification=RiskLevel.BENIGN,
                detector_results={},
                forensic_evidence={"reason": "Empty input text"},
                total_latency_ms=0.0
            )

        run_llm = self.include_llm_by_default if include_llm is None else include_llm

        # Run individual detectors
        results: Dict[str, DetectorResult] = {}
        results[rule_detector.name] = rule_detector.scan(text)
        results[tfidf_detector.name] = tfidf_detector.scan(text)
        results[semantic_detector.name] = semantic_detector.scan(text)

        if run_llm:
            results[llm_detector.name] = llm_detector.scan(text)
            effective_rule_w = self.rule_weight
            effective_tfidf_w = self.tfidf_weight
            effective_sem_w = self.semantic_weight
            effective_llm_w = self.llm_weight
        else:
            # Re-normalize weights without LLM
            sub_total = self.rule_weight + self.tfidf_weight + self.semantic_weight
            effective_rule_w = self.rule_weight / sub_total
            effective_tfidf_w = self.tfidf_weight / sub_total
            effective_sem_w = self.semantic_weight / sub_total
            effective_llm_w = 0.0

        r_score = results[rule_detector.name].score
        t_score = results[tfidf_detector.name].score
        s_score = results[semantic_detector.name].score
        l_score = results[llm_detector.name].score if run_llm else 0.0

        # Weighted baseline fusion
        weighted_risk = (
            effective_rule_w * r_score +
            effective_tfidf_w * t_score +
            effective_sem_w * s_score +
            effective_llm_w * l_score
        )

        escalations = []
        # Rule escalation: explicit rule hit overrides subtle ambiguities
        if r_score >= 0.90:
            weighted_risk = max(weighted_risk, 0.88)
            escalations.append("HIGH_CONFIDENCE_RULE_TRIGGER")

        # Multi-detector consensus escalation: if 2 or more detectors trigger
        triggered_count = sum(1 for res in results.values() if res.triggered)
        if triggered_count >= 2:
            weighted_risk = min(1.0, weighted_risk + 0.12)
            escalations.append(f"CONSENSUS_ESCALATION_{triggered_count}_LAYERS")

        final_risk = round(min(1.0, max(0.0, weighted_risk)), 3)

        # Classification decision
        if final_risk >= self.malicious_threshold:
            classification = RiskLevel.MALICIOUS_INJECTION
        elif final_risk >= self.suspicious_threshold:
            classification = RiskLevel.SUSPICIOUS
        else:
            classification = RiskLevel.BENIGN

        total_latency = round((time.perf_counter() - total_start) * 1000, 2)

        forensic_evidence = {
            "risk_score": final_risk,
            "classification": classification.value,
            "thresholds": {
                "suspicious": self.suspicious_threshold,
                "malicious": self.malicious_threshold
            },
            "weights": {
                "rule": effective_rule_w,
                "tfidf": effective_tfidf_w,
                "semantic": effective_sem_w,
                "llm": effective_llm_w
            },
            "layer_scores": {
                "rule": r_score,
                "tfidf": t_score,
                "semantic": s_score,
                "llm": l_score if run_llm else None
            },
            "escalations": escalations,
            "triggered_layers": [name for name, res in results.items() if res.triggered]
        }

        return EnsembleResult(
            risk_score=final_risk,
            classification=classification,
            detector_results=results,
            forensic_evidence=forensic_evidence,
            total_latency_ms=total_latency
        )

ensemble_detector = EnsembleRiskFusionEngine()
