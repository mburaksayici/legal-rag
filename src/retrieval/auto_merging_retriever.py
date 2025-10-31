from typing import List, Optional
from llama_index.core.retrievers import AutoMergingRetriever  # type: ignore
from llama_index.core import VectorStoreIndex, StorageContext  # type: ignore

from .schemas import QueryRequest, QueryResponse, RetrievalResult
from .storage_setup import StorageSetup
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding


class AutoMergingRetrieverWrapper:
	"""Wrapper for LlamaIndex AutoMergingRetriever."""

	def __init__(
		self,
		index: VectorStoreIndex,
		storage_context: StorageContext,
		similarity_top_k: int = 6,
	):
		self.index = index
		self.storage_context = storage_context
		self.similarity_top_k = similarity_top_k
		self.retriever = self._create_retriever()

	def _create_retriever(self) -> AutoMergingRetriever:
		"""Create AutoMergingRetriever from base retriever."""
		base_retriever = self.index.as_retriever(similarity_top_k=self.similarity_top_k)
		return AutoMergingRetriever(
			base_retriever=base_retriever,
			storage_context=self.storage_context,
			verbose=True,
		)

	def retrieve(self, query: str, top_k: Optional[int] = None) -> QueryResponse:
		"""Retrieve and merge nodes for a query."""
		k = top_k or self.similarity_top_k
		# Temporarily update top_k if different
		if k != self.similarity_top_k:
			self.retriever.base_retriever.similarity_top_k = k
		
		nodes = self.retriever.retrieve(query)
		
		results = []
		for node in nodes:
			source = node.metadata.get("source", "unknown")
			results.append(
				RetrievalResult(
					text=node.text,
					source=source,
					metadata=dict(node.metadata),
				)
			)
		
		return QueryResponse(results=results)

