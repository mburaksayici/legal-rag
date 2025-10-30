from pydantic import BaseModel
from typing import List

class ChunkItem(BaseModel):
	source: str
	len_characters: int
	text: str

class ChunkRequest(BaseModel):
	items: List[ChunkItem]

class ChunkResponse(BaseModel):
	chunks: List[ChunkItem]
