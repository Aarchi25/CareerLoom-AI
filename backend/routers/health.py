from fastapi import APIRouter
from backend.database import get_connection_status, sync_sqlite_to_mongodb

router = APIRouter(prefix="/health", tags=["System & Diagnostics"])


@router.get("/")
def health_check():
    """
    Check system health, database connection (MongoDB Atlas vs SQLite fallback),
    and view current public IP address for Atlas whitelisting.
    """
    status = get_connection_status()
    return {
        "status": "online",
        "service": "CareerLoom AI Backend",
        "database": status
    }


@router.post("/sync-to-mongo")
def trigger_mongo_sync():
    """
    Sync all registered users and chats from local SQLite into MongoDB Atlas.
    Call this once you have whitelisted your IP address in MongoDB Atlas!
    """
    success, message = sync_sqlite_to_mongodb()
    return {
        "success": success,
        "message": message
    }
