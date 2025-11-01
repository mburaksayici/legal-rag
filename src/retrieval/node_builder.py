from typing import List, Dict
import uuid
from llama_index.core.schema import TextNode, Document  # type: ignore
from src.chunking.schemas import ChunkItem


class NodeBuilder:
	"""Build LlamaIndex nodes from chunks with parent-child relationships."""

	@staticmethod
	def build_nodes_from_chunks(chunks: List[ChunkItem], parent_texts: Dict[str, str]) -> tuple[List[TextNode], List[Document]]:
		"""
		Build leaf nodes from chunks and parent documents.
		
		Args:
			chunks: List of chunk items with source, text, etc.
			parent_texts: Dict mapping source -> full document text for parent nodes
		
		Returns:
			tuple of (leaf_nodes, parent_documents)
		"""
		leaf_nodes: List[TextNode] = []
		parent_docs: List[Document] = []
		source_to_doc_id: Dict[str, str] = {}

		# Group chunks by source and assign UUID-based doc_id for Qdrant compatibility
		sources_seen = set()
		for chunk in chunks:
			source = chunk.source
			if source not in sources_seen:
				sources_seen.add(source)
				doc_id = str(uuid.uuid4())  # Use UUID instead of string for Qdrant
				source_to_doc_id[source] = doc_id

		# Create parent documents
		for source, doc_id in source_to_doc_id.items():
			parent_text = parent_texts.get(source, "")
			if parent_text:
				parent_doc = Document(
					id_=doc_id,
					text=parent_text,
				)
				parent_docs.append(parent_doc)

		# Create leaf nodes with parent relationships
		for idx, chunk in enumerate(chunks):
			source = chunk.source
			doc_id = source_to_doc_id.get(source, str(uuid.uuid4()))
			
			leaf_node = TextNode(
				text=chunk.text,
				id_=str(uuid.uuid4()),  # Use UUID instead of string for Qdrant
				parent_id=doc_id,
			)
			# Store metadata
			leaf_node.metadata = {
				"source": source,
				"chunk_index": idx,
				"len_characters": chunk.len_characters,
			}
			leaf_nodes.append(leaf_node)

		return leaf_nodes, parent_docs

