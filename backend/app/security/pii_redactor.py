"""PII (Personally Identifiable Information) redactor for BAPENDA Local AI Platform.

Redacts sensitive information from text before sending to LLM or logging.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class PIIPattern:
    """Pattern for detecting PII."""
    name: str
    pattern: str
    replacement: str
    description: str


class PIIRedactor:
    """Redacts PII from text."""

    def __init__(self):
        self.patterns = self._build_patterns()

    def _build_patterns(self) -> List[PIIPattern]:
        """Build list of PII patterns to redact."""
        return [
            # NPWP (Nomor Pokok Wajib Pajak) - 15 digits with dots and slash
            PIIPattern(
                name="npwp",
                pattern=r"\d{2}\.\d{3}\.\d{3}\.\d{1}-\d{3}\.\d{3}",
                replacement="[NPWP_REDACTED]",
                description="Nomor Pokok Wajib Pajak",
            ),
            # NPWPd (Nomor Pokok Wajib Pajak Daerah) - varies by region, typically 15-20 digits
            PIIPattern(
                name="npwpd",
                pattern=r"\d{15,20}",
                replacement="[NPWPD_REDACTED]",
                description="Nomor Pokok Wajib Pajak Daerah",
            ),
            # Email addresses
            PIIPattern(
                name="email",
                pattern=r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                replacement="[EMAIL_REDACTED]",
                description="Email address",
            ),
            # Phone numbers (Indonesian format)
            PIIPattern(
                name="phone",
                pattern=r"(\+62|62|0)8[1-9][0-9]{6,9}",
                replacement="[PHONE_REDACTED]",
                description="Indonesian phone number",
            ),
            # Names (simplified - looks for capitalized words that might be names)
            # Note: This is simplistic and may produce false positives. In production, use NER.
            PIIPattern(
                name="potential_name",
                pattern=r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b",
                replacement="[NAME_REDACTED]",
                description="Potential full name (two or more capitalized words)",
            ),
            # Addresses (simplified)
            PIIPattern(
                name="address",
                pattern=r"\d+\s+[A-Za-z\s]+(?:jalan|jl\.|raya|pasar|kampung|desa|kelurahan)\s+[A-Za-z\s]+",
                replacement="[ADDRESS_REDACTED]",
                description="Street address",
            ),
            # Bank account numbers
            PIIPattern(
                name="bank_account",
                pattern=r"\b\d{8,12}\b",
                replacement="[BANK_ACCOUNT_REDACTED]",
                description="Bank account number",
            ),
            # ID numbers (KTP/SIM)
            PIIPattern(
                name="id_number",
                pattern=r"\b\d{16}\b",
                replacement="[ID_NUMBER_REDACTED]",
                description="KTP/SIM number (16 digits)",
            ),
        ]

    def redact(self, text: str) -> str:
        """Redact all PII patterns from the text."""
        if not text:
            return text

        redacted = text
        for pattern in self.patterns:
            redacted = re.sub(
                pattern.pattern,
                pattern.replacement,
                redacted,
                flags=re.IGNORECASE,
            )
        return redacted

    def redact_and_count(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Redact PII and return counts of each type found."""
        if not text:
            return text, {}

        redacted = text
        counts = {}
        for pattern in self.patterns:
            # Find all matches
            matches = re.findall(pattern.pattern, text, flags=re.IGNORECASE)
            if matches:
                counts[pattern.name] = len(matches)
                redacted = re.sub(
                    pattern.pattern,
                    pattern.replacement,
                    redacted,
                    flags=re.IGNORECASE,
                )
        return redacted, counts

    def is_pii_present(self, text: str) -> bool:
        """Check if any PII is present in the text."""
        if not text:
            return False
        for pattern in self.patterns:
            if re.search(pattern.pattern, text, flags=re.IGNORECASE):
                return True
        return False