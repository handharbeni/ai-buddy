"""RAG data models for BAPENDA Local AI Platform."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class DocumentType(str, Enum):
    PERDA = "PERDA"
    PERGUB = "PERGUB"
    SOP = "SOP"
    SURAT_EDARAN = "SURAT_EDARAN"
    PERMEN = "PERMEN"
    PERDIR = "PERDIR"
    GENERAL = "GENERAL"


class Classification(str, Enum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    RESTRICTED = "RESTRICTED"


class ApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    REVIEW = "REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class RegulationDocument(BaseModel):
    """Regulation document model for RAG."""
    document_id: str = Field(..., pattern=r"^REG_\d{8}_\d{4}$")
    title: str
    document_type: DocumentType
    document_number: str
    issuing_authority: str
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    classification: Classification
    approval_status: ApprovalStatus
    version: str = Field(..., pattern=r"^v\d+(\.\d+)?$")
    tax_types: List[str] = []
    regions: List[str] = []
    keywords: List[str] = []
    content_hash: str = Field(..., pattern=r"^[a-f0-9]{64}$")  # SHA-256
    source_url: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None

    class Config:
        use_enum_values = True