# 🧶 CareerLoom AI
### *Weaving Skills into Career Opportunities.*

<p align="center">
  <strong>An AI-powered career assistance platform for smarter career guidance and resume insights.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/Streamlit-Frontend-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white" alt="Streamlit"/>
  <img src="https://img.shields.io/badge/Google_Gemini-AI-8E75B2?style=for-the-badge&logo=googlegemini&logoColor=white" alt="Google Gemini"/>
  <img src="https://img.shields.io/badge/MongoDB_Atlas-Database-47A248?style=for-the-badge&logo=mongodb&logoColor=white" alt="MongoDB Atlas"/>
</p>

---

## 🌟 Overview

**CareerLoom AI** is an AI-powered career assistance platform designed to help students and job seekers navigate their career journeys. It combines conversational AI and resume analysis to provide career guidance, resume insights, and personalized assistance through an interactive application.

The project integrates **Google Gemini AI, Streamlit, FastAPI, and MongoDB Atlas** to create an AI-driven career support experience.

## ✨ Features

- 💬 **CareerLoom AI Advisor** — Real-time career mentorship powered by Google Gemini 2.5 Flash.
- 📄 **Resume Analyzer** — Upload a PDF resume for text extraction and AI-assisted resume insights.
- 🔐 **Dual Architecture** — A REST API backend built with **FastAPI** and an interactive user interface powered by **Streamlit**.
- 🗄️ **Resilient Database** — Uses **MongoDB Atlas** for persistent data storage.
- 🌐 **Interactive API Documentation** — Explore and test API endpoints through OpenAPI/Swagger documentation at `/docs`.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| **Language** | Python 3.10+ |
| **Backend** | FastAPI, Uvicorn, Pydantic, PyJWT |
| **Frontend** | Streamlit |
| **AI Engine** | Google Gemini API (`gemini-2.5-flash`) |
| **Database** | MongoDB Atlas |
| **Version Control** | Git, GitHub |

## 🏗️ Project Structure

```text
CareerLoom-AI/
│
├── backend/
│   ├── config.py             # App and security configuration
│   ├── database.py           # MongoDB connection
│   ├── main.py               # FastAPI entry point and CORS
│   ├── run.py                # Backend development server runner
│   ├── models/               # Pydantic schemas (User, Chat, Resume)
│   ├── routers/              # API endpoints (Auth, Chat, Resume, Health)
│   └── services/             # Core business logic and Gemini AI
│
├── src/
│   ├── app.py                # Streamlit UI application
│   ├── database.py           # Database integration and sync helper
│   ├── chatbot.py            # AI advisor logic
│   ├── resume_analyzer.py    # Resume text extraction and ATS parsing
│   ├── styles/
│   │   └── custom.css        # Modern SaaS CSS design system
│   └── assets/
│       └── logo.png          # CareerLoom AI branding
│
├── requirements.txt
└── README.md
```

## ⚙️ Getting Started

### Prerequisites

Before running CareerLoom AI, ensure you have:

- Python 3.10+ compatible with the project dependencies
- Git installed on your system
- A Google Gemini API key
- A MongoDB Atlas account and database connection URI

### 1. Clone the Repository

```bash
git clone https://github.com/Aarchi25/CareerLoom-AI.git
cd CareerLoom-AI
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment on Windows:

```cmd
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and add your credentials:

```env
GEMINI_API_KEY=your_gemini_api_key
MONGODB_URI=your_mongodb_connection_string
```

Replace the placeholder values with your actual credentials. Ensure that the variable names match those expected by your application.

> **🔒 Security Note:** Never commit your `.env` file, API keys, database credentials, or other secrets to GitHub.

### 5. Run the Streamlit Application

```bash
streamlit run src/app.py
```

### 6. Run the FastAPI Backend

Open a separate terminal in the project root, activate the virtual environment, and run:

```bash
python -m uvicorn backend.main:app 
```

## 🔐 Security and Configuration

- Store API keys and database credentials in environment variables.
- Keep `.env` and `.venv/` out of version control.
- Validate user inputs and uploaded files.
- Apply appropriate authentication and access controls to user-specific data.
- Restrict database access through appropriate MongoDB Atlas network and database-user permissions.

## 🎯 Project Objectives

- Explore practical applications of generative AI in career development.
- Integrate an AI model into a Python application.
- Build and connect a REST API backend.
- Work with cloud-hosted NoSQL database storage.
- Develop modular application components and manage them using Git and GitHub.

## 🔮 Future Enhancements

- 🧭 Personalized career roadmaps based on skills and interests.
- 🎯 Job-description-based resume matching and skill-gap analysis.
- 🎤 Interview preparation with role-specific questions.
- 📈 Improved resume recommendations and actionable feedback.
- ☁️ Application deployment with secure production configuration.

## 👩‍💻 Author

**Aarchi Israni**

- **GitHub:** [@Aarchi25](https://github.com/Aarchi25)
- **Project Repository:** [CareerLoom AI](https://github.com/Aarchi25/CareerLoom-AI)

---

<p align="center">
  <strong>🧶 CareerLoom AI</strong><br/>
  <em>Connecting skills, opportunities, and career growth through AI.</em>
</p>