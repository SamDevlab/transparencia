from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks/raw")
OUT = ROOT.parent / "endpoint_index.json"
GROUPS = {
    "receita": ("/receita", "receita/", "/transferenciaentes", "/arrecadacaotransito", "/convenioreceita"),
    "despesa": ("/despesa", "despesa/", "/movimentoextraorc", "/gastosdiarios", "/vinculadatransito", "/adiantamentos"),
    "contratos": ("/contratos", "contratos/", "/fiscaiscontratos"),
    "fornecedores_credores": ("/credor", "credor/", "/fornecedor", "fornecedor/"),
    "aquisicoes_licitacoes": ("/aquisicao", "aquisicao/", "/licit", "licit/", "/filtro/aquisicoes"),
    "dados_abertos": ("/dadosabertos", "dadosabertos/", "/arquivo/dicionario-dados"),
}


def strings(text: str) -> list[str]:
    values: list[str] = []
    for match in re.finditer(r'(["\'])(.*?)(?<!\\)\1', text):
        value = match.group(2)
        if not value or len(value) > 500:
            continue
        if "/" not in value and "?" not in value:
            continue
        values.append(value)
    return values

index: dict[str, list[dict]] = defaultdict(list)
seen: set[tuple[str, str]] = set()
for path in sorted(ROOT.glob("*.js")):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for value in strings(text):
        low = value.casefold()
        for group, needles in GROUPS.items():
            if not any(n in low for n in needles):
                continue
            key = (group, value)
            if key in seen:
                continue
            seen.add(key)
            index[group].append({"literal": value, "chunk_sha256": path.stem})

for group in index:
    index[group].sort(key=lambda row: row["literal"].casefold())
OUT.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({k: len(v) for k, v in index.items()}, sort_keys=True))
