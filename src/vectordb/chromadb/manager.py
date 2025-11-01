import os
import chromadb
from chromadb.config import Settings
from llama_index.vector_stores.chroma import ChromaVectorStore  # type: ignore
from llama_index.core.storage.storage_context import StorageContext  # type: ignore


class ChromaDBManager:
	"""Manages ChromaDB client, collection, vector store, and storage context - initialized once."""
	
	def __init__(self, db_path: str, collection_name: str = "rag_docs"):
		self.db_path = db_path
		self.collection_name = collection_name
		self.persist_dir = self.db_path
		
		# Create directory
		os.makedirs(self.db_path, exist_ok=True)
		
		# Initialize ChromaDB client once
		self.client = chromadb.PersistentClient(
			path=self.db_path,
			settings=Settings(anonymized_telemetry=False)
		)
		
		# Get or create collection once
		self.collection = self.client.get_or_create_collection(self.collection_name)
		
		# Create vector store once
		self.vector_store = ChromaVectorStore(chroma_collection=self.collection)
		
		# Create storage context once (for saving - no persist_dir)
		self.storage_context = StorageContext.from_defaults(
			vector_store=self.vector_store
		)
	
	def get_vector_store(self):
		"""Return the initialized vector store."""
		return self.vector_store
	
	def get_collection(self):
		"""Return the initialized collection."""
		return self.collection
	
	def get_storage_context(self):
		"""Return the initialized storage context."""
		return self.storage_context
	
	def get_persist_dir(self):
		"""Return the persist directory path."""
		return self.persist_dir

