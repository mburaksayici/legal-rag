from pydantic import BaseModel
from typing import List

class EmbeddingInput(BaseModel):
    documents: List[str]

class EmbeddingOutput(BaseModel):
    embeddings: List[List[float]]  # one embedding per doc
