import json
import math
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.rag.embeddings import EmbeddingFactory
from app.detector.base import BaseInjectionDetector, DetectorResult

PATTERNS_FILE = Path(__file__).resolve().parent / "dataset" / "injection_patterns.json"

class SemanticEmbeddingDetector(BaseInjectionDetector):
    """
    Layer 3: Embedding-based Semantic Similarity Detector.
    Detects paraphrased, obfuscated, and semantic jailbreaks by projecting
    the input into dense vector space using the RAG system's embedding engine.
    """
    def __init__(self):
        self.embeddings = EmbeddingFactory.get_embeddings()
        self.patterns: List[Dict[str, Any]] = []
        self.exemplar_vectors: List[List[float]] = []
        self._initialized = False

    def _ensure_initialized(self):
        if self._initialized:
            return

        if not PATTERNS_FILE.exists():
            return

        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            self.patterns = json.load(f)

        texts = [p["text"] for p in self.patterns]
        try:
            self.exemplar_vectors = self.embeddings.embed_documents(texts)
            self._initialized = True
        except Exception:
            # If batch embed fails, try individual embedding
            self.exemplar_vectors = []
            for t in texts:
                try:
                    self.exemplar_vectors.append(self.embeddings.embed_query(t))
                except Exception:
                    self.exemplar_vectors.append([0.0] * EmbeddingFactory.get_dimension())
            self._initialized = True

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return max(0.0, min(1.0, dot / (norm_a * norm_b)))

    @property
    def name(self) -> str:
        return "semantic_embedding_detector"

    def scan(self, text: str) -> DetectorResult:
        start_time = time.perf_counter()
        if not text or not text.strip():
            return DetectorResult(
                detector_name=self.name,
                score=0.0,
                confidence=1.0,
                triggered=False,
                details={"max_similarity": 0.0, "nearest_exemplar": None},
                latency_ms=0.0
            )

        self._ensure_initialized()
        if not self.exemplar_vectors or not self.patterns:
            return DetectorResult(
                detector_name=self.name,
                score=0.0,
                confidence=0.5,
                triggered=False,
                details={"error": "Exemplars not loaded"},
                latency_ms=0.0
            )

        try:
            query_vector = self.embeddings.embed_query(text)
        except Exception as e:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return DetectorResult(
                detector_name=self.name,
                score=0.0,
                confidence=0.5,
                triggered=False,
                details={"error": str(e)},
                latency_ms=latency_ms
            )

        max_sim = 0.0
        best_idx = 0

        for idx, ex_vec in enumerate(self.exemplar_vectors):
            sim = self._cosine_similarity(query_vector, ex_vec)
            if sim > max_sim:
                max_sim = sim
                best_idx = idx

        best_pattern = self.patterns[best_idx]
        weight = best_pattern.get("weight", 1.0)
        # Apply slight threshold calibration for embedding distances
        # Typically similarity >= 0.72 indicates high semantic overlap
        calibrated_score = round(max(0.0, min(1.0, (max_sim - 0.25) / 0.65)) * weight, 4)
        triggered = calibrated_score >= 0.50

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DetectorResult(
            detector_name=self.name,
            score=calibrated_score,
            confidence=round(min(1.0, calibrated_score + 0.1), 2),
            triggered=triggered,
            details={
                "raw_cosine_similarity": round(max_sim, 4),
                "calibrated_score": calibrated_score,
                "nearest_exemplar": best_pattern["text"],
                "category": best_pattern["category"]
            },
            latency_ms=latency_ms
        )

semantic_detector = SemanticEmbeddingDetector()
