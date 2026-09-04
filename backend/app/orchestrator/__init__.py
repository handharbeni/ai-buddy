"""Orchestrator package for BAPENDA Local AI Platform.

Handles end-to-end query processing: intent detection, tool planning,
tool execution, RAG retrieval, and response synthesis.
"""

from .pipeline import Pipeline
from app.llm.client import LLMClient
from app.llm.prompts import IntentDetector, ToolPlanner, PromptTemplate

__all__ = ["Pipeline"]