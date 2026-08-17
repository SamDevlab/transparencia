from __future__ import annotations

import random
import time
from pathlib import Path

import httpx

from .provenance import SnapshotMeta, persist_snapshot

USER_AGENT = "transparencia-municipal/0.1 (+dados publicos; coleta auditavel)"


def fetch_and_archive(url: str, *, source_id: str, out_dir: Path,
                      timeout: float = 45.0, attempts: int = 4) -> SnapshotMeta:
    headers = {"User-Agent": USER_AGENT, "Accept": "*/*"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=timeout) as client:
        for attempt in range(1, attempts + 1):
            try:
                response = client.get(url)
                if response.status_code in {429, 500, 502, 503, 504} and attempt < attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = min(float(retry_after), 60.0) if retry_after and retry_after.isdigit() else min(2 ** (attempt - 1) + random.random(), 30.0)
                    time.sleep(delay)
                    continue
                response.raise_for_status()
                return persist_snapshot(
                    out_dir=out_dir, source_id=source_id, requested_url=url,
                    final_url=str(response.url), status_code=response.status_code,
                    content_type=response.headers.get("content-type", ""), body=response.content,
                )
            except (httpx.HTTPError, OSError) as exc:
                if attempt == attempts:
                    raise RuntimeError(f"falha ao coletar {url}: {exc}") from exc
                time.sleep(min(2 ** (attempt - 1) + random.random(), 30.0))
    raise RuntimeError(f"falha ao coletar {url}")
