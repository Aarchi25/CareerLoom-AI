import requests
from typing import Optional, Tuple, Dict, Any, List

BACKEND_BASE_URL = "http://localhost:8000/api"


def is_backend_online() -> bool:
    """Check if the FastAPI backend server is actively running on port 8000."""
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}/health/", timeout=1.5)
        return resp.status_code == 200
    except Exception:
        return False


def get_backend_health() -> Optional[Dict[str, Any]]:
    """Fetch backend system health & database diagnostics."""
    try:
        resp = requests.get(f"{BACKEND_BASE_URL}/health/", timeout=2.0)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


def api_register(username: str, email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Register a new user via FastAPI backend."""
    try:
        payload = {"username": username, "email": email, "password": password}
        resp = requests.post(f"{BACKEND_BASE_URL}/auth/register", json=payload, timeout=5.0)
        data = resp.json()
        if resp.status_code == 201:
            return data, None
        return None, data.get("detail", "Registration failed.")
    except Exception as e:
        return None, f"Could not reach backend: {str(e)}"


def api_login(email: str, password: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Authenticate via FastAPI backend."""
    try:
        payload = {"email": email, "password": password}
        resp = requests.post(f"{BACKEND_BASE_URL}/auth/login", json=payload, timeout=5.0)
        data = resp.json()
        if resp.status_code == 200:
            return data, None
        return None, data.get("detail", "Invalid email or password.")
    except Exception as e:
        return None, f"Could not reach backend: {str(e)}"


def api_chat_message(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    conversation_id: Optional[str] = None,
    token: Optional[str] = None
) -> Tuple[Optional[str], Optional[str]]:
    """Send a chat message to FastAPI backend."""
    try:
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        formatted_history = []
        if history:
            for h in history:
                formatted_history.append({
                    "role": "user" if h.get("role") == "user" else "model",
                    "content": h.get("content", "")
                })

        payload = {
            "message": message,
            "conversation_id": conversation_id,
            "history": formatted_history
        }
        resp = requests.post(f"{BACKEND_BASE_URL}/chat/message", json=payload, headers=headers, timeout=20.0)
        data = resp.json()
        if resp.status_code == 200:
            return data.get("response"), data.get("conversation_id")
        return None, data.get("detail", "Error receiving response.")
    except Exception as e:
        return None, f"Backend error: {str(e)}"


def api_analyze_resume(file_bytes: bytes, filename: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Upload resume PDF to FastAPI backend for ATS analysis."""
    try:
        files = {"file": (filename, file_bytes, "application/pdf")}
        resp = requests.post(f"{BACKEND_BASE_URL}/resume/analyze", files=files, timeout=30.0)
        data = resp.json()
        if resp.status_code == 200:
            return data, None
        return None, data.get("detail", "Resume analysis failed.")
    except Exception as e:
        return None, f"Backend connection error: {str(e)}"
