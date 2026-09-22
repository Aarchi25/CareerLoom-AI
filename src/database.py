import os
import sqlite3
import secrets
import uuid
from datetime import datetime, timezone
from bson import ObjectId
import bcrypt
import certifi
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "career_assistant.db"))

_client = None
_db = None
_mongo_tested = False
_mongo_available = False


def init_sqlite_db():
    """Initialize local SQLite tables for offline / fallback mode."""
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT,
                email TEXT UNIQUE,
                password BLOB,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT,
                role TEXT,
                content TEXT,
                created_at TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT,
                username TEXT,
                email TEXT,
                created_at TEXT
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass


# Ensure local database schema is ready
init_sqlite_db()


def get_db():
    """Get or initialize the MongoDB database connection safely and quickly."""
    global _client, _db, _mongo_tested, _mongo_available
    if _mongo_tested:
        return _db if _mongo_available else None

    _mongo_tested = True

    if not MONGODB_URI:
        _mongo_available = False
        return None

    try:
        _client = MongoClient(
            MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=400,
            connectTimeoutMS=400,
            socketTimeoutMS=500
        )
        _client.admin.command('ping')
        _db = _client["ai_career_assistant"]
        _mongo_available = True
        return _db
    except Exception:
        _client = None
        _db = None
        _mongo_available = False
        return None


def is_mongodb_ready():
    """Check if MongoDB is actively connected and reachable."""
    global _mongo_tested, _mongo_available
    if _mongo_tested:
        return _mongo_available
    db = get_db()
    return db is not None and _mongo_available


def get_current_utc_time():
    """Get timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def check_db_connection():
    """Verify database connection status (MongoDB or local SQLite)."""
    return True


# ---------------- USER FUNCTIONS ----------------

def create_user(username, email, password):
    """
    Create a new user with hashed password.
    Works with MongoDB Atlas, with automatic local SQLite fallback.
    """
    clean_email = email.strip().lower()
    clean_username = username.strip()

    # 1. Attempt MongoDB Atlas first
    if is_mongodb_ready():
        try:
            users_col = _db["users"]
            if users_col.find_one({"email": clean_email}):
                return None, "EMAIL_EXISTS"

            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            user_doc = {
                "username": clean_username,
                "email": clean_email,
                "password": hashed,
                "created_at": get_current_utc_time()
            }
            res = users_col.insert_one(user_doc)
            user_doc["_id"] = res.inserted_id
            return user_doc, None
        except Exception:
            pass

    # 2. Seamless local SQLite fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()

        # Check existing email
        cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        if cursor.fetchone():
            conn.close()
            return None, "EMAIL_EXISTS"

        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
        now_str = get_current_utc_time().isoformat()

        cursor.execute(
            "INSERT INTO users (id, username, email, password, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, clean_username, clean_email, hashed, now_str)
        )
        conn.commit()
        conn.close()

        return {
            "_id": user_id,
            "username": clean_username,
            "email": clean_email,
            "created_at": now_str
        }, None
    except Exception:
        return None, "UNKNOWN_ERROR"


def authenticate_user(email, password):
    """
    Authenticate user by email and password.
    """
    clean_email = email.strip().lower()

    # 1. Attempt MongoDB Atlas first
    if is_mongodb_ready():
        try:
            users_col = _db["users"]
            user = users_col.find_one({"email": clean_email})
            if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
                return user, None
            return None, "INVALID_CREDENTIALS"
        except Exception:
            pass

    # 2. Local SQLite fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, password, created_at FROM users WHERE email = ?", (clean_email,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None, "INVALID_CREDENTIALS"

        user_id, username, user_email, hashed_pw, created_at = row
        if isinstance(hashed_pw, str):
            hashed_pw = hashed_pw.encode("utf-8")

        if bcrypt.checkpw(password.encode("utf-8"), hashed_pw):
            return {
                "_id": user_id,
                "username": username,
                "email": user_email,
                "created_at": created_at
            }, None

        return None, "INVALID_CREDENTIALS"
    except Exception:
        return None, "UNKNOWN_ERROR"


# ---------------- SESSION FUNCTIONS (PERSISTENCE) ----------------

def create_session(user_id, username, email=""):
    """Generate and save session token."""
    token = secrets.token_urlsafe(32)
    now = get_current_utc_time()

    if is_mongodb_ready():
        try:
            sessions_col = _db["sessions"]
            sessions_col.insert_one({
                "token": token,
                "user_id": ObjectId(user_id) if len(str(user_id)) == 24 else str(user_id),
                "username": username,
                "email": email,
                "created_at": now
            })
            return token
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessions (token, user_id, username, email, created_at) VALUES (?, ?, ?, ?, ?)",
            (token, str(user_id), username, email, now.isoformat())
        )
        conn.commit()
        conn.close()
        return token
    except Exception:
        return token


def get_session(token):
    """Retrieve session by token."""
    if not token:
        return None

    if is_mongodb_ready():
        try:
            session = _db["sessions"].find_one({"token": str(token).strip()})
            if session:
                return session
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT token, user_id, username, email, created_at FROM sessions WHERE token = ?", (str(token).strip(),))
        row = cursor.fetchone()
        conn.close()
        if row:
            return {
                "token": row[0],
                "user_id": row[1],
                "username": row[2],
                "email": row[3],
                "created_at": row[4]
            }
        return None
    except Exception:
        return None


def delete_session(token):
    """Delete a session upon logout."""
    if not token:
        return False

    if is_mongodb_ready():
        try:
            _db["sessions"].delete_one({"token": str(token).strip()})
            return True
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (str(token).strip(),))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ---------------- CONVERSATION FUNCTIONS ----------------

def create_conversation(user_id, title="New Conversation"):
    """Create a new conversation."""
    clean_title = title.strip()[:60] if title else "New Conversation"
    now = get_current_utc_time()

    if is_mongodb_ready():
        try:
            user_obj_id = ObjectId(user_id) if len(str(user_id)) == 24 else str(user_id)
            doc = {
                "user_id": user_obj_id,
                "title": clean_title,
                "created_at": now,
                "updated_at": now
            }
            res = _db["conversations"].insert_one(doc)
            doc["_id"] = res.inserted_id
            return doc
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        conv_id = str(uuid.uuid4())
        now_str = now.isoformat()
        cursor.execute(
            "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (conv_id, str(user_id), clean_title, now_str, now_str)
        )
        conn.commit()
        conn.close()
        return {
            "_id": conv_id,
            "user_id": str(user_id),
            "title": clean_title,
            "created_at": now_str,
            "updated_at": now_str
        }
    except Exception:
        return None


def get_user_conversations(user_id):
    """Get all conversations for a user, sorted by most recent first."""
    if is_mongodb_ready():
        try:
            user_obj_id = ObjectId(user_id) if len(str(user_id)) == 24 else str(user_id)
            cursor = _db["conversations"].find({"user_id": user_obj_id}).sort("updated_at", -1)
            return list(cursor)
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, user_id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (str(user_id),)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "_id": r[0],
                "user_id": r[1],
                "title": r[2],
                "created_at": r[3],
                "updated_at": r[4]
            }
            for r in rows
        ]
    except Exception:
        return []


def delete_conversation(conversation_id, user_id):
    """Delete a conversation and all its messages."""
    if is_mongodb_ready():
        try:
            conv_obj_id = ObjectId(conversation_id) if len(str(conversation_id)) == 24 else str(conversation_id)
            user_obj_id = ObjectId(user_id) if len(str(user_id)) == 24 else str(user_id)
            _db["conversations"].delete_one({"_id": conv_obj_id, "user_id": user_obj_id})
            _db["messages"].delete_many({"conversation_id": conv_obj_id})
            return True
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE id = ? AND user_id = ?", (str(conversation_id), str(user_id)))
        cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (str(conversation_id),))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


# ---------------- MESSAGE FUNCTIONS ----------------

def add_message(conversation_id, role, content):
    """Save a chat message."""
    now = get_current_utc_time()

    if is_mongodb_ready():
        try:
            conv_obj_id = ObjectId(conversation_id) if len(str(conversation_id)) == 24 else str(conversation_id)
            doc = {
                "conversation_id": conv_obj_id,
                "role": role,
                "content": content,
                "created_at": now
            }
            res = _db["messages"].insert_one(doc)
            doc["_id"] = res.inserted_id
            _db["conversations"].update_one({"_id": conv_obj_id}, {"$set": {"updated_at": now}})
            return doc
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        msg_id = str(uuid.uuid4())
        now_str = now.isoformat()
        cursor.execute(
            "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
            (msg_id, str(conversation_id), role, content, now_str)
        )
        cursor.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now_str, str(conversation_id))
        )
        conn.commit()
        conn.close()
        return {
            "_id": msg_id,
            "conversation_id": str(conversation_id),
            "role": role,
            "content": content,
            "created_at": now_str
        }
    except Exception:
        return None


def get_conversation_messages(conversation_id):
    """Retrieve all messages for a given conversation in chronological order."""
    if is_mongodb_ready():
        try:
            conv_obj_id = ObjectId(conversation_id) if len(str(conversation_id)) == 24 else str(conversation_id)
            cursor = _db["messages"].find({"conversation_id": conv_obj_id}).sort("created_at", 1)
            return [
                {
                    "role": doc.get("role", "user"),
                    "content": doc.get("content", ""),
                    "created_at": doc.get("created_at")
                }
                for doc in cursor
            ]
        except Exception:
            pass

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (str(conversation_id),)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "role": r[0],
                "content": r[1],
                "created_at": r[2]
            }
            for r in rows
        ]
    except Exception:
        return []