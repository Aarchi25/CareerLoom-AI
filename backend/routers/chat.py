import uuid
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models.chat import ChatRequest, ChatResponse, ConversationSummary, ChatMessageItem
from backend.services.gemini_service import generate_career_response
from backend.services.auth_service import decode_access_token
from backend.database import get_mongo_db, SQLITE_DB_PATH

router = APIRouter(prefix="/chat", tags=["Career Advisor Chat"])
security = HTTPBearer(auto_error=False)


def get_optional_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[str]:
    if not credentials:
        return None
    payload = decode_access_token(credentials.credentials)
    return payload.get("sub") if payload else None


@router.post("/message", response_model=ChatResponse)
def send_chat_message(
    data: ChatRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Send a message to CareerLoom AI Advisor.
    Supports continuous conversational history.
    """
    ai_response = generate_career_response(data.message, data.history)
    conv_id = data.conversation_id or str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # If logged in, save to database
    if user_id:
        db = get_mongo_db()
        if db is not None:
            try:
                convs_col = db["conversations"]
                msgs_col = db["messages"]

                # Ensure conversation exists
                conv = convs_col.find_one({"_id": ObjectId(conv_id)}) if len(conv_id) == 24 else None
                if not conv:
                    title = data.message[:35] + ("..." if len(data.message) > 35 else "")
                    new_conv = {
                        "user_id": user_id,
                        "title": title,
                        "created_at": now,
                        "updated_at": now
                    }
                    res = convs_col.insert_one(new_conv)
                    conv_id = str(res.inserted_id)
                else:
                    convs_col.update_one({"_id": conv["_id"]}, {"$set": {"updated_at": now}})

                # Save user & AI messages
                msgs_col.insert_one({
                    "conversation_id": conv_id,
                    "role": "user",
                    "content": data.message,
                    "created_at": now
                })
                msgs_col.insert_one({
                    "conversation_id": conv_id,
                    "role": "assistant",
                    "content": ai_response,
                    "created_at": now
                })
            except Exception as e:
                print(f"[Chat Mongo Error] {e}")
        else:
            # SQLite fallback
            try:
                conn = sqlite3.connect(SQLITE_DB_PATH)
                cur = conn.cursor()
                cur.execute("SELECT id FROM conversations WHERE id = ?", (conv_id,))
                if not cur.fetchone():
                    title = data.message[:35] + ("..." if len(data.message) > 35 else "")
                    cur.execute(
                        "INSERT INTO conversations (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (conv_id, user_id, title, now.isoformat(), now.isoformat())
                    )
                else:
                    cur.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now.isoformat(), conv_id))

                cur.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), conv_id, "user", data.message, now.isoformat())
                )
                cur.execute(
                    "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), conv_id, "assistant", ai_response, now.isoformat())
                )
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Chat SQLite Error] {e}")

    return ChatResponse(
        response=ai_response,
        conversation_id=conv_id
    )


@router.get("/conversations", response_model=List[ConversationSummary])
def list_conversations(user_id: Optional[str] = Depends(get_optional_user_id)):
    """List saved conversations for authenticated user."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    results = []
    db = get_mongo_db()
    if db is not None:
        try:
            convs = list(db["conversations"].find({"user_id": user_id}).sort("updated_at", -1))
            for c in convs:
                c_id = str(c["_id"])
                count = db["messages"].count_documents({"conversation_id": c_id})
                results.append(ConversationSummary(
                    id=c_id,
                    title=c.get("title", "Career Discussion"),
                    created_at=c.get("created_at", "").isoformat() if hasattr(c.get("created_at"), "isoformat") else str(c.get("created_at", "")),
                    updated_at=c.get("updated_at", "").isoformat() if hasattr(c.get("updated_at"), "isoformat") else str(c.get("updated_at", "")),
                    message_count=count
                ))
            return results
        except Exception as e:
            print(f"[List Convs Mongo Error] {e}")

    # SQLite Fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, title, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
        for row in cur.fetchall():
            c_id, title, created_at, updated_at = row
            cur.execute("SELECT COUNT(*) FROM messages WHERE conversation_id = ?", (c_id,))
            count = cur.fetchone()[0]
            results.append(ConversationSummary(
                id=c_id,
                title=title,
                created_at=created_at,
                updated_at=updated_at,
                message_count=count
            ))
        conn.close()
    except Exception as e:
        print(f"[List Convs SQLite Error] {e}")

    return results


@router.get("/conversations/{conversation_id}/messages")
def get_messages(conversation_id: str, user_id: Optional[str] = Depends(get_optional_user_id)):
    """Get all messages for a specific conversation."""
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")

    messages = []
    db = get_mongo_db()
    if db is not None:
        try:
            msgs = list(db["messages"].find({"conversation_id": conversation_id}).sort("created_at", 1))
            for m in msgs:
                messages.append({
                    "id": str(m["_id"]),
                    "role": m.get("role", "user"),
                    "content": m.get("content", ""),
                    "created_at": m.get("created_at", "").isoformat() if hasattr(m.get("created_at"), "isoformat") else str(m.get("created_at", ""))
                })
            return messages
        except Exception as e:
            print(f"[Get Messages Mongo Error] {e}")

    # SQLite Fallback
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC", (conversation_id,))
        for row in cur.fetchall():
            m_id, role, content, created_at = row
            messages.append({
                "id": m_id,
                "role": role,
                "content": content,
                "created_at": created_at
            })
        conn.close()
    except Exception as e:
        print(f"[Get Messages SQLite Error] {e}")

    return messages
