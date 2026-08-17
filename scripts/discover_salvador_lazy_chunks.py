from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

BASE = "https://transparencia.salvador.ba.gov.br/"
MANIFEST_URL = urljoin(BASE, "asset-manifest.json")
OUT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks")
RAW = OUT / "raw"
TARGETS = (
    "realizacaoreceita", "realizacaodespesa", "receita", "despesa", "empenh", "liquid", "pagament",
    "contratosvigentes", "fornecedoresprestadoresdeservico", "licitacoesdispensasinexigibilidade",
    "contrat", "fornec", "licit", "dadosabertos", "gridresum", "griddetalh", "totalizador",
)


def quoted_strings(text: str) -> list[str]:
    out: list[str] = []
    for m in re.finditer(r'(["\'])(.*?)(?<!\\)\1', text):
        value = m.group(2)
        if value and len(value) <= 350:
            out.append(value)
    return out


def compact(text: str) -> str:
    return " ".join(text.split())


OUT.mkdir(parents=True, exist_ok=True)
RAW.mkdir(parents=True, exist_ok=True)
headers = {"User-Agent": "transparencia-municipal/0.2 (+public-data-audit)", "Accept": "application/json,text/javascript,*/*"}
report: dict = {"manifest_url": MANIFEST_URL, "manifest": {}, "relevant_chunks": [], "errors": []}
with httpx.Client(headers=headers, follow_redirects=True, timeout=90.0) as client:
    manifest_response = client.get(MANIFEST_URL)
    manifest_response.raise_for_status()
    manifest_bytes = manifest_response.content
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    (OUT / "asset-manifest.json").write_bytes(manifest_bytes)
    manifest = manifest_response.json()
    report["manifest"] = {"sha256": manifest_sha, "bytes": len(manifest_bytes)}
    urls: set[str] = set()
    for value in (manifest.get("files") or {}).values():
        if isinstance(value, str) and value.endswith(".js"):
            urls.add(urljoin(BASE, value))
    for value in manifest.get("entrypoints") or []:
        if isinstance(value, str) and value.endswith(".js"):
            urls.add(urljoin(BASE, value))
    origin = urlparse(BASE).netloc
    for url in sorted(urls):
        if urlparse(url).netloc != origin:
            continue
        try:
            response = client.get(url)
            response.raise_for_status()
            if len(response.content) > 10_000_000:
                report["errors"].append({"url": url, "error": "too_large", "bytes": len(response.content)})
                continue
            text = response.text
            low = text.casefold()
            matched = sorted({term for term in TARGETS if term in low})
            if not matched:
                continue
            sha = hashlib.sha256(response.content).hexdigest()
            raw_path = RAW / f"{sha}.js"
            raw_path.write_bytes(response.content)
            calls: list[dict] = []
            for m in re.finditer(r"\.(get|post|put|delete)\(", text, re.I):
                right = min(len(text), m.start() + 1900)
                strings = quoted_strings(text[m.start():right])
                searchable = " ".join(strings).casefold()
                if not any(term in searchable for term in TARGETS):
                    continue
                left = max(0, m.start() - 300)
                calls.append({
                    "offset": m.start(),
                    "method": m.group(1).upper(),
                    "strings_after_call": strings[:50],
                    "context": compact(text[left:right]),
                })
            report["relevant_chunks"].append({
                "url": str(response.url),
                "sha256": sha,
                "bytes": len(response.content),
                "matched_terms": matched,
                "raw_file": str(raw_path),
                "http_calls": calls,
            })
        except Exception as exc:
            report["errors"].append({"url": url, "error": f"{type(exc).__name__}: {exc}"})

(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"relevant_chunks": len(report["relevant_chunks"]), "errors": len(report["errors"])}, indent=2))
