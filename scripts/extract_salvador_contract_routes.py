from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks")
REPORT = ROOT / "report.json"
OUT = ROOT / "contract_supplier_route_summary.json"
TERMS = ("contrat", "fornec", "aditiv", "fiscal", "aquis", "licit")

payload = json.loads(REPORT.read_text(encoding="utf-8"))
routes: dict[str, dict] = {}
contexts: list[dict] = []
for chunk in payload.get("relevant_chunks", []):
    for call in chunk.get("http_calls", []):
        strings = call.get("strings_after_call") or []
        matches = [s for s in strings if isinstance(s, str) and any(t in s.casefold() for t in TERMS)]
        if not matches:
            continue
        for value in matches:
            if value.startswith(("/", "http", "filtro/")):
                key = f"{call.get('method')} {value}"
                routes.setdefault(key, {
                    "method": call.get("method"),
                    "route_literal": value,
                    "chunk_url": chunk.get("url"),
                    "chunk_sha256": chunk.get("sha256"),
                    "offsets": [],
                })["offsets"].append(call.get("offset"))
        contexts.append({
            "method": call.get("method"),
            "matched_literals": matches,
            "strings": strings[:50],
            "chunk_url": chunk.get("url"),
            "chunk_sha256": chunk.get("sha256"),
            "offset": call.get("offset"),
        })

out = {
    "routes": sorted(routes.values(), key=lambda r: ((r.get("method") or ""), r.get("route_literal") or "")),
    "contexts": contexts,
}
OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"routes": out["routes"], "context_count": len(contexts)}, ensure_ascii=False, indent=2))
