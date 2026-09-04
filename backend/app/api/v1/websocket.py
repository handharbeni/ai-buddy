"""WebSocket streaming endpoint for query with JWT auth."""

import json
import time
import logging
from uuid import uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Request
import jwt

from app.auth import get_current_user
from app.llm.simple_service import SimpleLLMService
from app.rbac import Role

logger = logging.getLogger(__name__)

router = APIRouter()

# Reuse query context helpers from query.py to avoid duplication
from app.api.v1.query import (
    _build_query_context,
    _build_scope,
    detect_intent,
    SYSTEM_PROMPT,
    _injection_detector,
)

SYSTEM_PROMPT_WS = """Anda adalah asisten AI untuk BAPENDA (Badan Pendapatan Daerah).
Jawab singkat dan tepat dalam Bahasa Indonesia.

Gunakan data dari hasil pencarian tool jika ada.
Jika ada data kuantitatif, sertakan angka dengan tepat.
Jika jawaban berdasarkan regulasi, sebutkan nama dokumen dan pasalnya."""


async def _send_json(ws: WebSocket, data: dict):
    """Send JSON over WebSocket."""
    await ws.send_text(json.dumps(data))


async def _authenticate(ws: WebSocket, request: Request) -> dict | None:
    """Authenticate user from URL param first, then first WS message."""
    # 1. Try URL query param
    token = None
    try:
        # get token from URL query param
        import urllib.parse
        parsed = urllib.parse.urlparse(str(ws.url))
        token = urllib.parse.parse_qs(parsed.query).get("token", [None])[0]
    except Exception:
        pass

    if not token:
        # 2. Wait for first message to be auth
        try:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            if msg.get("type") == "auth":
                token = msg.get("token")
        except Exception:
            pass

    if not token:
        await _send_json(ws, {"type": "error", "message": "Authentication required"})
        return None

    # Validate token
    auth = getattr(request.app.state, "auth", None)
    if auth is None:
        await _send_json(ws, {"type": "error", "message": "Auth service unavailable"})
        return None

    payload = auth.verify_access_token(token)
    if not payload:
        await _send_json(ws, {"type": "error", "message": "Invalid or expired token"})
        return None

    user_id = payload.get("username") or payload.get("sub")
    role_str = payload.get("role")
    if not user_id or not role_str:
        await _send_json(ws, {"type": "error", "message": "Invalid token payload"})
        return None

    try:
        role = Role(role_str)
    except ValueError:
        await _send_json(ws, {"type": "error", "message": "Invalid role in token"})
        return None

    return {
        "user_id": user_id,
        "role": role,
        "scope": payload.get("scope", {}),
        "token": token,
    }


@router.websocket("/ws/query")
async def ws_query(
    ws: WebSocket,
    request: Request,
):
    """WebSocket streaming query endpoint.

    Protocol:
      Client -> Server:
        {"type": "auth", "token": "<jwt>"}          # optional if token in URL
        {"question": "...", "conversation_id": "..."}

      Server -> Client:
        {"type": "chunk", "content": "partial text"}
        {"type": "done", "data": {...response data...}}
        {"type": "error", "message": "..."}
    """
    await ws.accept()

    # Authenticate
    user = await _authenticate(ws, request)
    if not user:
        await ws.close(code=4001)
        return

    try:
        # Receive query message
        raw = await ws.receive_text()
        msg = json.loads(raw)

        # Ignore re-auth messages
        if msg.get("type") == "auth":
            # Already authenticated, skip
            pass
        elif "question" not in msg:
            await _send_json(ws, {"type": "error", "message": "Missing 'question' field"})
            await ws.close(code=4000)
            return

        question = msg.get("question", "")
        conversation_id = msg.get("conversation_id") or str(uuid4())

        # Prompt injection check
        detection = _injection_detector.detect(question)
        if detection.blocked:
            await _send_json(ws, {
                "type": "error",
                "message": "Permintaan Anda mengandung pola yang tidak diizinkan.",
            })
            await ws.close(code=4000)
            return

        intent = detect_intent(question)
        llm = getattr(request.app.state, "llm", None)
        if llm is None:
            await _send_json(ws, {"type": "error", "message": "LLM service not initialized"})
            await ws.close(code=5000)
            return

        start = time.time()

        # Build context
        context, tools_used, raw_data = await _build_query_context(
            question, user, request
        )

        full_prompt = f"{context}\n\nPertanyaan: {question}\n\nJawaban:"

        # Stream LLM response
        full_text = ""
        async for chunk in llm.generate_stream(
            prompt=full_prompt,
            system=SYSTEM_PROMPT_WS,
            temperature=0.3,
            max_tokens=256,
        ):
            full_text += chunk
            await _send_json(ws, {"type": "chunk", "content": chunk})

        latency_ms = (time.time() - start) * 1000

        # Determine suggested format
        if not raw_data:
            suggested_format = "docx"
        else:
            suggested_format = "xlsx"

        await _send_json(ws, {
            "type": "done",
            "data": {
                "answer": full_text,
                "citations": [],
                "tools_used": [f"llm:bapenda-ai:latest"] + tools_used,
                "intent": intent,
                "conversation_id": conversation_id,
                "metadata": {
                    "user_id": user.get("user_id"),
                    "role": user.get("role").value if hasattr(user.get("role"), "value") else str(user.get("role")),
                    "model": "bapenda-ai:latest",
                    "latency_ms": round(latency_ms, 2),
                    "mcp_available": getattr(request.app.state, "mcp_router", None) is not None,
                    "rag_available": getattr(request.app.state, "rag_service", None) is not None,
                    "row_count": len(raw_data),
                },
                "data": raw_data,
                "suggested_format": suggested_format,
            },
        })

    except WebSocketDisconnect:
        logger.debug("WebSocket client disconnected")
    except json.JSONDecodeError:
        await _send_json(ws, {"type": "error", "message": "Invalid JSON"})
        await ws.close(code=4000)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await _send_json(ws, {"type": "error", "message": f"Internal error: {e}"})
        except Exception:
            pass
        await ws.close(code=1011)
