"""LLM health check endpoint."""

from fastapi import APIRouter, HTTPException
from app.llm.simple_service import get_llm_service

router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/health")
async def llm_health():
    """Check Ollama LLM health."""
    try:
        llm = get_llm_service()
        return await llm.health_check()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
