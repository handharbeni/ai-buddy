"""Query endpoint with full LLM+MCP+RAG orchestration."""

import re
import time
from uuid import uuid4
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

from app.auth import get_current_user
from app.db.base import ScopeFilter
from app.rbac import Role
from app.security.prompt_injection import PromptInjectionDetector

router = APIRouter()
_injection_detector = PromptInjectionDetector()


# ─── Request/Response Models ───────────────────────────────────────────────

class Message(BaseModel):
    role: str = Field(default="user")
    content: str


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    history: List[Message] = Field(default_factory=list)
    top_k: int = Field(5, ge=1, le=20)


class ToolUse(BaseModel):
    tool: str
    parameters: Dict[str, Any]
    result_preview: str


class QueryResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    intent: str  # "structured_query" | "regulation" | "general"
    conversation_id: str
    metadata: Dict[str, Any]
    # For structured queries: the raw data rows for download/table display
    data: List[Dict[str, Any]] = Field(default_factory=list)
    # Suggest a download format
    suggested_format: str = Field("xlsx")


# ─── Intent Detection (keyword-based, deterministic) ─────────────────────────

REGULATION_KEYWORDS = [
    "perda", "pergub", "uu ", "undang", "dasar hukum", "regulasi",
    "pasal", "ayat", "ayatnya", "peraturan", "sop ", "surat edaran",
    "izin", "insentif", "pajak daerah", "tarif", "persentase",
    "exemption", "exemption", "bebas pajak", "denda", "sanksi",
    "aturan", "ketentuan", "mekanisme", "prosedur", "cara ",
]
QUERY_KEYWORDS = [
    "jumlah", "total", "berapa", "hitung", "sum", "rata-rata",
    "growth", "pertumbuhan", "target", "realisasi", "pencapaian",
    "pendapatan", "penerimaan", "arrears", "piutang", "tunggakan",
    "bayar", "bayar", "wp ", "wajib pajak", "npwpd", "taxpayer",
    "perbandingan", "bandingkan", "komparasi", "vs ", "andai",
]


def detect_intent(question: str) -> str:
    """Determine query intent from question text."""
    q = question.lower()
    
    regulation_score = sum(1 for kw in REGULATION_KEYWORDS if kw in q)
    query_score = sum(1 for kw in QUERY_KEYWORDS if kw in q)
    
    if regulation_score > query_score:
        return "regulation"
    elif query_score > 0:
        return "structured_query"
    else:
        return "general"


# ─── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = """Anda adalah asisten AI untuk BAPENDA (Badan Pendapatan Daerah).
Jawab singkat dan tepat dalam Bahasa Indonesia.

Gunakan data dari hasil pencarian tool jika ada.
Jika ada data kuantitatif, sertakan angka dengan tepat.
Jika jawaban berdasarkan regulasi, sebutkan nama dokumen dan pasalnya."""


# ─── LLM Service getter ─────────────────────────────────────────────────────

def _get_llm_service_from_request(request: Request):
    """Get LLM service from app.state."""
    llm = getattr(request.app.state, "llm", None)
    if llm is None:
        raise RuntimeError("LLM service not initialized")
    return llm


# ─── MCP Tool Descriptions for LLM ─────────────────────────────────────────

MCP_TOOL_DESCRIPTIONS = """
Tool yang tersedia:
1. get_tax_revenue(period_start, period_end, region_code?, tax_type?) - Data penerimaan pajak
2. get_tax_arrears(period_start, period_end, region_code?, tax_type?) - Data piutang/tunggakan pajak
3. get_growth_statistics(period_start, period_end, region_code?, tax_type?) - Statistik pertumbuhan
4. get_region(region_code?, level?) - Data wilayah
5. get_taxpayer_summary(taxpayer_id) - Ringkasan wajib pajak
6. search_regulation(query, top_k?) - Cari regulasi

Format jawaban tool: [TOOL:tool_name|PARAM:value|...]
"""


# ─── Context Builder ────────────────────────────────────────────────────────

async def _build_query_context(question: str, user: dict, request: Request) -> tuple[str, List[str], List[Dict[str, Any]]]:
    """Build context from MCP database query results.

    Returns: (context_text, tools_used, raw_data_rows)
    """
    conversation_id = str(uuid4())
    mcp = getattr(request.app.state, "mcp_router", None)
    rag = getattr(request.app.state, "rag_service", None)
    llm = _get_llm_service_from_request(request)

    tools_used = []
    context_parts = []
    raw_data: List[Dict[str, Any]] = []  # accumulated data for download

    # ── Structured Query path ──────────────────────────────────────────────
    if detect_intent(question) == "structured_query":
        if mcp is None:
            context_parts.append("MCP router tidak tersedia (database tidak terhubung).")
        else:
            # Extract date/region/tax-type from question (simple regex)
            params = _extract_query_params(question)
            scope = _build_scope(user)
            role_str = user.get("role")
            if hasattr(role_str, "value"):
                role_str = role_str.value
            role_enum = Role(role_str) if isinstance(role_str, str) else role_str
            # Also patch scope.role to be the role string
            scope.role = role_str

            # Try tax revenue first
            if "pendapatan" in question.lower() or "penerimaan" in question.lower() or "pajak" in question.lower():
                try:
                    result = await mcp.execute(
                        tool_name="get_tax_revenue",
                        parameters=params.get("get_tax_revenue", {}),
                        role=role_enum,
                        scope=scope,
                    )
                    if result.status == "success":
                        data = result.result.data[:50] if result.result else []
                        if data:
                            # Save raw data for download
                            for row in data:
                                if isinstance(row, dict):
                                    raw_data.append(row)
                            context_parts.append(
                                f"Data Penerimaan Pajak:\n" +
                                "\n".join(_format_row(r) for r in data[:10])
                            )
                            tools_used.append("get_tax_revenue")
                except Exception as e:
                    context_parts.append(f"[Error querying tax data: {e}]")

            # Try growth statistics
            if "growth" in question.lower() or "pertumbuhan" in question.lower():
                try:
                    result = await mcp.execute(
                        tool_name="get_growth_statistics",
                        parameters=params.get("get_growth_statistics", {}),
                        role=role_enum,
                        scope=scope,
                    )
                    if result.status == "success":
                        data = result.result.data[:50] if result.result else []
                        if data:
                            for row in data:
                                if isinstance(row, dict):
                                    raw_data.append(row)
                            context_parts.append(
                                f"Statistik Pertumbuhan:\n" +
                                "\n".join(_format_row(r) for r in data[:10])
                            )
                            tools_used.append("get_growth_statistics")
                except Exception as e:
                    context_parts.append(f"[Error querying growth data: {e}]")

            # Try arrears
            if "tunggakan" in question.lower() or "arrears" in question.lower() or "piutang" in question.lower():
                try:
                    result = await mcp.execute(
                        tool_name="get_tax_arrears",
                        parameters=params.get("get_tax_arrears", {}),
                        role=role_enum,
                        scope=scope,
                    )
                    if result.status == "success":
                        data = result.result.data[:50] if result.result else []
                        if data:
                            for row in data:
                                if isinstance(row, dict):
                                    raw_data.append(row)
                            context_parts.append(
                                f"Data Tunggakan Pajak:\n" +
                                "\n".join(_format_row(r) for r in data[:10])
                            )
                            tools_used.append("get_tax_arrears")
                except Exception as e:
                    context_parts.append(f"[Error querying arrears data: {e}]")

    # ── Regulation path ────────────────────────────────────────────────────
    elif detect_intent(question) == "regulation":
        if rag is None:
            context_parts.append(
                "RAG service tidak tersedia. Qdrant mungkin belum berjalan atau belum ada dokumen terindeks.\n"
                "Silakan mulai Qdrant dan ingest dokumen regulasi terlebih dahulu."
            )
        else:
            try:
                results = await rag.search(
                    query=question,
                    top_k=5,
                    rerank=True,
                )
                if results.get("data"):
                    tools_used.append("search_regulation")
                    context_parts.append(
                        "Dokumen Regulasi Terkait:\n" +
                        "\n".join(
                            f"- {r['title']} ({r['document_number']}): {r['excerpt'][:300]}"
                            for r in results["data"]
                        )
                    )
                    # Save as table data for download
                    for r in results["data"]:
                        raw_data.append({
                            "title": r.get("title"),
                            "document_type": r.get("document_type"),
                            "document_number": r.get("document_number"),
                            "effective_date": r.get("effective_date"),
                            "classification": r.get("classification"),
                            "excerpt": (r.get("excerpt") or "")[:500],
                            "relevance_score": r.get("relevance_score"),
                        })
                    # Citations for response
                    citations = [
                        {
                            "title": r["title"],
                            "document_number": r["document_number"],
                            "document_type": r["document_type"],
                            "excerpt": r["excerpt"][:300],
                            "score": r["relevance_score"],
                        }
                        for r in results["data"]
                    ]
                else:
                    context_parts.append("Tidak ada dokumen regulasi yang relevan ditemukan.")
            except Exception as e:
                context_parts.append(f"[Error searching regulations: {e}]")

    # ── General path ───────────────────────────────────────────────────────
    else:
        context_parts.append("Tidak ada data konteks tambahan tersedia.")

    context = "\n\n".join(context_parts) if context_parts else "Tidak ada data tersedia."

    return context, tools_used, raw_data


def _format_row(row: Dict[str, Any]) -> str:
    """Format a DB row as readable text."""
    return "  " + " | ".join(f"{k}={v}" for k, v in row.items() if v is not None)


def _extract_query_params(question: str) -> dict:
    """Extract date/region/tax-type parameters from question text."""
    params = {}

    # Date patterns
    date_pattern = re.compile(r"(\d{4})[-/]?(\d{2})?[-/]?(\d{2})?|"
                               r"(januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)",
                               re.IGNORECASE)
    months = {
        "januari":"01","februari":"02","maret":"03","april":"04","mei":"05","juni":"06",
        "juli":"07","agustus":"08","september":"09","oktober":"10","november":"11","desember":"12"
    }

    # Region code: 4 digits
    region_match = re.search(r"\b(\d{4})\b", question)
    region_code = region_match.group(1) if region_match else None

    # Tax type
    tax_type = None
    q = question.lower()
    if "hotel" in q:
        tax_type = "HOTEL"
    elif "restoran" in q or "makan" in q:
        tax_type = "RESTORAN"
    elif "hiburan" in q:
        tax_type = "HIBURAN"
    elif "parkir" in q:
        tax_type = "PARKIR"
    elif "reklame" in q:
        tax_type = "REKLAME"
    elif "ppn" in q:
        tax_type = "PPN"
    elif "bbkb" in q:
        tax_type = "BBKB"

    # Year extraction
    year_match = re.search(r"20\d{2}", question)
    year = year_match.group() if year_match else "2024"

    # Build params for each tool
    params["get_tax_revenue"] = {
        "period_start": f"{year}-01-01",
        "period_end": f"{year}-12-31",
        "region_code": region_code,
        "tax_type": tax_type or "ALL",
        "group_by": "month",
    }
    params["get_tax_arrears"] = {
        "as_of_date": f"{year}-12-31",
        "region_code": region_code,
        "tax_type": tax_type,
        "status": "ALL",
    }
    params["get_growth_statistics"] = {
        "period_start": f"{year}-01-01",
        "period_end": f"{year}-12-31",
        "region_code": region_code,
        "tax_type": tax_type or "ALL",
    }
    params["get_region"] = {
        "region_code": region_code,
        "level": "ALL",
    }

    return params


def _build_scope(user: dict) -> ScopeFilter:
    """Build ScopeFilter from user data."""
    scope_data = user.get("scope", {})
    own_tp = scope_data.get("own_taxpayers")
    if isinstance(own_tp, bool):
        own_tp = [str(own_tp)] if own_tp else None
    return ScopeFilter(
        user_id=user.get("user_id", "UNKNOWN"),
        role=scope_data.get("role", "STAFF"),
        regions=scope_data.get("regions"),
        tax_types=scope_data.get("tax_types"),
        departments=scope_data.get("departments"),
        own_taxpayers=own_tp,
    )


# ─── Endpoint ────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    user: dict = Depends(get_current_user),
    req: Request = None,
):
    """Ask a question. System auto-detects intent and uses MCP+RAG+LLM."""
    # ── Zero Trust: prompt injection check at trust boundary ───────────
    detection = _injection_detector.detect(request.question)
    if detection.blocked:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail={
                "error": "prompt_injection_blocked",
                "message": "Permintaan Anda mengandung pola yang tidak diizinkan. Silakan ajukan pertanyaan yang relevan dengan data.",
                "layer": detection.layer,
                "confidence": detection.confidence,
            }
        )

    conversation_id = str(uuid4())
    intent = detect_intent(request.question)
    llm = _get_llm_service_from_request(req)

    start = time.time()

    # Build context from MCP/RAG
    context, tools_used, raw_data = await _build_query_context(
        request.question, user, req
    )

    # Synthesize with LLM (pass history as part of prompt for context)
    history_context = ""
    for msg in request.history[-6:]:
        history_context += f"\n{msg.role.upper()}: {msg.content}"

    full_prompt = f"{context}\n{history_context}\n\nPertanyaan: {request.question}\n\nJawaban:"

    try:
        result = await llm.generate(
            prompt=full_prompt,
            system=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=256,
        )
        answer = result.get("text", "Maaf, terjadi kesalahan dalam menghasilkan jawaban.")
        llm_status = "success"
    except Exception as e:
        answer = f"Maaf, terjadi kesalahan: {e}"
        llm_status = "error"

    latency_ms = (time.time() - start) * 1000

    # Suggest format based on data size
    if not raw_data:
        suggested_format = "docx"  # empty download still useful
    elif len(raw_data) > 100:
        suggested_format = "xlsx"  # large → spreadsheet
    else:
        suggested_format = "xlsx"  # default to spreadsheet

    return QueryResponse(
        answer=answer,
        citations=[],  # filled by _build_query_context if RAG used
        tools_used=[f"llm:bapenda-ai:latest"] + tools_used,
        intent=intent,
        conversation_id=conversation_id,
        metadata={
            "user_id": user.get("user_id"),
            "role": user.get("role"),
            "model": "bapenda-ai:latest",
            "latency_ms": round(latency_ms, 2),
            "llm_status": llm_status,
            "context_used": bool(context),
            "mcp_available": getattr(req.app.state, "mcp_router", None) is not None,
            "rag_available": getattr(req.app.state, "rag_service", None) is not None,
            "row_count": len(raw_data),
        },
        data=raw_data,
        suggested_format=suggested_format,
    )


@router.post("/query/chat", response_model=QueryResponse)
async def chat(
    request: QueryRequest,
    user: dict = Depends(get_current_user),
    req: Request = None,
):
    """Multi-turn chat. Same as /query but preserves history."""
    return await query(request, user, req)
