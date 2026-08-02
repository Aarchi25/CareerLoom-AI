import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY not found. Please check your .env file.")
    st.stop()


# Create a new Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


# Streamlit page configuration
st.set_page_config(
    page_title="AI Career Assistant",
    page_icon="🤖",
    layout="wide"
)


# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# Sidebar
with st.sidebar:

    st.title("🤖 AI Career Assistant")

    st.write(
        "Your personal AI-powered career companion."
    )

    st.write("Use this assistant to:")

    st.markdown("""
    - Learn new technologies
    - Prepare for interviews
    - Improve your resume
    - Plan your career
    """)

    if st.button("🗑️ Clear Chat"):

        st.session_state.chat_history = []

        st.rerun()


# Main page
st.title("💬 Career Assistant")

st.caption("Powered by Google Gemini AI")


# Display previous messages
for message in st.session_state.chat_history:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])


# Chat input
user_prompt = st.chat_input(
    "Ask me anything about your career..."
)


if user_prompt:

    # Add user message to history
    st.session_state.chat_history.append(
        {
            "role": "user",
            "content": user_prompt
        }
    )


    # Display user message
    with st.chat_message("user"):

        st.markdown(user_prompt)


    # Generate AI response
    with st.chat_message("assistant"):

        try:

            # Create Gemini-compatible conversation history
            contents = []

            for message in st.session_state.chat_history:

                if message["role"] == "user":

                    contents.append(
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "text": message["content"]
                                }
                            ]
                        }
                    )

                elif message["role"] == "assistant":

                    contents.append(
                        {
                            "role": "model",
                            "parts": [
                                {
                                    "text": message["content"]
                                }
                            ]
                        }
                    )


            # Send request to Gemini
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents
            )


            # Get response text
            assistant_response = response.text


            # Display response
            st.markdown(assistant_response)


            # Save assistant response
            st.session_state.chat_history.append(
                {
                    "role": "assistant",
                    "content": assistant_response
                }
            )


        except Exception as e:

            st.error(
                f"Something went wrong: {str(e)}"
            )