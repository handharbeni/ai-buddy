"""LLM client for BAPENDA Local AI Platform.

Supports both Ollama (development) and vLLM (production) backends
with a unified interface.
Uses centralized configuration for model selection.
"""

import time
import logging
from typing import List, Dict, Optional, AsyncGenerator
from dataclasses import dataclass
from enum import Enum

import httpx
from app.config import get_llm_config

logger = logging.getLogger(__name__)


class LLMBackend(str, Enum):
    """Supported LLM backends."""
    OLLAMA = "ollama"
    VLLM = "vllm"


@dataclass
class LLMConfig:
    """LLM configuration."""
    backend: LLMBackend = LLMBackend.OLLAMA
    base_url: str = "http://localhost:11434"
    model_name: str = "qwen2.5:14b"  # Will be overridden by config
    max_tokens: int = 4096
    temperature: float = 0.1
    top_p: float = 0.9
    timeout_s: int = 60


@dataclass
class GenerationRequest:
    """Request for LLM generation."""
    prompt: str
    system: Optional[str] = None
    max_tokens: int = 1024
    temperature: float = 0.1
    top_p: float = 0.9
    stop: Optional[List[str]] = None
    stream: bool = False
    json_mode: bool = False


@dataclass
class GenerationResponse:
    """Response from LLM generation."""
    text: str
    model: str
    tokens_used: int
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float
    finish_reason: str = "stop"


class LLMClient:
    """Unified client for Ollama and vLLM."""

    def __init__(self, config: Optional[LLMConfig] = None):
        # Use provided config or get from centralized config
        self.config = config or get_llm_config()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=httpx.Timeout(self.config.timeout_s),
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
            self._http_client = None

    async def health_check(self) -> Dict:
        """Check if LLM backend is healthy."""
        try:
            client = await self._get_client()

            if self.config.backend == LLMBackend.OLLAMA:
                response = await client.get("/api/tags")
            else:  # vLLM
                response = await client.get("/v1/models")

            response.raise_for_status()
            return {
                "status": "healthy",
                "backend": self.config.backend.value,
                "model": self.config.model_name,
            }
        except Exception as e:
            logger.error(f"LLM health check failed: {e}")
            return {
                "status": "unhealthy",
                "backend": self.config.backend.value,
                "error": str(e),
            }

    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate a completion from the LLM."""
        start_time = time.time()

        try:
            client = await self._get_client()

            if self.config.backend == LLMBackend.OLLAMA:
                response = await self._generate_ollama(client, request)
            else:
                response = await self._generate_vllm(client, request)

            response.latency_ms = (time.time() - start_time) * 1000
            return response

        except httpx.TimeoutException:
            raise TimeoutError(
                f"LLM request exceeded {self.config.timeout_s}s timeout"
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise RuntimeError(f"LLM generation failed: {e}")

    async def _generate_ollama(
        self,
        client: httpx.AsyncClient,
        request: GenerationRequest,
    ) -> GenerationResponse:
        """Generate using Ollama API."""
        payload = {
            "model": self.config.model_name,
            "prompt": request.prompt,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }

        if request.system:
            payload["system"] = request.system

        if request.stop:
            payload["options"]["stop"] = request.stop

        if request.json_mode:
            payload["format"] = "json"

        response = await client.post("/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()

        return GenerationResponse(
            text=data.get("response", ""),
            model=data.get("model", self.config.model_name),
            tokens_used=data.get("eval_count", 0) + data.get("prompt_eval_count", 0),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            latency_ms=0,  # Will be set by caller
            finish_reason=data.get("done_reason", "stop"),
        )

    async def _generate_vllm(
        self,
        client: httpx.AsyncClient,
        request: GenerationRequest,
    ) -> GenerationResponse:
        """Generate using vLLM OpenAI-compatible API."""
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": False,
        }

        if request.stop:
            payload["stop"] = request.stop

        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        response = await client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        choice = data["choices"][0]
        usage = data.get("usage", {})

        return GenerationResponse(
            text=choice["message"]["content"],
            model=data.get("model", self.config.model_name),
            tokens_used=usage.get("total_tokens", 0),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            latency_ms=0,  # Will be set by caller
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def generate_stream(
        self,
        request: GenerationRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from the LLM."""
        try:
            client = await self._get_client()

            if self.config.backend == LLMBackend.OLLAMA:
                async for chunk in self._stream_ollama(client, request):
                    yield chunk
            else:
                async for chunk in self._stream_vllm(client, request):
                    yield chunk
        except Exception as e:
            logger.error(f"LLM streaming failed: {e}")
            raise

    async def _stream_ollama(
        self,
        client: httpx.AsyncClient,
        request: GenerationRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream from Ollama."""
        payload = {
            "model": self.config.model_name,
            "prompt": request.prompt,
            "stream": True,
            "options": {
                "temperature": request.temperature,
                "top_p": request.top_p,
                "num_predict": request.max_tokens,
            },
        }

        if request.system:
            payload["system"] = request.system

        async with client.stream("POST", "/api/generate", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                import json
                if line.strip():
                    data = json.loads(line)
                    chunk = data.get("response", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        break

    async def _stream_vllm(
        self,
        client: httpx.AsyncClient,
        request: GenerationRequest,
    ) -> AsyncGenerator[str, None]:
        """Stream from vLLM."""
        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = {
            "model": self.config.model_name,
            "messages": messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": True,
        }

        async with client.stream("POST", "/v1/chat/completions", json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    chunk_data = line[6:]
                    if chunk_data.strip() == "[DONE]":
                        break
                    import json
                    data = json.loads(chunk_data)
                    if data["choices"]:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content