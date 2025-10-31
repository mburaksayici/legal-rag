from pydantic import BaseModel
from typing import List, Optional

class QueryRequest(BaseModel):
	query: str
	top_k: Optional[int] = 6

class RetrievalResult(BaseModel):
	text: str
	source: str
	metadata: dict

class QueryResponse(BaseModel):
	results: List[RetrievalResult]

