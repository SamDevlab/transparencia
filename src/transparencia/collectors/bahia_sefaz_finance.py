from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from transparencia.collectors.bahia_open_data import BahiaOpenDataError


@dataclass(frozen=True)
class TableSpec:
    delimiter: str
    encoding: str
    headers: tuple[str, ...]


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        parsed = float(text)
        return -parsed if negative else parsed
    except ValueError:
        return None


def _year(value: Any) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _decode_sample(sample: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return sample.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return sample.decode("utf-8", errors="replace"), "utf-8-replace"


def _detect_delimiter(text: str) -> str:
    lines = [line for line in text.splitlines() if line.strip()][:8]
    sample = "\n".join(lines)
    if not sample:
        return ";"
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,#|\t,").delimiter
    except csv.Error:
        counts = {candidate: sample.count(candidate) for candidate in (";", "#", "|", "\t", ",")}
        return max(counts, key=counts.get) if any(counts.values()) else ";"


def _spec(zf: zipfile.ZipFile, member: str) -> TableSpec:
    with zf.open(member, "r") as raw:
        sample = raw.read(128 * 1024)
    text, encoding = _decode_sample(sample)
    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        headers = tuple(next(reader))
    except StopIteration as exc:
        raise BahiaOpenDataError(f"Tabela vazia no ZIP: {member}") from exc
    if len(headers) < 2:
        raise BahiaOpenDataError(f"Tabela sem colunas suficientes: {member}")
    return TableSpec(delimiter=delimiter, encoding=encoding, headers=headers)


def _first(headers: Iterable[str], patterns: Iterable[tuple[str, ...]], *, reject: tuple[str, ...] = ()) -> str | None:
    rows = [(header, _norm(header)) for header in headers]
    for required in patterns:
        for original, normalized in rows:
            if all(token in normalized for token in required) and not any(token in normalized for token in reject):
                return original
    return None


def _money_field(headers: Iterable[str], stage: str) -> str | None:
    candidates: list[tuple[int, str]] = []
    stage_tokens = {
        "committed": ("EMPENH",),
        "liquidated": ("LIQUID",),
        "paid": ("PAGO", "PAGAMENTO", "PGTO"),
    }[stage]
    for header in headers:
        normalized = _norm(header)
        if not any(token in normalized for token in stage_tokens):
            continue
        if any(token in normalized for token in ("COD", "NUM", "DATA", "PROCESSO", "PERCENT", "PERC", "QTD", "QUANT")):
            continue
        score = 0
        if "VALOR" in normalized or normalized.startswith("VAL ") or normalized.startswith("VLR "):
            score += 8
        if "DESPESA" in normalized:
            score += 3
        if "SALDO" in normalized:
            score -= 5
        if "RETEN" in normalized or "DESCONTO" in normalized:
            score -= 4
        if stage == "paid" and ("PAGO" in normalized or "PAGAMENTO" in normalized or "PGTO" in normalized):
            score += 5
        if stage == "committed" and "EMPENH" in normalized:
            score += 5
        if stage == "liquidated" and "LIQUID" in normalized:
            score += 5
        candidates.append((score, header))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def _payment_value_fields(headers: Iterable[str]) -> list[str]:
    result: list[tuple[int, str]] = []
    for header in headers:
        normalized = _norm(header)
        payment_token = any(token in normalized for token in ("PAGAMENTO", "PAGO", "PGTO"))
        value_token = any(token in normalized for token in ("VALOR", "VAL ", "VLR "))
        if not (payment_token and value_token):
            continue
        if any(token in normalized for token in ("COD", "NUM", "DATA", "PROCESSO", "PERCENT", "PERC")):
            continue
        score = 10
        if "LIQUIDO" in normalized:
            score += 2
        if "BRUTO" in normalized:
            score += 1
        if "RETEN" in normalized or "DESCONTO" in normalized:
            score -= 5
        result.append((score, header))
    result.sort(key=lambda item: (-item[0], _norm(item[1])))
    return [header for _, header in result[:12]]


def _table_members(zf: zipfile.ZipFile, *, max_uncompressed: int = 8_000_000_000) -> tuple[list[str], int, int]:
    infos = [info for info in zf.infolist() if not info.is_dir()]
    if any(".." in Path(info.filename).parts for info in infos):
        raise BahiaOpenDataError("ZIP contém caminho inseguro")
    uncompressed = sum(info.file_size for info in infos)
    if uncompressed > max_uncompressed:
        raise BahiaOpenDataError(f"ZIP excede limite descompactado de {max_uncompressed} bytes")
    members = [info.filename for info in infos if info.filename.lower().endswith((".csv", ".txt")) and info.file_size > 0]
    if not members:
        raise BahiaOpenDataError("ZIP não contém tabelas CSV/TXT")
    return members, len(infos), uncompressed


def _privacy_headers(headers: Iterable[str]) -> list[str]:
    tokens = ("CPF", "CNPJ", "CREDOR", "FORNECEDOR", "BENEFICIARIO", "FAVORECIDO", "NOME PESSOA")
    return [header for header in headers if any(token in _norm(header) for token in tokens)]


def _expense_table(zf: zipfile.ZipFile, member: str, *, target_year: int) -> dict[str, Any]:
    spec = _spec(zf, member)
    headers = list(spec.headers)
    year_field = _first(headers, (("ANO", "EXERC"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
    date_field = _first(headers, (("DATA",),), reject=("ATUALIZ",))
    agency_field = _first(headers, (("NOM", "ORGAO"), ("ORGAO",), ("SECRETARIA",)), reject=("COD", "SIGLA"))
    function_field = _first(headers, (("NOM", "FUNCAO"), ("FUNCAO",)), reject=("COD",))
    stage_fields = {
        "committed": _money_field(headers, "committed"),
        "liquidated": _money_field(headers, "liquidated"),
        "paid": _money_field(headers, "paid"),
    }
    stage_fields = {key: value for key, value in stage_fields.items() if value}
    totals = {stage: 0.0 for stage in stage_fields}
    numeric_rows = {stage: 0 for stage in stage_fields}
    rows = 0
    selected_rows = 0
    years: Counter[int] = Counter()
    by_agency: dict[str, dict[str, float]] = defaultdict(lambda: {stage: 0.0 for stage in stage_fields})
    by_function: dict[str, dict[str, float]] = defaultdict(lambda: {stage: 0.0 for stage in stage_fields})

    encoding = "utf-8" if spec.encoding == "utf-8-replace" else spec.encoding
    with zf.open(member, "r") as raw:
        text = io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="")
        reader = csv.DictReader(text, delimiter=spec.delimiter)
        for row in reader:
            rows += 1
            row_year = _year(row.get(year_field)) if year_field else _year(row.get(date_field)) if date_field else None
            if row_year is not None:
                years[row_year] += 1
            if row_year != target_year:
                continue
            selected_rows += 1
            values: dict[str, float] = {}
            for stage, field in stage_fields.items():
                parsed = _number(row.get(field))
                if parsed is None:
                    values[stage] = 0.0
                    continue
                values[stage] = parsed
                totals[stage] += parsed
                numeric_rows[stage] += 1
            if agency_field:
                agency = str(row.get(agency_field) or "Não informado").strip() or "Não informado"
                for stage, value in values.items():
                    by_agency[agency][stage] += value
            if function_field:
                function = str(row.get(function_field) or "Não informado").strip() or "Não informado"
                for stage, value in values.items():
                    by_function[function][stage] += value

    score = len(stage_fields) * 20 + (12 if year_field or date_field else 0) + (4 if agency_field else 0) + (2 if function_field else 0)
    if selected_rows == 0:
        score -= 20

    def top(groups: dict[str, dict[str, float]], stage: str, limit: int = 40) -> list[dict[str, Any]]:
        ordered = sorted(groups.items(), key=lambda item: item[1].get(stage, 0.0), reverse=True)[:limit]
        return [{"name": name, stage: round(values.get(stage, 0.0), 2)} for name, values in ordered if values.get(stage, 0.0) != 0]

    return {
        "member": member,
        "rows": rows,
        "selected_rows": selected_rows,
        "score": score,
        "schema": {
            "delimiter": spec.delimiter,
            "encoding": spec.encoding,
            "headers": headers,
            "detected_fields": {
                "year": year_field,
                "date": date_field,
                "agency": agency_field,
                "function": function_field,
                "stages": stage_fields,
            },
            "privacy_sensitive_columns_present": _privacy_headers(headers),
        },
        "years": {str(year): count for year, count in sorted(years.items())},
        "stage_totals": {stage: {"sum": round(value, 2), "numeric_rows": numeric_rows[stage]} for stage, value in totals.items()},
        "top_agencies": {stage: top(by_agency, stage) for stage in stage_fields},
        "top_functions": {stage: top(by_function, stage) for stage in stage_fields},
    }


def summarize_sefaz_expenses_zip(path: Path, *, target_year: int) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de despesas não é um ZIP válido")
    with zipfile.ZipFile(path, "r") as zf:
        members, total_members, uncompressed = _table_members(zf)
        tables = [_expense_table(zf, member, target_year=target_year) for member in members]
    candidates = [table for table in tables if table["schema"]["detected_fields"]["stages"] and table["selected_rows"] > 0]
    primary = max(candidates, key=lambda table: (table["score"], table["selected_rows"]), default=None)
    if primary is None:
        raise BahiaOpenDataError("Nenhuma tabela principal de despesas com estágio financeiro e ano foi identificada")
    return {
        "dataset": "despesas",
        "selected_year": target_year,
        "archive": {"members": total_members, "tabular_members": len(tables), "uncompressed_bytes": uncompressed},
        "primary_table": primary,
        "tables": [
            {
                "member": table["member"],
                "rows": table["rows"],
                "selected_rows": table["selected_rows"],
                "score": table["score"],
                "schema": table["schema"],
                "years": table["years"],
                "stage_totals": table["stage_totals"],
            }
            for table in tables
        ],
        "interpretation": "Somente a tabela principal identificada pelo esquema alimenta os totais anuais. Empenho, liquidação e pagamento permanecem separados. Tabelas relacionadas não são somadas entre si.",
        "privacy_note": "Nenhuma linha bruta, CPF/CNPJ ou nome de credor é republicado. Agregações públicas são limitadas a órgãos e funções.",
    }


def _payment_table(zf: zipfile.ZipFile, member: str, *, target_year: int) -> dict[str, Any]:
    spec = _spec(zf, member)
    headers = list(spec.headers)
    year_field = _first(headers, (("ANO", "EXERC"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
    date_field = _first(headers, (("DATA", "PAG"), ("DATA",)), reject=("ATUALIZ",))
    agency_field = _first(headers, (("NOM", "ORGAO"), ("ORGAO",), ("SECRETARIA",)), reject=("COD", "SIGLA"))
    value_fields = _payment_value_fields(headers)
    totals = {field: 0.0 for field in value_fields}
    numeric_rows = {field: 0 for field in value_fields}
    rows = 0
    selected_rows = 0
    years: Counter[int] = Counter()
    by_agency: dict[str, dict[str, float]] = defaultdict(lambda: {field: 0.0 for field in value_fields})

    encoding = "utf-8" if spec.encoding == "utf-8-replace" else spec.encoding
    with zf.open(member, "r") as raw:
        text = io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="")
        reader = csv.DictReader(text, delimiter=spec.delimiter)
        for row in reader:
            rows += 1
            row_year = _year(row.get(year_field)) if year_field else _year(row.get(date_field)) if date_field else None
            if row_year is not None:
                years[row_year] += 1
            if row_year != target_year:
                continue
            selected_rows += 1
            for field in value_fields:
                parsed = _number(row.get(field))
                if parsed is None:
                    continue
                totals[field] += parsed
                numeric_rows[field] += 1
                if agency_field:
                    agency = str(row.get(agency_field) or "Não informado").strip() or "Não informado"
                    by_agency[agency][field] += parsed

    score = len(value_fields) * 12 + (12 if year_field or date_field else 0) + (4 if agency_field else 0)
    if selected_rows == 0:
        score -= 20
    primary_value_field = value_fields[0] if value_fields else None
    top_agencies: list[dict[str, Any]] = []
    if primary_value_field:
        top_agencies = [
            {"name": name, "value": round(values[primary_value_field], 2)}
            for name, values in sorted(by_agency.items(), key=lambda item: item[1][primary_value_field], reverse=True)[:40]
            if values[primary_value_field] != 0
        ]
    return {
        "member": member,
        "rows": rows,
        "selected_rows": selected_rows,
        "score": score,
        "schema": {
            "delimiter": spec.delimiter,
            "encoding": spec.encoding,
            "headers": headers,
            "detected_fields": {
                "year": year_field,
                "date": date_field,
                "agency": agency_field,
                "payment_value_fields": value_fields,
                "primary_value_field": primary_value_field,
            },
            "privacy_sensitive_columns_present": _privacy_headers(headers),
        },
        "years": {str(year): count for year, count in sorted(years.items())},
        "value_field_sums": {field: {"sum": round(value, 2), "numeric_rows": numeric_rows[field]} for field, value in totals.items()},
        "top_agencies": top_agencies,
    }


def summarize_sefaz_payments_zip(path: Path, *, target_year: int) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de pagamentos não é um ZIP válido")
    with zipfile.ZipFile(path, "r") as zf:
        members, total_members, uncompressed = _table_members(zf)
        tables = [_payment_table(zf, member, target_year=target_year) for member in members]
    candidates = [
        table for table in tables
        if table["schema"]["detected_fields"]["payment_value_fields"] and table["selected_rows"] > 0
    ]
    primary = max(candidates, key=lambda table: (table["score"], table["selected_rows"]), default=None)
    if primary is None:
        raise BahiaOpenDataError("Nenhuma tabela principal de pagamentos com valor e ano foi identificada")
    primary_field = primary["schema"]["detected_fields"]["primary_value_field"]
    primary_sum = primary["value_field_sums"].get(primary_field) if primary_field else None
    return {
        "dataset": "pagamentos",
        "selected_year": target_year,
        "archive": {"members": total_members, "tabular_members": len(tables), "uncompressed_bytes": uncompressed},
        "primary_table": primary,
        "selected_year_payment": {
            "source_field": primary_field,
            "sum": primary_sum.get("sum") if primary_sum else None,
            "numeric_rows": primary_sum.get("numeric_rows") if primary_sum else 0,
        },
        "tables": [
            {
                "member": table["member"],
                "rows": table["rows"],
                "selected_rows": table["selected_rows"],
                "score": table["score"],
                "schema": table["schema"],
                "years": table["years"],
                "value_field_sums": table["value_field_sums"],
            }
            for table in tables
        ],
        "interpretation": "O total publicado usa apenas o campo de pagamento identificado na tabela principal. Outros campos monetários permanecem rotulados pelo nome original e tabelas relacionadas não são somadas automaticamente.",
        "privacy_note": "Nenhuma linha bruta, CPF/CNPJ, favorecido ou credor é republicado. Agregações públicas são limitadas a órgãos.",
    }
