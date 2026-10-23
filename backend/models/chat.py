from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessageItem(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'model' / 'assistant'")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User prompt or career question")
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    history: Optional[List[ChatMessageItem]] = Field(default=[], description="Previous message history")


class ChatResponse(BaseModel):
    response: str
    conversation_id: str


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    message_count: int = 0
