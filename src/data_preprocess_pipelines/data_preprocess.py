import os
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional

from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.schemas import IngestedItem
from src.chunking.schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.chunking.semantic_chunker import SemanticChunker
from src.propositioner.t5_propositioner import T5Propositioner
from src.embeddings.e5_small import E5SmallEmbedding
from src.embeddings.schemas import EmbeddingInput
from src.retrieval.node_builder import NodeBuilder
from src.retrieval.storage_setup import StorageSetup
from llama_index.core import VectorStoreIndex  # type: ignore

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

		ingestor_cls = INGESTORS[ingestor_name]
		prop_cls = PROPOSITIONERS[prop_name]
		emb_cls = EMBEDDINGS[emb_name]

		self.ingestor: PDFIngestor = ingestor_cls()  # type: ignore[call-arg]
		self.propositioner: T5Propositioner = prop_cls()  # type: ignore[call-arg]
		self.embedding: E5SmallEmbedding = emb_cls()  # type: ignore[call-arg]
		self.chunker: SemanticChunker = CHUNKERS[chunker_name](self.propositioner, self.embedding)
		self.storage_setup = StorageSetup(embedding=self.embedding)
		self.index: Optional[VectorStoreIndex] = None

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

		if not chunk_response.chunks:
			return

		# Build parent texts dict (full text per source)
		parent_texts: Dict[str, str] = {}
		for item in ingested_items:
			source = item.source
			if source not in parent_texts:
				parent_texts[source] = item.text

		# Build LlamaIndex nodes
		leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
			chunk_response.chunks, parent_texts
		)

		# Create index directly - no StorageContext needed
		self.index = self.storage_setup.create_index_from_nodes(leaf_nodes)


data_preprocess_semantic_config = {
	"chunker": "semantic_chunking",
	"ingestor": "pdf",
	"embedding": "e5-small",
	"propositioner": "t5-propositioner",
}

data_preprocess_semantic_pipeline = DataPreprocessSemantic(config=data_preprocess_semantic_config)
# Export alias expected by router
