from abc import ABC, abstractmethod
from .schemas import EmbeddingInput, EmbeddingOutput

class BaseEmbedding(ABC):
    def __init__(self, embedding_size: int, embedding_name: str, weights_path: str):
        self.embedding_size = embedding_size
        self.embedding_name = embedding_name
        self.weights_path = weights_path

    @abstractmethod
    def embed(self, input_data: EmbeddingInput, *args, **kwargs) -> EmbeddingOutput:
        """
        Computes embeddings for input documents (returns embedding output schema).
        """
        pass

    @abstractmethod
    def load(self, weights_path: str):
        """
        Loads or downloads the model/embedding to the given path. Must be implemented by subclasses.
        """
        pass
