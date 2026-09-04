# Phase 7: Local LLM Integration - BAPENDA Local AI Data Intelligence Platform

## Overview

This document defines the Local LLM integration strategy for the BAPENDA Local AI Platform. The system uses Qwen2.5 models served locally via Ollama (development) and vLLM (production) to ensure data sovereignty and compliance with internal data policies.

## LLM Architecture

### Development Environment (Ollama)
- **Model**: Qwen2.5-14B-Instruct
- **Serving**: Ollama (http://localhost:11434)
- **GPU**: NVIDIA RTX 4090 (24GB VRAM) or equivalent
- **Model Format**: GGUF (quantized 4-bit)

### Production Environment (vLLM)
- **Model**: Qwen2.5-32B-Instruct or Qwen2.5-14B-Instruct
- **Serving**: vLLM with OpenAI-compatible API
- **GPU**: NVIDIA A100 80GB or H100 (multi-GPU with tensor parallelism)
- **Optimization**: Continuous batching, PagedAttention, FlashAttention

## Model Requirements

| Requirement | Development | Production |
|-------------|-------------|------------|
| **Model** | Qwen2.5-14B | Qwen2.5-14B/32B |
| **Context Length** | 32,768 tokens | 32,768 tokens |
| **Quantization** | 4-bit GGUF | AWQ/GPTQ 4-bit |
| **Throughput** | 1-5 req/s | 50+ req/s |
| **Latency (p50)** | < 2s | < 500ms |
| **Latency (p95)** | < 5s | < 2s |

## API Integration

### Ollama API (Development)
```
GET  /api/tags           - List available models
POST /api/generate       - Generate completion
POST /api/chat           - Chat completion
POST /api/embeddings     - Generate embeddings
```

### vLLM API (Production - OpenAI Compatible)
```
GET  /v1/models          - List available models
POST /v1/completions     - Text completion
POST /v1/chat/completions - Chat completion
POST /v1/embeddings      - Generate embeddings
```

## Prompt Engineering

### System Prompt
```
You are a tax intelligence assistant for Bapenda (Badan Pendapatan Daerah).
Your role is to answer questions using ONLY the provided tools and retrieved documents.

Rules:
1. NEVER generate SQL or execute database operations directly
2. ALWAYS use the provided MCP tools to query data
3. NEVER invent or hallucinate numbers - use tool results only
4. Cite all numerical values with tool source
5. For regulation questions, cite retrieved documents
6. If data is unavailable, say: "Data tidak tersedia pada sumber yang dapat saya akses."
7. Respond in Bahasa Indonesia unless asked otherwise
```

### Tool Calling Format
```json
{
  "tool": "get_tax_revenue",
  "parameters": {
    "period_start": "2025-01-01",
    "period_end": "2025-12-31",
    "region_code": "3201",
    "tax_type": "PBB"
  }
}
```

## Intent Detection & Tool Planning

The LLM performs three roles:
1. **Intent Classification**: Detect query type (revenue, arrears, growth, regulation, taxpayer)
2. **Tool Selection**: Choose appropriate MCP tools based on intent
3. **Response Generation**: Synthesize final answer with citations

## Token Budget Management

| Component | Budget (tokens) | Notes |
|-----------|-----------------|-------|
| System Prompt | 500 | Fixed |
| User Query | 500 | Variable |
| Tool Results | 2,000 | Max per tool |
| History | 1,000 | Last 3 exchanges |
| Generation | 500 | Response |
| **Total** | **4,500** | Within 32K limit |

## Implementation Details

### Backend Integration
```python
from app.llm.client import LLMClient, LLMConfig, LLMBackend

config = LLMConfig(
    backend=LLMBackend.OLLAMA,  # or VLLM
    base_url="http://ollama:11434",
    model_name="qwen2.5:14b",
    max_tokens=4096,
    temperature=0.1,
)

client = LLMClient(config)
response = await client.generate(GenerationRequest(
    prompt="User question...",
    system="System prompt...",
    max_tokens=1024,
))
```

### Streaming Response
```python
async for chunk in client.generate_stream(request):
    yield chunk  # SSE or WebSocket
```

## Prompt Injection Protection

1. **Sanitization**: Remove injection patterns before LLM
2. **System Prompt**: Immutable, cannot be overridden
3. **Input Validation**: Length limits, character validation
4. **Output Validation**: Verify no tool calls in response
5. **Token Limits**: Enforce strict token budgets

## Monitoring & Observability

| Metric | Target |
|--------|--------|
| Request Latency (p50) | < 2s (dev), < 500ms (prod) |
| Request Latency (p95) | < 5s (dev), < 2s (prod) |
| Error Rate | < 1% |
| Token Throughput | > 50 tok/s (prod) |
| GPU Utilization | 80-90% |

## Files Created

- `backend/app/llm/client.py` - Unified LLM client (Ollama/vLLM)
- `backend/app/llm/prompts.py` - Intent detection, tool planning, sanitization
- `backend/tests/llm/test_client.py` - Unit tests

## Next Steps

1. **Review** the LLM integration architecture
2. **Approve** before proceeding to Phase 8 (Security Hardening)
3. **Phase 7** will implement the orchestrator that connects LLM → MCP → DB

**Next Action**: Please review the LLM integration documentation and approve the architecture before I begin Phase 8 implementation.