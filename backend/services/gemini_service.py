import os
from typing import List, Optional
from google import genai
from backend.config import settings
from backend.models.chat import ChatMessageItem

RESPONSE_STYLE = """
You are CareerLoom AI, an expert AI career advisor and mentor.
Answer the user briefly, concisely, and clearly by default.
Give only the key, high-impact points needed to answer their question directly.

LANGUAGE & SCRIPT MATCHING RULES (STRICT):
1. Always match the exact language and script style used by the user.
2. If the user writes in Hinglish (Hindi written using English/Latin alphabet, e.g., "btao mai kya kru", "kaise start kare", "kya roadmap hai", "konsi skills chahiye"):
   - ALWAYS reply in natural, fluent Hinglish using the English/Latin alphabet (e.g., "DevOps Engineer banne ke liye ye key steps follow karein: ...").
   - DO NOT output Devanagari Hindi script (हिंदी / देवनागरी) when the user writes in Hinglish.
3. If the user writes in English, reply in English.
4. If the user writes in Devanagari Hindi script (हिंदी), reply in Devanagari Hindi script.

RESPONSE LENGTH & TONE:
- For normal questions, keep the answer structured around 3-6 crisp bullet points or 1-2 focused paragraphs.
- Maintain an encouraging, friendly, and professional mentor tone.
"""

_client = None


def get_gemini_client():
    global _client
    if _client is not None:
        return _client
    if not settings.GEMINI_API_KEY:
        return None
    try:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
        return _client
    except Exception as e:
        print(f"[Gemini Client Init Error] {e}")
        return None


def generate_career_response(prompt: str, history: Optional[List[ChatMessageItem]] = None) -> str:
    """Generate career mentorship response using Gemini 2.5 Flash."""
    client = get_gemini_client()
    if not client:
        return "⚠️ Gemini API key is not configured. Please set GEMINI_API_KEY in .env."

    contents = []
    if history:
        for item in history:
            role = "user" if item.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": item.content}]
            })

    contents.append({
        "role": "user",
        "parts": [{"text": prompt}]
    })

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={"system_instruction": RESPONSE_STYLE}
        )
        return response.text if response.text else "No response generated."
    except Exception as e:
        return f"Error communicating with Gemini AI: {str(e)}"
