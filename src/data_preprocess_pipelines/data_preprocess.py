import os
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
from src.chromadb.config import db_path

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


class DataPreprocessBase(ABC):
	@abstractmethod
	def run(self, folder_path: str) -> None:
		"""Legacy method for backward compatibility"""
		pass
	
	@abstractmethod
	def run_folder(self, folder_path: str) -> None:
		"""Process all documents in a folder"""
		pass
	
	@abstractmethod
	def run_single_doc(self, file_path: str) -> Dict[str, Any]:
		"""Process a single document and return result"""
		pass


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
		self.storage_setup = StorageSetup(embedding=self.embedding, chromadb_db_path=db_path)
		logger.info("✅ Storage setup initialized")
		
		self.index: Optional[VectorStoreIndex] = None
		logger.info("✅ DataPreprocessSemantic pipeline fully initialized")

	def run(self, folder_path: str) -> None:
		# For now we support folder paths. URI handling can be added later.
		logger.info(f"📂 Starting legacy run() method for folder: {folder_path}")
		
		pdf_files = [
			os.path.join(folder_path, f)
			for f in os.listdir(folder_path)
			if f.lower().endswith(".pdf")
		]
		logger.info(f"📄 Found {len(pdf_files)} PDF files in folder")
		
		if not pdf_files:
			logger.warning("⚠️ No PDF files found, exiting")
			return

		ingested_items: List[IngestedItem] = []
		for idx, path in enumerate(pdf_files, 1):
			logger.info(f"📖 [{idx}/{len(pdf_files)}] Ingesting: {os.path.basename(path)}")
			resp = self.ingestor.ingest(type("Req", (), {"path_or_url": path, "media_type": "pdf"})())
			logger.info(f"✅ [{idx}/{len(pdf_files)}] Ingested {len(resp.items)} items from {os.path.basename(path)}")
			ingested_items.extend(resp.items)

		logger.info(f"📦 Total ingested items: {len(ingested_items)}")
		logger.info("🔪 Starting semantic chunking process...")
		
		chunk_request = ChunkRequest(items=[ChunkItem(source=i.source, len_characters=i.len_characters, text=i.text) for i in ingested_items])
		chunk_response: ChunkResponse = self.chunker.chunk(chunk_request)

		logger.info(f"✅ Chunking complete. Generated {len(chunk_response.chunks) if chunk_response.chunks else 0} chunks")

		if not chunk_response.chunks:
			logger.warning("⚠️ No chunks generated, exiting")
			return

		# Build parent texts dict (full text per source)
		logger.info("🏗️ Building parent texts dictionary...")
		parent_texts: Dict[str, str] = {}
		for item in ingested_items:
			source = item.source
			if source not in parent_texts:
				parent_texts[source] = item.text
		logger.info(f"✅ Built parent texts for {len(parent_texts)} unique sources")

		# Build LlamaIndex nodes
		logger.info("🔨 Building LlamaIndex nodes from chunks...")
		leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
			chunk_response.chunks, parent_texts
		)
		logger.info(f"✅ Built {len(leaf_nodes)} leaf nodes and {len(parent_docs)} parent documents")

		# Create index directly - no StorageContext needed
		logger.info("📊 Creating vector store index...")
		self.index = self.storage_setup.create_index_from_nodes(leaf_nodes)
		logger.info("✅ Vector store index created successfully")
	
	def run_folder(self, folder_path: str) -> None:
		"""Process all documents in a folder"""
		logger.info(f"📂 Starting run_folder() for: {folder_path}")
		
		pdf_files = [
			os.path.join(folder_path, f)
			for f in os.listdir(folder_path)
			if f.lower().endswith(".pdf")
		]
		logger.info(f"📄 Found {len(pdf_files)} PDF files to process")
		
		if not pdf_files:
			logger.warning("⚠️ No PDF files found in folder, exiting")
			return

		ingested_items: List[IngestedItem] = []
		for idx, path in enumerate(pdf_files, 1):
			logger.info(f"📖 [{idx}/{len(pdf_files)}] Ingesting: {os.path.basename(path)}")
			try:
				resp = self.ingestor.ingest(type("Req", (), {"path_or_url": path, "media_type": "pdf"})())
				logger.info(f"✅ [{idx}/{len(pdf_files)}] Successfully ingested {len(resp.items)} items from {os.path.basename(path)}")
				ingested_items.extend(resp.items)
			except Exception as e:
				logger.error(f"❌ [{idx}/{len(pdf_files)}] Failed to ingest {os.path.basename(path)}: {str(e)}")
				raise

		logger.info(f"📦 Total items ingested from all files: {len(ingested_items)}")
		logger.info("🔄 Proceeding to process and index documents...")
		self._process_and_index(ingested_items)
		logger.info("✅ run_folder() completed successfully")
	
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
			
			# Build nodes (but don't create index for single doc)
			if chunk_response.chunks:
				logger.info(f"🔨 Building nodes from {len(chunk_response.chunks)} chunks...")
				leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
					chunk_response.chunks, parent_texts
				)
				node_count = len(leaf_nodes)
				logger.info(f"✅ Built {node_count} leaf nodes and {len(parent_docs)} parent documents")
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
	
	def _process_and_index(self, ingested_items: List[IngestedItem]) -> None:
		"""Helper method to process chunks and create index"""
		logger.info("🔄 Starting _process_and_index()...")
		
		if not ingested_items:
			logger.warning("⚠️ No ingested items to process, exiting")
			return
			
		logger.info(f"📦 Processing {len(ingested_items)} ingested items")
		total_chars = sum(item.len_characters for item in ingested_items)
		logger.info(f"📊 Total characters to process: {total_chars:,}")
		
		logger.info("🔪 Creating chunk request...")
		chunk_request = ChunkRequest(
			items=[ChunkItem(source=i.source, len_characters=i.len_characters, text=i.text) for i in ingested_items]
		)
		
		logger.info(f"🔪 Starting semantic chunking on {len(chunk_request.items)} items...")
		chunk_response: ChunkResponse = self.chunker.chunk(chunk_request)
		logger.info(f"✅ Chunking complete: {len(chunk_response.chunks) if chunk_response.chunks else 0} chunks generated")

		if not chunk_response.chunks:
			logger.warning("⚠️ No chunks generated, cannot create index")
			return

		# Build parent texts dict (full text per source)
		logger.info("🏗️ Building parent texts dictionary...")
		parent_texts: Dict[str, str] = {}
		for item in ingested_items:
			source = item.source
			if source not in parent_texts:
				parent_texts[source] = item.text
		logger.info(f"✅ Built parent texts for {len(parent_texts)} unique sources")

		# Build LlamaIndex nodes
		logger.info(f"🔨 Building LlamaIndex nodes from {len(chunk_response.chunks)} chunks...")
		leaf_nodes, parent_docs = NodeBuilder.build_nodes_from_chunks(
			chunk_response.chunks, parent_texts
		)
		logger.info(f"✅ Built {len(leaf_nodes)} leaf nodes and {len(parent_docs)} parent documents")

		# Create index directly - no StorageContext needed
		logger.info("📊 Creating vector store index from nodes...")
		self.index = self.storage_setup.create_index_from_nodes(leaf_nodes)
		logger.info("✅ Vector store index created successfully")
		logger.info("✅ _process_and_index() completed successfully")


data_preprocess_semantic_config = {
	"chunker": "semantic_chunking",
	"ingestor": "pdf",
	"embedding": "e5-small",
	"propositioner": "t5-propositioner",
}

data_preprocess_semantic_pipeline = DataPreprocessSemantic(config=data_preprocess_semantic_config)
# Export alias expected by router
