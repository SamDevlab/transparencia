from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IdentityKey:
    name: str
    parts: tuple[str, ...]


def normalize_identifier(value: object) -> str | None:
    """Normalize formatting only; never infer or fuzzy-match identifiers."""
    text = str(value or "").strip()
    if not text:
        return None
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^0-9A-Za-z]", "", text).upper()
    return text or None


def exact_identity_keys(row: dict) -> set[IdentityKey]:
    """Build exact keys from the canonical city-adapter schema.

    City-specific collectors must map source fields into these canonical names before
    reconciliation. The core deliberately knows nothing about source-specific aliases.
    """
    keys: set[IdentityKey] = set()
    process = normalize_identifier(row.get("process_number"))
    notice = normalize_identifier(row.get("notice_number"))
    contract = normalize_identifier(row.get("contract_number"))
    management_unit = normalize_identifier(row.get("management_unit"))
    agency_document = normalize_identifier(row.get("agency_document"))
    year = str(row.get("year") or "").strip()

    if process:
        keys.add(IdentityKey("process", (process,)))
        if year:
            keys.add(IdentityKey("process_year", (process, year)))
        if agency_document:
            keys.add(IdentityKey("process_agency", (process, agency_document)))
    if notice and year:
        keys.add(IdentityKey("notice_year", (notice, year)))
        if agency_document:
            keys.add(IdentityKey("notice_year_agency", (notice, year, agency_document)))
    if contract:
        keys.add(IdentityKey("contract", (contract,)))
        if management_unit:
            keys.add(IdentityKey("contract_management_unit", (contract, management_unit)))
    return keys


def reconcile_exact(local_rows: Iterable[dict], reference_rows: Iterable[dict]) -> list[dict]:
    """Reconcile records only on exact normalized official identifiers.

    Object text, supplier names and semantic similarity are intentionally ignored.
    Ambiguous exact matches are preserved as `multiple_candidates` rather than promoted
    to facts.
    """
    reference = list(reference_rows)
    index: dict[IdentityKey, set[int]] = defaultdict(set)
    for idx, row in enumerate(reference):
        for key in exact_identity_keys(row):
            index[key].add(idx)

    output: list[dict] = []
    for local in local_rows:
        candidates: set[int] = set()
        matched_keys: list[IdentityKey] = []
        for key in sorted(exact_identity_keys(local), key=lambda item: (item.name, item.parts)):
            hits = index.get(key, set())
            if hits:
                candidates.update(hits)
                matched_keys.append(key)

        if len(candidates) == 1:
            status = "exact_match"
        elif len(candidates) > 1:
            status = "multiple_candidates"
        else:
            status = "unmatched"

        candidate_rows = [reference[idx] for idx in sorted(candidates)]
        output.append(
            {
                "status": status,
                "local_source_system": local.get("source_system"),
                "local_source_record_key": local.get("source_record_key"),
                "matched_keys": [
                    {"name": key.name, "parts": list(key.parts)} for key in matched_keys
                ],
                "candidate_count": len(candidate_rows),
                "reference_record_keys": [row.get("source_record_key") for row in candidate_rows],
            }
        )
    return output
