"""Prompt injection detection package."""

from .detector import (
    PromptInjectionDetector,
    DetectionResult,
    is_injection_attempt,
)

__all__ = ["PromptInjectionDetector", "DetectionResult", "is_injection_attempt"]
