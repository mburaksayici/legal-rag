import os
import time
import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, List, Optional, Any

from src.ingestion.pdf_ingestor import PDFIngestor
from src.ingestion.schemas import IngestedItem
from src.chunking.schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.chunking.semantic_chunker import SemanticChunker
from src.propositioner.t5_propositioner import T5Propositioner
from src.embeddings.e5_small import E5SmallEmbedding
from src.embeddings.schemas import EmbeddingInput
from src.retrieval.node_builder import NodeBuilder
from src.retrieval.storage_setup import StorageSetup
from src.vectordb.qdrant_db.config import (
	qdrant_host as default_qdrant_host,
	qdrant_port as default_qdrant_port,
	collection_name as default_collection_name
)
from src.data_preprocess_pipelines.base import  DataPreprocessBase


from llama_index.core import VectorStoreIndex  # type: ignore

# Configure logger for data preprocessing
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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


class DataPreprocessSemantic(DataPreprocessBase):
	def __init__(self, config: Dict[str, str]):
		logger.info("🚀 Initializing DataPreprocessSemantic pipeline")
		
		# Resolve factories by names in config
		ingestor_name = config.get("ingestor", "pdf")
		prop_name = config.get("propositioner", "t5-propositioner")
		emb_name = config.get("embedding", "e5-small")
		chunker_name = config.get("chunker", "semantic_chunking")

		logger.info(f"📋 Configuration: ingestor={ingestor_name}, propositioner={prop_name}, embedding={emb_name}, chunker={chunker_name}")

		ingestor_cls = INGESTORS[ingestor_name]
		prop_cls = PROPOSITIONERS[prop_name]
		emb_cls = EMBEDDINGS[emb_name]

		logger.info("🔧 Initializing ingestor...")
		self.ingestor: PDFIngestor = ingestor_cls()  # type: ignore[call-arg]
		logger.info("✅ Ingestor initialized")
		
		logger.info("🔧 Initializing propositioner...")
		self.propositioner: T5Propositioner = prop_cls()  # type: ignore[call-arg]
		logger.info("✅ Propositioner initialized")
		
		logger.info("🔧 Initializing embedding model...")
		self.embedding: E5SmallEmbedding = emb_cls()  # type: ignore[call-arg]
		logger.info("✅ Embedding model initialized")
		
		logger.info("🔧 Initializing semantic chunker...")
		self.chunker: SemanticChunker = CHUNKERS[chunker_name](self.propositioner, self.embedding)
		logger.info("✅ Semantic chunker initialized")
		
		logger.info("🔧 Initializing storage setup...")
		self.storage_setup = StorageSetup(
			embedding=self.embedding,
			qdrant_host=default_qdrant_host,
			qdrant_port=default_qdrant_port,
			collection_name=default_collection_name
		)
		logger.info("✅ Storage setup initialized")
		
		self.index: Optional[VectorStoreIndex] = None
		logger.info("✅ DataPreprocessSemantic pipeline fully initialized")

	def run_single_doc(self, file_path: str) -> Dict[str, Any]:
		"""Process a single document and return result"""
		logger.info(f"📄 Starting run_single_doc() for: {os.path.basename(file_path)}")
		logger.info(f"📍 Full path: {file_path}")
		
		try:
			# Ingest the single document
			logger.info(f"📖 Ingesting document: {os.path.basename(file_path)}")
			resp = self.ingestor.ingest(type("Req", (), {"path_or_url": file_path, "media_type": "pdf"})())
			logger.info(f"✅ Ingestion complete: {len(resp.items)} items extracted")
			
			if not resp.items or not any(item.text.strip() for item in resp.items):
				logger.warning(f"⚠️ No content extracted from document: {os.path.basename(file_path)}")
				return {
					"success": False,
					"error": "No content extracted from document",
					"file_path": file_path,
					"character_count": 0
				}
			
			total_chars = sum(item.len_characters for item in resp.items)
			logger.info(f"📊 Document stats: {total_chars} total characters across {len(resp.items)} items")
			
			# Process chunks for this single document
			logger.info(f"🔪 Starting semantic chunking for: {os.path.basename(file_path)}")
			chunk_request = ChunkRequest(
				items=[ChunkItem(source=i.source, len_characters=i.len_characters, text=i.text) for i in resp.items]
			)
			chunk_response: ChunkResponse = self.chunker.chunk(chunk_request)
			logger.info(f"✅ Chunking complete: {len(chunk_response.chunks) if chunk_response.chunks else 0} chunks generated")
			
			# Build parent texts dict
			logger.info("🏗️ Building parent texts dictionary...")
			parent_texts: Dict[str, str] = {}
			for item in resp.items:
				source = item.source
				if source not in parent_texts:
					parent_texts[source] = item.text
			logger.info(f"✅ Parent texts built for {len(parent_texts)} unique sources")
			
			# Build nodes and write to Qdrant
			if chunk_response.chunks:
				logger.info(f"🔨 Building nodes from {len(chunk_response.chunks)} chunks...")
				leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
					chunk_response.chunks, parent_texts
				)
				node_count = len(leaf_nodes)
				logger.info(f"✅ Built {node_count} leaf nodes and {len(parent_docs)} parent documents")
				
				# Write to Qdrant (no retry needed - better concurrent write support)
				logger.info(f"💾 Writing {node_count} nodes to Qdrant...")
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
				"node_count": node_count
			}
			logger.info(f"✅ run_single_doc() completed successfully for: {os.path.basename(file_path)}")
			logger.info(f"📊 Final stats: {result['character_count']} chars, {result['chunk_count']} chunks, {result['node_count']} nodes")
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
				"character_count": 0
			}
	

data_preprocess_semantic_config = {
	"chunker": "semantic_chunking",
	"ingestor": "pdf",
	"embedding": "e5-small",
	"propositioner": "t5-propositioner",
}

data_preprocess_semantic_pipeline = DataPreprocessSemantic(config=data_preprocess_semantic_config)
# Export alias expected by router
