from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("cities/salvador/data/snapshots")
OUTPUT = Path("cities/salvador/data/validation/municipal_contracts_dedup_audit.json")


def stable_key(row: dict) -> str:
    stable = {key: value for key, value in row.items() if key != "id"}
    payload = json.dumps(stable, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def latest_complete_snapshot() -> tuple[str, Path, dict]:
    for date_dir in sorted((p for p in ROOT.iterdir() if p.is_dir()), reverse=True):
        directory = date_dir / "prefeitura_contracts"
        coverage_path = directory / "coverage.json"
        raw_dir = directory / "raw"
        if not coverage_path.exists() or not raw_dir.exists():
            continue
        coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
        if coverage.get("complete_for_filter") is True:
            return date_dir.name, directory, coverage
    raise SystemExit("Nenhum snapshot municipal completo com respostas brutas foi encontrado.")


def response_files(raw_dir: Path):
    for page_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        candidates = [p for p in page_dir.glob("*.json") if p.name != "manifest.json"]
        if not candidates:
            continue
        yield page_dir.name, sorted(candidates)[-1]


def safe_example(row: dict) -> dict:
    # Do not copy supplier/creditor names or document-like free text into the audit report.
    # The report is about duplicate mechanics, not people.
    keys = [
        "nuContratoSigef",
        "nuContratoOriginal",
        "nuProcesso",
        "sgOrgao",
        "cdUnidadeGestora",
        "vlAtualizado",
        "dtAssinatura",
        "dsSituacao",
    ]
    return {key: row.get(key) for key in keys if row.get(key) not in (None, "")}


def main() -> None:
    snapshot, directory, coverage = latest_complete_snapshot()
    counts: Counter[str] = Counter()
    exact_with_id_counts: Counter[str] = Counter()
    ids_by_key: dict[str, set[str]] = defaultdict(set)
    pages_by_key: dict[str, set[str]] = defaultdict(set)
    example_by_key: dict[str, dict] = {}
    technical_id_counts: Counter[str] = Counter()
    source_rows = 0
    pages_scanned = 0

    for page_name, response_file in response_files(directory / "raw"):
        payload = json.loads(response_file.read_text(encoding="utf-8"))
        rows = payload.get("dados") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            continue
        pages_scanned += 1
        for row in rows:
            if not isinstance(row, dict):
                continue
            source_rows += 1
            key = stable_key(row)
            counts[key] += 1
            pages_by_key[key].add(page_name)
            example_by_key.setdefault(key, row)
            technical_id = str(row.get("id") or "").strip()
            if technical_id:
                ids_by_key[key].add(technical_id)
                technical_id_counts[technical_id] += 1
            exact_payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            exact_with_id_counts[hashlib.sha256(exact_payload.encode("utf-8")).hexdigest()] += 1

    duplicate_keys = [key for key, count in counts.items() if count > 1]
    multi_id_groups = [key for key in duplicate_keys if len(ids_by_key[key]) > 1]
    same_or_missing_id_groups = [key for key in duplicate_keys if len(ids_by_key[key]) <= 1]
    cross_page_groups = [key for key in duplicate_keys if len(pages_by_key[key]) > 1]
    same_technical_id_repeated = {technical_id: count for technical_id, count in technical_id_counts.items() if count > 1}
    exact_duplicate_rows = sum(count - 1 for count in exact_with_id_counts.values() if count > 1)

    top = sorted(duplicate_keys, key=lambda key: counts[key], reverse=True)[:25]
    report = {
        "snapshot": snapshot,
        "period_start": coverage.get("period_start"),
        "period_end": coverage.get("period_end"),
        "pages_scanned": pages_scanned,
        "source_reported_pages": sum(int(w.get("reported_pages") or 0) for w in coverage.get("windows") or []),
        "source_reported_rows": sum(int(w.get("reported_total") or 0) for w in coverage.get("windows") or []),
        "source_rows_scanned": source_rows,
        "unique_substantive_rows_ignoring_technical_id": len(counts),
        "substantive_duplicate_rows": source_rows - len(counts),
        "substantive_duplicate_groups": len(duplicate_keys),
        "duplicate_groups_with_multiple_technical_ids": len(multi_id_groups),
        "duplicate_groups_with_one_or_missing_technical_id": len(same_or_missing_id_groups),
        "duplicate_groups_spanning_multiple_pages": len(cross_page_groups),
        "unique_technical_ids": len(technical_id_counts),
        "technical_ids_repeated_across_source_rows": len(same_technical_id_repeated),
        "rows_repeated_with_identical_technical_id": sum(count - 1 for count in same_technical_id_repeated.values()),
        "exact_duplicate_rows_including_technical_id": exact_duplicate_rows,
        "max_substantive_multiplicity": max(counts.values(), default=0),
        "display_deduplication_assessment": (
            "safe_for_presentation_only_if_technical_uuid_is_not_an_official_identifier"
            if multi_id_groups and not same_technical_id_repeated
            else "requires_caution"
        ),
        "pagination_integrity_assessment": (
            "technical_ids_repeat_across_rows_review_before_claiming_unique-record completeness"
            if same_technical_id_repeated
            else "no_repeated_technical_ids_detected"
        ),
        "privacy_rule": "Duplicate diagnostics publish only administrative contract/process/unit fields, counts and values; supplier/creditor names and document-like free text are omitted.",
        "methodology": [
            "The substantive key hashes every source field except the API technical field 'id'.",
            "No supplier/object/name similarity is used to merge records.",
            "The raw source row count is preserved even when a compact public view consolidates substantively identical rows.",
        ],
        "top_duplicate_groups": [
            {
                "rows": counts[key],
                "technical_ids": len(ids_by_key[key]),
                "pages": len(pages_by_key[key]),
                "example": safe_example(example_by_key[key]),
            }
            for key in top
        ],
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
