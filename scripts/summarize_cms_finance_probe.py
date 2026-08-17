from __future__ import annotations

import json
from pathlib import Path

src = Path('cities/salvador/data/snapshots/2026-08-17/cms_finance_probe.json')
out = Path('cities/salvador/data/snapshots/2026-08-17/cms_finance_probe_summary.json')
payload = json.loads(src.read_text(encoding='utf-8'))
rows = {}
for url, item in payload.items():
    candidates = item.get('candidates') or []
    rows[url] = {
        'status': item.get('status'),
        'title': item.get('title'),
        'final_url': item.get('final_url'),
        'content_type': item.get('content_type'),
        'bytes': item.get('bytes'),
        'sha256': item.get('sha256'),
        'forms': item.get('forms'),
        'export_candidates': [c for c in candidates if any(t in c.lower() for t in ('export', 'json', 'csv', 'xls', 'xml'))],
        'ajax_candidates': [c for c in candidates if any(t in c.lower() for t in ('ajax', 'pesq.class.php'))],
        'error': item.get('error'),
    }
out.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
