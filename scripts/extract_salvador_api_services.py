from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal")
ASSETS = ROOT / "snapshots" / "webapp_asset"
OUT = ROOT / "api_service_calls.json"
KEYWORDS = (
    "receita", "despesa", "contrat", "fornec", "licit", "empenh", "liquid", "pagament",
    "dadosabertos", "grid", "totalizador", "credor", "aditivo", "dotacao", "aquisi",
)


def compact(text: str) -> str:
    return " ".join(text.split())


def quoted_strings(text: str) -> list[str]:
    values: list[str] = []
    for m in re.finditer(r'(["\'])(.*?)(?<!\\)\1', text):
        value = m.group(2)
        if value and len(value) <= 220:
            values.append(value)
    return values


records: list[dict] = []
seen: set[tuple[str, int]] = set()
for path in sorted(ASSETS.glob("*")):
    if not path.is_file() or path.suffix.lower() not in {".js", ".json", ".html", ".bin"}:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for match in re.finditer(r"\.(get|post|put|delete)\(", text, re.I):
        left = max(0, match.start() - 500)
        right = min(len(text), match.start() + 1200)
        snippet = compact(text[left:right])
        strings = quoted_strings(text[match.start():right])
        searchable = (snippet + " " + " ".join(strings)).casefold()
        if not any(k in searchable for k in KEYWORDS):
            continue
        key = (str(path), match.start())
        if key in seen:
            continue
        seen.add(key)
        records.append({
            "asset": str(path),
            "offset": match.start(),
            "method": match.group(1).upper(),
            "strings_after_call": strings[:30],
            "context": snippet,
        })

# Also keep nearby contexts for the route names exposed by the current UI.
for path in sorted(ASSETS.glob("*")):
    if not path.is_file() or path.suffix.lower() not in {".js", ".json", ".html", ".bin"}:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for needle in ("RealizacaoReceita", "RealizacaoDespesa", "ContratosVigentes", "FornecedoresPrestadoresDeServico", "LicitacoesDispensasInexigibilidade", "ReceitaDadosAbertos", "DespesaDadosAbertos"):
        for match in re.finditer(re.escape(needle), text, re.I):
            left = max(0, match.start() - 900)
            right = min(len(text), match.end() + 1800)
            records.append({
                "asset": str(path),
                "offset": match.start(),
                "route_marker": needle,
                "context": compact(text[left:right]),
            })
            break

records.sort(key=lambda r: (r["asset"], r["offset"], r.get("method", "")))
OUT.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"wrote {len(records)} service contexts to {OUT}")
