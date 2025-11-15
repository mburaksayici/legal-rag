import torch
import torch.nn.functional as F
from torch import Tensor
from transformers import AutoTokenizer, AutoModel
from .base import BaseEmbedding
from .schemas import EmbeddingInput, EmbeddingOutput
from src.config import EMBEDDING_WEIGHTS_DIR
import os

class E5SmallEmbedding(BaseEmbedding):
    def __init__(self):
        name = 'intfloat/multilingual-e5-small'
        weights_folder = os.path.join(EMBEDDING_WEIGHTS_DIR, self.__class__.__name__.lower())
        super().__init__(
            embedding_size=384,
            embedding_name=name,
            weights_path=weights_folder,
            max_tokens=512,
        )
        self.model = None
        self.tokenizer = None
        self.device = None
        self.is_loaded = False

    def load(self, weights_path: str = None):
        """
        Loads the tokenizer and model for E5-small from a given directory.
        """
        if weights_path is None:
            weights_path = self.weights_path
        os.makedirs(weights_path, exist_ok=True)
        self.tokenizer = AutoTokenizer.from_pretrained(self.embedding_name, cache_dir=weights_path)
        self.model = AutoModel.from_pretrained(self.embedding_name, cache_dir=weights_path)
        
        # Set device: CUDA > MPS > CPU
        self.device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )
        self.model = self.model.to(self.device)
        self.is_loaded = True

    def embed(self, input_data: EmbeddingInput, *args, **kwargs) -> EmbeddingOutput:
        if not self.is_loaded:
            self.load()
        texts = input_data.documents
        batch_dict = self.tokenizer(texts, max_length=512, padding=True, truncation=True, return_tensors='pt')
        
        # Move input tensors to device
        batch_dict = {k: v.to(self.device) for k, v in batch_dict.items()}
        
        outputs = self.model(**batch_dict)
        embeddings = self.average_pool(outputs.last_hidden_state, batch_dict['attention_mask'])
        embeddings = F.normalize(embeddings, p=2, dim=1)
        embedding_list = embeddings.detach().cpu().tolist()
        return EmbeddingOutput(embeddings=embedding_list)

    @staticmethod
    def average_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
        last_hidden = last_hidden_states.masked_fill(~attention_mask[..., None].bool(), 0.0)
        return last_hidden.sum(dim=1) / attention_mask.sum(dim=1)[..., None]

# Usage example only:
# embedder = E5SmallEmbedding()
# embeddings = embedder.embed(input_texts)
