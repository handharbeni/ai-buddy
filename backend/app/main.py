"""FastAPI application entry point — Local AI Data Intelligence Platform.

Rename the project by setting environment variables:
  APP_NAME          — displayed title (e.g. "BAPENDA AI Platform")
  APP_TAGLINE       — subtitle
  APP_INSTITUTION   — e.g. "BAPENDA Batam"
  APP_DOMAIN        — e.g. "tax", "healthcare"
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from app.config import settings, get_branding, DATABASE_CONFIGS
from app.db import OracleAdapter, PostgreSQLAdapter, MySQLAdapter
from app.db.mocks.mock_adapter import MockAdapter
from app.auth.service import AuthService, SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
from app.rbac import RBACService
from app.api.v1 import query_router, auth_router, config_router, conversations_router, users_router
from app.api.v1.auth import set_auth_service
from app.api.v1.llm import router as llm_router
from app.api.v1.rag import router as rag_router
from app.api.v1.mcp import mcp_api
from app.api.v1.download import router as download_router
from app.api.v1.websocket import router as websocket_router
from app.llm.simple_service import SimpleLLMService, set_llm_service
from app.mcp import MCPRouter
from app.metrics.middleware import install_metrics

logger = logging.getLogger(__name__)


def _build_db_adapters() -> dict:
    """Build DB adapters. Auto-detects all DBs registered in DATABASE_CONFIGS.
    
    Falls back to MockAdapter when no credentials are available.
    Force mock with USE_MOCK_DB=1.
    """
    if os.environ.get("USE_MOCK_DB", "").lower() in ("1", "true"):
        logger.info("USE_MOCK_DB=1 — using mock adapters for all databases")
        return {
            "oracle": MockAdapter(),
            "postgresql": MockAdapter(),
            "mysql": MockAdapter(),
        }

    adapters = {}

    # Oracle
    oracle_configs = DATABASE_CONFIGS.get("oracle", {})
    if oracle_configs:
        for name in oracle_configs:
            try:
                adapters["oracle"] = OracleAdapter.from_config(name)
                logger.info(f"Oracle adapter: {name} ({oracle_configs[name]['host']})")
            except Exception as e:
                logger.warning(f"Oracle {name} failed ({e}) — using mock")
                adapters["oracle"] = MockAdapter()
    else:
        adapters["oracle"] = MockAdapter()
        logger.info("Oracle: no config — using mock")

    # PostgreSQL
    pg_configs = DATABASE_CONFIGS.get("postgresql", {})
    if pg_configs:
        for name, cfg in pg_configs.items():
            password = cfg.get("password") or os.environ.get(cfg["password_env"], "")
            try:
                adapter = PostgreSQLAdapter(
                    dsn=cfg.get("database", ""),
                    username=cfg.get("user", ""),
                    password=password,
                    host=cfg.get("host", ""),
                    port=cfg.get("port", 5432),
                )
                adapters["postgresql"] = adapter
                logger.info(f"PostgreSQL adapter: {name} ({cfg['host']})")
            except Exception as e:
                logger.warning(f"PostgreSQL {name} failed ({e}) — using mock")
                adapters["postgresql"] = MockAdapter()
    else:
        adapters["postgresql"] = MockAdapter()
        logger.info("PostgreSQL: no config — using mock")

    # MySQL
    mysql_configs = DATABASE_CONFIGS.get("mysql", {})
    if mysql_configs:
        for name, cfg in mysql_configs.items():
            password = cfg.get("password") or os.environ.get(cfg["password_env"], "")
            try:
                adapter = MySQLAdapter(
                    dsn=cfg.get("database", ""),
                    username=cfg.get("user", ""),
                    password=password,
                    host=cfg.get("host", ""),
                    port=cfg.get("port", 3306),
                )
                adapters["mysql"] = adapter
                logger.info(f"MySQL adapter: {name} ({cfg['host']})")
            except Exception as e:
                logger.warning(f"MySQL {name} failed ({e}) — using mock")
                adapters["mysql"] = MockAdapter()
    else:
        adapters["mysql"] = MockAdapter()
        logger.info("MySQL: no config — using mock")

    return adapters


def _build_rag_service():
    """Build RAG search service. Returns None if Qdrant is unavailable."""
    qdrant_url = settings.qdrant_url
    try:
        from qdrant_client import QdrantClient
        import sys

        # RAG module lives in /rag/app/
        rag_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "rag", "app"
        )
        if not os.path.exists(rag_path):
            logger.warning(f"RAG path not found: {rag_path}")
            return None

        sys.path.insert(0, os.path.dirname(rag_path))
        try:
            from app.search import SearchService
        except ImportError:
            from app.rag_app.search import SearchService  # type: ignore

        client = QdrantClient(url=qdrant_url, prefer_grpc=False)
        client.get_collections()
        service = SearchService(
            qdrant_client=client,
            embedding_model_name=settings.embedding_model,
        )
        logger.info(f"RAG service: Qdrant={qdrant_url}, model={settings.embedding_model}")
        return service
    except Exception as e:
        logger.warning(f"RAG service not available ({e})")
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    branding = get_branding()
    logger.info(f"Starting {branding.name} v{branding.version}")

    # Database adapters
    app.state.db = _build_db_adapters()

    # Auth & RBAC services
    app.state.auth = AuthService(app.state.db)
    app.state.rbac = RBACService(app.state.db)
    set_auth_service(app.state.auth)
    logger.info("Auth/RBAC services registered")

    # MCP Router
    app.state.mcp_router = MCPRouter(
        db_adapters=app.state.db,
        rbac_service=app.state.rbac,
    )

    # RAG service
    app.state.rag_service = _build_rag_service()

    # LLM service
    app.state.llm = SimpleLLMService(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        timeout_s=settings.llm_timeout,
    )
    set_llm_service(app.state.llm)
    logger.info(f"LLM: {settings.llm_model} @ {settings.llm_base_url}")

    yield

    # Shutdown
    if hasattr(app.state, "llm") and app.state.llm:
        await app.state.llm.close()
    for db in getattr(app.state, "db", {}).values():
        try:
            await db.close()
        except Exception as e:
            logger.warning(f"Error closing db: {e}")


branding = get_branding()

app = FastAPI(
    title=branding.name,
    version=branding.version,
    description=branding.tagline,
    lifespan=lifespan,
)

# CORS
origins = settings.cors_origins or [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(config_router, prefix="/api/v1", tags=["config"])
app.include_router(query_router, prefix="/api/v1", tags=["query"])
app.include_router(llm_router, prefix="/api/v1", tags=["llm"])
app.include_router(mcp_api, prefix="/api/v1", tags=["mcp"])
app.include_router(rag_router, prefix="/api/v1", tags=["rag"])
app.include_router(download_router, prefix="/api/v1", tags=["download"])
app.include_router(conversations_router, prefix="/api/v1", tags=["conversations"])
app.include_router(users_router, prefix="/api/v1", tags=["users"])
app.include_router(websocket_router, prefix="/api/v1", tags=["websocket"])

# Metrics: install middleware + route map after all routers are registered.
install_metrics(app)


@app.options("/{full_path:path}")
async def options_handler(full_path: str):
    return JSONResponse(content={"status": "ok"}, status_code=200)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": branding.short_name}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint. No auth — scraped by Prometheus."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    from fastapi.responses import Response

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/")
async def root():
    return {
        "service": branding.name,
        "version": branding.version,
        "institution": branding.institution,
        "domain": branding.domain,
        "docs": "/docs",
    }
