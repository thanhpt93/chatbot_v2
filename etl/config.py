"""
ETL Configuration Module.
Centralizes database connection strings, paths, and model parameters.
"""

import os
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parent.parent

@dataclass
class ETLConfig:
    # PostgreSQL Configuration
    pg_host: str = os.getenv("PG_HOST", "localhost")
    pg_port: int = int(os.getenv("PG_PORT", "5433"))
    pg_user: str = os.getenv("PG_USER", "postgres")
    pg_password: str = os.getenv("PG_PASSWORD", "postgres")
    pg_database: str = os.getenv("PG_DATABASE", "groupware")
    pg_dump_path: Path = ROOT / "database" / "inf_nffice_latest.dump"

    # Neo4j Configuration
    neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user: str = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "password")
    neo4j_database: str = os.getenv("NEO4J_DATABASE", "neo4j")
    graph_export_dir: Path = ROOT / "data" / "graph_export"

    # Qdrant Vector DB Configuration
    qdrant_path: Path = ROOT / "data" / "qdrant_storage"
    qdrant_url: str = os.getenv("QDRANT_URL", "")  # Empty string means local on-disk storage
    qdrant_collection: str = os.getenv("QDRANT_COLLECTION", "groupware_knowledge")

    # Embedding Model Configuration
    embedding_model_name: str = "intfloat/multilingual-e5-small"
    embedding_device: str = "cpu"
    vector_dimension: int = 384

    # Circuit Breaker Configuration
    max_delete_ratio: float = 0.05  # 5%
    max_delete_absolute: int = 100

    # LLM Serving Configuration (vLLM OpenAI-Compatible API)
    llm_api_base: str = os.getenv("LLM_API_BASE", "http://localhost:8000/v1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "EMPTY")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4")
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

config = ETLConfig()
