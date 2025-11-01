from typing import List, Tuple, Optional
from llama_index.core import VectorStoreIndex  # type: ignore
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.retrieval.embedding_adapter import LlamaIndexEmbeddingAdapter
from src.vectordb.qdrant_db.manager import QdrantManager
from src.vectordb.qdrant_db.config import (
	qdrant_host as default_qdrant_host,
	qdrant_port as default_qdrant_port,
	collection_name as default_collection_name
)


class SimpleQdrantRetriever:
	"""LlamaIndex-based retriever that works with existing Qdrant data."""
	
	def __init__(
		self,
		embedding: CustomBaseEmbedding,
		qdrant_host: str = None,
		qdrant_port: int = None,
		collection_name: str = None
	):
		self.embedding = embedding
		self.qdrant_host = qdrant_host if qdrant_host is not None else default_qdrant_host
		self.qdrant_port = qdrant_port if qdrant_port is not None else default_qdrant_port
		self.collection_name = collection_name if collection_name is not None else default_collection_name
		
		# Initialize Qdrant manager ONCE
		self.qdrant_manager = QdrantManager(
			host=self.qdrant_host,
			port=self.qdrant_port,
			collection_name=self.collection_name
		)
		
		# Get reusable components
		self.collection_name = self.qdrant_manager.get_collection()
		self.vector_store = self.qdrant_manager.get_vector_store()
		self.client = self.qdrant_manager.get_client()
		self.embed_adapter = LlamaIndexEmbeddingAdapter(self.embedding)
		
		self.index = None
		self.retriever = None
		
	def _ensure_connection(self):
		"""Ensure LlamaIndex index and retriever are set up."""
		if self.index is None:
			try:
				# Create index from existing vector store
				self.index = VectorStoreIndex.from_vector_store(
					vector_store=self.vector_store,
					embed_model=self.embed_adapter
				)
				
				# Create base retriever
				self.retriever = self.index.as_retriever(similarity_top_k=6)
			except Exception:
				# Collection might be empty or have issues
				return
				
	def retrieve(self, query: str, top_k: int = 6, auto_merge: bool = True) -> Tuple[str, List[str]]:
		"""Retrieve relevant chunks using LlamaIndex retriever."""
		self._ensure_connection()
		
		if self.retriever is None:
			return "", []
			
		# Update top_k if different
		self.retriever.similarity_top_k = top_k
		
		# Use the retriever (base retriever without auto-merging for now)
		nodes = self.retriever.retrieve(query)
		
		# Extract context and sources from nodes
		context_parts = []
		sources = set()
		
		for node in nodes:
			context_parts.append(node.text)
			if hasattr(node, 'metadata') and node.metadata:
				source = node.metadata.get("source", "unknown")
				if source != "unknown":
					sources.add(source)
				
		return "\n\n".join(context_parts), list(sources)
		
	def is_available(self) -> bool:
		"""Check if Qdrant collection exists and has data."""
		self._ensure_connection()
		if self.retriever is None:
			return False
			
		try:
			# Check collection info
			collection_info = self.client.get_collection(self.collection_name)
			return collection_info.points_count > 0
		except Exception:
			return False

