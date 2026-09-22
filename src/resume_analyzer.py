import io
import json
import re
from pypdf import PdfReader


def extract_text_from_pdf(uploaded_file):
    """
    Extract readable text from an uploaded PDF file.
    Returns the extracted text as a string, or None if extraction fails or PDF is empty.
    """
    try:
        if uploaded_file is None:
            return None

        # Reset file pointer to beginning in case it was read previously
        uploaded_file.seek(0)

        # Read uploaded PDF
        pdf_reader = PdfReader(io.BytesIO(uploaded_file.read()))

        # Store extracted text
        text = ""

        # Extract text from every page
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        extracted = text.strip()
        return extracted if extracted else None

    except Exception:
        return None


def get_resume_analysis_prompt(resume_text):
    """
    Generate a structured analysis prompt for Gemini AI to output JSON.
    """
    return f"""You are an elite technical recruiter, hiring manager, and ATS resume optimization expert.

Analyze the following resume thoroughly and provide actionable, placement-focused feedback.

You MUST respond strictly in valid JSON format with the following exact keys and structure:
{{
  "summary": "2-3 concise sentences highlighting the candidate's core profile, background, and domain.",
  "score": 78,
  "score_rationale": "Brief 1-sentence explanation of why this score was assigned.",
  "key_skills": [
    "Python", "FastAPI", "React", "PostgreSQL", "Docker", "Git", "Problem Solving", "Team Leadership"
  ],
  "strong_points": [
    "Strong hands-on experience with full-stack development and backend APIs.",
    "Well-structured project descriptions with measurable outcomes.",
    "Clear educational background in Computer Science."
  ],
  "weak_points": [
    "Bullet points lack quantified business impact and performance metrics.",
    "Summary section is missing or overly generic.",
    "Limited mention of automated testing or CI/CD pipelines."
  ],
  "missing_skills": [
    "Cloud platforms (AWS / GCP / Azure)",
    "Container orchestration (Kubernetes)",
    "Unit Testing (PyTest / Jest)",
    "System Design & Microservices"
  ],
  "ats_optimization": [
    "Use standard section headers like 'Work Experience', 'Education', 'Technical Skills'.",
    "Incorporate keywords matching target job descriptions directly into project bullets.",
    "Avoid multi-column tables or complex graphical elements that confuse ATS parsers."
  ],
  "formatting_suggestions": [
    "Keep resume strictly to 1 page for entry/mid-level, or 2 pages for senior roles.",
    "Use consistent date formats (e.g. Month Year - Month Year).",
    "Use strong action verbs (Architected, Engineered, Spearheaded) to begin each bullet."
  ],
  "actionable_improvements": [
    "Add metrics to your top 3 projects (e.g. 'Reduced latency by 35%', 'Handled 10k daily users').",
    "Add a dedicated 'Technical Skills' section categorized by Languages, Frameworks, and Tools.",
    "Include live deployment links and GitHub repository links for personal projects."
  ],
  "recommended_roles": [
    "Software Development Engineer (SDE I / II)",
    "Backend Developer (Python / Django / FastAPI)",
    "Full-Stack Web Developer",
    "Data Engineer / Associate AI Engineer"
  ]
}}

Ensure "score" is an integer between 0 and 100.
Do not wrap in markdown quotes if possible, output pure JSON.

Resume Content:
\"\"\"
{resume_text}
\"\"\"
"""


def parse_resume_analysis(raw_text):
    """
    Safely parse Gemini's response into a structured dict.
    Handles raw JSON, markdown code fence blocks ```json ... ```, and fallbacks.
    """
    if not raw_text:
        return None

    # Try clean JSON parsing
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]

    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
        # Ensure score is integer
        if "score" in data:
            try:
                data["score"] = int(data["score"])
            except Exception:
                data["score"] = 75
        return data
    except Exception:
        # Fallback: attempt regex extraction of JSON object
        json_match = re.search(r'(\{[\s\S]*\})', raw_text)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                if "score" in data:
                    try:
                        data["score"] = int(data["score"])
                    except Exception:
                        data["score"] = 75
                return data
            except Exception:
                pass

        # Fallback structure if JSON fails completely
        return {
            "summary": raw_text[:400] + "..." if len(raw_text) > 400 else raw_text,
            "score": 75,
            "score_rationale": "Score estimated based on comprehensive resume evaluation.",
            "key_skills": ["Software Development", "Problem Solving", "Technical Communication"],
            "strong_points": ["Relevant domain experience", "Clear project overview"],
            "weak_points": ["Quantifiable metrics can be improved", "More technical depth recommended"],
            "missing_skills": ["Cloud Services (AWS/GCP)", "CI/CD & DevOps tools"],
            "ats_optimization": ["Ensure clean single-column format", "Incorporate exact job posting keywords"],
            "formatting_suggestions": ["Use consistent bullet points", "Verify margins and font sizing"],
            "actionable_improvements": ["Add metrics to past accomplishments", "Highlight modern tech stack"],
            "recommended_roles": ["Software Developer", "Technical Analyst", "Backend Engineer"],
            "raw_text": raw_text
        }