from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from llama_index.vector_stores.qdrant import QdrantVectorStore  # type: ignore
from llama_index.core.storage.storage_context import StorageContext  # type: ignore


class QdrantManager:
	"""Manages Qdrant client, collection, vector store, and storage context - initialized once."""
	
	def __init__(self, host: str, port: int, collection_name: str = "documents"):
		self.host = host
		self.port = port
		self.collection_name = collection_name
		
		# Initialize Qdrant client once
		self.client = QdrantClient(host=self.host, port=self.port)
		
		# Ensure collection exists with proper configuration
		self._ensure_collection()
		
		# Create vector store once
		self.vector_store = QdrantVectorStore(
			client=self.client,
			collection_name=self.collection_name
		)
		
		# Create storage context once (for saving - mirrors ChromaDB pattern)
		self.storage_context = StorageContext.from_defaults(
			vector_store=self.vector_store
		)
	
	def _ensure_collection(self):
		"""Ensure the collection exists, create it if it doesn't."""
		try:
			# Check if collection exists
			collections = self.client.get_collections().collections
			collection_names = [col.name for col in collections]
			
			if self.collection_name not in collection_names:
				# Create collection with 384 dimensions (for e5-small embedding)
				self.client.create_collection(
					collection_name=self.collection_name,
					vectors_config=VectorParams(size=384, distance=Distance.COSINE)
				)
				print(f"✓ Created Qdrant collection: {self.collection_name}")
			else:
				print(f"✓ Qdrant collection '{self.collection_name}' already exists")
		except Exception as e:
			# Log the error and re-raise to make the issue visible
			print(f"❌ Error ensuring Qdrant collection '{self.collection_name}': {e}")
			raise
	
	def get_vector_store(self):
		"""Return the initialized vector store."""
		return self.vector_store
	
	def get_collection(self):
		"""Return the collection name (Qdrant uses names rather than objects)."""
		return self.collection_name
	
	def get_storage_context(self):
		"""Return the initialized storage context."""
		return self.storage_context
	
	def get_client(self):
		"""Return the Qdrant client."""
		return self.client

