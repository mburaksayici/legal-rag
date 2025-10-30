from abc import ABC, abstractmethod
from .schemas import ChunkRequest, ChunkResponse

class BaseChunker(ABC):
	def __init__(self, name: str):
		self.name = name

	@abstractmethod
	def chunk(self, request: ChunkRequest) -> ChunkResponse:
		"""
		Implement chunking logic producing chunks with fields: source, len_characters, text.
		"""
		pass
