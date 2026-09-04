"""Output download API endpoints."""

import time
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.auth import get_current_user
from app.output import format_data, list_formats

router = APIRouter()


class DownloadRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Data rows from query")
    format: str = Field("xlsx", description="Output format: xlsx, docx, pdf, csv, json, html, md")
    question: str = Field("", description="Original question (for header/filename)")
    answer: str = Field("", description="LLM answer (for context in document)")


@router.get("/download/formats", tags=["download"])
async def get_formats():
    """List available download formats."""
    return {"formats": list_formats()}


@router.post("/download", tags=["download"])
async def download(
    request: DownloadRequest,
    req: Request,
    user: dict = Depends(get_current_user),
):
    """Format query data and return as downloadable file."""
    try:
        content, filename, mime_type = format_data(
            data=request.data,
            fmt=request.format,
            question=request.question,
            answer=request.answer,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Format error: {e}")

    # Log download for audit
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        f"Download: user={user.get('user_id')} format={request.format} "
        f"rows={len(request.data)} size={len(content)} filename={filename}"
    )

    return Response(
        content=content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Filename": filename,
        },
    )


@router.get("/download/{format}/{conversation_id}", tags=["download"])
async def download_by_conversation(
    format: str,
    conversation_id: str,
    req: Request,
    user: dict = Depends(get_current_user),
):
    """Download a previously-stored query result by conversation ID.

    Note: requires in-memory result storage (not implemented yet).
    """
    raise HTTPException(
        status_code=501,
        detail="Conversation-based download not yet implemented. "
               "Use POST /api/v1/download with the data payload.",
    )
