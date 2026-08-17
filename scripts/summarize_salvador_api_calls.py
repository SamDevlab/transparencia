from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks")
REPORT = ROOT / "report.json"
OUT = ROOT / "api_call_signatures.json"
TARGETS = (
    "receita", "despesa", "contrat", "fornec", "licit", "empenh", "liquid", "pagament",
    "dadosabertos", "gridresum", "griddetalh", "totalizador", "credor", "aditivo", "dotacao",
)

payload = json.loads(REPORT.read_text(encoding="utf-8"))
rows: list[dict] = []
seen: set[tuple] = set()
for chunk in payload.get("relevant_chunks", []):
    for call in chunk.get("http_calls", []):
        strings = call.get("strings_after_call") or []
        searchable = " ".join(strings).casefold()
        if not any(term in searchable for term in TARGETS):
            continue
        # Keep string literals only; they are enough to reconstruct the route expression
        # while avoiding megabytes of minified surrounding code.
        signature = (call.get("method"), *strings[:20])
        if signature in seen:
            continue
        seen.add(signature)
        rows.append({
            "method": call.get("method"),
            "strings": strings[:30],
            "chunk_url": chunk.get("url"),
            "chunk_sha256": chunk.get("sha256"),
            "offset": call.get("offset"),
        })

rows.sort(key=lambda r: (r.get("method") or "", " ".join(r.get("strings") or [])))
OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(rows)} unique API call signatures")
