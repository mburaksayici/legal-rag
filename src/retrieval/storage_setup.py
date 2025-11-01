from llama_index.core import VectorStoreIndex  # type: ignore
from llama_index.core.schema import TextNode  # type: ignore
from llama_index.core.storage.storage_context import StorageContext  # type: ignore
from typing import List
import os

from .embedding_adapter import LlamaIndexEmbeddingAdapter
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.vectordb.qdrant_db.manager import QdrantManager
from src.vectordb.qdrant_db.config import (
	qdrant_host as default_qdrant_host,
	qdrant_port as default_qdrant_port,
	collection_name as default_collection_name
)


class StorageSetup:
	"""Set up LlamaIndex with Qdrant backend."""

	def __init__(
		self,
		embedding: CustomBaseEmbedding,
		qdrant_host: str = default_qdrant_host,
		qdrant_port: int = default_qdrant_port,
		collection_name: str = default_collection_name,
	):
		self.embedding = embedding
		self.qdrant_host = qdrant_host
		self.qdrant_port = qdrant_port
		self.collection_name = collection_name
		
		# Initialize Qdrant manager ONCE
		self.qdrant_manager = QdrantManager(
			host=self.qdrant_host,
			port=self.qdrant_port,
			collection_name=self.collection_name
		)
		
		# Get reusable components from manager
		self.vector_store = self.qdrant_manager.get_vector_store()
		self.storage_context = self.qdrant_manager.get_storage_context()
		self.client = self.qdrant_manager.get_client()
		self.embed_adapter = self.create_embedding_adapter()

	def create_index_from_nodes(
		self, leaf_nodes: List[TextNode]
	) -> VectorStoreIndex:
		"""Create and persist VectorStoreIndex from nodes."""
		# Create index with nodes using pre-initialized storage context
		index = VectorStoreIndex(
			nodes=leaf_nodes,
			embed_model=self.embed_adapter,
			storage_context=self.storage_context
		)
		
		# Qdrant persists automatically, no need to call persist()
		return index

	def load_existing_index(self) -> VectorStoreIndex:
		"""Load existing index from Qdrant."""
		try:
			# Load index from existing Qdrant collection
			index = VectorStoreIndex.from_vector_store(
				vector_store=self.vector_store,
				embed_model=self.embed_adapter
			)
			return index
		except Exception:
			return None

	def create_embedding_adapter(self):
		"""Create embedding adapter for LlamaIndex."""
		return LlamaIndexEmbeddingAdapter(self.embedding)

