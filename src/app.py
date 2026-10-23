import os
import sys
import json
import base64
import importlib
from datetime import datetime, timezone
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from google import genai

# Ensure src directory is in sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from database import (
    create_user,
    authenticate_user,
    create_conversation,
    get_user_conversations,
    get_conversation_messages,
    add_message,
    delete_conversation,
    create_session,
    get_session,
    delete_session,
    check_db_connection,
    is_mongodb_ready,
    sync_sqlite_to_mongodb
)
from resume_analyzer import extract_text_from_pdf, get_resume_analysis_prompt, parse_resume_analysis

# ---------------- CONFIGURATION & ENVIRONMENT ----------------

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Logo & Branding Assets
logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")

@st.cache_data
def get_logo_base64():
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as img_f:
            return base64.b64encode(img_f.read()).decode("utf-8")
    return ""

LOGO_B64 = get_logo_base64()

# Streamlit Page Configuration
st.set_page_config(
    page_title="CareerLoom AI",
    page_icon=logo_path if os.path.exists(logo_path) else "🧶",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load External Custom CSS
css_path = os.path.join(os.path.dirname(__file__), "styles", "custom.css")
if os.path.exists(css_path):
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Concise Career Advisor System Instructions
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


@st.cache_resource(show_spinner=False)
def get_gemini_client():
    """Create and cache Gemini Client instance safely."""
    if not GEMINI_API_KEY:
        return None
    try:
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception:
        return None


# ---------------- CLIPBOARD HELPER ----------------

def copy_to_clipboard_js(text_to_copy):
    """Trigger browser copy action via JavaScript execution."""
    escaped_text = json.dumps(text_to_copy)
    components.html(
        f"""
        <script>
        (function() {{
            const text = {escaped_text};
            if (navigator.clipboard && navigator.clipboard.writeText) {{
                navigator.clipboard.writeText(text);
            }} else {{
                const textArea = document.createElement("textarea");
                textArea.value = text;
                textArea.style.position = "fixed";
                textArea.style.opacity = "0";
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                try {{
                    document.execCommand('copy');
                }} catch (err) {{}}
                document.body.removeChild(textArea);
            }}
        }})();
        </script>
        """,
        height=0,
        width=0,
    )


# ---------------- SESSION STATE INITIALIZATION ----------------

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "user_id" not in st.session_state:
    st.session_state.user_id = ""

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_page" not in st.session_state:
    st.session_state.active_page = "💬 Career Chatbot"

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None

if "auth_tab" not in st.session_state:
    st.session_state.auth_tab = "login"

if "resume_analysis_data" not in st.session_state:
    st.session_state.resume_analysis_data = None

# AUTO-LOGIN ON REFRESH (Checks persistent session token in URL)
if not st.session_state.logged_in:
    session_token = st.query_params.get("session")
    if session_token:
        session_data = get_session(session_token)
        if session_data:
            st.session_state.logged_in = True
            st.session_state.username = session_data.get("username", "User")
            st.session_state.user_id = str(session_data.get("user_id", ""))
            st.session_state.user_email = session_data.get("email", f"{st.session_state.username.lower()}@example.com")


# ---------------- UTILITY FUNCTIONS ----------------

def generate_conversation_title(prompt_text):
    """Generate a clean conversation title from the first prompt."""
    clean = " ".join(prompt_text.strip().split())
    if len(clean) > 32:
        return clean[:29].strip() + "..."
    return clean if clean else "Career Discussion"


def switch_conversation(conv_id):
    """Switch active conversation and load its messages from MongoDB."""
    st.session_state.current_conversation_id = str(conv_id)
    messages = get_conversation_messages(conv_id)
    st.session_state.chat_history = messages
    st.session_state.active_page = "💬 Career Chatbot"
    st.session_state.pending_prompt = None


def start_new_chat():
    """Reset session state to start a clean new chat."""
    st.session_state.current_conversation_id = None
    st.session_state.chat_history = []
    st.session_state.active_page = "💬 Career Chatbot"
    st.session_state.pending_prompt = None


# ---------------- VIEW 1: AUTHENTICATION (LOGIN / SIGN UP) ----------------

if not st.session_state.logged_in:

    col1, col2, col3 = st.columns([1, 1.4, 1])

    with col2:
        st.markdown(f"""
        <div class="auth-card-container">
            <div class="auth-card-logo-wrap">
                <img src="data:image/png;base64,{LOGO_B64}" alt="CareerLoom AI Logo" />
            </div>
            <div class="auth-card-title">CareerLoom AI</div>
            <div class="auth-card-subtitle">Weaving Skills into Career Opportunities.</div>
        </div>
        """, unsafe_allow_html=True)

        login_tab, signup_tab = st.tabs(["🔑 Login", "📝 Sign Up"])

        # ---------- LOGIN TAB ----------
        with login_tab:
            st.write("")
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email address", placeholder="name@example.com", key="login_email")
                password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")
                
                col_rem, col_for = st.columns([0.55, 0.45])
                with col_rem:
                    remember_me = st.checkbox("Remember me", value=True, key="login_remember")
                with col_for:
                    st.markdown("<p style='text-align: right; font-size: 0.8rem; color: #2563EB; margin-top: 0.35rem; cursor: pointer;'>Forgot password?</p>", unsafe_allow_html=True)

                submit_login = st.form_submit_button("Login", type="primary", use_container_width=True)

                if submit_login:
                    if not email or not password:
                        st.error("Please enter both email and password.")
                    else:
                        user, err = authenticate_user(email, password)
                        if user:
                            st.session_state.logged_in = True
                            st.session_state.username = user.get("username", "User")
                            st.session_state.user_email = user.get("email", email)
                            st.session_state.user_id = str(user["_id"])
                            st.session_state.current_conversation_id = None
                            st.session_state.chat_history = []
                            st.session_state.active_page = "💬 Career Chatbot"

                            if remember_me:
                                token = create_session(str(user["_id"]), user["username"], user.get("email", email))
                                if token:
                                    st.query_params["session"] = token

                            st.rerun()
                        elif err == "DB_CONNECTION_ERROR":
                            st.error("⚠️ Database connection failed. Please ensure your IP address is whitelisted in MongoDB Atlas Network Access.")
                        else:
                            st.error("Invalid email or password.")

        # ---------- SIGN UP TAB ----------
        with signup_tab:
            st.write("")
            with st.form("signup_form", clear_on_submit=False):
                username = st.text_input("Username", placeholder="e.g. aditi", key="signup_username")
                email = st.text_input("Email address", placeholder="name@example.com", key="signup_email")
                password = st.text_input("Password", type="password", placeholder="Create password (min 6 chars)", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="confirm_password")
                submit_signup = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                if submit_signup:
                    if not username or not email or not password or not confirm_password:
                        st.error("Please fill in all fields.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password should be at least 6 characters.")
                    else:
                        new_user, err = create_user(username, email, password)
                        if new_user:
                            if is_mongodb_ready():
                                st.success("🎉 Account created in MongoDB Atlas! Please click the Login tab to sign in.")
                            else:
                                st.info("ℹ️ Account created in local storage. (MongoDB Atlas is currently unreachable). Click Login to sign in.")
                        elif err == "EMAIL_EXISTS":
                            st.error("An account with this email already exists.")
                        elif err == "DB_CONNECTION_ERROR":
                            st.error("⚠️ Database connection failed. Please check your internet connection and verify your IP is whitelisted in MongoDB Atlas.")
                        else:
                            st.error("Failed to create account. Please try again.")

        st.markdown("""
        <div class="auth-footer-tagline">
            Build your skills &nbsp;•&nbsp; Improve your resume &nbsp;•&nbsp; Achieve your goals
        </div>
        """, unsafe_allow_html=True)

        # Database Status & Cloud Sync Helper
        if not is_mongodb_ready():
            with st.expander("ℹ️ Cloud Database Status (MongoDB Atlas)", expanded=False):
                st.caption(
                    "Cloud MongoDB Atlas is currently not reachable from your network. "
                    "Accounts are safely saved in local offline mode."
                )
                st.markdown(
                    "**To enable MongoDB Atlas cloud storage:**\n"
                    "1. Open [MongoDB Atlas Dashboard](https://cloud.mongodb.com)\n"
                    "2. Go to **Security** → **Network Access**\n"
                    "3. Click **Add IP Address** → Choose **Allow Access from Anywhere** (`0.0.0.0/0`) or add your current IP.\n"
                    "4. Wait ~1 minute, then click below:"
                )
                if st.button("🔄 Sync Local Users to MongoDB Atlas", key="sync_local_to_atlas"):
                    success, msg = sync_sqlite_to_mongodb()
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    st.stop()


# ---------------- SIDEBAR NAVIGATION ----------------

with st.sidebar:
    st.markdown(f"""
    <div class="sidebar-brand">
        <img src="data:image/png;base64,{LOGO_B64}" class="sidebar-brand-logo-img" alt="CareerLoom AI" />
        <div class="sidebar-brand-title">CareerLoom AI</div>
    </div>
    """, unsafe_allow_html=True)

    # User Profile Pill
    avatar_char = st.session_state.username[0].upper() if st.session_state.username else "U"
    user_email_display = st.session_state.user_email if st.session_state.user_email else f"{st.session_state.username.lower()}@example.com"
    st.markdown(f"""
    <div class="user-profile-badge">
        <div class="user-avatar-circle">{avatar_char}</div>
        <div class="user-info-text">
            <div class="user-info-name">Hello, {st.session_state.username}</div>
            <div class="user-info-email">{user_email_display}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Feature Navigation
    nav_selection = st.radio(
        "Navigation",
        options=["💬 Career Chatbot", "📄 Resume Analyzer"],
        index=0 if st.session_state.active_page == "💬 Career Chatbot" else 1,
        label_visibility="collapsed",
        key="nav_radio"
    )
    if nav_selection != st.session_state.active_page:
        st.session_state.active_page = nav_selection
        st.rerun()

    st.markdown("<hr style='margin: 1rem 0; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Chat History
    st.markdown("<p style='font-size: 0.85rem; font-weight: 700; color: #94A3B8; margin-bottom: 0.5rem;'>Chat History</p>", unsafe_allow_html=True)

    # Primary Action: + New Chat
    if st.button("➕ New Chat", use_container_width=True, type="primary"):
        start_new_chat()
        st.rerun()

    user_conversations = get_user_conversations(st.session_state.user_id)

    if user_conversations:
        for conv in user_conversations:
            conv_id_str = str(conv["_id"])
            conv_title = conv.get("title", "Untitled Chat")
            is_active = (st.session_state.current_conversation_id == conv_id_str)

            col_title, col_del = st.columns([0.84, 0.16])

            with col_title:
                btn_label = f"💬 {conv_title}" if not is_active else f"👉 {conv_title}"
                if st.button(btn_label, key=f"conv_{conv_id_str}", use_container_width=True):
                    switch_conversation(conv_id_str)
                    st.rerun()

            with col_del:
                if st.button("🗑️", key=f"del_{conv_id_str}", help="Delete conversation"):
                    delete_conversation(conv_id_str, st.session_state.user_id)
                    if st.session_state.current_conversation_id == conv_id_str:
                        start_new_chat()
                    st.rerun()
    else:
        st.caption("No previous chats yet. Start a conversation!")

    st.markdown("<hr style='margin: 1.25rem 0; border-color: rgba(255,255,255,0.08);'>", unsafe_allow_html=True)

    # Logout Button
    if st.button("🚪 Logout", use_container_width=True):
        token = st.query_params.get("session")
        if token:
            delete_session(token)
        st.query_params.clear()
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_id = ""
        st.session_state.user_email = ""
        st.session_state.current_conversation_id = None
        st.session_state.chat_history = []
        st.session_state.active_page = "💬 Career Chatbot"
        st.session_state.pending_prompt = None
        st.rerun()


# ---------------- PAGE 1: CAREER CHATBOT ----------------

if st.session_state.active_page == "💬 Career Chatbot":

    # App Header
    st.markdown(f"""
    <div class="dashboard-header">
        <div class="dashboard-header-logo-wrap">
            <img src="data:image/png;base64,{LOGO_B64}" alt="CareerLoom AI Logo" />
        </div>
        <div class="dashboard-header-title">CareerLoom AI</div>
        <div class="dashboard-header-subtitle">Weaving Skills into Career Opportunities.</div>
    </div>
    """, unsafe_allow_html=True)

    has_chat_history = len(st.session_state.chat_history) > 0

    # 3 FEATURE TOPIC CARDS (Visible when starting fresh)
    if not has_chat_history and not st.session_state.pending_prompt:
        col_c1, col_c2, col_c3 = st.columns(3)

        with col_c1:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-header">🧭 Get career advice</div>
                <div class="feature-card-desc">Explore career paths, skills and growth opportunities.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Explore Career Paths", key="card_btn_1", use_container_width=True):
                st.session_state.pending_prompt = "What are the most promising career paths and high-demand skills for tech in 2026?"
                st.rerun()

        with col_c2:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-header">💡 Prepare for interviews</div>
                <div class="feature-card-desc">Get mock questions and answer suggestions.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Practice Mock Questions", key="card_btn_2", use_container_width=True):
                st.session_state.pending_prompt = "Give me 5 essential technical and behavioral interview questions for a Software Engineer role with sample answers."
                st.rerun()

        with col_c3:
            st.markdown("""
            <div class="feature-card">
                <div class="feature-card-header">📈 Improve your resume</div>
                <div class="feature-card-desc">Learn how to make your resume stand out.</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Resume Enhancement Tips", key="card_btn_3", use_container_width=True):
                st.session_state.pending_prompt = "How can I rewrite my resume project bullet points to make them highly impactful and ATS-friendly?"
                st.rerun()

        st.markdown("""
        <div class="start-conversation-card">
            <div class="start-conversation-icon">💬</div>
            <div class="start-conversation-title">Start a conversation</div>
            <div class="start-conversation-desc">Ask me anything about your career, interviews, resume, or skill development. I'm here to help!</div>
        </div>
        """, unsafe_allow_html=True)

    # RENDER EXISTING CHAT MESSAGES
    for idx, message in enumerate(st.session_state.chat_history):
        role = message["role"]
        content = message["content"]
        avatar = "👤" if role == "user" else "🤖"

        with st.chat_message(role, avatar=avatar):
            st.markdown(content)

            if role == "assistant":
                col_copy, col_retry, col_space = st.columns([0.15, 0.15, 0.7])
                with col_copy:
                    if st.button("📋 Copy", key=f"copy_{idx}"):
                        copy_to_clipboard_js(content)
                        st.toast("Copied to clipboard! 📋")
                with col_retry:
                    if idx == len(st.session_state.chat_history) - 1:
                        if st.button("🔄 Retry", key=f"retry_{idx}"):
                            if len(st.session_state.chat_history) >= 2:
                                last_user_prompt = st.session_state.chat_history[-2]["content"]
                                st.session_state.chat_history.pop()
                                st.session_state.pending_prompt = last_user_prompt
                                st.rerun()

    # CHAT INPUT
    chat_input_val = st.chat_input("Type your message here...")
    user_prompt = None

    if chat_input_val:
        user_prompt = chat_input_val
    elif st.session_state.pending_prompt:
        user_prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_prompt)

        # Create conversation if first turn
        if not st.session_state.current_conversation_id:
            title = generate_conversation_title(user_prompt)
            new_conv = create_conversation(st.session_state.user_id, title=title)
            if new_conv:
                st.session_state.current_conversation_id = str(new_conv["_id"])

        if st.session_state.current_conversation_id:
            add_message(st.session_state.current_conversation_id, "user", user_prompt)

        with st.chat_message("assistant", avatar="🤖"):
            gemini_client = get_gemini_client()
            if not gemini_client:
                st.error("Gemini API client could not be initialized. Please verify GEMINI_API_KEY in .env.")
            else:
                with st.spinner("CareerLoom AI is thinking..."):
                    try:
                        contents = []
                        for msg in st.session_state.chat_history:
                            r = "user" if msg["role"] == "user" else "model"
                            contents.append({
                                "role": r,
                                "parts": [{"text": msg["content"]}]
                            })

                        response = gemini_client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=contents,
                            config={"system_instruction": RESPONSE_STYLE}
                        )

                        assistant_text = response.text if response and response.text else "I could not generate a response. Please try again."
                        st.markdown(assistant_text)

                        st.session_state.chat_history.append({"role": "assistant", "content": assistant_text})
                        if st.session_state.current_conversation_id:
                            add_message(st.session_state.current_conversation_id, "assistant", assistant_text)

                        st.rerun()

                    except Exception as e:
                        st.error(f"Error generating response: {e}")

    st.markdown("<div class='input-tip-text'>💡 Tip: Keep your questions focused for better results.</div>", unsafe_allow_html=True)


# ---------------- PAGE 2: RESUME ANALYZER ----------------

elif st.session_state.active_page == "📄 Resume Analyzer":

    st.markdown("""
    <div class="dashboard-header" style="text-align: left; padding-bottom: 0.75rem;">
        <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 1.6rem;">📄</span>
            <span class="dashboard-header-title" style="font-size: 1.6rem; margin: 0;">AI Resume Analyzer</span>
        </div>
        <div class="dashboard-header-subtitle">Get AI-powered feedback to improve your resume for placements.</div>
    </div>
    """, unsafe_allow_html=True)

    # Drag and Drop PDF Upload Dropzone
    st.markdown("""
    <div class="upload-dropzone-box">
        <div class="upload-icon">☁️</div>
        <div class="upload-title">Upload your resume (PDF only)</div>
        <div class="upload-subtitle">Drag and drop your file here, or click to browse</div>
        <div class="upload-format-badge">Supported format: PDF (Max 5MB)</div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "Upload your resume PDF",
        type=["pdf"],
        label_visibility="collapsed"
    )

    if uploaded_file:
        st.success(f"✓ **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB) ready for analysis.")

        if st.button("Analyze Resume", type="primary", use_container_width=True):
            gemini_client = get_gemini_client()
            if not gemini_client:
                st.error("Gemini API client could not be initialized. Please check your GEMINI_API_KEY.")
            else:
                with st.spinner("Extracting text and generating comprehensive ATS analysis..."):
                    resume_text = extract_text_from_pdf(uploaded_file)
                    if not resume_text or len(resume_text.strip()) < 30:
                        st.error("Could not extract readable text from this PDF. Please ensure it contains selectable text.")
                    else:
                        try:
                            prompt = get_resume_analysis_prompt(resume_text)
                            response = gemini_client.models.generate_content(
                                model="gemini-2.5-flash",
                                contents=prompt
                            )
                            raw_result = response.text if response and response.text else "{}"
                            st.session_state.resume_analysis_data = parse_resume_analysis(raw_result)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Analysis failed: {e}")

    # RENDER STRUCTURED 10-CARD RESULTS GRID
    if st.session_state.resume_analysis_data:
        data = st.session_state.resume_analysis_data

        st.markdown("<h4 style='margin-top: 1.5rem; color: #0F172A;'>Analysis Results</h4>", unsafe_allow_html=True)

        # Row 1: Summary, Score, Key Skills (3 Columns)
        r1_c1, r1_c2, r1_c3 = st.columns([1.1, 0.9, 1])

        with r1_c1:
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title">📄 Resume Summary</div>
                <div class="analysis-card-item-body">{data.get('summary', 'Summary not available.')}</div>
            </div>
            """, unsafe_allow_html=True)

        with r1_c2:
            score = data.get('score', 78)
            score_color = "#10B981" if score >= 75 else ("#F59E0B" if score >= 60 else "#EF4444")
            st.markdown(f"""
            <div class="analysis-card-item" style="text-align: center;">
                <div class="analysis-card-item-title" style="justify-content: center;">🎯 Resume Score</div>
                <div class="score-circle-container">
                    <div class="score-circle" style="border-color: {score_color};">
                        <span class="score-number" style="color: {score_color};">{score}</span>
                        <span class="score-denom">/100</span>
                    </div>
                </div>
                <div style="font-size: 0.78rem; color: #64748B; margin-top: 0.25rem;">
                    {data.get('score_rationale', 'Overall resume strength evaluation.')}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with r1_c3:
            skills = data.get('key_skills', [])
            skills_html = "".join([f'<span class="skill-tag-pill">{s}</span>' for s in skills]) if skills else "<span>No skills extracted.</span>"
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title">🧩 Key Skills</div>
                <div class="analysis-card-item-body">{skills_html}</div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Row 2: Strong Points, Weak Points, Missing Skills (3 Columns)
        r2_c1, r2_c2, r2_c3 = st.columns(3)

        with r2_c1:
            strong = data.get('strong_points', [])
            strong_html = "".join([f"<li>{s}</li>" for s in strong])
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title" style="color: #059669;">🌟 Strong Points</div>
                <div class="analysis-card-item-body"><ul>{strong_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        with r2_c2:
            weak = data.get('weak_points', [])
            weak_html = "".join([f"<li>{w}</li>" for w in weak])
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title" style="color: #D97706;">⚠️ Weak Points</div>
                <div class="analysis-card-item-body"><ul>{weak_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        with r2_c3:
            missing = data.get('missing_skills', [])
            missing_html = "".join([f"<li>{m}</li>" for m in missing])
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title" style="color: #2563EB;">🔍 Missing Skills</div>
                <div class="analysis-card-item-body"><ul>{missing_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Row 3: ATS Optimization, Formatting Suggestions, Actionable Improvements (3 Columns)
        r3_c1, r3_c2, r3_c3 = st.columns(3)

        with r3_c1:
            ats = data.get('ats_optimization', [])
            ats_html = "".join([f"<li>{a}</li>" for a in ats]) if isinstance(ats, list) else f"<p>{ats}</p>"
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title">🤖 ATS Optimization</div>
                <div class="analysis-card-item-body"><ul>{ats_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        with r3_c2:
            fmt = data.get('formatting_suggestions', [])
            fmt_html = "".join([f"<li>{f}</li>" for f in fmt]) if isinstance(fmt, list) else f"<p>{fmt}</p>"
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title">📐 Formatting Suggestions</div>
                <div class="analysis-card-item-body"><ul>{fmt_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        with r3_c3:
            act = data.get('actionable_improvements', [])
            act_html = "".join([f"<li>{ac}</li>" for ac in act]) if isinstance(act, list) else f"<p>{act}</p>"
            st.markdown(f"""
            <div class="analysis-card-item">
                <div class="analysis-card-item-title" style="color: #059669;">🚀 Actionable Improvements</div>
                <div class="analysis-card-item-body"><ul>{act_html}</ul></div>
            </div>
            """, unsafe_allow_html=True)

        st.write("")

        # Row 4: Recommended Career Roles (Full Width Card)
        roles = data.get('recommended_roles', [])
        roles_html = "".join([f'<span class="skill-tag-pill" style="background: #F0FDF4; border-color: #BBF7D0; color: #15803D; font-size: 0.85rem; padding: 0.35rem 0.75rem;">💼 {r}</span>' for r in roles])
        st.markdown(f"""
        <div class="analysis-card-item">
            <div class="analysis-card-item-title">💼 Recommended Career Roles</div>
            <div class="analysis-card-item-body" style="padding-top: 0.35rem;">{roles_html}</div>
        </div>
        """, unsafe_allow_html=True)

        # Action Buttons for Report
        col_act1, col_act2 = st.columns([0.3, 0.7])
        with col_act1:
            if st.button("📋 Copy Analysis Report", key="copy_report_json_btn"):
                copy_to_clipboard_js(json.dumps(data, indent=2))
                st.toast("Report copied to clipboard! 📋")
        with col_act2:
            st.download_button(
                label="📥 Download Report (.json)",
                data=json.dumps(data, indent=2),
                file_name=f"resume_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )


# ---------------- FOOTER BRANDING & UNIQUE FEATURES ----------------

st.markdown(f"""
<div class="brand-footer-banner">
    <div class="brand-footer-text">
        <img src="data:image/png;base64,{LOGO_B64}" style="width: 24px; height: 24px; border-radius: 6px; object-fit: cover; vertical-align: middle; margin-right: 0.5rem;" alt="Logo" />
        <span>Simple. Smart. Focused on Your Career.</span>
    </div>
    <div class="brand-footer-sub">
        CareerLoom AI &ndash; Weaving Skills into Career Opportunities.
    </div>
</div>
""", unsafe_allow_html=True)