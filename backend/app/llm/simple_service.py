"""Simple LLM service for direct Ollama integration.

Bypasses the complex orchestrator and provides a working AI response.
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator

import httpx

logger = logging.getLogger(__name__)


class SimpleLLMService:
    """Direct Ollama integration - no dependencies on complex orchestrator."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "bapenda-ai:latest",
        timeout_s: int = 120,
    ):
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout_s),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def health_check(self) -> Dict[str, Any]:
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            resp.raise_for_status()
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return {
                "status": "healthy",
                "backend": "ollama",
                "model": self.model,
                "available_models": models,
            }
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"status": "unhealthy", "backend": "ollama", "error": str(e)}

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Generate a response from the LLM.

        Returns dict with text, model, tokens_used, latency_ms.
        """
        start = time.time()
        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                # Disable thinking mode for faster responses
                "think": False,
            }
            if system:
                payload["system"] = system

            resp = await client.post("/api/generate", json=payload, timeout=httpx.Timeout(self.timeout_s))
            resp.raise_for_status()
            data = resp.json()

            latency_ms = (time.time() - start) * 1000
            return {
                "text": data.get("response", ""),
                "model": data.get("model", self.model),
                "tokens_used": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                "prompt_tokens": data.get("prompt_eval_count", 0),
                "completion_tokens": data.get("eval_count", 0),
                "latency_ms": round(latency_ms, 2),
                "finish_reason": data.get("done_reason", "stop"),
                "status": "success",
            }
        except httpx.TimeoutException:
            return {
                "text": "LLM request timed out. Please try again with a shorter question.",
                "model": self.model,
                "tokens_used": 0,
                "latency_ms": (time.time() - start) * 1000,
                "status": "timeout",
                "error": f"Request exceeded {self.timeout_s}s timeout",
            }
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return {
                "text": f"LLM error: {str(e)}",
                "model": self.model,
                "tokens_used": 0,
                "latency_ms": (time.time() - start) * 1000,
                "status": "error",
                "error": str(e),
            }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> Dict[str, Any]:
        """Multi-turn chat completion."""
        start = time.time()
        try:
            client = await self._get_client()
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
            }
            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

            latency_ms = (time.time() - start) * 1000
            message = data.get("message", {})
            return {
                "text": message.get("content", ""),
                "model": data.get("model", self.model),
                "tokens_used": data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
                "latency_ms": round(latency_ms, 2),
                "status": "success",
            }
        except Exception as e:
            logger.error(f"LLM chat failed: {e}")
            return {
                "text": f"LLM error: {str(e)}",
                "tokens_used": 0,
                "latency_ms": (time.time() - start) * 1000,
                "status": "error",
                "error": str(e),
            }

    async def generate_stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response as text chunks.

        Yields raw text chunks from the model.
        """
        try:
            client = await self._get_client()
            payload: Dict[str, Any] = {
                "model": self.model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                "think": False,
            }
            if system:
                payload["system"] = system

            async with client.stream(
                "POST", "/api/generate", json=payload, timeout=httpx.Timeout(self.timeout_s)
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk
                        if data.get("done"):
                            break
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            yield f"[LLM stream error: {e}]"


# Module-level singleton
_llm_service: Optional[SimpleLLMService] = None


def set_llm_service(service: SimpleLLMService):
    global _llm_service
    _llm_service = service


def get_llm_service() -> SimpleLLMService:
    if _llm_service is None:
        raise RuntimeError("LLM service not initialized")
    return _llm_service
