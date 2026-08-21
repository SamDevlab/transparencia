from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from transparencia.collectors.bahia_open_data import BahiaOpenDataError


def _norm(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^A-Za-z0-9]+", " ", text.upper())
    return re.sub(r"\s+", " ", text).strip()


def normalize_identifier(value: Any) -> str | None:
    """Normaliza somente pontuação/espaço/capitalização de identificadores oficiais."""
    text = str(value or "").strip().upper()
    if not text:
        return None
    normalized = re.sub(r"[^A-Z0-9]+", "", text)
    return normalized or None


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


def _spec(zf: zipfile.ZipFile, member: str) -> dict[str, Any]:
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
    return {"delimiter": delimiter, "encoding": encoding, "headers": headers}


def _first(headers: Iterable[str], patterns: Iterable[tuple[str, ...]], *, reject: tuple[str, ...] = ()) -> str | None:
    rows = [(header, _norm(header)) for header in headers]
    for required in patterns:
        for original, normalized in rows:
            if all(token in normalized for token in required) and not any(token in normalized for token in reject):
                return original
    return None


def _contract_value_field(headers: Iterable[str]) -> str | None:
    candidates: list[tuple[int, str]] = []
    for header in headers:
        normalized = _norm(header)
        if not any(token in normalized for token in ("VALOR", "VAL ", "VLR ")):
            continue
        if any(token in normalized for token in ("COD", "PERCENT", "PERC", "DATA", "NUM")):
            continue
        score = 0
        if "CONTRAT" in normalized or "INSTRUMENTO" in normalized:
            score += 10
        if "GLOBAL" in normalized or "TOTAL" in normalized or "ATUAL" in normalized:
            score += 4
        if "ORIGINAL" in normalized or "INICIAL" in normalized:
            score += 2
        if "EMPENH" in normalized or "LIQUID" in normalized or "PAGO" in normalized or "PAGAMENTO" in normalized:
            score -= 12
        if "ADIT" in normalized:
            score -= 5
        candidates.append((score, header))
    return max(candidates, default=(0, None), key=lambda item: item[0])[1]


def _document_kind(value: Any) -> tuple[str | None, str | None]:
    digits = re.sub(r"\D+", "", str(value or ""))
    if len(digits) == 14:
        return "cnpj", digits
    if len(digits) == 11:
        return "cpf", None
    return None, None


def _classify_table(member: str, headers: Iterable[str]) -> str:
    name = _norm(member)
    joined = " ".join(_norm(header) for header in headers)
    if "ADIT" in name or "APOSTIL" in name:
        return "aditivos"
    if "CONTRATO" in name or "INSTRUMENTO" in name:
        if any(token in joined for token in ("FORNECEDOR", "CONTRATADA", "CNPJ", "CPF")):
            return "contratos"
    if "FORNEC" in name or "CONTRATAD" in name:
        return "fornecedores"
    if any(token in joined for token in ("NUMERO DO CONTRATO", "NUM CONTRATO", "NUM INSTRUMENTO")):
        return "contratos"
    return "tabela_relacionada"


def _summarize_member(zf: zipfile.ZipFile, member: str, *, target_year: int) -> dict[str, Any]:
    spec = _spec(zf, member)
    headers = list(spec["headers"])
    year_field = _first(headers, (("ANO", "EXERC"), ("ANO", "CONTRAT"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
    signature_field = _first(headers, (("DATA", "ASSIN"), ("DATA", "CELEBR"), ("DATA", "INICIO"), ("DATA",)), reject=("ATUALIZ", "VENC"))
    contract_field = _first(headers, (("NUM", "INSTRUMENTO", "FORMAT"), ("NUM", "INSTRUMENTO"), ("NUMERO", "CONTRATO"), ("NUM", "CONTRATO")), reject=("COD",))
    process_field = _first(headers, (("NUM", "PROCESSO", "LICIT"), ("PROCESSO", "LICIT"), ("NUM", "PROCESSO"), ("PROCESSO",)), reject=("COD",))
    agency_field = _first(headers, (("NOM", "ORGAO"), ("ORGAO",), ("SECRETARIA",), ("UNIDADE", "GESTORA")), reject=("COD", "SIGLA"))
    supplier_field = _first(headers, (("NOME", "FORNECEDOR"), ("FORNECEDOR",), ("CONTRATADA",), ("CREDOR",)), reject=("COD", "CPF", "CNPJ"))
    supplier_doc_field = _first(headers, (("CPF", "CNPJ"), ("CNPJ",), ("DOCUMENTO", "FORNECEDOR"), ("DOCUMENTO", "CONTRATADA")), reject=("COD",))
    status_field = _first(headers, (("SITUACAO",), ("STATUS",)), reject=("COD",))
    object_field = _first(headers, (("OBJETO",),), reject=("COD",))
    modality_field = _first(headers, (("MODALIDADE", "LICIT"), ("MODALIDADE",)), reject=("COD",))
    value_field = _contract_value_field(headers)

    rows = 0
    selected_rows = 0
    years: Counter[int] = Counter()
    statuses: Counter[str] = Counter()
    agencies: dict[str, dict[str, float]] = defaultdict(lambda: {"rows": 0.0, "value": 0.0})
    suppliers: dict[str, dict[str, Any]] = {}
    instruments: dict[str, dict[str, Any]] = {}
    processes: Counter[str] = Counter()
    total_value = 0.0
    numeric_value_rows = 0

    encoding = "utf-8" if spec["encoding"] == "utf-8-replace" else spec["encoding"]
    with zf.open(member, "r") as raw:
        text = io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="")
        reader = csv.DictReader(text, delimiter=spec["delimiter"])
        for row in reader:
            rows += 1
            row_year = _year(row.get(year_field)) if year_field else _year(row.get(signature_field)) if signature_field else None
            if row_year is not None:
                years[row_year] += 1
            if row_year != target_year:
                continue
            selected_rows += 1
            value = _number(row.get(value_field)) if value_field else None
            if value is not None:
                total_value += value
                numeric_value_rows += 1
            if status_field:
                status = str(row.get(status_field) or "").strip()
                if status:
                    statuses[status[:160]] += 1
            agency = str(row.get(agency_field) or "Não informado").strip() if agency_field else "Não informado"
            agency = agency or "Não informado"
            agencies[agency]["rows"] += 1
            agencies[agency]["value"] += value or 0.0

            contract_id = normalize_identifier(row.get(contract_field)) if contract_field else None
            process_id = normalize_identifier(row.get(process_field)) if process_field else None
            if process_id:
                processes[process_id] += 1
            if contract_id:
                current = instruments.setdefault(contract_id, {
                    "rows": 0,
                    "value": 0.0,
                    "process_ids": set(),
                    "agencies": set(),
                })
                current["rows"] += 1
                current["value"] += value or 0.0
                if process_id:
                    current["process_ids"].add(process_id)
                if agency != "Não informado":
                    current["agencies"].add(agency)

            doc_kind, cnpj = _document_kind(row.get(supplier_doc_field)) if supplier_doc_field else (None, None)
            if cnpj:
                supplier_name = str(row.get(supplier_field) or "Não informado").strip() if supplier_field else "Não informado"
                key = cnpj
                current = suppliers.setdefault(key, {"cnpj": cnpj, "name": supplier_name or "Não informado", "rows": 0, "value": 0.0, "contracts": set()})
                current["rows"] += 1
                current["value"] += value or 0.0
                if contract_id:
                    current["contracts"].add(contract_id)
            elif doc_kind == "cpf":
                # Pessoa física pode existir na fonte, mas não é republicada nesta camada.
                pass

    classification = _classify_table(member, headers)
    score = 0
    if classification == "contratos": score += 30
    if contract_field: score += 20
    if year_field or signature_field: score += 12
    if supplier_doc_field: score += 8
    if value_field: score += 8
    if agency_field: score += 4
    if selected_rows == 0: score -= 20

    top_agencies = [
        {"name": name, "rows": int(values["rows"]), "value": round(values["value"], 2)}
        for name, values in sorted(agencies.items(), key=lambda item: (item[1]["value"], item[1]["rows"]), reverse=True)[:60]
    ]
    top_suppliers = [
        {"cnpj": values["cnpj"], "name": values["name"], "rows": values["rows"], "contracts": len(values["contracts"]), "value": round(values["value"], 2)}
        for _, values in sorted(suppliers.items(), key=lambda item: (item[1]["value"], item[1]["rows"]), reverse=True)[:100]
    ]
    instrument_index = [
        {
            "instrument_id": instrument_id,
            "rows": values["rows"],
            "value": round(values["value"], 2),
            "process_ids": sorted(values["process_ids"]),
            "agencies": sorted(values["agencies"]),
        }
        for instrument_id, values in sorted(instruments.items())
    ]

    privacy_fields = [header for header in headers if any(token in _norm(header) for token in ("CPF", "CNPJ", "CREDOR", "FORNECEDOR", "CONTRATADA"))]
    return {
        "member": member,
        "classification": classification,
        "rows": rows,
        "selected_rows": selected_rows,
        "score": score,
        "schema": {
            "delimiter": spec["delimiter"],
            "encoding": spec["encoding"],
            "headers": headers,
            "detected_fields": {
                "year": year_field,
                "signature_date": signature_field,
                "contract": contract_field,
                "process": process_field,
                "agency": agency_field,
                "supplier": supplier_field,
                "supplier_document": supplier_doc_field,
                "status": status_field,
                "object": object_field,
                "modality": modality_field,
                "contract_value": value_field,
            },
            "privacy_sensitive_columns_present": privacy_fields,
        },
        "years": {str(year): count for year, count in sorted(years.items())},
        "contract_value": {"field": value_field, "sum": round(total_value, 2), "numeric_rows": numeric_value_rows} if value_field else None,
        "top_statuses": [{"name": name, "rows": count} for name, count in statuses.most_common(40)],
        "top_agencies": top_agencies,
        "top_suppliers_cnpj_only": top_suppliers,
        "instrument_index": instrument_index,
        "process_ids": [{"process_id": key, "rows": count} for key, count in processes.most_common()],
    }


def summarize_sefaz_contracts_zip(path: Path, *, target_year: int) -> dict[str, Any]:
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de contratos não é um ZIP válido")
    errors: list[dict[str, str]] = []
    tables: list[dict[str, Any]] = []
    with zipfile.ZipFile(path, "r") as zf:
        infos = [info for info in zf.infolist() if not info.is_dir()]
        if any(".." in Path(info.filename).parts for info in infos):
            raise BahiaOpenDataError("ZIP de contratos contém caminho inseguro")
        uncompressed = sum(info.file_size for info in infos)
        if uncompressed > 12_000_000_000:
            raise BahiaOpenDataError("ZIP de contratos excede limite descompactado de segurança")
        members = [info.filename for info in infos if info.filename.lower().endswith((".csv", ".txt")) and info.file_size > 0]
        if not members:
            raise BahiaOpenDataError("ZIP de contratos não contém tabelas CSV/TXT")
        for member in members:
            try:
                tables.append(_summarize_member(zf, member, target_year=target_year))
            except BahiaOpenDataError as exc:
                errors.append({"member": member, "error_type": type(exc).__name__, "error": str(exc)[:1000]})

    candidates = [
        table for table in tables
        if table["classification"] == "contratos"
        and table["selected_rows"] > 0
        and table["schema"]["detected_fields"]["contract"]
    ]
    primary = max(candidates, key=lambda table: (table["score"], table["selected_rows"]), default=None)
    if primary is None:
        raise BahiaOpenDataError("Nenhuma tabela principal de contratos com identificador oficial e recorte 2026 foi identificada")

    return {
        "dataset": "contratos",
        "selected_year": target_year,
        "archive": {
            "members": len(infos),
            "candidate_tabular_members": len(members),
            "processed_tabular_members": len(tables),
            "invalid_tabular_members": len(errors),
            "uncompressed_bytes": uncompressed,
        },
        "primary_table": primary,
        "tables": [
            {
                "member": table["member"],
                "classification": table["classification"],
                "rows": table["rows"],
                "selected_rows": table["selected_rows"],
                "score": table["score"],
                "schema": table["schema"],
                "years": table["years"],
                "contract_value": table["contract_value"],
            }
            for table in tables
        ],
        "table_errors": errors,
        "interpretation": "A contagem e os valores anuais vêm somente da tabela principal identificada por esquema e identificador oficial de contrato. Aditivos e tabelas relacionadas não são somados como novos contratos.",
        "identity_rule": "Vínculos usam apenas identificadores oficiais normalizados por remoção de pontuação/espaço e capitalização. Não há correspondência aproximada por nome, fornecedor ou objeto.",
        "privacy_note": "CNPJ empresarial pode aparecer em agregações. CPF e documentos com 11 dígitos não são republicados nesta camada.",
    }
