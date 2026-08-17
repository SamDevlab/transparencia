from __future__ import annotations

import hashlib
import json
import re
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

import httpx

from ..provenance import persist_snapshot

CMS_BASE = "https://www.cms.ba.gov.br"
TRAVEL_URL = f"{CMS_BASE}/transparencia/despesas-viagem"
DOCUMENT_SECTIONS = {
    "prestacao_contas": f"{CMS_BASE}/transparencia/prestacao-contas",
    "execucao_orcamentaria_financeira": f"{CMS_BASE}/transparencia/exec-orcamentaria-financeira",
}
CERTAMES_URL = "https://cmsalvador.sys.inf.br/ca/licitacao/"


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.replace("\xa0", " ").split())
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


class _AnchorParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.current_href: str | None = None
        self.current_text: list[str] = []
        self.anchors: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self.current_href = dict(attrs).get("href")
        self.current_text = []

    def handle_data(self, data: str) -> None:
        if self.current_href is not None:
            self.current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self.current_href is not None:
            text = " ".join("".join(self.current_text).replace("\xa0", " ").split())
            self.anchors.append((self.current_href, text))
            self.current_href = None
            self.current_text = []


def visible_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    return parser.text()


def parse_travel_entries(html: str, *, source_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    text = visible_text(html)
    pattern = re.compile(
        r"Data:\s*(?P<date>\d{2}/\d{2}/\d{4})\s+"
        r"Tipo:\s*(?P<type>.*?)\s+"
        r"Usuário:\s*(?P<user>.*?)\s+"
        r"Valor:\s*R\$\s*(?P<value>[\d.,]+)\s+"
        r"Localidade:\s*(?P<location>.*?)\s+"
        r"Justificativa:\s*(?P<justification>.*?)"
        r"(?=\s+Data:\s*\d{2}/\d{2}/\d{4}|\s+Transparência\s+|\Z)",
        re.S | re.I,
    )
    rows: list[dict] = []
    for m in pattern.finditer(text):
        raw_value = m.group("value").strip()
        if "," in raw_value and "." in raw_value:
            value = float(raw_value.replace(".", "").replace(",", "."))
        else:
            value = float(raw_value.replace(",", "."))
        justification = " ".join(m.group("justification").split())
        process_match = re.search(r"PROCESSO\s*(?:N[º°.]*)?\s*[:\-]?\s*(\d+/\d{4})", justification, re.I)
        identity = "|".join([m.group("date"), m.group("user"), f"{value:.2f}", m.group("location"), justification])
        rows.append({
            "source_system": "CMS",
            "event_key": hashlib.sha256(identity.encode("utf-8")).hexdigest(),
            "date": m.group("date"),
            "expense_type": " ".join(m.group("type").split()),
            "user_name": " ".join(m.group("user").split()),
            "value_brl": value,
            "location": " ".join(m.group("location").split()),
            "justification": justification,
            "process_number": process_match.group(1) if process_match else None,
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def parse_document_links(html: str, *, section: str, page_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    parser = _AnchorParser()
    parser.feed(html)
    rows: list[dict] = []
    seen: set[str] = set()
    for href, title in parser.anchors:
        absolute = urljoin(page_url, href)
        low = absolute.lower()
        if not ("/transparencia/uploads/" in low or low.endswith((".pdf", ".xlsx", ".xls", ".csv"))):
            continue
        if absolute in seen:
            continue
        seen.add(absolute)
        rows.append({
            "source_system": "CMS",
            "section": section,
            "title": title,
            "document_url": absolute,
            "page_url": page_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def parse_certames(html: str, *, source_url: str, observed_at: str, snapshot_sha256: str) -> list[dict]:
    text = visible_text(html)
    parts = re.split(r"(?=Modalidade:\s*)", text)
    rows: list[dict] = []
    for part in parts:
        if not part.startswith("Modalidade:"):
            continue
        modality = re.search(r"Modalidade:\s*(.*?)\s+Número:", part, re.S)
        number = re.search(r"Número:\s*([^\n]+)", part)
        schedule = re.search(r"Horário Previsto:\s*([^\n]+)", part)
        updated = re.search(r"Última Atualização:\s*([^\n]+)", part)
        if not modality or not number:
            continue
        obj = ""
        if updated:
            start = updated.end()
            end = part.find("Valor Estimado:", start)
            obj = " ".join(part[start:(end if end >= 0 else len(part))].split())
        status_matches = re.findall(r"\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}\s+([^\n]+)", part)
        rows.append({
            "source_system": "CMS_CERTAMES",
            "modality_name": " ".join(modality.group(1).split()),
            "notice_number": number.group(1).strip(),
            "scheduled_at_text": schedule.group(1).strip() if schedule else None,
            "updated_at_text": updated.group(1).strip() if updated else None,
            "object": obj,
            "latest_status_text": status_matches[0].strip() if status_matches else None,
            "source_url": source_url,
            "observed_at": observed_at,
            "snapshot_sha256": snapshot_sha256,
        })
    return rows


def collect_travel(out_dir: Path, *, max_pages: int = 100, sleep_seconds: float = 0.15) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "cms_travel_expenses.jsonl"
    headers = {"User-Agent": "transparencia-municipal/0.2", "Accept": "text/html"}
    seen: set[str] = set()
    empty_pages = 0
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        for page in range(max_pages):
            url = TRAVEL_URL if page == 0 else f"{TRAVEL_URL}?page={page}"
            response = client.get(url)
            response.raise_for_status()
            meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id="cms_viagens", requested_url=url,
                                    final_url=str(response.url), status_code=response.status_code,
                                    content_type=response.headers.get("content-type", "text/html"), body=response.content)
            rows = parse_travel_entries(response.text, source_url=str(response.url), observed_at=meta.collected_at, snapshot_sha256=meta.sha256)
            new = 0
            for row in rows:
                if row["event_key"] in seen:
                    continue
                seen.add(row["event_key"])
                sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                new += 1
            if new == 0:
                empty_pages += 1
                if empty_pages >= 2:
                    break
            else:
                empty_pages = 0
            time.sleep(sleep_seconds)
    return output


def collect_document_catalog(out_dir: Path, *, max_pages: int = 100, sleep_seconds: float = 0.15) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "cms_documents.jsonl"
    seen: set[str] = set()
    headers = {"User-Agent": "transparencia-municipal/0.2", "Accept": "text/html"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client, output.open("w", encoding="utf-8") as sink:
        for section, base_url in DOCUMENT_SECTIONS.items():
            empty_pages = 0
            for page in range(max_pages):
                url = base_url if page == 0 else f"{base_url}?page={page}"
                response = client.get(url)
                response.raise_for_status()
                meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id=f"cms_{section}", requested_url=url,
                                        final_url=str(response.url), status_code=response.status_code,
                                        content_type=response.headers.get("content-type", "text/html"), body=response.content)
                rows = parse_document_links(response.text, section=section, page_url=str(response.url), observed_at=meta.collected_at, snapshot_sha256=meta.sha256)
                new = 0
                for row in rows:
                    key = row["document_url"]
                    if key in seen:
                        continue
                    seen.add(key)
                    sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    new += 1
                if new == 0:
                    empty_pages += 1
                    if empty_pages >= 2:
                        break
                else:
                    empty_pages = 0
                time.sleep(sleep_seconds)
    return output


def collect_certames_visible(out_dir: Path) -> Path:
    """Collect only the server-visible certame page; never claim full catalogue coverage."""
    out_dir.mkdir(parents=True, exist_ok=True)
    output = out_dir / "cms_certames_visible.jsonl"
    headers = {"User-Agent": "transparencia-municipal/0.2", "Accept": "text/html"}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=60.0) as client:
        response = client.get(CERTAMES_URL)
        response.raise_for_status()
        meta = persist_snapshot(out_dir=out_dir / "snapshots", source_id="cms_certames", requested_url=CERTAMES_URL,
                                final_url=str(response.url), status_code=response.status_code,
                                content_type=response.headers.get("content-type", "text/html"), body=response.content)
        rows = parse_certames(response.text, source_url=str(response.url), observed_at=meta.collected_at, snapshot_sha256=meta.sha256)
    with output.open("w", encoding="utf-8") as sink:
        for row in rows:
            row["coverage"] = "server_visible_page_only"
            sink.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return output
