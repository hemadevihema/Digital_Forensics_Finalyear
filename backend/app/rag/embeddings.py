import time
from typing import List, Optional
from langchain_core.embeddings import Embeddings
from app.config import settings
from app.logger import logger

class FallbackDeterministicEmbeddings(Embeddings):
    """
    Lightweight deterministic CPU embedding generator using normalized hash projections.
    Guarantees 100% offline functionality without network or GPU requirement.
    """
    def __init__(self, dimension: int = 384):
        self.dimension = dimension

    def _embed(self, text: str) -> List[float]:
        import hashlib
        import math
        vec = [0.0] * self.dimension
        words = text.lower().split()
        if not words:
            return vec
        for i, word in enumerate(words):
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            vec[idx] += 1.0 / (math.log(i + 2))
        # Normalize L2
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

class EmbeddingFactory:
    _cached_instance: Optional[Embeddings] = None
    _dimension: int = 384

    @classmethod
    def get_embeddings(cls) -> Embeddings:
        if cls._cached_instance is not None:
            return cls._cached_instance

        provider = settings.embedding_provider.lower()
        model_name = settings.embedding_model

        start_time = time.perf_counter()
        logger.info("Initializing embedding model", provider=provider, model=model_name)

        if provider == "gemini" and settings.gemini_api_key:
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                cls._cached_instance = GoogleGenerativeAIEmbeddings(
                    model="models/text-embedding-004",
                    google_api_key=settings.gemini_api_key
                )
                cls._dimension = 768
                logger.info("Gemini embeddings initialized successfully", model="models/text-embedding-004")
                return cls._cached_instance
            except Exception as e:
                logger.warning("Failed to initialize Gemini embeddings. Falling back to local embeddings.", error=str(e))

        # Default: sentence-transformers local model
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            cls._cached_instance = HuggingFaceEmbeddings(
                model_name=model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True}
            )
            cls._dimension = 384
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info("Local HuggingFace embeddings loaded", model=model_name, duration_ms=round(duration_ms, 2))
            return cls._cached_instance
        except Exception as e:
            logger.warning("Could not load HuggingFaceEmbeddings, falling back to Deterministic Embeddings", error=str(e))
            cls._cached_instance = FallbackDeterministicEmbeddings(dimension=384)
            cls._dimension = 384
            return cls._cached_instance

    @classmethod
    def get_dimension(cls) -> int:
        return cls._dimension
