from __future__ import annotations

from pathlib import Path

from ..http import fetch_and_archive


def collect_known_pages(sources: tuple[dict[str, str], ...], out_dir: Path) -> list[dict]:
    results: list[dict] = []
    for source in sources:
        url = (source.get("url") or "").strip()
        source_id = (source.get("id") or "").strip()
        if not source_id or not url:
            continue
        try:
            meta = fetch_and_archive(url, source_id=source_id, out_dir=out_dir)
            results.append({"source_id": source_id, "ok": True, "sha256": meta.sha256,
                            "status": meta.status_code, "final_url": meta.final_url})
        except Exception as exc:
            results.append({"source_id": source_id, "ok": False, "error": str(exc)})
    return results
