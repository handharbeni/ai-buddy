#!/usr/bin/env python3
"""
RAG ingest CLI — ingest Perda/Pergub/SOP documents into the RAG pipeline.

Usage:
    python ingest_cli.py ./regulations/perda_3_2024.pdf
    python ingest_cli.py ./regulations/
    python ingest_cli.py ./regulations/ --url http://qdrant-host:8002 --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Supported extensions
EXTS = {".pdf", ".docx", ".md", ".txt"}

# Document type patterns (order matters — more specific first)
TYPE_PATTERNS = [
    (re.compile(r"^perda[_\s-]", re.I), "PERDA"),
    (re.compile(r"^pergub[_\s-]", re.I), "PERGUB"),
    (re.compile(r"^sop[_\s-]", re.I), "SOP"),
    (re.compile(r"^surat_edaran[_\s-]", re.I), "SURAT_EDARAN"),
    (re.compile(r"^permen[_\s-]", re.I), "PERMEN"),
    (re.compile(r"^perdir[_\s-]", re.I), "PERDIR"),
]

# Counter for sequential numbering
_counter = 0
_counter_lock = None  # not needed for single-process

def next_seq() -> int:
    global _counter
    _counter += 1
    return _counter


def detect_doc_type(filename: str) -> str:
    stem = Path(filename).stem
    for pattern, dtype in TYPE_PATTERNS:
        if pattern.match(stem):
            return dtype
    return "GENERAL"


def extract_doc_number(filename: str) -> str:
    """Extract document number from filename patterns like perda_3_2024, pergub_15_2025."""
    stem = Path(filename).stem
    # Match patterns like perda_3_2024, perda-3-2024, perda 3 2024
    m = re.search(r"(\d+)[_\s-]*(\d{4})", stem)
    if m:
        num, year = m.group(1), m.group(2)
        return f"{num}/{year}"
    # Fallback: just grab the first run of digits
    m2 = re.search(r"(\d+)", stem)
    return m2.group(1) if m2 else "1"


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Extract YAML frontmatter from markdown. Returns (metadata_dict, remaining_content)."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return {}, content
    import yaml  # optional dep; lazy import
    try:
        meta = yaml.safe_load(match.group(1)) or {}
    except Exception:
        return {}, content
    return meta, content[match.end() :]


def build_metadata(filepath: Path, dry_run: bool = False) -> dict:
    """Build metadata dict for a file."""
    filename = filepath.name
    doc_type = detect_doc_type(filename)
    doc_number = extract_doc_number(filename)
    today = date.today().isoformat()

    meta = {
        "document_id": f"REG_{date.today().strftime('%Y%m%d')}_{next_seq():04d}",
        "title": filepath.stem.replace("_", " ").replace("-", " ").strip(),
        "document_type": doc_type,
        "document_number": doc_number,
        "issuing_authority": "BAPENDA",
        "effective_date": today,
        "classification": "INTERNAL",
        "version": "v1.0",
        "tax_types": [],
        "regions": [],
        "keywords": [],
    }

    # Enrich from frontmatter if markdown
    if filepath.suffix.lower() == ".md":
        try:
            raw = filepath.read_text(encoding="utf-8", errors="ignore")
            fm, _ = parse_frontmatter(raw)
            for key in ("title", "document_type", "document_number",
                        "issuing_authority", "effective_date",
                        "classification", "version", "tax_types",
                        "regions", "keywords"):
                if fm.get(key) not in (None, ""):
                    meta[key] = fm[key]
            # Allow frontmatter to override document_id
            if fm.get("document_id"):
                meta["document_id"] = fm["document_id"]
        except Exception:
            pass

    # Compute content hash
    try:
        raw_bytes = filepath.read_bytes()
        content_hash = hashlib.sha256(raw_bytes).hexdigest()
    except Exception as e:
        print(f"  [WARN] could not read file: {e}", file=sys.stderr)
        content_hash = hashlib.sha256(b"").hexdigest()
    meta["content_hash"] = content_hash

    if dry_run:
        print(f"  [DRY-RUN] metadata preview: {json.dumps(meta, indent=2, default=str)}")

    return meta


def ingest_file(filepath: Path, url: str, api_key: str | None, dry_run: bool) -> bool:
    """POST one file to /ingest. Returns True on success."""
    print(f"  Processing: {filepath.name}")
    meta = build_metadata(filepath, dry_run)
    if dry_run:
        return True

    # Prepare FormData
    import urllib.request

    boundary = b"----IngestFormBoundary" + os.urandom(8)
    body = b""

    # metadata field
    meta_json = json.dumps(meta, default=str)
    body += (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="metadata"\r\n'
        b"Content-Type: application/json\r\n\r\n"
    )
    body += meta_json.encode("utf-8") + b"\r\n"

    # file field
    file_bytes = filepath.read_bytes()
    filename_enc = filepath.name.encode("utf-8")
    body += (
        b"--" + boundary + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename="' + filename_enc + b'"\r\n'
        b"Content-Type: application/octet-stream\r\n\r\n"
    )
    body += file_bytes + b"\r\n"
    body += b"--" + boundary + b"--\r\n"

    req = Request(url, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary.decode()}")
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")

    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            print(f"  [OK] {filepath.name} → {result.get('document_id', 'n/a')} "
                  f"({result.get('chunks_indexed', 0)} chunks)")
            return True
    except HTTPError as e:
        body_err = e.read().decode("utf-8", errors="ignore")
        print(f"  [FAIL] {filepath.name} → HTTP {e.code}: {body_err[:200]}", file=sys.stderr)
        return False
    except URLError as e:
        print(f"  [FAIL] {filepath.name} → connection error: {e.reason}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"  [FAIL] {filepath.name} → {e}", file=sys.stderr)
        return False


def collect_files(paths: list[str]) -> list[Path]:
    """Collect all supported files from args (files or directories)."""
    files = []
    for p in paths:
        p = Path(p)
        if p.is_file():
            if p.suffix.lower() in EXTS:
                files.append(p)
        elif p.is_dir():
            for ext in EXTS:
                files.extend(p.rglob(f"*{ext}"))
        else:
            print(f"  [SKIP] not found: {p}", file=sys.stderr)
    # Sort for deterministic ordering
    files.sort(key=lambda f: (str(f.parent), f.name))
    return files


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest regulation documents into the RAG pipeline."
    )
    parser.add_argument(
        "paths",
        nargs="+",
        metavar="PATH",
        help="File or directory to ingest.",
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8002/ingest",
        help="Ingest endpoint URL. Default: http://localhost:8002/ingest",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token for authenticated endpoints.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print metadata without calling the ingest endpoint.",
    )
    args = parser.parse_args()

    files = collect_files(args.paths)
    if not files:
        print("No supported files (.pdf, .docx, .md, .txt) found.", file=sys.stderr)
        sys.exit(1)

    print(f"Ingesting {len(files)} file(s) → {args.url}" +
          (" [DRY-RUN]" if args.dry_run else ""))
    print()

    success = 0
    failed = 0
    for fp in files:
        ok = ingest_file(fp, args.url, args.api_key, args.dry_run)
        if ok:
            success += 1
        else:
            failed += 1

    print()
    print(f"Done: {success} succeeded, {failed} failed")
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
