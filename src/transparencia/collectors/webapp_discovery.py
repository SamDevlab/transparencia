from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from ..provenance import persist_snapshot

KEYWORDS = ("api", "receita", "despesa", "empenh", "liquid", "pagament", "contrat", "licit", "fornecedor")


class _Assets(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        value = data.get("src") if tag.lower() == "script" else data.get("href") if tag.lower() == "link" else None
        if value:
            self.urls.append(value)


def _candidates(text: str) -> list[str]:
    normalized: set[str] = set()
    for value in re.findall(r"https?://[^\s'\"<>]+", text, re.I):
        if any(k in value.casefold() for k in KEYWORDS):
            normalized.add(value.rstrip(");,}"))
    for value in re.findall(r"['\"](/[^'\"\s]{2,180})['\"]", text, re.I):
        if any(k in value.casefold() for k in KEYWORDS):
            normalized.add(value)
    return sorted(normalized)


def discover(base_url: str, out_dir: Path, *, max_assets: int = 30, max_asset_bytes: int = 8_000_000) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "webapp_discovery.json"
    headers = {"User-Agent": "transparencia-municipal/0.2", "Accept": "text/html,application/javascript,*/*"}
    report: dict = {"base_url": base_url, "assets": [], "candidates": [], "errors": []}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        response = client.get(base_url)
        response.raise_for_status()
        meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id="webapp_home", requested_url=base_url,
                                final_url=str(response.url), status_code=response.status_code,
                                content_type=response.headers.get("content-type", "text/html"), body=response.content)
        report["homepage"] = {"final_url": str(response.url), "sha256": meta.sha256, "bytes": meta.byte_count}
        parser = _Assets()
        parser.feed(response.text)
        origin = urlparse(str(response.url))
        all_candidates = set(_candidates(response.text))
        for raw in parser.urls[:max_assets]:
            asset_url = urljoin(str(response.url), raw)
            parsed = urlparse(asset_url)
            if parsed.scheme not in {"http", "https"} or parsed.netloc != origin.netloc:
                continue
            try:
                asset_response = client.get(asset_url)
                asset_response.raise_for_status()
                if len(asset_response.content) > max_asset_bytes:
                    report["errors"].append({"url": asset_url, "error": "asset_too_large", "bytes": len(asset_response.content)})
                    continue
                asset_meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id="webapp_asset", requested_url=asset_url,
                                             final_url=str(asset_response.url), status_code=asset_response.status_code,
                                             content_type=asset_response.headers.get("content-type", ""), body=asset_response.content)
                found = _candidates(asset_response.text)
                all_candidates.update(found)
                report["assets"].append({"url": str(asset_response.url), "sha256": asset_meta.sha256, "bytes": asset_meta.byte_count, "candidates": found})
            except Exception as exc:
                report["errors"].append({"url": asset_url, "error": f"{type(exc).__name__}: {exc}"})
    report["candidates"] = sorted(all_candidates)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report_path
