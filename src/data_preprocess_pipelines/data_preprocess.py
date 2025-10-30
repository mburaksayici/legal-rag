import os
from abc import ABC, abstractmethod
from typing import Callable, Dict, List

from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.schemas import IngestedItem
from src.chunking.schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.chunking.semantic_chunker import SemanticChunker
from src.propositioner.t5_propositioner import T5Propositioner
from src.embeddings.e5_small import E5SmallEmbedding
from src.embeddings.schemas import EmbeddingInput
from src.vectordb.milvus.client import MilvusInterface

# Named factories
INGESTORS: Dict[str, Callable[[], object]] = {
	"pdf": PDFIngestor,
}

PROPOSITIONERS: Dict[str, Callable[[], object]] = {
	"t5-propositioner": T5Propositioner,
}

EMBEDDINGS: Dict[str, Callable[[], object]] = {
	"e5-small": E5SmallEmbedding,
}

CHUNKERS: Dict[str, Callable[[T5Propositioner, E5SmallEmbedding], SemanticChunker]] = {
	"semantic_chunking": lambda prop, emb: SemanticChunker(propositioner=prop, embeddings=emb),
}

VECTORDBS: Dict[str, Callable[[], object]] = {
	"milvus-local": MilvusInterface,
}


class DataPreprocessBase(ABC):
	@abstractmethod
	def run(self, folder_path: str) -> None:
		pass


class DataPreprocessSemantic(DataPreprocessBase):
	def __init__(self, config: Dict[str, str]):
		# Resolve factories by names in config
		ingestor_name = config.get("ingestor", "pdf")
		prop_name = config.get("propositioner", "t5-propositioner")
		emb_name = config.get("embedding", "e5-small")
		chunker_name = config.get("chunker", "semantic_chunking")
		vectordb_name = config.get("vectordb", "milvus-local")

		ingestor_cls = INGESTORS[ingestor_name]
		prop_cls = PROPOSITIONERS[prop_name]
		emb_cls = EMBEDDINGS[emb_name]
		vectordb_cls = VECTORDBS[vectordb_name]

		self.ingestor: PDFIngestor = ingestor_cls()  # type: ignore[call-arg]
		self.propositioner: T5Propositioner = prop_cls()  # type: ignore[call-arg]
		self.embedding: E5SmallEmbedding = emb_cls()  # type: ignore[call-arg]
		self.chunker: SemanticChunker = CHUNKERS[chunker_name](self.propositioner, self.embedding)
		self.vectordb: MilvusInterface = vectordb_cls()  # type: ignore[call-arg]

	def run(self, folder_path: str) -> None:
		# For now we support folder paths. URI handling can be added later.
		
		pdf_files = [
			os.path.join(folder_path, f)
			for f in os.listdir(folder_path)
			if f.lower().endswith(".pdf")
		][:5]
		if not pdf_files:
			return

		ingested_items: List[IngestedItem] = []
		for path in pdf_files:
			resp = self.ingestor.ingest(type("Req", (), {"path_or_url": path, "media_type": "pdf"})())
			ingested_items.extend(resp.items)

		chunk_request = ChunkRequest(items=[ChunkItem(source=i.source, len_characters=i.len_characters, text=i.text) for i in ingested_items])
		chunk_response: ChunkResponse = self.chunker.chunk(chunk_request)

		texts = [c.text for c in chunk_response.chunks]
		if not texts:
			return
		emb = self.embedding.embed(EmbeddingInput(documents=texts))

		metadatas = [{"source": c.source, "len_characters": c.len_characters} for c in chunk_response.chunks]
		self.vectordb.ensure_collection(dim=self.embedding.embedding_size)
		self.vectordb.upsert_embeddings(emb.embeddings, metadatas)


data_preprocess_semantic_config = {
	"vectordb": "milvus-local",
	"chunker": "semantic_chunking",
	"ingestor": "pdf",
	"embedding": "e5-small",
	"propositioner": "t5-propositioner",
}

data_preprocess_semantic_pipeline = DataPreprocessSemantic(config=data_preprocess_semantic_config)
# Export alias expected by router
