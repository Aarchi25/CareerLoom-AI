import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Create Gemini client safely
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

RESPONSE_STYLE = """
You are CareerLoom AI, an expert AI career advisor and mentor.
Answer the user briefly, concisely, and clearly by default.
Give only the key, high-impact points needed to answer their question directly.

LANGUAGE & SCRIPT MATCHING RULES (STRICT):
1. Always match the exact language and script style used by the user.
2. If the user writes in Hinglish (Hindi written using English/Latin alphabet, e.g., "btao mai kya kru", "kaise start kare", "kya roadmap hai"):
   - ALWAYS reply in natural, fluent Hinglish using the English/Latin alphabet.
   - DO NOT output Devanagari Hindi script (हिंदी / देवनागरी) when the user writes in Hinglish.
3. If the user writes in English, reply in English.
4. If the user writes in Devanagari Hindi script (हिंदी), reply in Devanagari Hindi script.
"""


def get_response(chat_history):
    """
    Send the complete conversation history to Gemini
    and return the AI response.
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=chat_history,
        config={
            "system_instruction": RESPONSE_STYLE
        }
    )
    return response.text