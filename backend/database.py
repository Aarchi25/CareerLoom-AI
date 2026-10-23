import os
import sqlite3
import urllib.request
import certifi
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ServerSelectionTimeoutError, ConnectionFailure
from backend.config import settings

SQLITE_DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "career_assistant.db"))

_mongo_client = None
_mongo_db = None
_mongo_connected = False
_last_error = None


_cached_ip = None
_last_check_time = 0


def get_public_ip() -> str:
    """Helper to get public IP for MongoDB Atlas whitelisting (cached)."""
    global _cached_ip
    if _cached_ip:
        return _cached_ip
    try:
        req = urllib.request.Request("https://api.ipify.org", headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            _cached_ip = resp.read().decode("utf-8").strip()
            return _cached_ip
    except Exception:
        return "116.72.195.109"


def init_sqlite():
    """Ensure fallback local SQLite tables exist."""
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
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[SQLite Init Error] {e}")


init_sqlite()


def get_mongo_db(force_retry: bool = False):
    """
    Connect to MongoDB Atlas with timeout protection and retry interval.
    """
    global _mongo_client, _mongo_db, _mongo_connected, _last_error, _last_check_time

    if _mongo_connected and _mongo_db is not None:
        return _mongo_db

    import time
    now = time.time()
    # Don't hammer failing connection on every micro-request unless force_retry or 30s elapsed
    if not force_retry and (now - _last_check_time < 30) and _last_error is not None:
        return None

    _last_check_time = now

    if not settings.MONGODB_URI:
        _last_error = "MONGODB_URI is not set in environment."
        _mongo_connected = False
        return None

    try:
        _mongo_client = MongoClient(
            settings.MONGODB_URI,
            tlsCAFile=certifi.where(),
            serverSelectionTimeoutMS=2000,
            connectTimeoutMS=2000,
            socketTimeoutMS=2000
        )
        _mongo_client.admin.command('ping')
        _mongo_db = _mongo_client[settings.DATABASE_NAME]
        _mongo_connected = True
        _last_error = None
        print("[MongoDB] Connected successfully to Atlas!")
        return _mongo_db
    except ServerSelectionTimeoutError as e:
        _mongo_connected = False
        _last_error = "Atlas connection timeout / IP whitelist blocked: Check Network Access in Atlas."
        return None
    except Exception as e:
        _mongo_connected = False
        _last_error = str(e)[:200]
        return None


def get_connection_status(force_retry: bool = False):
    """Returns database connection status & troubleshooting info instantly."""
    get_mongo_db(force_retry=force_retry)
    public_ip = get_public_ip()
    return {
        "mongodb_connected": _mongo_connected,
        "active_backend": "MongoDB Atlas" if _mongo_connected else "Local SQLite (Fallback)",
        "database_name": settings.DATABASE_NAME if _mongo_connected else "career_assistant.db",
        "current_public_ip": public_ip,
        "last_error": _last_error,
        "whitelist_instructions": "Add your IP to MongoDB Atlas > Security > Network Access > Add IP Address." if not _mongo_connected else "Connected"
    }


def sync_sqlite_to_mongodb():
    """
    Migrates users and conversations stored in SQLite into MongoDB Atlas
    once MongoDB Atlas is reachable.
    """
    db = get_mongo_db()
    if not db:
        return False, "MongoDB is not reachable yet. Please ensure your IP is whitelisted in Atlas."

    users_col = db["users"]
    convs_col = db["conversations"]
    msgs_col = db["messages"]

    migrated_users = 0
    migrated_convs = 0

    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()

        # Migrate Users
        cur.execute("SELECT id, username, email, password, created_at FROM users")
        for row in cur.fetchall():
            u_id, u_name, u_email, u_pass, u_created = row
            if not users_col.find_one({"email": u_email}):
                users_col.insert_one({
                    "username": u_name,
                    "email": u_email,
                    "password": u_pass if isinstance(u_pass, (bytes, str)) else str(u_pass).encode("utf-8"),
                    "created_at": datetime.fromisoformat(u_created) if u_created else datetime.now(timezone.utc),
                    "legacy_sqlite_id": u_id
                })
                migrated_users += 1

        # Migrate Conversations
        cur.execute("SELECT id, user_id, title, created_at, updated_at FROM conversations")
        for row in cur.fetchall():
            c_id, c_uid, c_title, c_created, c_updated = row
            if not convs_col.find_one({"legacy_id": c_id}):
                convs_col.insert_one({
                    "legacy_id": c_id,
                    "user_id": c_uid,
                    "title": c_title,
                    "created_at": datetime.fromisoformat(c_created) if c_created else datetime.now(timezone.utc),
                    "updated_at": datetime.fromisoformat(c_updated) if c_updated else datetime.now(timezone.utc)
                })
                migrated_convs += 1

        conn.close()
        return True, f"Successfully synced {migrated_users} user(s) and {migrated_convs} conversation(s) to MongoDB Atlas!"
    except Exception as e:
        return False, f"Sync failed: {str(e)}"
