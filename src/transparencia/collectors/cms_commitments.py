from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import httpx

from ..provenance import persist_snapshot
from .cms import visible_text

URL = "https://cmsalvador.sys.inf.br/ca/gridRegistroEmpenho/"
SOURCE_SYSTEM = "CMS_EMPENHOS"


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


def parse_visible_commitments(text: str, *, source_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    # The ScriptCase page renders repeated labeled records. Restrict to the actual record section.
    pattern = re.compile(
        r"Empenho:\s*(?P<note>\d{4}NE\d+)\s+"
        r"Modalidade:\s*(?P<modality>.*?)\s+"
        r"Tipo:\s*(?P<type>.*?)\s+"
        r"Data de Emiss[aã]o:\s*(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"Valor R\$:\s*(?P<value>[\d.,]+)\s+"
        r"CNPJCPF:\s*(?P<document>.*?)\s+"
        r"Credor:\s*(?P<creditor>.*?)\s+"
        r"Fonte de Recurso:\s*(?P<funding>.*?)\s+"
        r"Poder:\s*(?P<power>.*?)\s+Org[aã]o:\s*(?P<agency>.*?)\s+Unidade:\s*(?P<unit>.*?)\s+"
        r"Funç[aã]o:\s*(?P<function>.*?)\s+Sub Funç[aã]o:\s*(?P<subfunction>.*?)\s+Programa:\s*(?P<program>.*?)\s+Projeto Atividade:\s*(?P<action>.*?)\s+"
        r"Categoria Econ[oô]mica:\s*(?P<category>.*?)\s+Grupo de Despesa:\s*(?P<group>.*?)\s+Modelo de Aplicaç[aã]o:\s*(?P<application>.*?)\s+Elemento de Despesa:\s*(?P<element>.*?)\s+"
        r"(?P<object>.*?)"
        r"(?=\s+Empenho:\s*\d{4}NE\d+|\Z)",
        re.S | re.I,
    )
    rows: list[dict] = []
    seen: set[str] = set()
    for match in pattern.finditer(text):
        note = match.group("note").strip()
        if note in seen:
            continue
        seen.add(note)
        document, document_type = _mask_document(match.group("document"))
        obj = " ".join(match.group("object").split())
        process = re.search(r"PROCESSO\s*(?:N[º°.]*)?\s*[:\-]?\s*(\d+/\d{4})", obj, re.I)
        rows.append({
            "source_system": SOURCE_SYSTEM,
            "commitment_number": note,
            "modality": " ".join(match.group("modality").split()),
            "record_type": " ".join(match.group("type").split()),
            "issue_date": datetime.strptime(match.group("date"), "%d/%m/%Y").date().isoformat(),
            "committed_value": _money(match.group("value")),
            "creditor_document": document,
            "creditor_document_type": document_type,
            "creditor_name": " ".join(match.group("creditor").split()),
            "funding_source": " ".join(match.group("funding").split()),
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


def collect(root: Path, out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "municipal-transparency-research/0.2 (+public-data-audit)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "pt-BR,pt;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        response = client.get(URL)
        response.raise_for_status()
    meta = persist_snapshot(
        out_dir=out_dir / "raw",
        source_id="cms_empenhos_visible",
        requested_url=URL,
        final_url=str(response.url),
        status_code=response.status_code,
        content_type=response.headers.get("content-type", "text/html"),
        body=response.content,
    )
    rows = parse_visible_commitments(
        visible_text(response.text), source_url=str(response.url), observed_at=meta.collected_at, snapshot_sha256=meta.sha256
    )
    attach_verified_official_matches(rows, root)
    output = out_dir / "commitments_visible.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    coverage = {
        "source_url": URL,
        "records_visible_and_parsed": len(rows),
        "complete": False,
        "coverage_note": "The public ScriptCase HTML exposes a current visible slice. Pagination/all-record retrieval has not yet been proven, so this snapshot must not be described as the complete Câmara commitment ledger.",
        "privacy_note": "Individual CPF values displayed by the source are masked in normalized output; CNPJ values are retained.",
        "snapshot_sha256": meta.sha256,
        "observed_at": meta.collected_at,
    }
    (out_dir / "coverage.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"output": output, "coverage": coverage, "rows": rows}
