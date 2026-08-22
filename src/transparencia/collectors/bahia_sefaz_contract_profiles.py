from __future__ import annotations

import csv
import io
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from transparencia.collectors.bahia_open_data import BahiaOpenDataError
from transparencia.collectors.bahia_sefaz_contracts import (
    _contract_value_field,
    _document_kind,
    _first,
    _number,
    _spec,
    _year,
    normalize_identifier,
)


def _text(value: Any, *, limit: int | None = None) -> str:
    result = " ".join(str(value or "").split()).strip()
    if limit is not None:
        result = result[:limit]
    return result


def _single(values: set[str]) -> str | None:
    return next(iter(values)) if len(values) == 1 else None


def extract_contract_profiles(
    path: Path,
    *,
    target_year: int,
    instrument_ids: Iterable[str],
    member: str | None = None,
) -> dict[str, Any]:
    """Extrai somente perfis dos instrumentos solicitados, sem publicar CPF.

    Nenhum campo descritivo é resolvido por similaridade. Campos que apresentam mais de um
    valor oficial permanecem ambíguos em vez de escolher uma variante arbitrariamente.
    """
    requested = {
        normalized
        for normalized in (normalize_identifier(value) for value in instrument_ids)
        if normalized
    }
    if not requested:
        return {
            "selected_year": target_year,
            "requested_instruments": 0,
            "matched_instruments": 0,
            "profiles": {},
        }
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de contratos não é um ZIP válido")

    with zipfile.ZipFile(path, "r") as zf:
        members = [info.filename for info in zf.infolist() if not info.is_dir()]
        selected_member = member if member in members else None
        if selected_member is None:
            candidates: list[tuple[int, str]] = []
            for candidate in members:
                try:
                    spec = _spec(zf, candidate)
                except (BahiaOpenDataError, UnicodeError, csv.Error):
                    continue
                headers = list(spec["headers"])
                contract_field = _first(
                    headers,
                    (("NUM", "INSTRUMENTO", "FORMAT"), ("NUM", "INSTRUMENTO"), ("NUMERO", "CONTRATO"), ("NUM", "CONTRATO")),
                    reject=("COD",),
                )
                year_field = _first(headers, (("ANO", "EXERC"), ("ANO", "CONTRAT"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
                score = (20 if contract_field else 0) + (10 if year_field else 0)
                if "CONTRAT" in candidate.upper() or "INSTRUMENT" in candidate.upper():
                    score += 15
                candidates.append((score, candidate))
            selected_member = max(candidates, default=(0, None), key=lambda item: item[0])[1]
        if not selected_member:
            raise BahiaOpenDataError("Tabela contratual não encontrada no ZIP")

        spec = _spec(zf, selected_member)
        headers = list(spec["headers"])
        year_field = _first(headers, (("ANO", "EXERC"), ("ANO", "CONTRAT"), ("EXERCICIO",), ("ANO",)), reject=("COD",))
        signature_field = _first(headers, (("DATA", "ASSIN"), ("DATA", "CELEBR"), ("DATA", "INICIO"), ("DATA",)), reject=("ATUALIZ", "VENC"))
        contract_field = _first(
            headers,
            (("NUM", "INSTRUMENTO", "FORMAT"), ("NUM", "INSTRUMENTO"), ("NUMERO", "CONTRATO"), ("NUM", "CONTRATO")),
            reject=("COD",),
        )
        process_field = _first(headers, (("NUM", "PROCESSO", "LICIT"), ("PROCESSO", "LICIT"), ("NUM", "PROCESSO"), ("PROCESSO",)), reject=("COD",))
        agency_field = _first(headers, (("NOM", "ORGAO"), ("ORGAO",), ("SECRETARIA",), ("UNIDADE", "GESTORA")), reject=("COD", "SIGLA"))
        supplier_field = _first(headers, (("NOME", "FORNECEDOR"), ("FORNECEDOR",), ("CONTRATADA",), ("CREDOR",)), reject=("COD", "CPF", "CNPJ"))
        supplier_doc_field = _first(headers, (("CPF", "CNPJ"), ("CNPJ",), ("DOCUMENTO", "FORNECEDOR"), ("DOCUMENTO", "CONTRATADA")), reject=("COD",))
        status_field = _first(headers, (("SITUACAO",), ("STATUS",)), reject=("COD",))
        object_field = _first(headers, (("OBJETO",),), reject=("COD",))
        modality_field = _first(headers, (("MODALIDADE", "LICIT"), ("MODALIDADE",)), reject=("COD",))
        value_field = _contract_value_field(headers)
        if not contract_field:
            raise BahiaOpenDataError("Tabela contratual sem identificador de instrumento")

        profiles: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "rows": 0,
                "values": set(),
                "process_ids": set(),
                "agencies": set(),
                "statuses": set(),
                "objects": set(),
                "modalities": set(),
                "cnpjs": set(),
                "supplier_names": defaultdict(Counter),
                "private_person_rows": 0,
            }
        )
        encoding = "utf-8" if spec["encoding"] == "utf-8-replace" else spec["encoding"]
        with zf.open(selected_member, "r") as raw:
            text = io.TextIOWrapper(raw, encoding=encoding, errors="replace", newline="")
            reader = csv.DictReader(text, delimiter=spec["delimiter"])
            for row in reader:
                row_year = _year(row.get(year_field)) if year_field else _year(row.get(signature_field)) if signature_field else None
                if row_year != target_year:
                    continue
                instrument_id = normalize_identifier(row.get(contract_field))
                if not instrument_id or instrument_id not in requested:
                    continue

                current = profiles[instrument_id]
                current["rows"] += 1
                value = _number(row.get(value_field)) if value_field else None
                if value is not None:
                    current["values"].add(round(value, 2))
                process_id = normalize_identifier(row.get(process_field)) if process_field else None
                if process_id:
                    current["process_ids"].add(process_id)
                for field, key, limit in (
                    (agency_field, "agencies", 240),
                    (status_field, "statuses", 160),
                    (object_field, "objects", 1000),
                    (modality_field, "modalities", 160),
                ):
                    if field:
                        value_text = _text(row.get(field), limit=limit)
                        if value_text:
                            current[key].add(value_text)

                doc_kind, cnpj = _document_kind(row.get(supplier_doc_field)) if supplier_doc_field else (None, None)
                supplier_name = _text(row.get(supplier_field), limit=240) if supplier_field else ""
                if cnpj:
                    current["cnpjs"].add(cnpj)
                    if supplier_name:
                        current["supplier_names"][cnpj][supplier_name] += 1
                elif doc_kind == "cpf":
                    current["private_person_rows"] += 1

    public_profiles: dict[str, dict[str, Any]] = {}
    for instrument_id, current in sorted(profiles.items()):
        values = current["values"]
        if len(values) == 1:
            contract_value = next(iter(values))
            value_status = "single_official_value"
        elif len(values) > 1:
            contract_value = None
            value_status = "conflicting_official_values"
        else:
            contract_value = None
            value_status = "value_not_available"

        supplier = None
        if len(current["cnpjs"]) == 1:
            cnpj = next(iter(current["cnpjs"]))
            names = current["supplier_names"].get(cnpj) or Counter()
            supplier = {
                "cnpj": cnpj,
                "name": names.most_common(1)[0][0] if names else "Não informado",
            }

        public_profiles[instrument_id] = {
            "instrument_id": instrument_id,
            "contract_rows": current["rows"],
            "contract_value": contract_value,
            "contract_value_status": value_status,
            "contract_value_field": value_field,
            "agency": _single(current["agencies"]),
            "agency_variants": len(current["agencies"]),
            "supplier": supplier,
            "supplier_cnpj_variants": len(current["cnpjs"]),
            "object": _single(current["objects"]),
            "object_variants": len(current["objects"]),
            "statuses": sorted(current["statuses"]),
            "modalities": sorted(current["modalities"]),
            "contract_process_ids": sorted(current["process_ids"]),
            "has_private_person_supplier": current["private_person_rows"] > 0,
        }

    return {
        "selected_year": target_year,
        "source_table": selected_member,
        "requested_instruments": len(requested),
        "matched_instruments": len(public_profiles),
        "profiles": public_profiles,
        "identity_rule": "Perfis são recuperados somente pelo mesmo identificador oficial normalizado do instrumento. Nenhuma aproximação textual é usada.",
        "ambiguity_rule": "Órgão e objeto só são publicados como valor único quando todas as linhas do instrumento concordam; divergências permanecem explícitas. Fornecedor só é publicado quando existe um único CNPJ empresarial.",
        "privacy_rule": "CPF e nome associado a fornecedor pessoa física não são republicados.",
    }
