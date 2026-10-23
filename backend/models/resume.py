from typing import List, Optional
from pydantic import BaseModel


class ResumeAnalysisResponse(BaseModel):
    ats_score: int
    summary: str
    strengths: List[str]
    improvements: List[str]
    missing_keywords: List[str]
    extracted_text_preview: Optional[str] = None
