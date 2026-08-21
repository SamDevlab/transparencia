from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from transparencia.collectors.bahia_open_data import BahiaOpenDataError


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def normalize_identifier(value: Any) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    compact = re.sub(r"[^A-Z0-9]+", "", text)
    return compact or None


def _year(value: Any) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _decode(sample: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return sample.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    return sample.decode("utf-8", errors="replace"), "utf-8-replace"


def _delimiter(text: str) -> str:
    sample = "\n".join(line for line in text.splitlines()[:8] if line.strip())
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,#|\t,").delimiter
    except csv.Error:
        return ";"


def _reader(zf: zipfile.ZipFile, member: str):
    with zf.open(member, "r") as raw:
        sample = raw.read(128 * 1024)
    text, encoding = _decode(sample)
    delimiter = _delimiter(text)
    header_reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        headers = next(header_reader)
    except StopIteration as exc:
        raise BahiaOpenDataError(f"Tabela vazia: {member}") from exc
    actual_encoding = "utf-8" if encoding == "utf-8-replace" else encoding
    raw = zf.open(member, "r")
    wrapper = io.TextIOWrapper(raw, encoding=actual_encoding, errors="replace", newline="")
    return raw, wrapper, csv.DictReader(wrapper, delimiter=delimiter), headers


def _field(headers: list[str], *candidates: str) -> str | None:
    normalized = {header: _norm(header) for header in headers}
    for candidate in candidates:
        target = _norm(candidate)
        for original, normed in normalized.items():
            if normed == target:
                return original
    return None


def extract_procurement_instrument_links(path: Path, *, target_year: int) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de licitações não é um ZIP válido")
    with zipfile.ZipFile(path, "r") as zf:
        names = [info.filename for info in zf.infolist() if not info.is_dir()]
        primary_member = next((name for name in names if _norm(Path(name).name).startswith("VW PROC AQUISICAO LIC REQ")), None)
        relation_member = next((name for name in names if _norm(Path(name).name).startswith("VW PROC AQUISICAO ITEM INSTRUMENTO")), None)
        if not primary_member or not relation_member:
            raise BahiaOpenDataError("Tabelas oficiais de aquisição/instrumento não encontradas no ZIP")

        raw, wrapper, reader, headers = _reader(zf, primary_member)
        try:
            year_field = _field(headers, "Ano da Aquisição")
            process_field = _field(headers, "Processo de Aquisição", "Processo de Aquisição Formatado")
            if not year_field or not process_field:
                raise BahiaOpenDataError("Tabela principal sem ano/processo de aquisição")
            processes: set[str] = set()
            primary_rows = 0
            selected_rows = 0
            for row in reader:
                primary_rows += 1
                if _year(row.get(year_field)) != target_year:
                    continue
                selected_rows += 1
                key = normalize_identifier(row.get(process_field))
                if key:
                    processes.add(key)
        finally:
            wrapper.close()
            raw.close()

        raw, wrapper, reader, headers = _reader(zf, relation_member)
        try:
            relation_process = _field(headers, "Processo_de_Aquisicao", "Processo de Aquisição")
            instrument_field = _field(headers, "NUM_INST_FORMATADO", "NUM_INSTRUMENTO_ORCAMENTO")
            if not relation_process or not instrument_field:
                raise BahiaOpenDataError("Tabela de relacionamento sem processo/instrumento")
            relation_rows = 0
            matched_rows = 0
            links: set[tuple[str, str]] = set()
            for row in reader:
                relation_rows += 1
                process_key = normalize_identifier(row.get(relation_process))
                if not process_key or process_key not in processes:
                    continue
                instrument_key = normalize_identifier(row.get(instrument_field))
                if not instrument_key:
                    continue
                matched_rows += 1
                links.add((process_key, instrument_key))
        finally:
            wrapper.close()
            raw.close()

    process_with_instruments = len({process for process, _ in links})
    instruments = len({instrument for _, instrument in links})
    return {
        "dataset": "licitacoes_contratos_links",
        "selected_year": target_year,
        "source_tables": {
            "primary": primary_member,
            "relation": relation_member,
        },
        "fields": {
            "primary_year": year_field,
            "primary_process": process_field,
            "relation_process": relation_process,
            "relation_instrument": instrument_field,
        },
        "primary_rows": primary_rows,
        "primary_selected_rows": selected_rows,
        "unique_processes_selected": len(processes),
        "relation_rows": relation_rows,
        "relation_rows_matching_selected_processes": matched_rows,
        "exact_links": [
            {"process_id": process, "instrument_id": instrument}
            for process, instrument in sorted(links)
        ],
        "exact_link_count": len(links),
        "processes_with_instruments": process_with_instruments,
        "unique_instruments": instruments,
        "identity_rule": "Somente igualdade após normalização de pontuação/espaço/capitalização de dois campos oficiais. Nenhuma aproximação textual é usada.",
    }
