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
from urllib.parse import urlsplit

import httpx

from transparencia.collectors.bahia_open_data import BahiaOpenDataError, DownloadEvidence, stream_to_temp

OFFICIAL_DATA_HOST = "dados.ba.gov.br"


@dataclass(frozen=True)
class TabularSpec:
    delimiter: str
    encoding: str
    headers: tuple[str, ...]


def _norm(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def _words(value: str | None) -> list[str]:
    return _norm(value).split()


def _has_word_prefix(value: str | None, *prefixes: str) -> bool:
    return any(word.startswith(prefix) for word in _words(value) for prefix in prefixes)


def _number(value: Any) -> float | None:
    if value in (None, ""):
        return None
    text = str(value).strip().replace("R$", "").replace("US$", "").replace(" ", "")
    if not text:
        return None
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _year(value: Any) -> int | None:
    match = re.search(r"\b(20\d{2}|19\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _certificate_chain_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "CERTIFICATE_VERIFY_FAILED" in text or "CERTIFICATE VERIFY FAILED" in text


def download_ckan_resource(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    max_bytes: int = 900_000_000,
) -> tuple[Path, DownloadEvidence, dict[str, Any]]:
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != OFFICIAL_DATA_HOST:
        raise BahiaOpenDataError(f"Recurso SEFAZ fora do host oficial permitido: {url}")

    timeout = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)
    try:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True, verify=True) as client:
            path, evidence = stream_to_temp(client, url, max_bytes=max_bytes)
        return path, evidence, {"tls_verified": True, "transport_note": "Validação TLS concluída normalmente."}
    except httpx.ConnectError as exc:
        if not _certificate_chain_error(exc):
            raise
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True, verify=False) as client:
            path, evidence = stream_to_temp(client, url, max_bytes=max_bytes)
        return path, evidence, {
            "tls_verified": False,
            "fallback_reason": "certificate_chain_error",
            "transport_note": "O recurso foi baixado do mesmo host oficial dados.ba.gov.br sem validação TLS porque o runner não conseguiu validar a cadeia de certificados; a condição foi registrada.",
        }


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


def inspect_csv_path(path: Path) -> TabularSpec:
    with path.open("rb") as handle:
        sample = handle.read(128 * 1024)
    text, encoding = _decode_sample(sample)
    delimiter = _detect_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        headers = tuple(next(reader))
    except StopIteration as exc:
        raise BahiaOpenDataError("Arquivo tabular vazio") from exc
    if len(headers) < 2:
        raise BahiaOpenDataError("Arquivo tabular não contém ao menos duas colunas")
    return TabularSpec(delimiter=delimiter, encoding=encoding, headers=headers)


def _open_dict_reader(path: Path, spec: TabularSpec):
    encoding = "utf-8" if spec.encoding == "utf-8-replace" else spec.encoding
    handle = path.open("r", encoding=encoding, errors="replace", newline="")
    return handle, csv.DictReader(handle, delimiter=spec.delimiter)


def _first_header(headers: Iterable[str], predicates: Iterable[tuple[str, ...]], *, reject: tuple[str, ...] = ()) -> str | None:
    normalized = [(header, _norm(header)) for header in headers]
    for required in predicates:
        for original, normed in normalized:
            if all(token in normed for token in required) and not any(token in normed for token in reject):
                return original
    return None


def _value_headers(headers: Iterable[str]) -> dict[str, str | None]:
    return {
        "forecast": _first_header(headers, (("PREVIST",), ("PREVISAO",)), reject=("COD", "PERCENT")),
        "updated": _first_header(headers, (("ATUALIZ",),), reject=("DATA", "COD", "PERCENT")),
        "realized": _first_header(headers, (("ARRECAD",), ("REALIZ",)), reject=("DATA", "COD", "PERCENT")),
    }


def summarize_sefaz_revenues(path: Path, *, target_year: int | None = None) -> dict[str, Any]:
    spec = inspect_csv_path(path)
    headers = list(spec.headers)
    year_field = _first_header(headers, (("ANO", "EXERC"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
    month_field = _first_header(headers, (("MES", "EXERC"), ("MES",)), reject=("COD",))
    agency_field = _first_header(headers, (("NOM", "ORGAO", "ORCAMENTO"), ("ORGAO",), ("UNIDADE", "ORCAMENT")), reject=("COD", "SIGLA"))
    nature_field = _first_header(headers, (("NATUREZA", "RECEITA"), ("RECEITA", "NATUREZA")), reject=("COD",))
    category_field = _first_header(headers, (("CATEGORIA",),), reject=("COD",))
    origin_field = _first_header(headers, (("ORIGEM",),), reject=("COD",))
    source_field = _first_header(headers, (("NOME", "FONTE", "RECURSO"), ("FONTE", "RECURSO")), reject=("COD",))
    value_fields = _value_headers(headers)

    rows = 0
    rows_by_year: Counter[int | str] = Counter()
    totals_by_year: dict[int | str, dict[str, float]] = defaultdict(lambda: {"forecast": 0.0, "updated": 0.0, "realized": 0.0})
    monthly: dict[str, dict[str, float]] = defaultdict(lambda: {"forecast": 0.0, "updated": 0.0, "realized": 0.0, "rows": 0.0})
    agencies: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, "realized": 0.0})
    categories: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, "realized": 0.0})
    origins: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, "realized": 0.0})
    sources: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, "realized": 0.0})

    handle, reader = _open_dict_reader(path, spec)
    try:
        for row in reader:
            rows += 1
            row_year = _year(row.get(year_field)) if year_field else None
            year_key: int | str = row_year if row_year is not None else "nao_identificado"
            rows_by_year[year_key] += 1
            values: dict[str, float] = {}
            for semantic, field in value_fields.items():
                parsed = _number(row.get(field)) if field else None
                values[semantic] = parsed or 0.0
                totals_by_year[year_key][semantic] += values[semantic]

            if target_year is None or row_year == target_year:
                realized = values["realized"]
                if month_field:
                    month_raw = str(row.get(month_field) or "").strip()
                    month_number = int(month_raw) if month_raw.isdigit() and 1 <= int(month_raw) <= 12 else None
                    if month_number:
                        month_key = f"{row_year or target_year or 'ano'}-{month_number:02d}"
                        monthly[month_key]["rows"] += 1
                        for semantic in ("forecast", "updated", "realized"):
                            monthly[month_key][semantic] += values[semantic]
                for field, bucket in (
                    (agency_field, agencies),
                    (category_field or nature_field, categories),
                    (origin_field, origins),
                    (source_field, sources),
                ):
                    if field:
                        name = str(row.get(field) or "Não informado").strip() or "Não informado"
                        bucket[name]["rows"] += 1
                        bucket[name]["realized"] += realized
    finally:
        handle.close()

    selected = totals_by_year.get(target_year) if target_year is not None else None
    if target_year is not None and target_year not in rows_by_year:
        selected = None

    def top(items: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
        ordered = sorted(items.items(), key=lambda item: (item[1]["realized"], item[1]["rows"]), reverse=True)[:100]
        return [{"name": name, "rows": int(values["rows"]), "realized": round(values["realized"], 2)} for name, values in ordered]

    return {
        "dataset": "receitas",
        "schema": {
            "delimiter": spec.delimiter,
            "encoding": spec.encoding,
            "headers": headers,
            "detected_fields": {
                "year": year_field,
                "month": month_field,
                "agency": agency_field,
                "revenue_nature": nature_field,
                "category": category_field,
                "origin": origin_field,
                "funding_source": source_field,
                **value_fields,
            },
        },
        "rows": rows,
        "rows_by_year": {str(key): value for key, value in sorted(rows_by_year.items(), key=lambda item: str(item[0]))},
        "totals_by_year": {str(key): {name: round(value, 2) for name, value in values.items()} for key, values in sorted(totals_by_year.items(), key=lambda item: str(item[0]))},
        "selected_year": target_year,
        "selected_year_totals": {name: round(value, 2) for name, value in selected.items()} if selected else None,
        "selected_year_monthly": [{"month": key, **{name: round(value, 2) if name != "rows" else int(value) for name, value in values.items()}} for key, values in sorted(monthly.items())],
        "top_agencies_by_realized": top(agencies) if value_fields["realized"] else [],
        "top_revenue_categories_by_realized": top(categories) if value_fields["realized"] else [],
        "top_revenue_origins_by_realized": top(origins) if value_fields["realized"] else [],
        "top_funding_sources_by_realized": top(sources) if value_fields["realized"] else [],
        "interpretation": "Os valores são somas dos campos detectados no arquivo oficial. Previsão, atualização e arrecadação permanecem separados; ausência de campo não é convertida em zero factual.",
    }


def _tabular_spec_from_zip(zf: zipfile.ZipFile, member: str) -> TabularSpec:
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
        raise BahiaOpenDataError(f"Tabela sem colunas suficientes no ZIP: {member}")
    return TabularSpec(delimiter=delimiter, encoding=encoding, headers=headers)


def _classify_licitacao_table(member: str, headers: Iterable[str]) -> str:
    name = _norm(member)
    if "FORNEC" in name:
        return "participantes"
    if "ITEM INSTRUMENTO" in name:
        return "tabela_relacionada"
    if "ITEM" in name:
        return "itens"
    if "LIC REQ" in name or "LICITAC" in name:
        return "licitacoes"

    if any(_has_word_prefix(header, "PARTICIP", "LICITANTE", "FORNECEDOR") for header in headers):
        return "participantes"
    joined = " ".join(_norm(header) for header in headers)
    if "MODALIDADE" in joined or "CERTAME" in joined:
        return "licitacoes"
    if "ITEM" in joined and "VALOR" in joined:
        return "itens"
    if "HOMOLOG" in joined or "ADJUDIC" in joined:
        return "homologacoes"
    return "tabela_relacionada"


def _safe_category(row: dict[str, Any], field: str | None) -> str | None:
    if not field:
        return None
    value = str(row.get(field) or "").strip()
    return value[:240] if value else None


def _summarize_zip_member(zf: zipfile.ZipFile, member: str, *, target_year: int | None) -> dict[str, Any]:
    spec = _tabular_spec_from_zip(zf, member)
    headers = list(spec.headers)
    modality_field = _first_header(headers, (("MODALIDADE",),), reject=("COD",))
    status_field = _first_header(headers, (("SITUACAO",), ("STATUS",)), reject=("COD",))
    agency_field = _first_header(headers, (("SIGLA", "ORGAO", "SOLICITANTE"), ("ORGAO", "SOLICITANTE"), ("ORGAO",), ("UNIDADE",)), reject=("COD", "CPF", "CNPJ"))
    year_field = _first_header(headers, (("ANO", "AQUISICAO"), ("ANO",), ("EXERCICIO",)), reject=("COD",))
    date_field = _first_header(headers, (("DATA", "HOMOLOG"), ("DATA", "ABERT"), ("DATA", "PUBLIC"), ("DATA",)), reject=("ATUALIZ",))
    value_fields = [
        header for header in headers
        if (_has_word_prefix(header, "VALOR") or _norm(header).startswith("VAL "))
        and not any(token in _norm(header) for token in ("COD", "PERCENT"))
    ][:12]
    filterable = bool(year_field or date_field)

    counters = {"modalities": Counter(), "statuses": Counter(), "agencies": Counter(), "years": Counter()}
    value_totals = {header: 0.0 for header in value_fields}
    numeric_counts = {header: 0 for header in value_fields}
    rows = 0
    selected_rows = 0 if target_year is None or filterable else None

    encoding = "utf-8" if spec.encoding == "utf-8-replace" else spec.encoding
    with zf.open(member, "r") as raw:
        text = io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="")
        reader = csv.DictReader(text, delimiter=spec.delimiter)
        for row in reader:
            rows += 1
            row_year = _year(row.get(year_field)) if year_field else _year(row.get(date_field)) if date_field else None
            if row_year is not None:
                counters["years"][row_year] += 1

            if target_year is not None and not filterable:
                continue
            in_scope = target_year is None or row_year == target_year
            if not in_scope:
                continue
            assert selected_rows is not None
            selected_rows += 1
            for counter_name, field in (("modalities", modality_field), ("statuses", status_field), ("agencies", agency_field)):
                category = _safe_category(row, field)
                if category:
                    counters[counter_name][category] += 1
            for field in value_fields:
                parsed = _number(row.get(field))
                if parsed is not None:
                    value_totals[field] += parsed
                    numeric_counts[field] += 1

    def top(counter: Counter[str], limit: int = 50) -> list[dict[str, Any]]:
        return [{"name": name, "rows": count} for name, count in counter.most_common(limit)]

    privacy_fields = [header for header in headers if _has_word_prefix(header, "CPF", "CNPJ", "PARTICIP", "LICITANTE", "FORNECEDOR")]
    return {
        "member": member,
        "classification": _classify_licitacao_table(member, headers),
        "rows": rows,
        "selected_rows": selected_rows,
        "scope_status": "year_filtered" if target_year is not None and filterable else "year_not_filterable" if target_year is not None else "all_years",
        "schema": {
            "delimiter": spec.delimiter,
            "encoding": spec.encoding,
            "headers": headers,
            "detected_fields": {"year": year_field, "date": date_field, "modality": modality_field, "status": status_field, "agency": agency_field, "value_fields": value_fields},
            "privacy_sensitive_columns_present": privacy_fields,
        },
        "years": {str(year): count for year, count in sorted(counters["years"].items())},
        "top_modalities": top(counters["modalities"]),
        "top_statuses": top(counters["statuses"]),
        "top_agencies": top(counters["agencies"]),
        "value_field_sums": {field: {"sum": round(value_totals[field], 2), "numeric_rows": numeric_counts[field]} for field in value_fields},
    }


def _semantic_value(table: dict[str, Any], token: str) -> dict[str, Any] | None:
    for field, value in (table.get("value_field_sums") or {}).items():
        if token in _norm(field):
            return {"field": field, **value}
    return None


def summarize_sefaz_licitacoes_zip(path: Path, *, target_year: int | None = None) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de licitações não é um ZIP válido")
    with zipfile.ZipFile(path, "r") as zf:
        members = [info for info in zf.infolist() if not info.is_dir()]
        if any(".." in Path(info.filename).parts for info in members):
            raise BahiaOpenDataError("ZIP de licitações contém caminho inseguro")
        total_uncompressed = sum(info.file_size for info in members)
        if total_uncompressed > 4_000_000_000:
            raise BahiaOpenDataError("ZIP de licitações excede limite de segurança descompactado")
        csv_members = [info.filename for info in members if info.filename.lower().endswith((".csv", ".txt")) and info.file_size > 0]
        if not csv_members:
            raise BahiaOpenDataError("ZIP de licitações não contém tabelas CSV/TXT")
        tables = [_summarize_zip_member(zf, member, target_year=target_year) for member in csv_members]

    classification_counts = Counter(table["classification"] for table in tables)
    primary_candidates = [table for table in tables if table["classification"] == "licitacoes"]
    primary = max(primary_candidates, key=lambda table: table["rows"], default=None)
    filterable = [table for table in tables if table["selected_rows"] is not None]
    unfilterable = [table for table in tables if table["selected_rows"] is None]

    primary_summary = None
    if primary:
        primary_summary = {
            "member": primary["member"],
            "rows_all_years": primary["rows"],
            "rows_selected_year": primary["selected_rows"],
            "years": primary["years"],
            "top_modalities": primary["top_modalities"],
            "top_statuses": primary["top_statuses"],
            "top_agencies": primary["top_agencies"],
            "estimated_value": _semantic_value(primary, "ESTIMADO"),
            "homologated_value": _semantic_value(primary, "HOMOLOGADO"),
        }

    return {
        "dataset": "licitacoes",
        "archive": {"members": len(members), "tabular_members": len(tables), "uncompressed_bytes": total_uncompressed},
        "selected_year": target_year,
        "tables": tables,
        "table_classes": dict(classification_counts),
        "primary_licitacoes": primary_summary,
        "total_rows_across_related_tables": sum(table["rows"] for table in tables),
        "selected_rows_across_filterable_tables": sum(int(table["selected_rows"] or 0) for table in filterable),
        "year_filterable_tables": len(filterable),
        "year_unfilterable_tables": len(unfilterable),
        "unfilterable_related_rows": sum(table["rows"] for table in unfilterable),
        "interpretation": "As linhas pertencem a tabelas relacionadas e não são somadas como número de licitações. O número anual de processos é extraído apenas da tabela principal quando ela possui campo de ano/data. Tabelas sem campo temporal ficam fora do total anual.",
        "privacy_note": "Nenhuma linha bruta, CPF, CNPJ ou nome de participante é republicado por este resumo. O esquema apenas registra a existência de colunas sensíveis.",
    }
