from abc import ABC, abstractmethod
from .schemas import IngestRequest, IngestResponse

class BaseIngestor(ABC):
	def __init__(self, name: str):
		self.name = name

	@abstractmethod
	def ingest(self, request: IngestRequest) -> IngestResponse:
		"""
		Implement reading of the input path_or_url and return a list of text items
		with source and character length. Implementation deferred to subclasses.
		"""
		pass
