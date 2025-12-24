from pydantic import BaseModel
from typing import List

class Recommendation(BaseModel):
    label: str
    description: str

class RecommendationsResponse(BaseModel):
    recommendations: List[Recommendation]