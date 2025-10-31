from llama_index.core import VectorStoreIndex  # type: ignore
from llama_index.core.schema import TextNode, Document  # type: ignore
from llama_index.vector_stores.chroma import ChromaVectorStore  # type: ignore
from typing import List
import chromadb  # type: ignore

from .embedding_adapter import LlamaIndexEmbeddingAdapter
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.chromadb.config import db_path


class StorageSetup:
	"""Set up LlamaIndex with ChromaDB backend - no StorageContext needed."""

	def __init__(
		self,
		embedding: CustomBaseEmbedding,
		chromadb_db_path: str = None,
		collection_name: str = "rag_docs",
	):
		self.embedding = embedding
		self.chromadb_db_path = chromadb_db_path or db_path
		self.collection_name = collection_name

	def create_index_from_nodes(
		self, leaf_nodes: List[TextNode]
	) -> VectorStoreIndex:
		"""Create VectorStoreIndex directly from nodes - no StorageContext."""
		import os
		
		# Use local ChromaDB client (path must be a directory, not a file)
		# Ensure directory exists
		os.makedirs(self.chromadb_db_path, exist_ok=True)
		chroma_client = chromadb.PersistentClient(path=self.chromadb_db_path)
		chroma_collection = chroma_client.get_or_create_collection(name=self.collection_name)
		vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

		# Create embedding adapter
		embed_adapter = self.create_embedding_adapter()
		
		# Create index directly with vector store and embedding model
		index = VectorStoreIndex(
			nodes=leaf_nodes,
			embed_model=embed_adapter,
			vector_store=vector_store
		)
		return index

	def load_existing_index(self) -> VectorStoreIndex:
		"""Load existing ChromaDB as VectorStoreIndex."""
		import os
		
		# Ensure directory exists
		os.makedirs(self.chromadb_db_path, exist_ok=True)
		chroma_client = chromadb.PersistentClient(path=self.chromadb_db_path)
		
		try:
			chroma_collection = chroma_client.get_collection(name=self.collection_name)
			vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
			embed_adapter = self.create_embedding_adapter()
			
			# Create index from existing vector store
			index = VectorStoreIndex.from_vector_store(
				vector_store=vector_store,
				embed_model=embed_adapter
			)
			return index
		except Exception:
			# Collection doesn't exist
			return None

	def create_embedding_adapter(self):
		"""Create embedding adapter for LlamaIndex."""
		return LlamaIndexEmbeddingAdapter(self.embedding)

