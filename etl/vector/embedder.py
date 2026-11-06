"""
Embedding Generator Module.
Encodes text chunks using intfloat/multilingual-e5-small on CPU.
Follows E5 specification:
- Documents/passages: prefixed with "passage: "
- Queries: prefixed with "query: "
"""

import logging
from typing import List
from etl.config import config

logger = logging.getLogger("etl.vector.embedder")

class TextEmbedder:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TextEmbedder, cls).__new__(cls)
            cls._instance._init_model()
        return cls._instance

    def _init_model(self):
        logger.info(f"Loading embedding model '{config.embedding_model_name}' on device '{config.embedding_device}'...")
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(config.embedding_model_name, device=config.embedding_device)
        logger.info("Embedding model loaded successfully.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        # E5 requires "passage: " prefix for documents
        prefixed = [f"passage: {t}" for t in texts]
        embeddings = self.model.encode(prefixed, batch_size=64, normalize_embeddings=True, show_progress_bar=False)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        # E5 requires "query: " prefix for search queries
        prefixed = f"query: {query}"
        emb = self.model.encode(prefixed, normalize_embeddings=True, show_progress_bar=False)
        return emb.tolist()
