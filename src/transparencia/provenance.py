from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class SnapshotMeta:
    source_id: str
    requested_url: str
    final_url: str
    status_code: int
    content_type: str
    collected_at: str
    sha256: str
    byte_count: int
    body_path: str


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_suffix(content_type: str, url: str) -> str:
    ctype = (content_type or "").lower()
    if "json" in ctype:
        return ".json"
    if "html" in ctype:
        return ".html"
    if "pdf" in ctype:
        return ".pdf"
    suffix = Path(urlparse(url).path).suffix.lower()
    return suffix if suffix and len(suffix) <= 8 else ".bin"


def persist_snapshot(*, out_dir: Path, source_id: str, requested_url: str,
                     final_url: str, status_code: int, content_type: str, body: bytes) -> SnapshotMeta:
    digest = sha256_bytes(body)
    suffix = safe_suffix(content_type, final_url)
    body_dir = out_dir / source_id
    body_dir.mkdir(parents=True, exist_ok=True)
    body_path = body_dir / f"{digest}{suffix}"
    if not body_path.exists():
        body_path.write_bytes(body)
    collected_at = datetime.now(timezone.utc).isoformat()
    meta = SnapshotMeta(source_id, requested_url, final_url, status_code, content_type,
                        collected_at, digest, len(body), str(body_path))
    with (body_dir / "manifest.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(meta), ensure_ascii=False, sort_keys=True) + "\n")
    return meta
