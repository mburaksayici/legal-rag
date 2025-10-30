import os
import json
from typing import List

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # type: ignore

from .base import BasePropositioner
from .schemas import ChunkItem, ChunkRequest, ChunkResponse
from src.config import EMBEDDING_WEIGHTS_DIR

# Optional LangChain sentence splitter
try:
	from langchain_text_splitters import NLTKTextSplitter, SpacyTextSplitter  # type: ignore
except Exception:  # pragma: no cover
	NLTKTextSplitter = None  # type: ignore
	SpacyTextSplitter = None  # type: ignore

MAX_INPUT_TOKENS = 512

class T5Propositioner(BasePropositioner):
	def __init__(self, model_name: str = "chentong00/propositionizer-wiki-flan-t5-large"):
		super().__init__(name="t5_propositioner")
		self.model_name = model_name
		self.tokenizer = None
		self.model = None
		self.is_loaded = False
		self.cache_dir = os.path.join(EMBEDDING_WEIGHTS_DIR, "propositioner", self.__class__.__name__.lower())

	def load(self):
		os.makedirs(self.cache_dir, exist_ok=True)
		self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, cache_dir=self.cache_dir, use_fast=False)
		self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name, cache_dir=self.cache_dir)
		self.is_loaded = True

	def propose(self, request: ChunkRequest) -> ChunkResponse:
		if not self.is_loaded:
			self.load()
		assert self.tokenizer is not None and self.model is not None
		results: List[ChunkItem] = []
		for item in request.items:
			text = item.text or ""
			if not text:
				results.append(ChunkItem(source=item.source, len_characters=0, text=""))
				continue

			sentences = self._split_sentences(text)
			if not sentences:
				sentences = [text]

			# Pack sentences into chunks under MAX_INPUT_TOKENS; if a single sentence exceeds, keep as its own chunk
			chunk_texts: List[str] = []
			current: List[str] = []
			current_len = 0
			for s in sentences:
				ids = self.tokenizer(s, add_special_tokens=False)["input_ids"]
				sent_len = len(ids)
				if current and current_len + sent_len > MAX_INPUT_TOKENS:
					chunk_texts.append(" ".join(current))
					current = []
					current_len = 0
				if sent_len > MAX_INPUT_TOKENS:
					chunk_texts.append(s)
				else:
					current.append(s)
					current_len += sent_len
			if current:
				chunk_texts.append(" ".join(current))

			aggregated_props: List[str] = []
			device = self.model.device
			for chunk_text in chunk_texts:
				input_text = chunk_text
				input_ids = self.tokenizer(input_text, return_tensors="pt").input_ids
				outputs = self.model.generate(input_ids.to(device), max_new_tokens=512).cpu()
				out_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
				try:
					props = json.loads(out_text)
					if isinstance(props, list):
						aggregated_props.extend([str(p) for p in props])
				except Exception:
					pass

			merged_text = " ".join(aggregated_props)
			results.append(ChunkItem(source=item.source, len_characters=len(merged_text), text=merged_text))

		return ChunkResponse(chunks=results)

	def _split_sentences(self, text: str) -> List[str]:
		if NLTKTextSplitter is None:
			import re
			parts = re.split(r"(?<=[.?!])\s+", text)
			return [p.strip() for p in parts if p and p.strip()]
		splitter = NLTKTextSplitter()
		out = []
		for i in splitter.split_text(text):
			splitted_text = i.split("\n")
			splitted_text = [j for j in splitted_text if j.strip() and len(j.strip()) > 2]
			if len(splitted_text) > 2:
				out.extend(splitted_text)
		return out


		