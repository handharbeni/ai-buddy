"""Prompt templates and engineering for BAPENDA LLM integration."""

import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    """Base prompt template with formatting and validation."""
    
    template: str
    system_prompt: Optional[str] = None
    
    def format(self, **kwargs) -> str:
        """Format template with kwargs."""
        result = self.template.format(**kwargs)
        return result
    
    def sanitize(self, text: str) -> str:
        """Sanitize user input to prevent prompt injection."""
        # Remove or escape common injection patterns
        sanitized = text
        
        # Remove instructions to ignore system prompts
        patterns = [
            r"(?i)ignore\s+(previous|all|system|prior)\s+instructions",
            r"(?i)disregard\s+the\s+(system|prompt|instructions)",
            r"(?i)forget\s+(previous|all|system|prior)",
            r"(?i)override\s+(the\s+system|your|rules)",
            r"(?i)you\s+are\s+(now|henceforth)\s+",
            r"(?i)system\s*:\s*",
            r"(?i)namespace\s*:\s*",
            r"(?i)<\|channel\|>.*?<\|/channel\|>",
        ]
        
        for pattern in patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)
        
        return sanitized
    
    def assemble(
        self,
        user_content: str,
        system_parts: Optional[List[str]] = None,
    ) -> str:
        """Assemble prompt from parts with sanitization."""
        parts = []
        
        if self.system_prompt:
            parts.append(self.system_prompt)
        
        if system_parts:
            parts.extend(system_parts)
        
        # Sanitize user content
        sanitized_content = self.sanitize(user_content)
        parts.append(sanitized_content)
        
        return "\n\n".join(parts)


class IntentClassifier:
    """Classify user intent for query planning."""
    
    INTENT_PATTERNS = {
        "tax_revenue": [
            r"(?i)realisasi|penerimaan|penjualan|pajak.*target|%.*target",
            r"(?i)target\s+(tercapai|tercapai|tercapai)",
            r"(?i)pengumuman\s+(pengeluaran|penerimaan)",
        ],
        "tax_arrears": [
            r"(?i)tunggakan|terlambat|terhitung|aging|menunggak",
            r"(?i)hutang pajak|delinquent|delinquent",
            r"(?i)status\s+(wajib pajak|pajak)",
        ],
        "growth_statistics": [
            r"(?i)pertumbuhan|naik turun|naik menurun|trend|kenaikan",
            r"(?i)cagr|volatilitas|variansi|standard deviasi",
            r"(?i)perbandingan.*awal|perbandingan.*akhir",
        ],
        "regulation_search": [
            r"(?i)dokumen|peraturan|perda|pergub|sop|surat edaran",
            r"(?i)aturan|batasan|aturan penggunaan",
            r"(?i)mengambil kuat kuat|aturan mengenai",
        ],
        "taxpayer_info": [
            r"(?i)wajib pajak|npwpd|profil|pengguna|pembayaran",
            r"(?i)data\s+(pihak pajak|wajib)",
            r"(?i)ringkasan.*pajak|detail.*pajak",
        ],
        "general_query": [],
    }
    
    def classify(self, query: str) -> str:
        """Classify the intent of a user query."""
        if not query or not isinstance(query, str):
            return "general_query"
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query):
                    return intent
        
        return "general_query"


class ToolPlanner:
    """Plan which MCP tools to use based on intent and query."""
    
    def __init__(self, intent_classifier: IntentClassifier = None):
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.tool_map = {
            "tax_revenue": ["get_tax_revenue"],
            "tax_arrears": ["get_tax_arrears"],
            "growth_statistics": ["get_growth_statistics"],
            "regulation_search": ["search_regulation"],
            "taxpayer_info": ["get_taxpayer_summary"],
        }
    
    def plan(self, query: str, user_role: str = "STAFF", 
             available_scopes: List[str] = None) -> Dict[str, Any]:
        """Plan tool usage for a query.
        
        Returns a dict with:
        - intent: classified intent
        - tools: list of tools to use
        - scope: filtered scope based on user_role
        - reasons: explanation of tool choices
        """
        intent = self.intent_classifier.classify(query)
        
        # Get tools for this intent
        tools = self.tool_map.get(intent, [])
        
        # Filter scopes based on user role
        scope = available_scopes or ["region:3201"]
        if user_role == "STAFF":
            scope = [s for s in scope if s in ["region:3201", "tax_type:PBB"]]
        elif user_role == "SUPERVISOR":
            scope = [s for s in scope if s in ["region:3201", "tax_type:PBB", "tax_type:BPHTB"]]
        elif user_role == "ANALYST":
            scope = [s for s in scope if s not in ["own:"]]  # All except own restrictions
        # ADMIN keeps all scopes
        
        reasons = self._generate_reasons(intent, tools, query)
        
        return {
            "intent": intent,
            "tools": tools,
            "scope": scope,
            "reasons": reasons,
            "tool_count": len(tools),
        }
    
    def _generate_reasons(
        self,
        intent: str,
        tools: List[str],
        query: str,
    ) -> str:
        """Generate human-readable explanation for tool selection."""
        reasons = f"Query classified as {intent}"
        if tools:
            reasons += f". Tools: {', '.join(tools)}"
        else:
            reasons += ". No specialized tools required."
        
        if len(query) > 100:
            reasons += " (long query - may require multi-step processing)"
        
        return reasons