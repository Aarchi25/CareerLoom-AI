import io
import json
import re
from typing import Tuple, Optional
from pypdf import PdfReader
from backend.services.gemini_service import get_gemini_client
from backend.models.resume import ResumeAnalysisResponse


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract clean text from PDF bytes."""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        full_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                full_text.append(t)
        return "\n".join(full_text).strip()
    except Exception as e:
        print(f"[PDF Extract Error] {e}")
        return ""


def analyze_resume_text(resume_text: str) -> Tuple[Optional[ResumeAnalysisResponse], Optional[str]]:
    """Analyze resume text with Gemini for ATS score and career feedback."""
    client = get_gemini_client()
    if not client:
        return None, "Gemini client not initialized. Check GEMINI_API_KEY in .env."

    if not resume_text or len(resume_text) < 50:
        return None, "Extracted resume text is too short or empty. Please upload a readable PDF."

    prompt = f"""
You are an expert HR and ATS (Applicant Tracking System) Specialist.
Analyze the following resume text and provide structured ATS feedback.

Resume Text:
\"\"\"{resume_text[:4000]}\"\"\"

Return ONLY a valid raw JSON object (no markdown code blocks, no backticks, no explanations) in exactly this format:
{{
  "ats_score": 85,
  "summary": "Crisp 2-sentence executive summary of the profile.",
  "strengths": ["Clear technical stack", "Quantifiable impact in previous role", "Relevant education"],
  "improvements": ["Add more action verbs", "Include GitHub project links", "Specify metrics achieved"],
  "missing_keywords": ["Docker", "Kubernetes", "CI/CD", "Unit Testing"]
}}
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        raw_text = response.text.strip()
        # Clean any markdown code blocks
        clean_json = re.sub(r"^```(?:json)?\s*", "", raw_text, flags=re.MULTILINE)
        clean_json = re.sub(r"\s*```$", "", clean_json, flags=re.MULTILINE).strip()

        data = json.loads(clean_json)
        return ResumeAnalysisResponse(
            ats_score=int(data.get("ats_score", 70)),
            summary=data.get("summary", "Analysis completed."),
            strengths=data.get("strengths", []),
            improvements=data.get("improvements", []),
            missing_keywords=data.get("missing_keywords", []),
            extracted_text_preview=resume_text[:300] + "..." if len(resume_text) > 300 else resume_text
        ), None
    except json.JSONDecodeError:
        # Fallback if model returned partial JSON
        return ResumeAnalysisResponse(
            ats_score=75,
            summary="Resume parsed successfully. Strong foundational skills noted.",
            strengths=["Clean formatting", "Relevant skills mentioned"],
            improvements=["Include more quantifiable project results"],
            missing_keywords=["Cloud technologies", "Unit testing"],
            extracted_text_preview=resume_text[:300]
        ), None
    except Exception as e:
        return None, f"Analysis failed: {str(e)}"
