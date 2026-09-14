import os
import streamlit as st
from dotenv import load_dotenv
from google import genai

from resume_analyzer import extract_text_from_pdf
from database import create_user, authenticate_user

# Load environment variables
load_dotenv()

# Get Gemini API key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# Response style instruction
RESPONSE_STYLE = """
Answer the user briefly and clearly by default.
Give only the key points needed to answer the question.

Do NOT give long explanations unless the user asks for:
- detailed explanation
- in-depth explanation
- more details
- explain fully
- elaborate
- step-by-step explanation
- examples in detail

If the user asks for more detail, then provide a thorough and well-structured explanation.

For normal questions, keep the answer around 3-6 short points or a short paragraph.
"""

if not GEMINI_API_KEY:
    st.error("GEMINI_API_KEY not found. Please check your .env file.")
    st.stop()


# Create a new Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)
# Initialize login state
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

# Streamlit page configuration
st.set_page_config(
    page_title="AI Career Assistant",
    page_icon="🤖",
    layout="wide"
)

# ---------------- LOGIN / SIGNUP ----------------

if not st.session_state.logged_in:

    st.title("🤖 AI Career Assistant")

    login_tab, signup_tab = st.tabs(["🔑 Login", "📝 Sign Up"])

    # ---------- LOGIN ----------
    with login_tab:

        st.subheader("Login")

        email = st.text_input(
            "Email",
            key="login_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login"):

            user = authenticate_user(
                email,
                password
            )

            if user:

                st.session_state.logged_in = True
                st.session_state.username = user["username"]

                st.success("Login successful!")

                st.rerun()

            else:

                st.error(
                    "Invalid email or password."
                )

    # ---------- SIGN UP ----------
    with signup_tab:

        st.subheader("Create Account")

        username = st.text_input(
            "Username",
            key="signup_username"
        )

        email = st.text_input(
            "Email",
            key="signup_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="signup_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="confirm_password"
        )

        if st.button("Create Account"):

            if not username or not email or not password:

                st.error(
                    "Please fill all fields."
                )

            elif password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            else:

                success = create_user(
                    username,
                    email,
                    password
                )

                if success:

                    st.success(
                        "Account created successfully! Please login."
                    )

                else:

                    st.error(
                        "An account with this email already exists."
                    )

    st.stop()

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []


# Sidebar
# Sidebar
with st.sidebar:

    st.title("🤖 AI Career Assistant")
    st.write(f"👤 Welcome, {st.session_state.username}")

    if st.button("🚪 Logout"):

        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.chat_history = []

        st.rerun()

    st.divider()
    page = st.radio(
        "Choose a feature:",
        [
            "💬 Career Chatbot",
            "📄 Resume Analyzer"
        ]
    )

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

    st.divider()

    # Resume Analyzer
    st.subheader("📄 Resume Analyzer")

    uploaded_resume = st.file_uploader(
        "Upload your resume",
        type=["pdf", "docx", "txt"]
    )

    if uploaded_resume:
        st.success("Resume uploaded successfully!")

    st.divider()

    # Clear Chat
    if st.button("🗑️ Clear Chat"):

        st.session_state.chat_history = []

        st.rerun()


# Main page
if page == "💬 Career Chatbot":

    st.title("💬 Career Assistant")

    st.caption(
        "Powered by Google Gemini AI"
    )

    # Display previous messages
    for message in st.session_state.chat_history:

        with st.chat_message(message["role"]):

            st.markdown(message["content"])


    # Chat input
    user_prompt = st.chat_input(
        "Ask me anything about your career..."
    )


    if user_prompt:

        # Add user message
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


                    response = client.models.generate_content(
                      model="gemini-2.5-flash",
                      contents=contents,
                      config={
                        "system_instruction": RESPONSE_STYLE
                     }
                    )


                assistant_response = response.text


                st.markdown(
                    assistant_response
                )


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
if page == "📄 Resume Analyzer":

    st.title("📄 AI Resume Analyzer")

    st.write(
        "Upload your resume and get AI-powered feedback."
    )


    # Upload resume
    uploaded_file = st.file_uploader(
        "Upload your resume",
        type=["pdf"]
    )


    if uploaded_file:

        st.success(
            f"Uploaded: {uploaded_file.name}"
        )


        # Analyze button
        if st.button(
            "🔍 Analyze Resume"
        ):

            with st.spinner(
                "Analyzing your resume..."
            ):

                # Extract resume text
                resume_text = extract_text_from_pdf(
                    uploaded_file
                )


                # Check extracted text
                if not resume_text:

                    st.error(
                        "Could not extract text from the PDF."
                    )

                    st.stop()


                # Create prompt
                prompt = f"""
You are an expert resume reviewer and career advisor.

Analyze the following resume.

Provide the following sections:

1. Resume Summary
2. Overall Resume Score out of 100
3. Key Skills Detected
4. Strong Points
5. Weak Points
6. Missing or Recommended Skills
7. ATS Optimization Suggestions
8. Formatting Suggestions
9. Actionable Improvements
10. Recommended Career Roles

Be specific and practical.

Resume:

{resume_text}
"""


                # Send to Gemini
                response = client.models.generate_content(

                    model="gemini-2.5-flash",

                    contents=prompt
                )


                # Display results
                st.subheader(
                    "📊 Resume Analysis"
                )

                st.markdown(
                    response.text
                )