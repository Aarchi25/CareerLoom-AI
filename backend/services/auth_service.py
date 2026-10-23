import uuid
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import bcrypt
import jwt
from bson import ObjectId
from backend.config import settings
from backend.database import get_mongo_db, SQLITE_DB_PATH


def hash_password(password: str) -> bytes:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(plain_password: str, hashed_password) -> bool:
    """Verify a plain password against hashed password."""
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode("utf-8")
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        return None


def register_user(username: str, email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    """Register a new user in MongoDB Atlas (with SQLite fallback)."""
    clean_email = email.strip().lower()
    clean_username = username.strip()
    hashed_pw = hash_password(password)
    now = datetime.now(timezone.utc)

    # 1. Try MongoDB Atlas
    db = get_mongo_db()
    if db is not None:
        try:
            users_col = db["users"]
            if users_col.find_one({"email": clean_email}):
                return None, "An account with this email already exists."
            
            doc = {
                "username": clean_username,
                "email": clean_email,
                "password": hashed_pw,
                "created_at": now
            }
            res = users_col.insert_one(doc)
            return {
                "id": str(res.inserted_id),
                "username": clean_username,
                "email": clean_email,
                "created_at": now.isoformat()
            }, None
        except Exception as e:
            print(f"[Register Mongo Error] {e}")

    # 2. SQLite Fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        if cur.fetchone():
            conn.close()
            return None, "An account with this email already exists."

        user_id = str(uuid.uuid4())
        cur.execute(
            "INSERT INTO users (id, username, email, password, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, clean_username, clean_email, hashed_pw, now.isoformat())
        )
        conn.commit()
        conn.close()

        return {
            "id": user_id,
            "username": clean_username,
            "email": clean_email,
            "created_at": now.isoformat()
        }, None
    except Exception as e:
        return None, f"Failed to register user: {str(e)}"


def authenticate_user(email: str, password: str) -> Tuple[Optional[dict], Optional[str]]:
    """Authenticate user credentials."""
    clean_email = email.strip().lower()

    # 1. Try MongoDB Atlas
    db = get_mongo_db()
    if db is not None:
        try:
            users_col = db["users"]
            user = users_col.find_one({"email": clean_email})
            if user and verify_password(password, user["password"]):
                return {
                    "id": str(user["_id"]),
                    "username": user["username"],
                    "email": user["email"],
                    "created_at": user.get("created_at", "").isoformat() if hasattr(user.get("created_at"), "isoformat") else str(user.get("created_at", ""))
                }, None
            elif user:
                return None, "Incorrect password."
        except Exception as e:
            print(f"[Auth Mongo Error] {e}")

    # 2. SQLite Fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, username, email, password, created_at FROM users WHERE email = ?", (clean_email,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return None, "No account found with this email."

        u_id, u_name, u_email, u_hash, u_created = row
        if verify_password(password, u_hash):
            return {
                "id": u_id,
                "username": u_name,
                "email": u_email,
                "created_at": u_created
            }, None
        return None, "Incorrect password."
    except Exception as e:
        return None, f"Authentication failed: {str(e)}"
