"""Conversation storage API — server-side persistence.

GET    /api/v1/conversations                       — list user's conversations
POST   /api/v1/conversations                       — create new conversation
GET    /api/v1/conversations/{id}                  — get conversation with messages
PATCH  /api/v1/conversations/{id}                  — update title
DELETE /api/v1/conversations/{id}                  — delete conversation
POST   /api/v1/conversations/{id}/messages         — append a message
DELETE /api/v1/conversations/{id}/messages         — clear all messages
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.auth import get_current_user
from app.storage import (
    create_conversation, list_conversations, get_conversation_messages,
    update_conversation, delete_conversation, add_message,
    clear_conversation_messages,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


class ConversationCreate(BaseModel):
    title: str = ""


class ConversationUpdate(BaseModel):
    title: str


class MessageCreate(BaseModel):
    id: str
    role: str  # "user" or "assistant"
    content: str
    metadata: Optional[Dict[str, Any]] = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: int


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: int
    updated_at: int
    message_count: int = 0


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: int
    updated_at: int
    messages: List[MessageOut]


@router.get("", response_model=List[ConversationOut])
async def list_my_conversations(user: dict = Depends(get_current_user)):
    """List conversations belonging to the current user."""
    user_id = user.get("user_id")
    convs = list_conversations(user_id=user_id)
    # Count messages per conv (cheap: do a single query)
    from app.storage import get_connection
    with get_connection() as conn:
        out = []
        for c in convs:
            row = conn.execute(
                "SELECT COUNT(*) as n FROM messages WHERE conversation_id = ?",
                (c["id"],)
            ).fetchone()
            out.append(ConversationOut(
                id=c["id"], title=c["title"],
                created_at=c["created_at"], updated_at=c["updated_at"],
                message_count=row["n"] if row else 0,
            ))
        return out


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
async def create_new_conversation(body: ConversationCreate,
                                  user: dict = Depends(get_current_user)):
    import uuid
    conv_id = str(uuid.uuid4())
    title = body.title.strip() or f"Conversation {datetime.now().strftime('%b %d, %H:%M')}"
    create_conversation(conv_id, user["user_id"], title)
    now = int(datetime.utcnow().timestamp() * 1000)
    return ConversationOut(id=conv_id, title=title,
                           created_at=now, updated_at=now, message_count=0)


@router.get("/{conv_id}", response_model=ConversationDetail)
async def get_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    from app.storage import get_connection
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                         (conv_id, user["user_id"])).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msgs = get_conversation_messages(conv_id)
    return ConversationDetail(
        id=c["id"], title=c["title"],
        created_at=c["created_at"], updated_at=c["updated_at"],
        messages=[
            MessageOut(
                id=m["id"], role=m["role"], content=m["content"],
                metadata=json.loads(m["metadata_json"]) if m.get("metadata_json") else None,
                created_at=m["created_at"],
            )
            for m in msgs
        ],
    )


@router.patch("/{conv_id}", response_model=ConversationOut)
async def rename_conversation(conv_id: str, body: ConversationUpdate,
                              user: dict = Depends(get_current_user)):
    from app.storage import get_connection
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                         (conv_id, user["user_id"])).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    update_conversation(conv_id, title=body.title,
                        updated_at=int(datetime.utcnow().timestamp() * 1000))
    return ConversationOut(
        id=c["id"], title=body.title,
        created_at=c["created_at"],
        updated_at=int(datetime.utcnow().timestamp() * 1000),
        message_count=0,
    )


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_one_conversation(conv_id: str, user: dict = Depends(get_current_user)):
    from app.storage import get_connection
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                         (conv_id, user["user_id"])).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    delete_conversation(conv_id)
    return None


@router.post("/{conv_id}/messages", response_model=MessageOut, status_code=201)
async def append_message(conv_id: str, body: MessageCreate,
                          user: dict = Depends(get_current_user)):
    from app.storage import get_connection
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                         (conv_id, user["user_id"])).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    add_message(body.id, conv_id, body.role, body.content, body.metadata)
    return MessageOut(
        id=body.id, role=body.role, content=body.content,
        metadata=body.metadata,
        created_at=int(datetime.utcnow().timestamp() * 1000),
    )


@router.delete("/{conv_id}/messages", status_code=204)
async def clear_messages(conv_id: str, user: dict = Depends(get_current_user)):
    from app.storage import get_connection
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                         (conv_id, user["user_id"])).fetchone()
    if not c:
        raise HTTPException(status_code=404, detail="Conversation not found")
    clear_conversation_messages(conv_id)
    return None


# JSON helper
import json
