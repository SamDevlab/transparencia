from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Iterable


def normalize_identifier(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return text or None


def _keys(row: dict) -> set[tuple[str, ...]]:
    keys: set[tuple[str, ...]] = set()
    process = normalize_identifier(row.get("process_number") or row.get("numeroProcesso"))
    notice = normalize_identifier(row.get("notice_number") or row.get("numeroCompra") or row.get("numeroControlePNCP"))
    year = str(row.get("year") or row.get("anoCompra") or "").strip()
    agency_doc = normalize_identifier(row.get("agency_cnpj") or row.get("orgaoEntidadeCnpj") or row.get("cnpj"))
    if process:
        keys.add(("process", process))
        if year:
            keys.add(("process_year", process, year))
        if agency_doc:
            keys.add(("process_agency", process, agency_doc))
    if notice and year:
        keys.add(("notice_year", notice, year))
        if agency_doc:
            keys.add(("notice_year_agency", notice, year, agency_doc))
    return keys


def reconcile_exact(local_rows: Iterable[dict], reference_rows: Iterable[dict]) -> list[dict]:
    """Reconcile only on exact normalized identifiers.

    The function intentionally does not use object-text similarity, vendor-name similarity or fuzzy
    matching. Ambiguous exact identifiers are returned as multiple_candidates rather than promoted
    to facts.
    """
    reference = list(reference_rows)
    index: dict[tuple[str, ...], set[int]] = defaultdict(set)
    for idx, row in enumerate(reference):
        for key in _keys(row):
            index[key].add(idx)

    output: list[dict] = []
    for local in local_rows:
        candidates: set[int] = set()
        matched_keys: list[tuple[str, ...]] = []
        for key in sorted(_keys(local)):
            hits = index.get(key, set())
            if hits:
                candidates.update(hits)
                matched_keys.append(key)
        if len(candidates) == 1:
            idx = next(iter(candidates))
            status = "exact_match"
            candidate_rows = [reference[idx]]
        elif len(candidates) > 1:
            status = "multiple_candidates"
            candidate_rows = [reference[idx] for idx in sorted(candidates)]
        else:
            status = "unmatched"
            candidate_rows = []
        output.append({
            "status": status,
            "local_source_system": local.get("source_system"),
            "local_source_record_key": local.get("source_record_key") or local.get("pncp_control_number"),
            "process_number": local.get("process_number"),
            "notice_number": local.get("notice_number"),
            "year": local.get("year"),
            "matched_keys": [list(key) for key in matched_keys],
            "candidate_count": len(candidate_rows),
            "reference_control_numbers": [
                row.get("pncp_control_number") or row.get("numeroControlePNCP") or row.get("numero_controle_pncp")
                for row in candidate_rows
            ],
        })
    return output


def read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.exists():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_reconciliation(local_path: Path, reference_path: Path, output_path: Path) -> Path:
    rows = reconcile_exact(read_jsonl(local_path), read_jsonl(reference_path))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return output_path
