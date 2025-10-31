from typing import List
from llama_index.core.embeddings import BaseEmbedding  # type: ignore
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.embeddings.schemas import EmbeddingInput


class LlamaIndexEmbeddingAdapter(BaseEmbedding):
	"""Adapter to use custom E5SmallEmbedding with LlamaIndex."""

	def __init__(self, embedding: CustomBaseEmbedding):
		super().__init__(model_name=embedding.embedding_name)
		# Use object.__setattr__ to bypass Pydantic's attribute validation
		object.__setattr__(self, '_custom_embedding', embedding)
		object.__setattr__(self, '_embedding_size', embedding.embedding_size)

	@property
	def dimension(self) -> int:
		return self._embedding_size

	def _get_query_embedding(self, query: str) -> List[float]:
		result = self._custom_embedding.embed(EmbeddingInput(documents=[query]))
		return result.embeddings[0] if result.embeddings else []

	def _get_text_embedding(self, text: str) -> List[float]:
		"""Get embedding for a single text."""
		result = self._custom_embedding.embed(EmbeddingInput(documents=[text]))
		return result.embeddings[0] if result.embeddings else []

	def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
		result = self._custom_embedding.embed(EmbeddingInput(documents=texts))
		return result.embeddings

	async def _aget_query_embedding(self, query: str) -> List[float]:
		return self._get_query_embedding(query)

	async def _aget_text_embedding(self, text: str) -> List[float]:
		"""Get embedding for a single text (async)."""
		return self._get_text_embedding(text)

	async def _aget_text_embeddings(self, texts: List[str]) -> List[List[float]]:
		return self._get_text_embeddings(texts)

