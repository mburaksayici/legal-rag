import os
from typing import List, Dict, Any
import chromadb

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../assets"))
DB_PATH = os.path.join(ASSETS_DIR, "chromadb_local.db")


class ChromaDBInterface:
	def __init__(self, uri: str = "local-persistent", collection: str = "documents"):
		self.uri = uri
		self.collection = collection
		os.makedirs(ASSETS_DIR, exist_ok=True)
		self.client = chromadb.PersistentClient(path=DB_PATH)
		self._init_db()

	def _init_db(self) -> None:
		# ChromaDB automatically creates collections when accessed
		# Just ensure the collection exists
		self.client.get_or_create_collection(name=self.collection)

	def ensure_collection(self, dim: int = None) -> None:
		# ChromaDB doesn't require dimension at collection creation
		# Dimension is inferred from first add operation
		self.client.get_or_create_collection(name=self.collection)

	def upsert_embeddings(self, vectors: List[List[float]], metadatas: List[Dict[str, Any]]) -> None:
		if not vectors:
			return
		collection = self.client.get_or_create_collection(name=self.collection)
		# Generate IDs for the vectors
		ids = [f"vec_{i}" for i in range(len(vectors))]
		# Upsert to ChromaDB
		collection.upsert(
			ids=ids,
			embeddings=vectors,
			metadatas=metadatas
		)

