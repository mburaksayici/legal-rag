from abc import ABC, abstractmethod
from .schemas import ChunkRequest, ChunkResponse

class BasePropositioner(ABC):
	def __init__(self, name: str):
		self.name = name

	@abstractmethod
	def load(self):
		"""Load or prepare underlying model/resources."""
		pass

	@abstractmethod
	def propose(self, request: ChunkRequest) -> ChunkResponse:
		"""
		Transform input items into propositions and return them as chunks
		(ChunkResponse) with fields: source, len_characters, text.
		"""
		pass
