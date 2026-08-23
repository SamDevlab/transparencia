from __future__ import annotations

import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import httpx

from ..provenance import persist_snapshot
from .cms import CERTAMES_URL, _headers, parse_certames, visible_text


class _F3Parser(HTMLParser):
    """Extract the hidden ScriptCase F3 form without adding a parser dependency."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_f3 = False
        self.fields: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag.lower() == "form" and values.get("name") == "F3":
            self.in_f3 = True
            return
        if self.in_f3 and tag.lower() == "input":
            name = values.get("name")
            if name:
                self.fields[name] = values.get("value") or ""

    def handle_endtag(self, tag: str) -> None:
        if self.in_f3 and tag.lower() == "form":
            self.in_f3 = False


def parse_scriptcase_form(html: str) -> dict[str, str]:
    parser = _F3Parser()
    parser.feed(html)
    return parser.fields


def parse_pagination_window(html: str) -> tuple[int, int, int] | None:
    """Return the server-declared (first, last, total) grid window when present."""
    text = visible_text(html)
    matches = re.findall(r"(?<!\d)(\d+)\s+a\s+(\d+)\s+de\s+(\d+)(?!\d)", text, re.I)
    if not matches:
        return None
    # The certame grid exposes the same pager at top/bottom; prefer the largest total.
    start, end, total = max(((int(a), int(b), int(c)) for a, b, c in matches), key=lambda item: item[2])
    if start < 1 or end < start or total < end:
        return None
    return start, end, total


def _row_key(row: dict[str, Any]) -> str:
    # No fuzzy identity matching. This key only prevents the same server row from
    # being emitted twice when a page is repeated by ScriptCase.
    payload = [
        row.get("modality_name"),
        row.get("notice_number"),
        row.get("scheduled_at_text"),
        row.get("updated_at_text"),
        row.get("object"),
    ]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def collect_certames(
    out_dir: Path,
    *,
    max_pages: int = 100,
    sleep_seconds: float = 0.5,
) -> Path:
    """Collect the public Câmara certame grid through its own ScriptCase pager.

    Completeness is asserted only when the grid itself reports a total, navigation
    reaches the final declared window, and the number of distinct parsed rows is
    exactly equal to that reported total. HTTP/session failures remain partial.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "cms_certames.jsonl"
    legacy_output = out_dir / "cms_certames_visible.jsonl"
    coverage_path = out_dir / "cms_certames.coverage.json"

    seen: dict[str, dict[str, Any]] = {}
    pages_collected = 0
    page_windows: list[dict[str, int]] = []
    expected_total: int | None = None
    stopped_status: int | None = None
    error: str | None = None
    reached_server_end = False
    previous_signature: str | None = None

    try:
        with httpx.Client(headers=_headers(), follow_redirects=True, timeout=60.0) as client:
            response = client.get(CERTAMES_URL)
            for page_index in range(max_pages):
                if response.status_code in {403, 429} or response.status_code >= 500:
                    stopped_status = response.status_code
                    break
                response.raise_for_status()
                pages_collected += 1

                meta = persist_snapshot(
                    out_dir=out_dir / "snapshots",
                    source_id="cms_certames",
                    requested_url=CERTAMES_URL,
                    final_url=str(response.url),
                    status_code=response.status_code,
                    content_type=response.headers.get("content-type", "text/html"),
                    body=response.content,
                )
                rows = parse_certames(
                    response.text,
                    source_url=str(response.url),
                    observed_at=meta.collected_at,
                    snapshot_sha256=meta.sha256,
                )
                page_keys: list[str] = []
                for row in rows:
                    key = _row_key(row)
                    page_keys.append(key)
                    row["coverage"] = "scriptcase_full_catalogue_attempt"
                    row["event_key"] = key
                    seen.setdefault(key, row)

                window = parse_pagination_window(response.text)
                if window is None:
                    error = "server_pagination_window_missing"
                    break
                start, end, total = window
                expected_total = total if expected_total is None else expected_total
                if total != expected_total:
                    error = f"server_total_changed:{expected_total}->{total}"
                    break
                page_windows.append({"start": start, "end": end, "total": total})

                signature = hashlib.sha256(
                    (f"{start}:{end}:{total}|" + "|".join(page_keys)).encode("utf-8")
                ).hexdigest()
                if previous_signature == signature:
                    error = "scriptcase_page_repeated_before_end"
                    break
                previous_signature = signature

                if end >= total:
                    reached_server_end = True
                    break

                fields = parse_scriptcase_form(response.text)
                if not fields.get("script_case_init"):
                    error = "scriptcase_f3_or_init_missing"
                    break
                fields.update(
                    {
                        "nmgp_opcao": "avanca",
                        "nmgp_parms": "SC_null",
                        "nmgp_orig_pesq": "",
                        "nmgp_url_saida": "",
                        "nmgp_outra_jan": "",
                    }
                )
                time.sleep(sleep_seconds)
                response = client.post(CERTAMES_URL, data=fields, headers={"Referer": str(response.url)})
            else:
                error = f"max_pages_reached:{max_pages}"
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        error = f"{type(exc).__name__}: {exc}"
    except httpx.HTTPStatusError as exc:
        stopped_status = exc.response.status_code
        error = f"HTTPStatusError: {exc}"

    complete = bool(
        reached_server_end
        and expected_total is not None
        and len(seen) == expected_total
        and stopped_status is None
        and error is None
    )

    with output.open("w", encoding="utf-8") as sink:
        for row in seen.values():
            sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    # Preserve the historical filename for downstream readers while they migrate.
    legacy_output.write_text(output.read_text(encoding="utf-8"), encoding="utf-8")

    coverage = {
        "records": len(seen),
        "server_reported_total": expected_total,
        "pages_collected": pages_collected,
        "page_windows": page_windows,
        "reached_server_end": reached_server_end,
        "complete": complete,
        "stopped_status": stopped_status,
        "error": error,
        "navigation": "ScriptCase F3 POST nmgp_opcao=avanca in the same HTTP session",
        "identity_rule": "Exact normalized row fingerprint; no fuzzy identity matching.",
        "coverage_rule": "complete=true only when the server reports a total, the final pagination window is reached normally, and distinct parsed rows exactly equal that total. A transport/HTTP/session/parser failure is partial and never interpreted as zero.",
    }
    coverage_path.write_text(json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
