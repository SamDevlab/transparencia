from __future__ import annotations

import csv
import io
import re
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from transparencia.collectors.bahia_open_data import BahiaOpenDataError
from transparencia.collectors.bahia_sefaz_procurement_links import (
    extract_procurement_instrument_links,
    normalize_identifier,
)


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


def _decode(sample: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return sample.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return sample.decode("utf-8", errors="replace"), "utf-8-replace"


def _delimiter(text: str) -> str:
    sample = "\n".join(line for line in text.splitlines()[:8] if line.strip())
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,#|\t,").delimiter
    except csv.Error:
        return ";"


def _field(headers: list[str], *candidates: str) -> str | None:
    normalized = {header: _norm(header) for header in headers}
    for candidate in candidates:
        target = _norm(candidate)
        for original, value in normalized.items():
            if value == target:
                return original
    return None


def extract_payment_instrument_index(path: Path, *, target_year: int) -> dict[str, Any]:
    """Agrega pagamentos por instrumento oficial sem republicar credores ou documentos."""
    if not zipfile.is_zipfile(path):
        raise BahiaOpenDataError("Recurso de pagamentos não é um ZIP válido")

    with zipfile.ZipFile(path, "r") as zf:
        members = [info.filename for info in zf.infolist() if not info.is_dir()]
        member = next(
            (
                name for name in members
                if _norm(Path(name).name).startswith("VW PAINEL PAGAMENTO NOTA ORDEM BANCARIA")
            ),
            None,
        )
        if not member:
            raise BahiaOpenDataError("Tabela principal de nota/ordem bancária não encontrada")

        with zf.open(member, "r") as raw:
            sample = raw.read(128 * 1024)
        sample_text, encoding = _decode(sample)
        delimiter = _delimiter(sample_text)
        header_reader = csv.reader(io.StringIO(sample_text), delimiter=delimiter)
        try:
            headers = next(header_reader)
        except StopIteration as exc:
            raise BahiaOpenDataError("Tabela principal de pagamentos vazia") from exc

        date_field = _field(headers, "Data do Pagamento")
        instrument_field = _field(headers, "num_instrumento_formatado", "num_instrumento")
        process_field = _field(headers, "Nº do Processo de Licitação/Inexigibilidade/Dispensa")
        payment_field = _field(headers, "Nº do Pagamento Formatado", "Nº do Pagamento")
        commitment_field = _field(headers, "Nº do Empenho", "NUM_EMPENHO_ORCAMENTO")
        liquidation_field = _field(headers, "Nº da Liquidação")
        value_field = _field(headers, "Valor do Pagamento")
        if not date_field or not instrument_field or not value_field:
            raise BahiaOpenDataError("Tabela de pagamentos sem data, instrumento ou Valor do Pagamento")

        actual_encoding = "utf-8" if encoding == "utf-8-replace" else encoding
        total_rows = 0
        selected_rows = 0
        selected_value = 0.0
        rows_with_instrument = 0
        value_with_instrument = 0.0
        instruments: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "rows": 0,
                "value": 0.0,
                "payments": set(),
                "commitments": set(),
                "liquidations": set(),
                "processes": set(),
            }
        )

        with zf.open(member, "r") as raw:
            text = io.TextIOWrapper(raw, encoding=actual_encoding, errors="replace", newline="")
            reader = csv.DictReader(text, delimiter=delimiter)
            for row in reader:
                total_rows += 1
                if _year(row.get(date_field)) != target_year:
                    continue
                selected_rows += 1
                amount = _number(row.get(value_field))
                if amount is not None:
                    selected_value += amount
                instrument_id = normalize_identifier(row.get(instrument_field))
                if not instrument_id:
                    continue
                rows_with_instrument += 1
                current = instruments[instrument_id]
                current["rows"] += 1
                if amount is not None:
                    current["value"] += amount
                    value_with_instrument += amount
                for field, key in (
                    (payment_field, "payments"),
                    (commitment_field, "commitments"),
                    (liquidation_field, "liquidations"),
                    (process_field, "processes"),
                ):
                    if not field:
                        continue
                    normalized = normalize_identifier(row.get(field))
                    if normalized:
                        current[key].add(normalized)

    public_index = [
        {
            "instrument_id": instrument_id,
            "payment_rows": values["rows"],
            "payment_value": round(values["value"], 2),
            "payment_ids": len(values["payments"]),
            "commitment_ids": len(values["commitments"]),
            "liquidation_ids": len(values["liquidations"]),
            "process_ids": sorted(values["processes"]),
        }
        for instrument_id, values in sorted(instruments.items())
    ]
    return {
        "dataset": "pagamentos_por_instrumento",
        "selected_year": target_year,
        "source_table": member,
        "fields": {
            "date": date_field,
            "instrument": instrument_field,
            "process": process_field,
            "payment": payment_field,
            "commitment": commitment_field,
            "liquidation": liquidation_field,
            "value": value_field,
        },
        "rows": total_rows,
        "selected_rows": selected_rows,
        "selected_payment_value": round(selected_value, 2),
        "rows_with_instrument": rows_with_instrument,
        "payment_value_with_instrument": round(value_with_instrument, 2),
        "unique_instruments": len(instruments),
        "instrument_index": public_index,
        "privacy_rule": "O índice público contém somente identificadores administrativos, contagens e valores agregados por instrumento. Nomes de recebedores, CPF e CNPJ da base de pagamentos não são republicados.",
    }


def build_exact_money_flow(
    procurement_zip: Path,
    payments_zip: Path,
    contract_instrument_keys: list[str],
    *,
    target_year: int,
    top_limit: int = 200,
) -> dict[str, Any]:
    procurement = extract_procurement_instrument_links(procurement_zip, target_year=target_year)
    payments = extract_payment_instrument_index(payments_zip, target_year=target_year)

    contract_set = {key for key in (normalize_identifier(value) for value in contract_instrument_keys) if key}
    procurement_by_instrument: dict[str, set[str]] = defaultdict(set)
    for link in procurement.get("exact_links") or []:
        instrument = normalize_identifier(link.get("instrument_id"))
        process = normalize_identifier(link.get("process_id"))
        if instrument and process:
            procurement_by_instrument[instrument].add(process)

    payment_by_instrument = {
        row["instrument_id"]: row
        for row in payments.get("instrument_index") or []
        if row.get("instrument_id")
    }

    procurement_contract_instruments = set(procurement_by_instrument) & contract_set
    payment_contract_instruments = set(payment_by_instrument) & contract_set
    end_to_end_instruments = procurement_contract_instruments & payment_contract_instruments

    linked_payment_value = round(
        sum(payment_by_instrument[key]["payment_value"] for key in payment_contract_instruments),
        2,
    )
    end_to_end_payment_value = round(
        sum(payment_by_instrument[key]["payment_value"] for key in end_to_end_instruments),
        2,
    )

    top = []
    for instrument_id in sorted(
        end_to_end_instruments,
        key=lambda key: payment_by_instrument[key]["payment_value"],
        reverse=True,
    )[:top_limit]:
        payment = payment_by_instrument[instrument_id]
        top.append({
            "instrument_id": instrument_id,
            "procurement_process_ids": sorted(procurement_by_instrument[instrument_id]),
            "payment_value": payment["payment_value"],
            "payment_rows": payment["payment_rows"],
            "payment_ids": payment["payment_ids"],
            "commitment_ids": payment["commitment_ids"],
            "liquidation_ids": payment["liquidation_ids"],
        })

    return {
        "dataset": "bahia_fio_do_dinheiro",
        "selected_year": target_year,
        "coverage": {
            "procurement": "Processos de aquisição do ano ligados a instrumentos pela tabela oficial VW_PROC_AQUISICAO_ITEM_INSTRUMENTO.",
            "contracts": "Instrumentos presentes no recorte contratual validado da SEFAZ/FIPLAN.",
            "payments": "Pagamentos com Data do Pagamento no ano e num_instrumento_formatado preenchido.",
        },
        "summary": {
            "procurement_processes_selected": procurement.get("unique_processes_selected", 0),
            "procurement_instrument_exact_links": procurement.get("exact_link_count", 0),
            "procurement_unique_instruments": procurement.get("unique_instruments", 0),
            "contract_unique_instruments": len(contract_set),
            "payment_rows_selected": payments.get("selected_rows", 0),
            "payment_unique_instruments": payments.get("unique_instruments", 0),
            "payment_rows_with_instrument": payments.get("rows_with_instrument", 0),
            "payment_value_with_instrument": payments.get("payment_value_with_instrument", 0.0),
            "instruments_procurement_to_contract": len(procurement_contract_instruments),
            "instruments_contract_to_payment": len(payment_contract_instruments),
            "payment_value_linked_to_contracts": linked_payment_value,
            "instruments_end_to_end": len(end_to_end_instruments),
            "payment_value_end_to_end": end_to_end_payment_value,
        },
        "top_end_to_end": top,
        "identity_rule": "Todos os vínculos exigem igualdade do identificador oficial após remover apenas pontuação/espaços e padronizar maiúsculas. Nome, objeto, fornecedor e similaridade textual nunca criam vínculo.",
        "interpretation": "O fluxo mede correspondências documentais entre bases. Não significa que o valor contratual seja igual ao valor pago no ano, nem que todo instrumento relacionado ao recorte tenha sido celebrado no próprio ano.",
        "privacy_rule": payments.get("privacy_rule"),
    }
