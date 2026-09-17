import json
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.detector.base import BaseInjectionDetector, DetectorResult

PATTERNS_FILE = Path(__file__).resolve().parent / "dataset" / "injection_patterns.json"

class FallbackTfidfEngine:
    """
    Lightweight, pure-Python TF-IDF & Cosine Similarity implementation.
    Guarantees deterministic execution even if scikit-learn is unavailable.
    """
    def __init__(self, corpus: List[str]):
        self.corpus = corpus
        self.vocabulary: Dict[str, int] = {}
        self.idf: Dict[str, float] = {}
        self.corpus_vectors: List[Dict[int, float]] = []
        self._build()

    def _tokenize(self, text: str) -> List[str]:
        words = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
        bigrams = [f"{words[i]}_{words[i+1]}" for i in range(len(words) - 1)]
        return words + bigrams

    def _build(self):
        doc_count = len(self.corpus)
        df: Dict[str, int] = {}

        tokenized_docs = [self._tokenize(doc) for doc in self.corpus]
        for tokens in tokenized_docs:
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1

        term_idx = 0
        for term, freq in df.items():
            self.vocabulary[term] = term_idx
            self.idf[term] = math.log((doc_count + 1) / (freq + 1)) + 1.0
            term_idx += 1

        for tokens in tokenized_docs:
            vec = self._vectorize_tokens(tokens)
            self.corpus_vectors.append(vec)

    def _vectorize_tokens(self, tokens: List[str]) -> Dict[int, float]:
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        vec: Dict[int, float] = {}
        norm_sq = 0.0
        for t, count in tf.items():
            if t in self.vocabulary:
                idx = self.vocabulary[t]
                val = count * self.idf[t]
                vec[idx] = val
                norm_sq += val * val

        norm = math.sqrt(norm_sq) or 1.0
        return {idx: val / norm for idx, val in vec.items()}

    def compute_similarity(self, query: str) -> List[float]:
        q_tokens = self._tokenize(query)
        q_vec = self._vectorize_tokens(q_tokens)
        sims = []
        for d_vec in self.corpus_vectors:
            dot = sum(val * d_vec.get(idx, 0.0) for idx, val in q_vec.items())
            sims.append(round(dot, 4))
        return sims

class TfidfSimilarityDetector(BaseInjectionDetector):
    """
    Layer 2: Classical NLP baseline using TF-IDF n-gram vectorization
    and Cosine Similarity against a curated prompt-injection pattern corpus.
    """
    def __init__(self):
        self.patterns: List[Dict[str, Any]] = []
        self.texts: List[str] = []
        self.vectorizer: Optional[Any] = None
        self.tfidf_matrix: Optional[Any] = None
        self.fallback_engine: Optional[FallbackTfidfEngine] = None
        self._init_corpus()

    def _init_corpus(self):
        if not PATTERNS_FILE.exists():
            return

        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            self.patterns = json.load(f)

        self.texts = [p["text"] for p in self.patterns]

        # Attempt sklearn vectorizer first
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                lowercase=True,
                stop_words="english",
                token_pattern=r"(?u)\b\w+\b"
            )
            self.tfidf_matrix = self.vectorizer.fit_transform(self.texts)
        except Exception:
            self.vectorizer = None

        # Always initialize fallback engine for resilience
        self.fallback_engine = FallbackTfidfEngine(self.texts)

    @property
    def name(self) -> str:
        return "tfidf_similarity_detector"

    def scan(self, text: str) -> DetectorResult:
        start_time = time.perf_counter()
        if not text or not text.strip() or not self.texts:
            return DetectorResult(
                detector_name=self.name,
                score=0.0,
                confidence=1.0,
                triggered=False,
                details={"max_similarity": 0.0, "matched_sample": None},
                latency_ms=0.0
            )

        max_sim = 0.0
        best_idx = 0

        if self.vectorizer is not None and self.tfidf_matrix is not None:
            try:
                from sklearn.metrics.pairwise import cosine_similarity
                q_vec = self.vectorizer.transform([text])
                sims = cosine_similarity(q_vec, self.tfidf_matrix)[0]
                best_idx = int(sims.argmax())
                max_sim = float(sims[best_idx])
            except Exception:
                # Fallback to pure-Python engine
                sims = self.fallback_engine.compute_similarity(text)
                best_idx = max(range(len(sims)), key=lambda i: sims[i])
                max_sim = sims[best_idx]
        else:
            sims = self.fallback_engine.compute_similarity(text)
            best_idx = max(range(len(sims)), key=lambda i: sims[i])
            max_sim = sims[best_idx]

        best_pattern = self.patterns[best_idx]
        weight = best_pattern.get("weight", 1.0)
        weighted_score = min(1.0, round(max_sim * weight, 4))
        # Consider triggered if similarity >= 0.40
        triggered = weighted_score >= 0.40
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return DetectorResult(
            detector_name=self.name,
            score=weighted_score,
            confidence=round(min(1.0, weighted_score + 0.15), 2),
            triggered=triggered,
            details={
                "max_similarity": round(max_sim, 4),
                "weighted_score": weighted_score,
                "matched_sample": best_pattern["text"],
                "category": best_pattern["category"]
            },
            latency_ms=latency_ms
        )

tfidf_detector = TfidfSimilarityDetector()
