from __future__ import annotations

import hashlib
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from transparencia.collectors.bahia_open_data import BahiaOpenDataError, DownloadEvidence, stream_to_temp

OFFICIAL_DATA_HOST = "dados.ba.gov.br"


def _certificate_chain_error(exc: Exception) -> bool:
    text = str(exc).upper()
    return "CERTIFICATE_VERIFY_FAILED" in text or "CERTIFICATE VERIFY FAILED" in text


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _whole_download(
    client: httpx.Client,
    url: str,
    *,
    max_bytes: int,
    attempts: int = 3,
) -> tuple[Path, DownloadEvidence, list[dict[str, Any]]]:
    history: list[dict[str, Any]] = []
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            path, evidence = stream_to_temp(client, url, max_bytes=max_bytes)
            history.append({"attempt": attempt, "mode": "whole", "status": "success", "bytes": evidence.bytes})
            return path, evidence, history
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            history.append({
                "attempt": attempt,
                "mode": "whole",
                "status": "failed",
                "error_type": type(exc).__name__,
                "error": str(exc)[:500],
            })
            if attempt < attempts:
                time.sleep(min(2**attempt, 8))
    assert last_error is not None
    raise last_error


def _range_download(
    client: httpx.Client,
    url: str,
    *,
    expected_size: int,
    max_bytes: int,
    chunk_size: int,
    attempts_per_chunk: int = 5,
) -> tuple[Path, DownloadEvidence, list[dict[str, Any]]]:
    if expected_size <= 0:
        raise BahiaOpenDataError("Tamanho esperado inválido para download por faixas")
    if expected_size > max_bytes:
        raise BahiaOpenDataError(f"Arquivo declarado com {expected_size} bytes excede limite de {max_bytes}")

    handle = tempfile.NamedTemporaryFile(prefix="bahia-sefaz-range-", suffix=".bin", delete=False)
    path = Path(handle.name)
    history: list[dict[str, Any]] = []
    content_type = ""
    try:
        start = 0
        while start < expected_size:
            end = min(start + chunk_size - 1, expected_size - 1)
            expected_chunk = end - start + 1
            last_error: Exception | None = None
            for attempt in range(1, attempts_per_chunk + 1):
                try:
                    response = client.get(
                        url,
                        headers={"Range": f"bytes={start}-{end}", "Accept-Encoding": "identity"},
                    )
                    if response.status_code != 206:
                        raise BahiaOpenDataError(
                            f"Servidor não aceitou faixa bytes={start}-{end}: HTTP {response.status_code}"
                        )
                    content_range = response.headers.get("content-range", "")
                    if not content_range.lower().startswith(f"bytes {start}-{end}/".lower()):
                        raise BahiaOpenDataError(
                            f"Content-Range inesperado para {start}-{end}: {content_range or 'ausente'}"
                        )
                    data = response.content
                    if len(data) != expected_chunk:
                        raise BahiaOpenDataError(
                            f"Faixa incompleta {start}-{end}: recebidos {len(data)} de {expected_chunk} bytes"
                        )
                    handle.write(data)
                    content_type = content_type or response.headers.get("content-type", "")
                    history.append({
                        "range": f"{start}-{end}",
                        "attempt": attempt,
                        "status": "success",
                        "bytes": len(data),
                    })
                    start = end + 1
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    history.append({
                        "range": f"{start}-{end}",
                        "attempt": attempt,
                        "status": "failed",
                        "error_type": type(exc).__name__,
                        "error": str(exc)[:500],
                    })
                    if attempt < attempts_per_chunk:
                        time.sleep(min(2**attempt, 8))
            if last_error is not None:
                raise last_error
        handle.flush()
    except Exception:
        handle.close()
        path.unlink(missing_ok=True)
        raise
    finally:
        if not handle.closed:
            handle.close()

    actual_size = path.stat().st_size
    if actual_size != expected_size:
        path.unlink(missing_ok=True)
        raise BahiaOpenDataError(f"Tamanho final divergente: {actual_size} != {expected_size}")
    evidence = DownloadEvidence(
        url=url,
        status_code=206,
        sha256=_sha256(path),
        bytes=actual_size,
        content_type=content_type,
    )
    return path, evidence, history


def _download_with_client(
    client: httpx.Client,
    url: str,
    *,
    expected_size: int | None,
    max_bytes: int,
    range_threshold: int,
    chunk_size: int,
) -> tuple[Path, DownloadEvidence, dict[str, Any]]:
    if expected_size and expected_size >= range_threshold:
        try:
            path, evidence, history = _range_download(
                client,
                url,
                expected_size=expected_size,
                max_bytes=max_bytes,
                chunk_size=chunk_size,
            )
            return path, evidence, {
                "download_mode": "http_range",
                "expected_size": expected_size,
                "range_chunk_bytes": chunk_size,
                "range_attempts": history,
            }
        except BahiaOpenDataError as exc:
            # Se o servidor simplesmente não implementar Range, ainda permitimos a
            # estratégia tradicional com retentativas. Falhas de faixa após suporte
            # confirmado continuam visíveis no histórico do erro do download inteiro.
            if "não aceitou faixa" not in str(exc):
                raise
    path, evidence, history = _whole_download(client, url, max_bytes=max_bytes)
    if expected_size and evidence.bytes != expected_size:
        path.unlink(missing_ok=True)
        raise BahiaOpenDataError(
            f"Download completo com tamanho divergente: {evidence.bytes} != {expected_size}"
        )
    return path, evidence, {
        "download_mode": "whole_with_retries",
        "expected_size": expected_size,
        "attempts": history,
    }


def download_ckan_resource_resilient(
    url: str,
    *,
    expected_size: int | None = None,
    headers: dict[str, str] | None = None,
    max_bytes: int = 900_000_000,
    range_threshold: int = 250_000_000,
    chunk_size: int = 16 * 1024 * 1024,
) -> tuple[Path, DownloadEvidence, dict[str, Any]]:
    """Baixa recurso grande do CKAN estadual com verificação de tamanho e retomada.

    O modo por faixas é preferido para arquivos grandes. O fallback TLS é permitido
    apenas para o mesmo host oficial `dados.ba.gov.br` e sempre fica registrado.
    """
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname != OFFICIAL_DATA_HOST:
        raise BahiaOpenDataError(f"Recurso SEFAZ fora do host oficial permitido: {url}")

    timeout = httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
    common_headers = {**(headers or {}), "Accept-Encoding": "identity"}
    try:
        with httpx.Client(headers=common_headers, timeout=timeout, follow_redirects=True, verify=True) as client:
            path, evidence, download = _download_with_client(
                client,
                url,
                expected_size=expected_size,
                max_bytes=max_bytes,
                range_threshold=range_threshold,
                chunk_size=chunk_size,
            )
        return path, evidence, {
            "tls_verified": True,
            "transport_note": "Validação TLS concluída normalmente.",
            **download,
        }
    except httpx.ConnectError as exc:
        if not _certificate_chain_error(exc):
            raise
        with httpx.Client(headers=common_headers, timeout=timeout, follow_redirects=True, verify=False) as client:
            path, evidence, download = _download_with_client(
                client,
                url,
                expected_size=expected_size,
                max_bytes=max_bytes,
                range_threshold=range_threshold,
                chunk_size=chunk_size,
            )
        return path, evidence, {
            "tls_verified": False,
            "fallback_reason": "certificate_chain_error",
            "transport_note": "O recurso foi baixado do mesmo host oficial dados.ba.gov.br sem validação TLS porque o runner não conseguiu validar a cadeia de certificados; a condição foi registrada.",
            **download,
        }
