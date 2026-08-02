import os

from dotenv import load_dotenv
from google import genai


# Load environment variables
load_dotenv()


# Create Gemini client
client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def get_response(chat_history):
    """
    Send the complete conversation history to Gemini
    and return the AI response.
    """

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=chat_history
    )

    return response.text