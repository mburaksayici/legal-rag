from pydantic import BaseModel, AnyUrl
from typing import List, Optional

class IngestRequest(BaseModel):
	path_or_url: str  # can be local path or URL
	media_type: Optional[str] = None  # optional hint like 'json' or 'pdf'

class IngestedItem(BaseModel):
	source: str
	len_characters: int
	text: str

class IngestResponse(BaseModel):
	items: List[IngestedItem]
