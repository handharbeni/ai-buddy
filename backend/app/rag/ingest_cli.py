"""RAG Ingestion CLI — batch upload documents to Qdrant.

Usage:
    python -m app.rag.ingest_cli ingest <file> --title "..." --type PERDA --number "..."
    python -m app.rag.ingest_cli ingest-batch <directory> --pattern "*.txt" --type PERDA
    python -m app.rag.ingest_cli list
    python -m app.rag.ingest_cli delete <document_id>
    python -m app.rag.ingest_cli info
    python -m app.rag.ingest_cli test-connection

Standalone — no FastAPI server needed. Talks directly to Qdrant.
"""
import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    PointStruct,
    VectorParams,
    Distance,
    Filter,
    FieldCondition,
    MatchValue,
)
from sentence_transformers import SentenceTransformer

from app.config import get_settings
from app.rag.models import (
    DocumentType,
    Classification,
    ApprovalStatus,
    RegulationDocument,
)
from app.rag.ingestion import DocumentIngester

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("rag-ingest")


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    url = settings.qdrant_url or "http://localhost:6333"
    # Parse host:port from URL
    if "://" in url:
        url = url.split("://", 1)[1]
    host, _, port = url.partition(":")
    port = int(port) if port else 6333
    return QdrantClient(host=host, port=port)


def read_file_content(path: Path) -> str:
    """Read text from .txt, .md, .json, .pdf (best-effort), .docx (best-effort)."""
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md", ".csv", ".log"):
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".json":
        return path.read_text(encoding="utf-8", errors="ignore")
    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return "\n".join(p.extract_text() or "" for p in reader.pages)
        except ImportError:
            log.warning("pypdf not installed, falling back to raw bytes")
            return path.read_bytes().decode("utf-8", errors="ignore")
    if suffix == ".docx":
        try:
            import docx
            doc = docx.Document(str(path))
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            log.warning("python-docx not installed, falling back to raw bytes")
            return path.read_bytes().decode("utf-8", errors="ignore")
    # Fallback: best-effort text decode
    return path.read_bytes().decode("utf-8", errors="ignore")


def make_document_id(prefix: str = "REG") -> str:
    """Generate a unique document_id like REG_20260903_0001."""
    now = datetime.utcnow()
    return f"{prefix}_{now.strftime('%Y%m%d')}_{now.strftime('%H%M%S%f')[:4]}"


async def cmd_ingest(args):
    path = Path(args.file)
    if not path.exists():
        log.error(f"File not found: {path}")
        return 1

    log.info(f"Reading: {path}")
    content = read_file_content(path)
    log.info(f"  size: {len(content)} chars")

    # Compute hash
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    log.info(f"  sha256: {content_hash[:16]}...")

    # Auto-generate document_id if not provided
    doc_id = args.document_id or make_document_id("REG")

    # Build document
    document = RegulationDocument(
        document_id=doc_id,
        title=args.title or path.stem,
        document_type=DocumentType(args.type),
        document_number=args.number or path.stem,
        issuing_authority=args.authority or "Unknown",
        effective_date=datetime.fromisoformat(args.effective_date) if args.effective_date else datetime.utcnow(),
        classification=Classification(args.classification),
        approval_status=ApprovalStatus.APPROVED,  # CLI = manual approval
        version=args.version,
        tax_types=args.tax_types or [],
        regions=args.regions or [],
        keywords=args.keywords or [],
        content_hash=content_hash,
        source_url=args.source_url,
        created_at=datetime.utcnow(),
        approved_at=datetime.utcnow(),
        approved_by="cli-tool",
    )

    client = get_qdrant_client()
    ingester = DocumentIngester(client, embedding_model=args.embedding_model)

    log.info(f"Ingesting: {document.document_id} ({document.document_type})")
    chunk_ids = await ingester.ingest_document(document, content)
    log.info(f"✅ Done: {len(chunk_ids)} chunks indexed")

    print(json.dumps({
        "document_id": document.document_id,
        "chunks": len(chunk_ids),
        "content_hash": content_hash,
        "title": document.title,
    }, indent=2))
    return 0


async def cmd_ingest_batch(args):
    directory = Path(args.directory)
    if not directory.is_dir():
        log.error(f"Not a directory: {directory}")
        return 1

    pattern = args.pattern or "*"
    files = sorted(directory.glob(pattern))
    # Filter out hidden files and the directory itself
    files = [f for f in files if f.is_file() and not f.name.startswith(".")]

    if not files:
        log.warning(f"No files match {pattern} in {directory}")
        return 1

    log.info(f"Found {len(files)} files matching {pattern}")
    client = get_qdrant_client()
    ingester = DocumentIngester(client, embedding_model=args.embedding_model)

    results = []
    for i, file in enumerate(files, 1):
        try:
            content = read_file_content(file)
            if len(content.strip()) < 50:
                log.warning(f"  [{i}/{len(files)}] SKIP (too short): {file.name}")
                continue

            content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            doc_id = make_document_id(f"REG{args.type}")
            document = RegulationDocument(
                document_id=doc_id,
                title=args.title_prefix + file.stem if args.title_prefix else file.stem,
                document_type=DocumentType(args.type),
                document_number=args.number_prefix + file.stem if args.number_prefix else file.stem,
                issuing_authority=args.authority or "Unknown",
                effective_date=datetime.fromisoformat(args.effective_date) if args.effective_date else datetime.utcnow(),
                classification=Classification(args.classification),
                approval_status=ApprovalStatus.APPROVED,
                version=args.version,
                tax_types=args.tax_types or [],
                regions=args.regions or [],
                keywords=args.keywords or [],
                content_hash=content_hash,
                created_at=datetime.utcnow(),
                approved_at=datetime.utcnow(),
                approved_by="cli-batch",
            )
            chunk_ids = await ingester.ingest_document(document, content)
            log.info(f"  [{i}/{len(files)}] ✅ {file.name}: {len(chunk_ids)} chunks")
            results.append({"file": file.name, "doc_id": doc_id, "chunks": len(chunk_ids)})
        except Exception as e:
            log.error(f"  [{i}/{len(files)}] ❌ {file.name}: {e}")
            results.append({"file": file.name, "error": str(e)})

    # Summary
    ok = sum(1 for r in results if "chunks" in r)
    fail = sum(1 for r in results if "error" in r)
    log.info(f"\n=== Batch complete: {ok} success, {fail} failed ===")
    print(json.dumps({"results": results, "summary": {"ok": ok, "fail": fail}}, indent=2))
    return 0


async def cmd_list(args):
    client = get_qdrant_client()
    settings = get_settings()
    collection = args.collection or "regulation_documents"
    try:
        # Scroll all distinct documents
        seen = set()
        documents = []
        offset = None
        while True:
            result = client.scroll(
                collection_name=collection,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            points, offset = result
            for point in points:
                doc_id = point.payload.get("document_id")
                if doc_id in seen:
                    continue
                seen.add(doc_id)
                documents.append({
                    "document_id": doc_id,
                    "title": point.payload.get("title"),
                    "document_type": point.payload.get("document_type"),
                    "document_number": point.payload.get("document_number"),
                    "effective_date": point.payload.get("effective_date"),
                    "classification": point.payload.get("classification"),
                    "version": point.payload.get("version"),
                    "chunks": point.payload.get("chunk_count"),
                })
            if offset is None or len(points) == 0:
                break
        log.info(f"Found {len(documents)} documents in '{collection}'")
        print(json.dumps(documents, indent=2))
        return 0
    except Exception as e:
        log.error(f"List failed: {e}")
        return 1


async def cmd_delete(args):
    client = get_qdrant_client()
    collection = args.collection or "regulation_documents"
    ingester = DocumentIngester(client)
    n = await ingester.delete_document(args.document_id)
    log.info(f"Deleted {n} chunks for document {args.document_id}")
    return 0


async def cmd_info(args):
    client = get_qdrant_client()
    collection = args.collection or "regulation_documents"
    ingester = DocumentIngester(client)
    info = ingester.get_collection_info()
    print(json.dumps(info, indent=2))
    return 0


async def cmd_test_connection(args):
    try:
        client = get_qdrant_client()
        collections = client.get_collections().collections
        log.info(f"✅ Connected to Qdrant")
        log.info(f"  Collections: {[c.name for c in collections]}")
        # Test embedding model
        log.info("Testing embedding model...")
        model = SentenceTransformer("BAAI/bge-m3")
        embedding = model.encode("test")
        log.info(f"✅ Embedding model loaded: dim={len(embedding)}")
        return 0
    except Exception as e:
        log.error(f"❌ Connection failed: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="RAG Ingestion CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    # ingest
    p_ingest = sub.add_parser("ingest", help="Ingest a single document")
    p_ingest.add_argument("file", help="Path to file (txt, md, pdf, docx)")
    p_ingest.add_argument("--title", help="Document title (default: filename)")
    p_ingest.add_argument("--type", default="PERDA", help="Document type (PERDA, PERGUB, SOP, ...)")
    p_ingest.add_argument("--number", help="Document number (e.g. '3 Tahun 2024')")
    p_ingest.add_argument("--authority", help="Issuing authority (e.g. 'DPRD Batam')")
    p_ingest.add_argument("--effective-date", help="ISO date (e.g. 2024-03-15)")
    p_ingest.add_argument("--classification", default="INTERNAL")
    p_ingest.add_argument("--version", default="v1.0")
    p_ingest.add_argument("--document-id", help="Custom document_id")
    p_ingest.add_argument("--source-url", help="Source URL")
    p_ingest.add_argument("--tax-types", nargs="*", help="e.g. hotel restaurant")
    p_ingest.add_argument("--regions", nargs="*", help="e.g. batam tanjung-pinang")
    p_ingest.add_argument("--keywords", nargs="*", help="search keywords")
    p_ingest.add_argument("--embedding-model", default="BAAI/bge-m3")
    p_ingest.set_defaults(func=cmd_ingest)

    # ingest-batch
    p_batch = sub.add_parser("ingest-batch", help="Ingest all files in a directory")
    p_batch.add_argument("directory", help="Directory path")
    p_batch.add_argument("--pattern", default="*.md", help="Glob pattern (e.g. '*.txt', '*.pdf')")
    p_batch.add_argument("--type", default="PERDA")
    p_batch.add_argument("--title-prefix", default="", help="Prefix for titles")
    p_batch.add_argument("--number-prefix", default="", help="Prefix for document numbers")
    p_batch.add_argument("--authority", help="Issuing authority")
    p_batch.add_argument("--effective-date", help="ISO date")
    p_batch.add_argument("--classification", default="INTERNAL")
    p_batch.add_argument("--version", default="v1.0")
    p_batch.add_argument("--tax-types", nargs="*")
    p_batch.add_argument("--regions", nargs="*")
    p_batch.add_argument("--keywords", nargs="*")
    p_batch.add_argument("--embedding-model", default="BAAI/bge-m3")
    p_batch.set_defaults(func=cmd_ingest_batch)

    # list
    p_list = sub.add_parser("list", help="List indexed documents")
    p_list.add_argument("--collection", default="regulation_documents")
    p_list.set_defaults(func=cmd_list)

    # delete
    p_del = sub.add_parser("delete", help="Delete a document and all its chunks")
    p_del.add_argument("document_id")
    p_del.add_argument("--collection", default="regulation_documents")
    p_del.set_defaults(func=cmd_delete)

    # info
    p_info = sub.add_parser("info", help="Collection statistics")
    p_info.add_argument("--collection", default="regulation_documents")
    p_info.set_defaults(func=cmd_info)

    # test-connection
    p_test = sub.add_parser("test-connection", help="Verify Qdrant + embedding model")
    p_test.set_defaults(func=cmd_test_connection)

    args = parser.parse_args()
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main() or 0)
