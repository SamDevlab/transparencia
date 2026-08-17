from __future__ import annotations

import json
from pathlib import Path

root = Path('cities/salvador/data/snapshots/2026-08-17/discovery/prefeitura_portal/lazy_chunks')
payload = json.loads((root / 'contract_supplier_route_summary.json').read_text(encoding='utf-8'))
(root / 'contract_supplier_routes.json').write_text(
    json.dumps(payload.get('routes', []), ensure_ascii=False, indent=2, sort_keys=True) + '\n',
    encoding='utf-8',
)
print(json.dumps(payload.get('routes', []), ensure_ascii=False, indent=2, sort_keys=True))
