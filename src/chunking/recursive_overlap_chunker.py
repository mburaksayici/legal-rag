from typing import List

from .base import BaseChunker
from .schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.embeddings.base import BaseEmbedding


class RecursiveOverlapChunker(BaseChunker):
    def __init__(
        self,
        embedding: BaseEmbedding,
        chunk_overlap_ratio: float = 0.2,
    ):
        super().__init__(name="recursive_overlap_chunker")
        self.embedding = embedding
        self.separators = ["\n\n", "\n", ". ", " "]
        self.chunk_size = int(getattr(self.embedding, "max_characters", 0))
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")

        ratio = max(0.0, float(chunk_overlap_ratio))
        if ratio >= 1.0:
            raise ValueError("chunk_overlap_ratio must be smaller than 1.0")
        self.chunk_overlap = max(0, int(self.chunk_size * ratio))

    def chunk(self, request: ChunkRequest) -> ChunkResponse:
        all_chunks: List[ChunkItem] = []
        for item in request.items:
            base_chunks = self._split_text(item.text)
            overlapped_chunks = self._apply_overlap(base_chunks)
            for ch in overlapped_chunks:
                if not ch:
                    continue
                all_chunks.append(
                    ChunkItem(source=item.source, len_characters=len(ch), text=ch)
                )
        return ChunkResponse(chunks=all_chunks)

    def _split_text(self, text: str) -> List[str]:
        chunks: List[str] = []
        self._split_fragment(text.strip(), 0, chunks)
        return [chunk for chunk in chunks if chunk]

    def _split_fragment(self, fragment: str, level: int, chunks: List[str]) -> None:
        fragment = fragment.strip()
        if not fragment:
            return
        if len(fragment) <= self.chunk_size:
            chunks.append(fragment)
            return

        if level >= len(self.separators):
            for start in range(0, len(fragment), self.chunk_size):
                chunk = fragment[start : start + self.chunk_size].strip()
                if chunk:
                    chunks.append(chunk)
            return

        separator = self.separators[level]
        pieces = fragment.split(separator) if separator else list(fragment)
        if len(pieces) == 1:
            self._split_fragment(fragment, level + 1, chunks)
            return

        buffer = ""
        for idx, piece in enumerate(pieces):
            piece = piece.strip()
            if not piece:
                continue
            candidate = piece if not buffer else f"{buffer}{separator}{piece}"
            if len(candidate) > self.chunk_size and buffer:
                self._split_fragment(buffer, level + 1, chunks)
                buffer = piece
            elif len(candidate) > self.chunk_size:
                self._split_fragment(piece, level + 1, chunks)
                buffer = ""
            else:
                buffer = candidate

            if buffer and idx < len(pieces) - 1 and separator:
                buffer = f"{buffer}{separator}"

        if buffer:
            if buffer.endswith(separator):
                buffer = buffer[: -len(separator)]
            self._split_fragment(buffer, level + 1, chunks)

    def _apply_overlap(self, chunks: List[str]) -> List[str]:
        if self.chunk_overlap <= 0 or len(chunks) <= 1:
            return chunks

        overlapped: List[str] = []
        prev = ""
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            if not prev:
                overlapped.append(chunk)
            else:
                tail = prev[-self.chunk_overlap :]
                combined = f"{tail}{chunk}"
                if len(combined) > self.chunk_size:
                    combined = combined[-self.chunk_size :]
                overlapped.append(combined)
            prev = chunk
        return overlapped

