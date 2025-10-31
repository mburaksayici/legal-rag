from pydantic import BaseModel
from typing import List


class EnhancedQueries(BaseModel):
    """Schema for enhanced query responses from QueryEnhancerAgent."""
    enhanced_queries: List[str]
