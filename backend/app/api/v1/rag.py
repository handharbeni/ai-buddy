"""Thin proxy to the RAG service (RAG_BASE_URL, default http://localhost:8002).

All endpoints forward to the RAG service via httpx. No business logic here.

Auth:
  any user    → search, health, documents (list)
  admin/supervisor → ingest, delete
"""
import os
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form

from app.auth import get_current_user
from app.rbac.service import Role

router = APIRouter()
log = logging.getLogger(__name__)

RAG_BASE_URL = os.environ.get("RAG_BASE_URL", "http://localhost:8002").rstrip("/")
_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
_CLIENT = httpx.AsyncClient(base_url=RAG_BASE_URL, timeout=_TIMEOUT)


async def _proxy(request: Request, method: str, path: str, *, params: Optional[dict] = None) -> httpx.Response:
    """Forward an HTTP call to the RAG service, passthrough body/params."""
    try:
        # Forward raw body (JSON) and query params; RAG service has no auth.
        body = await request.body()
        headers = {"Content-Type": request.headers.get("content-type", "application/json")}
        return await _CLIENT.request(
            method, path, params=params, content=body, headers=headers,
        )
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"RAG service unavailable: {e}")


def _require_admin_or_supervisor(user: dict) -> None:
    if user.get("role") not in (Role.ADMIN, Role.SUPERVISOR):
        raise HTTPException(status_code=403, detail="Admin or supervisor access required")


@router.get("/rag/health", tags=["rag"])
async def rag_health():
    """RAG service health."""
    try:
        r = await _CLIENT.get("/health")
        return {"status": "healthy" if r.status_code == 200 else "unhealthy", "upstream": r.json() if r.headers.get("content-type", "").startswith("application/json") else None}
    except httpx.RequestError as e:
        return {"status": "unhealthy", "error": str(e)}


@router.post("/rag/search", tags=["rag"])
async def search(request: Request, user: dict = Depends(get_current_user)):
    """Semantic search — any authenticated user."""
    r = await _proxy(request, "POST", "/search")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.get("/rag/documents", tags=["rag"])
async def list_documents(
    request: Request,
    user: dict = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0,
):
    """List indexed documents — any authenticated user."""
    # RAG service exposes GET /documents/{id}/status; for listing we use collection info
    # plus scroll via /collection/info. The RAG service does not currently expose a
    # /documents list endpoint, so proxy /collection/info and let the client filter.
    r = await _proxy(request, "GET", "/collection/info", params={"limit": limit, "offset": offset})
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.post("/rag/ingest", tags=["rag"])
async def ingest(
    request: Request,
    file: UploadFile = File(...),
    metadata: str = Form(...),
    user: dict = Depends(get_current_user),
):
    """Proxy ingest — admin/supervisor only. Forwards FormData as-is."""
    _require_admin_or_supervisor(user)
    try:
        files = {"file": (file.filename, await file.read(), file.content_type or "application/octet-stream")}
        data = {"metadata": metadata}
        r = await _CLIENT.post("/ingest", files=files, data=data)
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"RAG service unavailable: {e}")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@router.delete("/rag/documents/{document_id}", tags=["rag"])
async def delete_document(
    document_id: str,
    user: dict = Depends(get_current_user),
):
    """Delete a document — admin/supervisor only."""
    _require_admin_or_supervisor(user)
    try:
        r = await _CLIENT.delete(f"/documents/{document_id}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail=f"RAG service unavailable: {e}")
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()
