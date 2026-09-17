import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-3.6-flash", alias="GEMINI_MODEL")

    # MongoDB Atlas
    mongodb_uri: str = Field(default="", alias="MONGODB_URI")
    mongodb_database: str = Field(default="rag_forensics", alias="MONGODB_DATABASE")

    # Embeddings
    embedding_provider: str = Field(default="local", alias="EMBEDDING_PROVIDER")  # "local" or "gemini"
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="EMBEDDING_MODEL")

    # RAG Settings
    chunk_size: int = Field(default=800, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=100, alias="CHUNK_OVERLAP")
    top_k: int = Field(default=5, alias="TOP_K")

    # Prompt Injection Detector Settings
    detector_rule_weight: float = Field(default=0.35, alias="DETECTOR_RULE_WEIGHT")
    detector_tfidf_weight: float = Field(default=0.20, alias="DETECTOR_TFIDF_WEIGHT")
    detector_semantic_weight: float = Field(default=0.25, alias="DETECTOR_SEMANTIC_WEIGHT")
    detector_llm_weight: float = Field(default=0.20, alias="DETECTOR_LLM_WEIGHT")
    detector_suspicious_threshold: float = Field(default=0.35, alias="DETECTOR_SUSPICIOUS_THRESHOLD")
    detector_malicious_threshold: float = Field(default=0.70, alias="DETECTOR_MALICIOUS_THRESHOLD")

    # Storage & Uploads
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")
    debug_mode: bool = Field(default=True, alias="DEBUG_MODE")
    storage_dir: str = Field(default=str(BASE_DIR / "storage"), alias="STORAGE_DIR")

    @property
    def uploads_dir(self) -> Path:
        path = Path(self.storage_dir) / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def faiss_dir(self) -> Path:
        path = Path(self.storage_dir) / "faiss_index"
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()
