import os
import logging
from typing import Any, Dict, Optional

from src.data_preprocess_pipelines.base import DataPreprocessBase
from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.pdf_docling_ingestor import PDFDoclingIngestor
from src.ingestion.schemas import IngestedItem
from src.chunking.schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.chunking.router import get_chunker
from src.embeddings.e5_small import E5SmallEmbedding
from src.retrieval.node_builder import NodeBuilder
from src.retrieval.storage_setup import StorageSetup
from src.vectordb.qdrant_db.config import (
	qdrant_host as default_qdrant_host,
	qdrant_port as default_qdrant_port,
	collection_name as default_collection_name,
)

from llama_index.core import VectorStoreIndex  # type: ignore


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


INGESTORS: Dict[str, Any] = {
	"pdf": PDFIngestor,
	"pdf-docling": PDFDoclingIngestor,
}

EMBEDDINGS: Dict[str, Any] = {
	"e5-small": E5SmallEmbedding,
}


class DataPreprocessRecursiveOverlap(DataPreprocessBase):
	def __init__(self, config: Dict[str, Any]):
		logger.info("🚀 Initializing DataPreprocessRecursiveOverlap pipeline")

		ingestor_name = config.get("ingestor", "pdf")
		embedding_name = config.get("embedding", "e5-small")
		chunker_name = config.get("chunker", "recursive_overlap")

		logger.info(
			f"📋 Configuration: ingestor={ingestor_name}, embedding={embedding_name}, chunker={chunker_name}"
		)

		ingestor_cls = INGESTORS[ingestor_name]
		embedding_cls = EMBEDDINGS[embedding_name]

		self.ingestor: PDFIngestor = ingestor_cls()  # type: ignore[call-arg]
		logger.info("✅ Ingestor initialized")

		self.embedding: E5SmallEmbedding = embedding_cls()  # type: ignore[call-arg]
		logger.info("✅ Embedding initialized")

		chunker_ratio = float(config.get("chunk_overlap_ratio", 0.2))
		self.chunker = get_chunker(
			chunker_name,
			embedding=self.embedding,
			chunk_overlap_ratio=chunker_ratio,
		)
		logger.info("✅ Recursive overlap chunker initialized")

		self.storage_setup = StorageSetup(
			embedding=self.embedding,
			qdrant_host=default_qdrant_host,
			qdrant_port=default_qdrant_port,
			collection_name=default_collection_name,
		)
		logger.info("✅ Storage setup initialized")

		self.index: Optional[VectorStoreIndex] = None
		logger.info("✅ DataPreprocessRecursiveOverlap pipeline fully initialized")

	def run_single_doc(self, file_path: str) -> Dict[str, Any]:
		logger.info(f"📄 Starting run_single_doc() for: {os.path.basename(file_path)}")
		logger.info(f"📍 Full path: {file_path}")

		try:
			logger.info(f"📖 Ingesting document: {os.path.basename(file_path)}")
			resp = self.ingestor.ingest(
				type("Req", (), {"path_or_url": file_path, "media_type": "pdf"})()
			)
			logger.info(f"✅ Ingestion complete: {len(resp.items)} items extracted")

			if not resp.items or not any(item.text.strip() for item in resp.items):
				logger.warning(
					f"⚠️ No content extracted from document: {os.path.basename(file_path)}"
				)
				return {
					"success": False,
					"error": "No content extracted from document",
					"file_path": file_path,
					"character_count": 0,
				}

			total_chars = sum(item.len_characters for item in resp.items)
			logger.info(
				f"📊 Document stats: {total_chars} total characters across {len(resp.items)} items"
			)

			logger.info(f"🔪 Starting recursive overlap chunking for: {os.path.basename(file_path)}")
			chunk_request = ChunkRequest(
				items=[
					ChunkItem(source=i.source, len_characters=i.len_characters, text=i.text)
					for i in resp.items
				]
			)
			chunk_response: ChunkResponse = self.chunker.chunk(chunk_request)
			logger.info(
				f"✅ Chunking complete: {len(chunk_response.chunks) if chunk_response.chunks else 0} chunks generated"
			)

			parent_texts: Dict[str, str] = {}
			for item in resp.items:
				source = item.source
				if source not in parent_texts:
					parent_texts[source] = item.text
			logger.info(f"✅ Parent texts built for {len(parent_texts)} unique sources")

			if chunk_response.chunks:
				logger.info(f"🔨 Building nodes from {len(chunk_response.chunks)} chunks...")
				leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
					chunk_response.chunks, parent_texts
				)
				node_count = len(leaf_nodes)
				logger.info(
					f"✅ Built {node_count} leaf nodes and {len(parent_docs)} parent documents"
				)

				try:
					self.storage_setup.create_index_from_nodes(leaf_nodes)
					logger.info(f"✅ Successfully wrote {node_count} nodes to Qdrant")
				except Exception as e:
					logger.error(f"❌ Failed to write to Qdrant: {e}")
					raise
			else:
				logger.warning("⚠️ No chunks to process, no nodes built")
				node_count = 0

			result = {
				"success": True,
				"file_path": file_path,
				"character_count": total_chars,
				"chunk_count": len(chunk_response.chunks) if chunk_response.chunks else 0,
				"node_count": node_count,
			}
			logger.info(
				f"✅ run_single_doc() completed successfully for: {os.path.basename(file_path)}"
			)
			logger.info(
				f"📊 Final stats: {result['character_count']} chars, {result['chunk_count']} chunks, {result['node_count']} nodes"
			)
			return result

		except Exception as e:
			logger.error(f"❌ Failed to process {os.path.basename(file_path)}: {str(e)}")
			logger.error(f"❌ Exception type: {type(e).__name__}")
			import traceback

			logger.error(f"❌ Stack trace:\n{traceback.format_exc()}")
			return {
				"success": False,
				"error": str(e),
				"file_path": file_path,
				"character_count": 0,
			}


data_preprocess_recursive_overlap_config: Dict[str, Any] = {
	"chunker": "recursive_overlap",
	"ingestor": "pdf",
	"embedding": "e5-small",
}

data_preprocess_recursive_overlap_pipeline = DataPreprocessRecursiveOverlap(
	config=data_preprocess_recursive_overlap_config
)
