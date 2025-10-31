from typing import List, Tuple, Optional
import chromadb
from llama_index.core import VectorStoreIndex  # type: ignore
from llama_index.vector_stores.chroma import ChromaVectorStore  # type: ignore
from llama_index.core.retrievers import AutoMergingRetriever  # type: ignore
from src.embeddings.base import BaseEmbedding as CustomBaseEmbedding
from src.retrieval.embedding_adapter import LlamaIndexEmbeddingAdapter
from src.chromadb.config import db_path


class SimpleChromaDBRetriever:
	"""LlamaIndex-based retriever that works with existing ChromaDB data."""
	
	def __init__(self, embedding: CustomBaseEmbedding, chromadb_db_path: str = None, collection_name: str = "rag_docs"):
		self.embedding = embedding
		self.chromadb_db_path = chromadb_db_path or db_path
		self.collection_name = collection_name
		self.client = None
		self.collection = None
		self.index = None
		self.retriever = None
		
	def _ensure_connection(self):
		"""Ensure ChromaDB connection and LlamaIndex setup."""
		if self.client is None:
			import os
			os.makedirs(self.chromadb_db_path, exist_ok=True)
			self.client = chromadb.PersistentClient(path=self.chromadb_db_path)
			
		if self.collection is None:
			try:
				self.collection = self.client.get_collection(name=self.collection_name)
			except Exception:
				# Collection doesn't exist
				self.collection = None
				return
				
		if self.index is None and self.collection is not None:
			# Set up LlamaIndex components - no StorageContext needed
			vector_store = ChromaVectorStore(chroma_collection=self.collection)
			embed_adapter = LlamaIndexEmbeddingAdapter(self.embedding)
			
			# Create index from existing vector store
			self.index = VectorStoreIndex.from_vector_store(
				vector_store=vector_store,
				embed_model=embed_adapter
			)
			
			# Create base retriever (AutoMergingRetriever needs StorageContext, so use base retriever)
			self.retriever = self.index.as_retriever(similarity_top_k=6)
				
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
		"""Check if ChromaDB collection exists and has data."""
		self._ensure_connection()
		if self.collection is None or self.retriever is None:
			return False
			
		try:
			count = self.collection.count()
			return count > 0
		except Exception:
			return False
