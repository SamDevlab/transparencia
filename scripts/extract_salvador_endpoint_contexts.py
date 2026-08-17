from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks/raw")
OUT = ROOT.parent / "core_endpoint_contexts.json"
TARGETS = {
    "receita_totalizador": ("43f0a2a75c6c3cc92c9b7549b4de0849fe65bf017b6cefe923fd26557d8ec875", "/receita/totalizador"),
    "receita_grid_resumida": ("43f0a2a75c6c3cc92c9b7549b4de0849fe65bf017b6cefe923fd26557d8ec875", "/receita/gridResumida/"),
    "receita_grid_detalhada": ("43f0a2a75c6c3cc92c9b7549b4de0849fe65bf017b6cefe923fd26557d8ec875", "/receita/gridDetalhada"),
    "despesa_totalizador": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/totalizador"),
    "despesa_grid_resumida": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/gridresumida"),
    "despesa_grid_detalhada": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/gridDetalhada"),
    "despesa_detalhamento_empenho": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/detalhamentoEmpenho"),
    "despesa_liquidacao": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/liquidacaoRelacionado?pagina="),
    "despesa_pagamento": ("0348f73f94f0e26a4ecb47774ff99077cb828375c9753bd813c939e58cc37e71", "/despesa/pagamentoRelacionado?pagina="),
    "contratos_totalizador": ("743eb1ebf7796d2397d01c70636026ecc1de9bfa8c7ff87229a58a0c38325c66", "/contratos/totalizador"),
    "contratos_grid": ("743eb1ebf7796d2397d01c70636026ecc1de9bfa8c7ff87229a58a0c38325c66", "/contratos/gridDetalhada?pagina="),
    "credor_grid": ("3a1f53f3521f4a5cf363f23f5c6c4384ec8771f77b3383e6b3efe7f256c707bf", "/credor/gridCredores?pagina="),
}

out: dict[str, list[dict]] = {}
for name, (sha, literal) in TARGETS.items():
    path = ROOT / f"{sha}.js"
    text = path.read_text(encoding="utf-8", errors="ignore")
    contexts: list[dict] = []
    start = 0
    while True:
        pos = text.find(literal, start)
        if pos < 0:
            break
        left = max(0, pos - 1400)
        right = min(len(text), pos + len(literal) + 2200)
        contexts.append({
            "offset": pos,
            "literal": literal,
            "context": " ".join(text[left:right].split()),
        })
        start = pos + len(literal)
        if len(contexts) >= 6:
            break
    out[name] = contexts

OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({k: len(v) for k, v in out.items()}, sort_keys=True))
