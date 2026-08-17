from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import datetime
from html import unescape
from pathlib import Path

import httpx

from ..provenance import persist_snapshot
from .cms import visible_text

URL = "https://cmsalvador.sys.inf.br/ca/gridRegistroEmpenho/"
SOURCE_SYSTEM = "CMS_EMPENHOS"
NOTE_RE = re.compile(r"\bEmpenho:\s*(\d{4}NE\d+)", re.I)


def _norm_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(value.casefold().split())


def _money(value: str) -> float:
    return float(value.replace(".", "").replace(",", "."))


def _mask_document(value: str) -> tuple[str | None, str | None]:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 14:
        return digits, "cnpj"
    if len(digits) == 11:
        return f"***.***.***-{digits[-2:]}", "cpf_masked"
    return None, None


def _field(block: str, label: str, next_labels: tuple[str, ...]) -> str:
    stops = "|".join(re.escape(item) for item in next_labels)
    pattern = rf"{re.escape(label)}\s*(.*?)(?=\s+(?:{stops})\s*|\Z)"
    match = re.search(pattern, block, re.I | re.S)
    return " ".join(match.group(1).split()) if match else ""


def parse_visible_commitments(text: str, *, source_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    """Parse each visible ScriptCase commitment as an independent block."""
    blocks = re.split(r"(?=\bEmpenho:\s*\d{4}NE\d+)", unescape(text), flags=re.I)
    rows: list[dict] = []
    seen: set[str] = set()
    for block in blocks:
        note_match = NOTE_RE.search(block)
        if not note_match:
            continue
        note = note_match.group(1).upper()
        if note in seen:
            continue
        seen.add(note)

        modality = _field(block, "Modalidade:", ("Tipo:",))
        record_type = _field(block, "Tipo:", ("Data de Emissão:", "Data de Emissao:"))
        date_match = re.search(r"Data de Emiss[aã]o:\s*(\d{2}/\d{2}/\d{4})", block, re.I)
        value_match = re.search(r"Valor R\$:\s*([\d.,]+)", block, re.I)
        document_text = _field(block, "CNPJCPF:", ("Credor:",))
        creditor = _field(block, "Credor:", ("Fonte de Recurso:",))
        funding = _field(block, "Fonte de Recurso:", ("Poder:",))
        object_match = re.search(r"Elemento de Despesa:\s*(.*)\Z", block, re.I | re.S)
        obj = " ".join(object_match.group(1).split()) if object_match else ""

        if not date_match or not value_match or not creditor:
            continue

        document, document_type = _mask_document(document_text)
        process = re.search(r"PROCESSO\s*(?:N[º°.]*)?\s*[:\-]?\s*(\d+/\d{4})", obj, re.I)
        rows.append({
            "source_system": SOURCE_SYSTEM,
            "commitment_number": note,
            "modality": modality,
            "record_type": record_type,
            "issue_date": datetime.strptime(date_match.group(1), "%d/%m/%Y").date().isoformat(),
            "committed_value": _money(value_match.group(1)),
            "creditor_document": document,
            "creditor_document_type": document_type,
            "creditor_name": creditor,
            "funding_source": funding,
            "object": obj,
            "process_number": process.group(1) if process else None,
            "is_parliamentary_compensatory_allowance": "VERBA COMPENSATÓRIA DE ATIVIDADE PARLAMENTAR" in obj.upper(),
            "is_travel_related": "DIÁRIA" in obj.upper() or "VIAGEN" in obj.upper(),
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def load_official_identity(root: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    officials: dict[str, dict] = {}
    with (root / "cities/salvador/data/seed/officials.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            officials[_norm_name(row["name"])] = row
    aliases: dict[str, dict] = {}
    alias_path = root / "cities/salvador/data/seed/official_aliases.csv"
    if alias_path.exists():
        with alias_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                aliases[_norm_name(row["record_name"])] = row
    return officials, aliases


def attach_verified_official_matches(rows: list[dict], root: Path) -> list[dict]:
    officials, aliases = load_official_identity(root)
    for row in rows:
        name_key = _norm_name(row["creditor_name"])
        match = officials.get(name_key)
        evidence_url = None
        match_type = None
        if match:
            match_type = "exact_normalized_official_name"
            evidence_url = match["source_url"]
        elif name_key in aliases:
            alias = aliases[name_key]
            official_key = _norm_name(alias["official_name"])
            match = officials.get(official_key)
            if match:
                match_type = alias["match_type"]
                evidence_url = alias["evidence_url"]
        row["matched_official_name"] = match["name"] if match else None
        row["matched_official_office"] = match["office"] if match else None
        row["matched_official_party"] = match["party"] if match else None
        row["official_match_type"] = match_type
        row["official_match_evidence_url"] = evidence_url
    return rows


def to_expense_event(row: dict, *, city_slug: str = "salvador") -> dict:
    """Map a CMS commitment to the reusable event model without changing its accounting stage."""
    return {
        "city_slug": city_slug,
        "source_system": SOURCE_SYSTEM,
        "event_key": row["commitment_number"],
        "stage": "commitment",
        "event_date": row.get("issue_date"),
        "agency_code": None,
        "agency_name": "Câmara Municipal de Salvador",
        "supplier_document": row.get("creditor_document"),
        "supplier_name": row.get("creditor_name"),
        "process_number": row.get("process_number"),
        "contract_number": None,
        "function_code": None,
        "function_name": None,
        "subfunction_code": None,
        "subfunction_name": None,
        "program_code": None,
        "program_name": None,
        "action_code": None,
        "action_name": None,
        "expense_nature_code": None,
        "expense_nature_name": None,
        "funding_source_code": None,
        "funding_source_name": row.get("funding_source"),
        "gross_value": row.get("committed_value"),
        "net_value": None,
        "source_url": row["source_url"],
        "observed_at": row["observed_at"],
        "snapshot_sha256": row["snapshot_sha256"],
    }


def _headers() -> dict[str, str]:
    return {
        "User-Agent": "municipal-transparency-research/0.3 (+public-data-audit)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }


def _f3_fields(html: str) -> dict[str, str]:
    form = re.search(r'<form\b(?=[^>]*\bname=["\']F3["\'])[^>]*>.*?</form>', html, re.I | re.S)
    if not form:
        raise ValueError("CMS ScriptCase F3 navigation form not found")
    fields: dict[str, str] = {}
    for match in re.finditer(r'<input[^>]+name=["\']([^"\']+)["\'][^>]*>', form.group(0), re.I):
        tag = match.group(0)
        name = match.group(1)
        value_match = re.search(r'value=["\']([^"\']*)["\']', tag, re.I)
        fields[name] = value_match.group(1) if value_match else ""
    return fields


def _navigation_payload(html: str, opcode: str) -> dict[str, str]:
    fields = _f3_fields(html)
    fields.update({
        "nmgp_opcao": opcode,
        "nmgp_parms": "SC_null",
        "nmgp_orig_pesq": "",
        "nmgp_url_saida": "",
        "nmgp_outra_jan": "",
    })
    return fields


def collect(root: Path, out_dir: Path, *, max_pages: int = 1000) -> dict:
    """Exhaust the default public commitment ledger and prove both navigation and parser coverage."""
    out_dir.mkdir(parents=True, exist_ok=True)
    all_rows: dict[str, dict] = {}
    page_meta: list[dict] = []
    termination_reason: str | None = None
    stopped_error: str | None = None
    parse_gaps: list[dict] = []

    with httpx.Client(headers=_headers(), follow_redirects=True, timeout=60.0) as client:
        response = client.get(URL)
        response.raise_for_status()
        html = response.text
        page = 1
        previous_visible_notes: tuple[str, ...] | None = None

        while page <= max_pages:
            meta = persist_snapshot(
                out_dir=out_dir / "raw",
                source_id=f"cms_empenhos_p{page:04d}",
                requested_url=URL if page == 1 else f"{URL}#scriptcase-avanca-{page}",
                final_url=str(response.url),
                status_code=response.status_code,
                content_type=response.headers.get("content-type", "text/html"),
                body=response.content,
            )
            text = visible_text(html)
            visible_notes = tuple(note.upper() for note in NOTE_RE.findall(text))
            rows = parse_visible_commitments(
                text, source_url=str(response.url), observed_at=meta.collected_at, snapshot_sha256=meta.sha256
            )
            parsed_notes = tuple(row["commitment_number"] for row in rows)

            if previous_visible_notes is not None and visible_notes == previous_visible_notes:
                termination_reason = "source_repeated_page_after_avanca"
                break

            missing = sorted(set(visible_notes) - set(parsed_notes))
            if missing or len(parsed_notes) != len(set(visible_notes)):
                parse_gaps.append({
                    "page": page,
                    "visible_records": len(set(visible_notes)),
                    "parsed_records": len(parsed_notes),
                    "missing_commitments": missing,
                })

            new_count = 0
            for row in rows:
                if row["commitment_number"] not in all_rows:
                    all_rows[row["commitment_number"]] = row
                    new_count += 1
            page_meta.append({
                "page": page,
                "visible_records": len(set(visible_notes)),
                "records_parsed": len(rows),
                "new_records": new_count,
                "first_commitment": visible_notes[0] if visible_notes else None,
                "last_commitment": visible_notes[-1] if visible_notes else None,
                "sha256": meta.sha256,
                "status_code": response.status_code,
            })

            if not visible_notes:
                termination_reason = "source_returned_empty_page"
                break
            previous_visible_notes = visible_notes
            try:
                payload = _navigation_payload(html, "avanca")
                response = client.post(URL, data=payload)
                response.raise_for_status()
                html = response.text
            except Exception as exc:
                stopped_error = f"{type(exc).__name__}: {exc}"
                termination_reason = "navigation_error"
                break
            page += 1
        else:
            termination_reason = "max_pages_reached"

    rows = list(all_rows.values())
    attach_verified_official_matches(rows, root)
    output = out_dir / "commitments.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    expense_output = out_dir / "expense_events.jsonl"
    with expense_output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(to_expense_event(row), ensure_ascii=False, sort_keys=True) + "\n")

    source_exhausted = termination_reason in {"source_repeated_page_after_avanca", "source_returned_empty_page"}
    parser_complete = not parse_gaps
    complete = source_exhausted and parser_complete
    coverage = {
        "source_url": URL,
        "records_parsed": len(rows),
        "expense_events_emitted": len(rows),
        "pages_with_records": sum(1 for item in page_meta if item["visible_records"]),
        "source_exhausted": source_exhausted,
        "parser_complete_for_visible_records": parser_complete,
        "complete": complete,
        "coverage_scope": "default public ScriptCase commitment ledger view in the observed session",
        "termination_reason": termination_reason,
        "stopped_error": stopped_error,
        "parse_gaps": parse_gaps,
        "coverage_note": (
            "Complete for the default public ScriptCase commitment view: navigation reached source exhaustion and every visible commitment identifier on every collected page was normalized. This does not assert completeness for hidden historical filters or other CMS accounting systems."
            if complete else
            "Coverage is partial unless both source_exhausted=true and parser_complete_for_visible_records=true. Collected records remain valid snapshots."
        ),
        "privacy_note": "Individual CPF values displayed by the source are masked in normalized output; CNPJ values are retained.",
        "accounting_note": "Every normalized expense event has stage=commitment. No commitment is re-labelled as liquidation or payment.",
        "pages": page_meta,
    }
    coverage_path = out_dir / "coverage.json"
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output": output, "expense_output": expense_output, "coverage": coverage, "coverage_path": coverage_path, "rows": rows}
