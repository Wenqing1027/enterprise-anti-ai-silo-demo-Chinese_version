"""共享 RAG 设施（切块 / TF-IDF 索引）。控制环仍在 agents/rag/。"""

from shared.rag.chunking import (
    STRATEGY_ID,
    ChunkParams,
    ChunkRecord,
    build_chunks_payload,
    chunk_markdown_document,
)
from shared.rag.tfidf_index import (
    INDEX_ID,
    IndexParams,
    SearchHit,
    TfidfIndex,
    build_and_save_index,
)
from shared.rag.tokenize import tokenize

__all__ = [
    "STRATEGY_ID",
    "ChunkParams",
    "ChunkRecord",
    "build_chunks_payload",
    "chunk_markdown_document",
    "INDEX_ID",
    "IndexParams",
    "SearchHit",
    "TfidfIndex",
    "build_and_save_index",
    "tokenize",
]
