from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots/2026-08-17/prefeitura_api")
src = json.loads((ROOT / "expense_detail_probe.json").read_text(encoding="utf-8"))
out = {}
for name, item in src.items():
    out[name] = {
        "status": item.get("status"),
        "bytes": item.get("bytes"),
        "dados_count": item.get("dados_count"),
        "first_rows": item.get("first_rows"),
        "paginacao": item.get("paginacao"),
        "totalizadores": item.get("totalizadores"),
        "payload": item.get("payload"),
        "error": item.get("error"),
    }
(ROOT / "expense_detail_probe_summary.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
print(json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True))
