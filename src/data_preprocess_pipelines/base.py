from abc import ABC, abstractmethod
from typing import Dict, Any

class DataPreprocessBase(ABC):	
	@abstractmethod
	def run_single_doc(self, file_path: str) -> Dict[str, Any]:
		"""Process a single document and return result"""
		pass

