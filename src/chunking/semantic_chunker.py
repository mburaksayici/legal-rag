import os
import re
from typing import List, Tuple


import torch
import torch.nn.functional as F
import spacy
from spacy.lang.en import English


from .base import BaseChunker
from .schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.propositioner.base import BasePropositioner
from src.embeddings.base import BaseEmbedding
from src.embeddings.schemas import EmbeddingInput

# LangChain splitters
from langchain_text_splitters import RecursiveCharacterTextSplitter, NLTKTextSplitter, SpacyTextSplitter  # type: ignore


class SemanticChunker(BaseChunker):
	"""Chunk text via propositioning + semantic breakpoints.

	Pipeline per document:
	1) Run propositioner to get atomic statements.
	2) Split using LangChain: paragraphs first, then sentences within paragraphs.
	3) Group sentences (buffer) and embed.
	4) Compute cosine distances between adjacent groups.
	5) Choose breakpoints via simple percentile threshold.
	6) Join sentences between breakpoints into final chunks.
	"""

	def __init__(
		self,
		propositioner: BasePropositioner,
		embeddings: BaseEmbedding,
		buffer_size: int = 1,
		sentence_split_regex: str = r"(?<=[.?!])\s+",
		breakpoint_percentile: float = 85.0,
	):
		super().__init__(name="semantic_chunker")
		self.propositioner = propositioner
		self.embeddings = embeddings
		self.buffer_size = max(1, int(buffer_size))
		self.sentence_split_regex = sentence_split_regex
		self.breakpoint_percentile = float(breakpoint_percentile)
		self.sentence_split_nlp = spacy.load('en_core_web_sm')

	def chunk(self, request: ChunkRequest) -> ChunkResponse:
		all_chunks: List[ChunkItem] = []
		for item in request.items:
			proposed = self._propositionize_item(item)
			# Flatten propositions text for this item
			proposition_text = " ".join([c.text for c in proposed])
			sentences = self._langchain_split_to_sentences(proposition_text)
			if len(sentences) <= 1:
				# trivial case
				text = sentences[0] if sentences else proposition_text
				all_chunks.append(ChunkItem(source=item.source, len_characters=len(text), text=text))
				continue

			grouped = self._combine_with_buffer(sentences, self.buffer_size)
			embeddings_tensor = self._embed_texts([g["combined_sentence"] for g in grouped])
			# attach for clarity
			for i in range(len(grouped)):
				grouped[i]["embedding"] = embeddings_tensor[i]

			distances = self._cosine_distances_adjacent(embeddings_tensor)
			threshold = self._percentile_threshold(distances, self.breakpoint_percentile)
			break_indices = [i for i, d in enumerate(distances) if d > threshold]

			# Build chunks by breakpoints (operate over original sentences via grouped map)
			chunks_for_doc = self._slice_by_breakpoints(sentences, grouped, break_indices)
			for ch in chunks_for_doc:
				all_chunks.append(ChunkItem(source=item.source, len_characters=len(ch), text=ch))

		return ChunkResponse(chunks=all_chunks)

	def _propositionize_item(self, item: ChunkItem) -> List[ChunkItem]:
		# Runs propositioner on a single-item request
		req = ChunkRequest(items=[item])
		resp = self.propositioner.propose(req)
		return resp.chunks

	def _langchain_split_to_sentences(self, text: str) -> List[str]:
		if not text:
			return []
		#paragraphs = self._split_paragraphs(text)
		# If paragraph splitter yields nothing, treat whole text as one paragraph
		#if not paragraphs:
		#	paragraphs = [text]
		#	paragraphs = [text]
		sentences: List[str] = []
		#for para in paragraphs:
			# Prefer spaCy splitter if available
		if SpacyTextSplitter is not None:
			try:
				#text=text.replace("\n", " ")
				sentences.extend([ str(s) for s  in self.sentence_split_nlp(text).sents])
			except Exception:
				pass
		# sentences.extend([s for s in re.split(self.sentence_split_regex, text) if s and s.strip()])
		return sentences

	def _split_paragraphs(self, text: str) -> List[str]:
		if RecursiveCharacterTextSplitter is None:
			# Fallback: naive paragraph split on double newline
			return [p for p in text.split("\n\n") if p.strip()]
		splitter = RecursiveCharacterTextSplitter(
			separators=["\n\n"],
			chunk_size=1000000,
			chunk_overlap=0,
		)
		return splitter.split_text(text)

	def _combine_with_buffer(self, sentences: List[str], buffer_size: int) -> List[dict]:
		combined: List[dict] = []
		for idx, s in enumerate(sentences):
			start = max(0, idx - buffer_size)
			end = min(len(sentences), idx + buffer_size + 1)
			group = sentences[start:end]
			combined.append({"sentence": s, "index": idx, "combined_sentence": " ".join(group)})
		return combined

	def _embed_texts(self, texts: List[str]) -> torch.Tensor:
		out = self.embeddings.embed(EmbeddingInput(documents=texts))
		# Convert to torch tensor (N, D)
		return torch.tensor(out.embeddings, dtype=torch.float32)

	def _cosine_distances_adjacent(self, embeddings: torch.Tensor) -> List[float]:
		# Normalize
		normed = F.normalize(embeddings, p=2, dim=1)
		# Similarity between consecutive vectors
		cos_sims: List[float] = []
		for i in range(len(normed) - 1):
			cos = float((normed[i] * normed[i + 1]).sum().item())
			cos_sims.append(cos)
		# Convert to distances
		return [1.0 - s for s in cos_sims]

	def _percentile_threshold(self, distances: List[float], percentile: float) -> float:
		if not distances:
			return 1.0
		dist_tensor = torch.tensor(distances, dtype=torch.float32)
		q = torch.quantile(dist_tensor, min(max(percentile / 100.0, 0.0), 1.0))
		return float(q.item())

	def _slice_by_breakpoints(self, sentences: List[str], grouped: List[dict], break_indices: List[int]) -> List[str]:
		chunks: List[str] = []
		# Map from grouped index to original sentence index
		# We will slice based on breakpoints in grouped pairs (between i and i+1)
		start_idx = 0
		for idx in break_indices:
			end_idx = idx + 1  # inclusive end in grouped space
			# Map to sentences indices covered by groups [start_idx, end_idx]
			left = grouped[start_idx]["index"]
			right = grouped[end_idx]["index"]
			segment = sentences[left:right + 1]
			chunks.append(" ".join(segment))
			start_idx = end_idx + 1
		# Tail
		if start_idx < len(grouped):
			left = grouped[start_idx]["index"]
			right = grouped[-1]["index"]
			segment = sentences[left:right + 1]
			if segment:
				chunks.append(" ".join(segment))
		return chunks
