from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

ROOT = Path('cities/salvador/data/snapshots/2026-08-17/prefeitura_acquisitions')
SOURCE = ROOT / 'acquisitions.jsonl'
OUT = ROOT / 'analysis.json'

rows = [json.loads(line) for line in SOURCE.read_text(encoding='utf-8').splitlines() if line.strip()]


def aggregate(field: str) -> list[dict]:
    bucket: dict[str, dict] = defaultdict(lambda: {'records': 0, 'declared_value': 0.0, 'records_with_value': 0})
    for row in rows:
        key = str(row.get(field) or '(não informado)')
        item = bucket[key]
        item['records'] += 1
        value = row.get('acquisition_value')
        if isinstance(value, (int, float)):
            item['declared_value'] += float(value)
            item['records_with_value'] += 1
    result = [{field: key, **value} for key, value in bucket.items()]
    result.sort(key=lambda x: (x['declared_value'], x['records']), reverse=True)
    return result

largest = sorted(rows, key=lambda r: float(r.get('acquisition_value') or 0), reverse=True)[:100]
missing = {}
for field in ('process_number','notice_number','acquisition_number','modality_name','acquisition_type','object','agency_name','unit_name','published_at','acquisition_value'):
    missing[field] = sum(1 for row in rows if row.get(field) in (None, '', []))

analysis = {
    'period_start': '2026-01-01',
    'period_end': '2026-08-17',
    'source_system': 'SALVADOR_TRANSPARENCIA_API',
    'source_url': 'https://transparencia.salvador.ba.gov.br/',
    'record_count': len(rows),
    'methodology_warning': 'This is descriptive aggregation of official records. High values, concentration, modality, direct purchase, exemption or inexigibility do not by themselves establish fraud, corruption, overpricing, favoritism or any other irregularity.',
    'value_semantics': "The source field is vlAquisicao and is retained here as acquisition_value / declared acquisition value; it is not relabelled as estimated or homologated value.",
    'by_modality': aggregate('modality_name'),
    'by_acquisition_type': aggregate('acquisition_type'),
    'by_agency': aggregate('agency_name'),
    'by_direct_purchase_basis': aggregate('direct_purchase_basis'),
    'missing_fields': missing,
    'largest_declared_value_records': largest,
}
OUT.write_text(json.dumps(analysis, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
print(json.dumps({k: analysis[k] for k in ('record_count','by_modality','by_acquisition_type','missing_fields')}, ensure_ascii=False, indent=2)[:60000])
