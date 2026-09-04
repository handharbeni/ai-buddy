"""Orchestrator pipeline for end-to-end query processing.

Coordinates intent detection, tool planning, tool execution, RAG retrieval,
and response synthesis to answer user questions using approved data sources.
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional
from uuid import uuid4

from app.llm.client import LLMClient, GenerationRequest
from app.llm.prompts import IntentDetector, ToolPlanner
from app.mcp import MCPRouter, ToolResponse
from app.rag.search import SearchService
from app.rbac.service import RBACService, Role, Resource, Action

logger = logging.getLogger(__name__)


class Pipeline:
    """Main orchestrator pipeline for processing user queries."""

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_router: MCPRouter,
        rag_search_service: SearchService,
        rbac_service: RBACService,
    ):
        self.llm = llm_client
        self.mcp = mcp_router
        self.rag = rag_search_service
        self.rbac = rbac_service

        # Initialize intent detector and tool planner
        self.intent_detector = IntentDetector()
        self.tool_planner = ToolPlanner()

        # System prompt for the LLM (tax assistant)
        self.system_prompt = (
            "You are a tax intelligence assistant for Bapenda (Badan Pendapatan Daerah). "
            "Your role is to answer questions using ONLY the provided tools and retrieved documents. "
            "Rules:\n"
            "1. NEVER generate SQL or execute database operations directly.\n"
            "2. ALWAYS use the provided MCP tools to query data.\n"
            "3. NEVER invent or hallucinate numbers - use tool results only.\n"
            "4. Cite all numerical values with tool source.\n"
            "5. For regulation questions, cite retrieved documents.\n"
            "6. If data is unavailable, say: \"Data tidak tersedia pada sumber yang dapat saya akses.\"\n"
            "7. Respond in Bahasa Indonesia unless asked otherwise.\n"
            "8. Keep answers concise and focused on the question."
        )

    async def process_query(
        self,
        query: str,
        user_id: str,
        role: Role,
        scope: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a user query end-to-end.

        Args:
            query: User's natural language question.
            user_id: Authenticated user ID.
            role: User's role (ADMIN, SUPERVISOR, ANALYST, STAFF).
            scope: User's scope (regions, tax_types, etc.).
            conversation_id: Optional conversation ID for tracking.

        Returns:
            Dictionary containing the answer, citations, tools used, and metadata.
        """
        start_time = time.time()
        request_id = str(uuid4())
        conversation_id = conversation_id or str(uuid4())

        logger.info(
            f"Processing query {request_id}: '{query[:100]}...' "
            f"user={user_id} role={role.value}"
        )

        try:
            # Step 1: Detect intent and plan tool usage
            intent = self.intent_detector.detect(query)
            tool_plan = self.tool_planner.plan(
                query=query,
                user_role=role.value,
                available_scopes=scope.get("regions", []) + scope.get("tax_types", []),
            )

            logger.info(
                f"Query {request_id} intent: {intent}, "
                f"planned tools: {tool_plan.tools}"
            )

            # Step 2: Execute planned tools in parallel
            tool_results = await self._execute_tools(
                tool_plan=tool_plan,
                user_id=user_id,
                role=role,
                scope=scope,
            )

            # Step 3: Perform RAG search if regulation-related
            rag_results = []
            if self._is_regulation_intent(intent):
                rag_results = await self._search_regulations(
                    query=query,
                    scope=scope,
                )

            # Step 4: Synthesize final answer using LLM
            answer, citations = await self._synthesize_answer(
                query=query,
                intent=intent,
                tool_results=tool_results,
                rag_results=rag_results,
            )

            # Step 5: Prepare response
            latency_ms = (time.time() - start_time) * 1000

            response = {
                "request_id": request_id,
                "conversation_id": conversation_id,
                "answer": answer,
                "citations": citations,
                "tools_used": [t.tool for t in tool_results if t.status == "success"],
                "rag_results_count": len(rag_results),
                "metadata": {
                    "user_id": user_id,
                    "role": role.value,
                    "intent": intent,
                    "tool_plan": {
                        "tools": [t.tool for t in tool_plan.tools],
                        "reasoning": tool_plan.reasoning,
                    },
                    "latency_ms": round(latency_ms, 2),
                    "timestamp": time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()
                    ),
                },
            }

            logger.info(
                f"Query {request_id} completed in {latency_ms:.2f}ms "
                f"with {len(tool_results)} tool results and {len(rag_results)} RAG results"
            )

            return response

        except Exception as e:
            logger.error(f"Query {request_id} failed: {e}", exc_info=True)
            return {
                "request_id": request_id,
                "conversation_id": conversation_id,
                "answer": "Maaf, terjadi kesalahan saat memproses pertanyaan Anda. Silakan coba lagi nanti.",
                "citations": [],
                "tools_used": [],
                "rag_results_count": 0,
                "metadata": {
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000,
                },
            }

    async def _execute_tools(
        self,
        tool_plan: Any,  # ToolPlan from ToolPlanner
        user_id: str,
        role: Role,
        scope: Dict[str, Any],
    ) -> List[Any]:  # List of ToolResponse
        """Execute the planned tools in parallel."""
        # Convert scope to ScopeFilter-like dict for MCP router
        mcp_scope = {
            "regions": scope.get("regions", []),
            "tax_types": scope.get("tax_types", []),
            "departments": scope.get("departments", []),
            "own_taxpayers": scope.get("own_taxpayers", []),
        }

        # Prepare tool execution tasks
        tasks = []
        for tool_name in tool_plan.tools:
            # Get tool parameters from the plan (simplified - in reality, the planner would extract these)
            # For now, we'll use empty parameters and let the tool use defaults
            # In a full implementation, the tool planner would extract parameters from the query
            parameters = {}

            task = self.mcp.execute(
                tool_name=tool_name,
                parameters=parameters,
                role=role,
                scope=mcp_scope,
            )
            tasks.append(task)

        # Execute all tools in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        tool_results = []
        for i, result in enumerate(results):
            tool_name = tool_plan.tools[i]
            if isinstance(result, Exception):
                logger.error(f"Tool {tool_name} failed: {result}")
                # Create an error response
                tool_results.append(
                    type(
                        "ToolResponse",
                        (),
                        {
                            "status": "error",
                            "tool": tool_name,
                            "error": {"code": "INTERNAL_ERROR", "message": str(result)},
                        },
                    )()
                )
            else:
                tool_results.append(result)

        return tool_results

    def _is_regulation_intent(self, intent: str) -> bool:
        """Check if the intent requires RAG search."""
        return intent in ["regulation_search", "general_query"]  # Simplified

    async def _search_regulations(
        self,
        query: str,
        scope: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Search for relevant regulations using RAG."""
        try:
            # Build filter from scope
            filters = {}
            if scope.get("regions"):
                # Note: RAG search currently doesn't filter by region in the vector store
                # This would require extending the document metadata to include regions
                pass
            if scope.get("tax_types"):
                filters["tax_types"] = scope["tax_types"]

            results = await self.rag.search(
                query=query,
                document_types=None,  # Search all types
                classification=None,  # Search all classifications
                top_k=5,
                rerank=True,
                **filters,  # Pass any additional filters
            )

            return results.get("data", [])

        except Exception as e:
            logger.error(f"RAG search failed: {e}")
            return []

    async def _synthesize_answer(
        self,
        query: str,
        intent: str,
        tool_results: List[Any],
        rag_results: List[Dict[str, Any]],
    ) -> tuple[str, List[Dict[str, Any]]]:
        """Synthesize a final answer using the LLM with citations."""
        # Prepare context for the LLM
        context_parts = []

        # Add tool results
        for tool_result in tool_results:
            if getattr(tool_result, "status", None) == "success":
                data = getattr(tool_result, "result", None)
                if data and hasattr(data, "data"):
                    # Format the data for the LLM
                    formatted_data = self._format_tool_data(
                        tool_result.tool, data.data
                    )
                    context_parts.append(
                        f"Hasil dari alat {tool_result.tool}:\n{formatted_data}"
                    )

        # Add RAG results
        if rag_results:
            rag_context = self._format_rag_results(rag_results)
            context_parts.append(
                f"Dokumen peraturan yang relevan:\n{rag_context}"
            )

        # Combine context
        context = "\n\n".join(context_parts) if context_parts else "Tidak ada data tambahan."

        # Create the prompt for the LLM
        prompt = (
            f"Pertanyaan pengguna: {query}\n\n"
            f"Konteks dari alat dan dokumen:\n{context}\n\n"
            "Instruksi: Jawab pertanyaan pengguna berdasarkan konteks yang diberikan. "
            "Jawab dalam Bahasa Indonesia. Sertakan kutipan dari sumber-sumber yang digunakan. "
            "Jika tidak ada data yang cukup, katakan: 'Data tidak tersedia pada sumber yang dapat saya akses.'"
        )

        # Generate response from LLM
        generation_request = GenerationRequest(
            prompt=prompt,
            system=self.system_prompt,
            max_tokens=1024,
            temperature=0.1,
            top_p=0.9,
        )

        try:
            llm_response = await self.llm.generate(generation_request)
            answer = llm_response.text.strip()

            # Extract citations from the context (simplified)
            citations = self._extract_citations(
                tool_results=tool_results,
                rag_results=rag_results,
                answer=answer,
            )

            return answer, citations

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return (
                "Maaf, terjadi kesalahan saat menghasilkan jawaban. Silakan coba lagi nanti.",
                [],
            )

    def _format_tool_data(self, tool_name: str, data: List[Dict[str, Any]]) -> str:
        """Format tool data for inclusion in the LLM prompt."""
        if not data:
            return "Tidak ada data yang ditemukan."

        # Limit to first 5 rows to avoid overwhelming the LLM
        limited_data = data[:5]

        # Format as a simple table
        if not limited_data:
            return "Tidak ada data."

        # Get headers from the first row
        headers = list(limited_data[0].keys())
        rows = []
        for row in limited_data:
            rows.append([str(row.get(h, "")) for h in headers])

        # Create a simple text table
        lines = []
        lines.append(" | ".join(headers))
        lines.append("-" * (len(" | ".join(headers))))
        for row in rows:
            lines.append(" | ".join(row))

        return "\n".join(lines)

    def _format_rag_results(self, results: List[Dict[str, Any]]) -> str:
        """Format RAG results for inclusion in the LLM prompt."""
        if not results:
            return "Tidak ada dokumen peraturan yang relevan yang ditemukan."

        formatted = []
        for i, doc in enumerate(results[:3], 1):  # Limit to top 3
            formatted.append(
                f"{i}. {doc.get('title', 'Tanpa judul')} "
                f"({doc.get('document_number', 'Tanpa nomor')}) "
                f"diperiksa pada {doc.get('effective_date', 'Tanggal tidak diketahui')}: "
                f"{doc.get('excerpt', '')[:200]}..."
            )

        return "\n".join(formatted)

    def _extract_citations(
        self,
        tool_results: List[Any],
        rag_results: List[Dict[str, Any]],
        answer: str,
    ) -> List[Dict[str, Any]]:
        """Extract citations from the context for the final answer."""
        citations = []

        # Tool citations
        for tool_result in tool_results:
            if getattr(tool_result, "status", None) == "success":
                # In a real implementation, we would extract specific rows that were cited
                # For now, we cite the tool generally
                citations.append(
                    {
                        "type": "tool",
                        "tool": getattr(tool_result, "tool", "unknown"),
                        "description": f"Hasil dari alat {getattr(tool_result, 'tool', 'unknown')}",
                    }
                )

        # RAG citations
        for doc in rag_results:
            citations.append(
                {
                    "type": "regulation",
                    "document_id": doc.get("document_id"),
                    "title": doc.get("title"),
                    "document_number": doc.get("document_number"),
                    "excerpt": doc.get("excerpt"),
                }
            )

        # Deduplicate citations (simplified)
        unique_citations = []
        seen = set()
        for cit in citations:
            key = (cit.get("type"), cit.get("tool") or cit.get("document_id"))
            if key not in seen:
                seen.add(key)
                unique_citations.append(cit)

        return unique_citations


# Factory function for creating the pipeline
def create_pipeline(
    llm_client: LLMClient,
    mcp_router: MCPRouter,
    rag_search_service: SearchService,
    rbac_service: RBACService,
) -> Pipeline:
    """Factory function to create a Pipeline instance."""
    return Pipeline(
        llm_client=llm_client,
        mcp_router=mcp_router,
        rag_search_service=rag_search_service,
        rbac_service=rbac_service,
    )