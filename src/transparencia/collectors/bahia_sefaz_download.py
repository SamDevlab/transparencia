from __future__ import annotations

import hashlib
import re
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


def _probe_remote_size(client: httpx.Client, url: str) -> int | None:
    """Obtém o tamanho atual sem baixar o corpo inteiro.

    O CKAN pode atualizar o arquivo antes do metadado do snapshot. A resposta Range
    é usada apenas para ler cabeçalhos; se o host ignorar Range, o corpo não é lido.
    """
    try:
        with client.stream(
            "GET",
            url,
            headers={"Range": "bytes=0-0", "Accept-Encoding": "identity"},
        ) as response:
            if response.status_code == 206:
                content_range = response.headers.get("content-range", "")
                match = re.search(r"/(\d+)\s*$", content_range)
                if match:
                    return int(match.group(1))
            if response.status_code == 200:
                content_length = response.headers.get("content-length")
                if content_length and content_length.isdigit():
                    return int(content_length)
    except httpx.HTTPError:
        return None
    return None


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
        raise BahiaOpenDataError(f"Arquivo atual com {expected_size} bytes excede limite de {max_bytes}")

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
                    match = re.fullmatch(rf"bytes\s+{start}-{end}/(\d+)", content_range.strip(), flags=re.IGNORECASE)
                    if not match:
                        raise BahiaOpenDataError(
                            f"Content-Range inesperado para {start}-{end}: {content_range or 'ausente'}"
                        )
                    reported_total = int(match.group(1))
                    if reported_total != expected_size:
                        raise BahiaOpenDataError(
                            f"Arquivo mudou durante o download: tamanho atual {reported_total}, esperado {expected_size}"
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
    remote_size = _probe_remote_size(client, url)
    effective_size = remote_size or expected_size
    if effective_size and effective_size > max_bytes:
        raise BahiaOpenDataError(f"Arquivo atual com {effective_size} bytes excede limite de {max_bytes}")

    size_context = {
        "metadata_expected_size": expected_size,
        "remote_size": remote_size,
        "effective_size": effective_size,
        "metadata_size_mismatch": bool(remote_size and expected_size and remote_size != expected_size),
    }

    if effective_size and effective_size >= range_threshold:
        try:
            path, evidence, history = _range_download(
                client,
                url,
                expected_size=effective_size,
                max_bytes=max_bytes,
                chunk_size=chunk_size,
            )
            return path, evidence, {
                "download_mode": "http_range",
                "range_chunk_bytes": chunk_size,
                "range_attempts": history,
                **size_context,
            }
        except BahiaOpenDataError as exc:
            if "não aceitou faixa" not in str(exc):
                raise

    path, evidence, history = _whole_download(client, url, max_bytes=max_bytes)
    if effective_size and evidence.bytes != effective_size:
        path.unlink(missing_ok=True)
        raise BahiaOpenDataError(
            f"Download completo com tamanho divergente: {evidence.bytes} != {effective_size}"
        )
    return path, evidence, {
        "download_mode": "whole_with_retries",
        "attempts": history,
        **size_context,
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
    """Baixa recurso estadual com retomada e verificação do tamanho atual.

    O tamanho publicado no CKAN é evidência de metadado, mas pode ficar defasado em
    relação ao arquivo de atualização diária. O downloader consulta o tamanho atual
    no mesmo host antes da transferência e registra qualquer divergência.
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
