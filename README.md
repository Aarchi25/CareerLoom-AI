# 🧶 CareerLoom AI
> **Weaving Skills into Career Opportunities.**

An AI-powered career platform built using **FastAPI**, **Streamlit**, **MongoDB Atlas**, and **Google Gemini API**.

## Features

- 💬 **CareerLoom AI Advisor**: Real-time career mentorship powered by Google Gemini 2.5 Flash.
- 📄 **Resume & ATS Analyzer**: PDF text extraction and detailed ATS score breakdown.
- 🔐 **Dual Architecture**: Full REST API via **FastAPI** + interactive UI via **Streamlit**.
- 🗄️ **Resilient Database**: Cloud **MongoDB Atlas** with automatic local SQLite offline mode.
- 🌐 **Interactive API Documentation**: Live OpenAPI / Swagger docs at `/docs`.

## Tech Stack

- **Backend**: FastAPI, Uvicorn, Pydantic, PyJWT
- **Database**: MongoDB Atlas (with SQLite offline resilience)
- **AI Engine**: Google Gemini API (`gemini-2.5-flash`)
- **Frontend**: Streamlit, Custom SaaS CSS Design System
- **Language**: Python 3.10+

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables (`.env`)
```ini
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_atlas_connection_string
JWT_SECRET=your_secret_key_here
```

### 3. Run FastAPI Backend
```bash
# Option A: using runner script
python backend/run.py

# Option B: using uvicorn directly
uvicorn backend.main:app --reload --port 8000
```
- **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

### 4. Run Streamlit Frontend
```bash
streamlit run src/app.py
```

## Project Structure

```
CareerLoom-AI/
├── backend/
│   ├── config.py             # App & security configuration
│   ├── database.py           # MongoDB connection & SQLite fallback
│   ├── main.py               # FastAPI entry point & CORS
│   ├── run.py                # Backend dev server runner
│   ├── models/               # Pydantic schemas (User, Chat, Resume)
│   ├── routers/              # API endpoints (Auth, Chat, Resume, Health)
│   └── services/             # Core business logic & Gemini AI
├── src/
│   ├── app.py                # Streamlit UI application
│   ├── database.py           # Database integration & sync helper
│   ├── chatbot.py            # AI advisor logic
│   ├── resume_analyzer.py    # Resume text extraction & ATS parsing
│   ├── styles/custom.css     # Modern SaaS CSS design system
│   └── assets/logo.png       # Official CareerLoom AI branding
├── requirements.txt
└── README.md
```

## Author

**Aarchi Israni**