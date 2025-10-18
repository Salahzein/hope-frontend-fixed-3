from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Lead(BaseModel):
    title: str
    subreddit: str
    snippet: str
    permalink: str
    author: str
    created_utc: float
    score: int = 0
    matched_keywords: List[str] = []
    
    # AI-enhanced fields (optional for backward compatibility)
    ai_relevance_score: Optional[int] = Field(None, description="AI-calculated relevance score (0-100)")
    urgency_level: Optional[str] = Field(None, description="Urgency level: High, Medium, Low")
    business_context: Optional[str] = Field(None, description="Detected business type/context")
    problem_category: Optional[str] = Field(None, description="Category of problem identified")
    ai_summary: Optional[str] = Field(None, description="AI-generated summary of the post")
