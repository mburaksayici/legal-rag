from typing import Any

from .base import BaseChunker
from .recursive_overlap_chunker import RecursiveOverlapChunker
from src.embeddings.base import BaseEmbedding


def get_chunker(name: str, embedding: BaseEmbedding, **kwargs: Any) -> BaseChunker:
    if name == "recursive_overlap":
        return RecursiveOverlapChunker(embedding=embedding, **kwargs)
    raise ValueError(f"Unknown chunker '{name}'")

