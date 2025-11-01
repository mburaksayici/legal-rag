from pydantic import BaseModel
from typing import List, Optional


class EnhancedQueries(BaseModel):
    """Schema for enhanced query responses from QueryEnhancerAgent."""
    enhanced_queries: List[str]


class RankedDocument(BaseModel):
    """Schema for a single ranked document with relevance score."""
    index: int
    relevance_score: float
    reasoning: Optional[str] = None


class RerankedResults(BaseModel):
    """Schema for reranked document results from RerankingAgent."""
    ranked_documents: List[RankedDocument]
