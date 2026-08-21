from __future__ import annotations

import csv
import hashlib
import json
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit, urlunsplit

import httpx

CKAN_BASE = "https://dados.ba.gov.br/api/3/action"
RETRYABLE = {429, 500, 502, 503, 504}


class BahiaOpenDataError(RuntimeError):
    pass


@dataclass(frozen=True)
class DownloadEvidence:
    url: str
    status_code: int
    sha256: str
    bytes: int
    content_type: str


def _request(client: httpx.Client, method: str, url: str, *, max_retries: int = 4, **kwargs: Any) -> httpx.Response:
    response: httpx.Response | None = None
    for attempt in range(max_retries + 1):
        response = client.request(method, url, **kwargs)
        if response.status_code not in RETRYABLE:
            response.raise_for_status()
            return response
        if attempt >= max_retries:
            break
        retry_after = response.headers.get("retry-after")
        try:
            delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 20)
        except ValueError:
            delay = min(2 ** (attempt + 1), 20)
        time.sleep(max(0.5, min(delay, 30)))
    assert response is not None
    raise BahiaOpenDataError(f"Fonte estadual respondeu HTTP {response.status_code} após retentativas: {url}")


def ckan_package(client: httpx.Client, dataset: str) -> dict[str, Any]:
    response = _request(client, "GET", f"{CKAN_BASE}/package_show", params={"id": dataset})
    payload = response.json()
    if not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(payload.get("result"), dict):
        raise BahiaOpenDataError(f"CKAN não devolveu package_show válido para {dataset}")
    return payload


def _certificate_chain_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "CERTIFICATE_VERIFY_FAILED" in text or "CERTIFICATE VERIFY FAILED" in text


def ckan_package_resilient(
    dataset: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 60.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Consulta o CKAN oficial e só desativa a validação TLS se a cadeia oficial falhar.

    O fallback fica explícito no metadado retornado; ele nunca é silencioso e só vale
    para o host fixo dados.ba.gov.br definido em CKAN_BASE.
    """
    try:
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True, verify=True) as client:
            return ckan_package(client, dataset), {
                "tls_verified": True,
                "transport_note": "Validação TLS concluída normalmente.",
            }
    except httpx.ConnectError as exc:
        if not _certificate_chain_error(exc):
            raise
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True, verify=False) as client:
            payload = ckan_package(client, dataset)
        return payload, {
            "tls_verified": False,
            "transport_note": "O runner não conseguiu validar a cadeia de certificados do host oficial; a consulta foi repetida no mesmo domínio oficial sem verificação TLS e essa condição foi registrada.",
            "fallback_reason": "certificate_chain_error",
        }


def normalize_ckan_package(payload: dict[str, Any]) -> dict[str, Any]:
    result = payload["result"]
    resources = []
    for row in result.get("resources") or []:
        if not isinstance(row, dict):
            continue
        resources.append({
            "id": row.get("id"),
            "name": row.get("name") or row.get("description") or row.get("url"),
            "format": row.get("format"),
            "mimetype": row.get("mimetype"),
            "url": row.get("url"),
            "size": row.get("size"),
            "hash": row.get("hash"),
            "last_modified": row.get("last_modified"),
            "metadata_modified": row.get("metadata_modified"),
            "state": row.get("state"),
        })
    return {
        "id": result.get("id"),
        "name": result.get("name"),
        "title": result.get("title"),
        "notes": result.get("notes"),
        "organization": (result.get("organization") or {}).get("title"),
        "metadata_created": result.get("metadata_created"),
        "metadata_modified": result.get("metadata_modified"),
        "resources": resources,
    }


def persist_json_snapshot(out_dir: Path, name: str, payload: Any) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    target = out_dir / f"{name}.json"
    target.write_bytes(encoded + b"\n")
    return {"file": target.name, "sha256": digest, "bytes": target.stat().st_size}


def _parse_brl(value: str | None) -> float:
    if value is None:
        return 0.0
    text = str(value).strip().replace("R$", "").replace(" ", "")
    if not text:
        return 0.0
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return 0.0


def _norm_header(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().upper())


def official_tce_url_candidates(url: str) -> list[str]:
    """Mantém somente hosts oficiais do TCE e tenta os dois frontends observados."""
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"www.tce.ba.gov.br", "its.tce.ba.gov.br"}:
        return [url]
    hosts = [parts.hostname, "its.tce.ba.gov.br" if parts.hostname == "www.tce.ba.gov.br" else "www.tce.ba.gov.br"]
    result: list[str] = []
    for host in hosts:
        candidate = urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))
        if candidate not in result:
            result.append(candidate)
    return result


def stream_to_temp(client: httpx.Client, url: str, *, max_bytes: int = 800_000_000) -> tuple[Path, DownloadEvidence]:
    digest = hashlib.sha256()
    total = 0
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        suffix = ".csv" if "csv" in content_type.lower() or url.lower().endswith(".csv") else ".bin"
        handle = tempfile.NamedTemporaryFile(prefix="bahia-open-data-", suffix=suffix, delete=False)
        path = Path(handle.name)
        try:
            for chunk in response.iter_bytes():
                if not chunk:
                    continue
                total += len(chunk)
                if total > max_bytes:
                    raise BahiaOpenDataError(f"Arquivo excede limite de segurança de {max_bytes} bytes: {url}")
                digest.update(chunk)
                handle.write(chunk)
        finally:
            handle.close()
        evidence = DownloadEvidence(
            url=str(response.url),
            status_code=response.status_code,
            sha256=digest.hexdigest(),
            bytes=total,
            content_type=content_type,
        )
    return path, evidence


def stream_first_available(
    urls: Sequence[str],
    *,
    headers: dict[str, str] | None = None,
    max_bytes: int = 800_000_000,
) -> tuple[Path, DownloadEvidence, list[dict[str, str]]]:
    attempts: list[dict[str, str]] = []
    timeout = httpx.Timeout(connect=18.0, read=240.0, write=30.0, pool=30.0)
    for url in urls:
        try:
            with httpx.Client(
                headers=headers,
                timeout=timeout,
                follow_redirects=True,
                verify=True,
            ) as client:
                path, evidence = stream_to_temp(client, url, max_bytes=max_bytes)
            attempts.append({"url": url, "status": "success"})
            return path, evidence, attempts
        except Exception as exc:  # noqa: BLE001 - cada host oficial é tentado e registrado
            attempts.append({"url": url, "status": "failed", "error_type": type(exc).__name__, "error": str(exc)[:500]})
    raise BahiaOpenDataError("Nenhum endpoint oficial do TCE respondeu: " + json.dumps(attempts, ensure_ascii=False))


def summarize_tce_expenses(path: Path) -> dict[str, Any]:
    totals = {"rows": 0, "committed": 0.0, "gross_paid": 0.0, "net_paid": 0.0}
    by_agency: dict[str, dict[str, Any]] = {}
    by_creditor: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        if not reader.fieldnames or len(reader.fieldnames) < 3:
            raise BahiaOpenDataError("Resposta do TCE não possui cabeçalho tabular de despesas")
        field_map = {_norm_header(name): name for name in reader.fieldnames if name}
        if not field_map.get("VALOR DO EMPENHO"):
            raise BahiaOpenDataError("CSV de despesas do TCE não contém o campo VALOR DO EMPENHO esperado")

        def pick(row: dict[str, str], *names: str) -> str:
            for name in names:
                original = field_map.get(_norm_header(name))
                if original:
                    return row.get(original) or ""
            return ""

        for row in reader:
            totals["rows"] += 1
            committed = _parse_brl(pick(row, "VALOR DO EMPENHO"))
            gross = _parse_brl(pick(row, "PAGAMENTO COM RETENÇÕES"))
            net = _parse_brl(pick(row, "PAGAMENTO LÍQUIDO AO CREDOR", "PAGAMENTO LIQUIDO AO CREDOR"))
            totals["committed"] += committed
            totals["gross_paid"] += gross
            totals["net_paid"] += net
            agency = pick(row, "SECRETARIA/ÓRGÃO", "SECRETARIA/ORGAO") or "Não informado"
            creditor = pick(row, "NOME DO CREDOR") or "Não informado"
            a = by_agency.setdefault(agency, {"agency": agency, "rows": 0, "committed": 0.0, "gross_paid": 0.0, "net_paid": 0.0})
            c = by_creditor.setdefault(creditor, {"creditor": creditor, "rows": 0, "committed": 0.0, "gross_paid": 0.0, "net_paid": 0.0})
            for item in (a, c):
                item["rows"] += 1
                item["committed"] += committed
                item["gross_paid"] += gross
                item["net_paid"] += net
    return {
        "totals": totals,
        "by_agency": sorted(by_agency.values(), key=lambda item: item["gross_paid"], reverse=True)[:100],
        "by_creditor": sorted(by_creditor.values(), key=lambda item: item["gross_paid"], reverse=True)[:200],
    }


def summarize_hash_csv(path: Path, *, delimiter: str = "#", value_headers: Iterable[str] = ()) -> dict[str, Any]:
    """Resume CSVs do TCE sem persistir linhas brutas ou documentos pessoais."""
    rows = 0
    value_sum = 0.0
    agencies: dict[str, int] = {}
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as fh:
        reader = csv.DictReader(fh, delimiter=delimiter)
        if not reader.fieldnames or len(reader.fieldnames) < 2:
            raise BahiaOpenDataError("Resposta do TCE não possui cabeçalho tabular compatível")
        field_map = {_norm_header(name): name for name in reader.fieldnames if name}
        agency_field = field_map.get("ÓRGÃO CONTRATANTE") or field_map.get("ORGAO CONTRATANTE") or field_map.get("ORGÃO") or field_map.get("ORGAO")
        value_field = None
        for candidate in value_headers:
            value_field = field_map.get(_norm_header(candidate))
            if value_field:
                break
        if not agency_field and not value_field:
            raise BahiaOpenDataError("CSV do TCE não contém nenhum dos campos esperados para validação")
        for row in reader:
            rows += 1
            if agency_field:
                agency = row.get(agency_field) or "Não informado"
                agencies[agency] = agencies.get(agency, 0) + 1
            if value_field:
                value_sum += _parse_brl(row.get(value_field))
    return {
        "rows": rows,
        "declared_value_sum": value_sum,
        "top_agencies_by_rows": [
            {"agency": key, "rows": value}
            for key, value in sorted(agencies.items(), key=lambda item: item[1], reverse=True)[:100]
        ],
    }
