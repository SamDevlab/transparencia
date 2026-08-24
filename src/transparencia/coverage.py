from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

VALID_STATUSES = {"complete_for_filter", "partial", "unavailable", "not_run"}


@dataclass(frozen=True)
class CoverageEntry:
    """Coverage proof for one source + dataset + filter scope.

    `complete_for_filter` is intentionally narrow: it means the collector reconciled
    the source's own pagination/count metadata for the stated filter. It never means
    the dataset is universally complete across other public systems.
    """

    dataset: str
    source_system: str
    status: str
    period_start: str | None = None
    period_end: str | None = None
    records: int | None = None
    pages: int | None = None
    reported_total: int | None = None
    reported_pages: int | None = None
    source_url: str | None = None
    evidence_path: str | None = None
    filter_description: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid coverage status: {self.status}")
        for field_name in ("records", "pages", "reported_total", "reported_pages"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative")
        if self.status == "complete_for_filter":
            if not self.note:
                raise ValueError("complete_for_filter requires a scope note")
            if self.reported_total is not None and self.records != self.reported_total:
                raise ValueError("complete_for_filter requires records == reported_total")
            if self.reported_pages is not None and (self.pages is None or self.pages < self.reported_pages):
                raise ValueError("complete_for_filter requires all reported pages")


@dataclass
class CoverageManifest:
    city_slug: str
    period_start: str
    period_end: str
    entries: list[CoverageEntry] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    methodology_note: str = (
        "Coverage is source-and-filter specific. A complete_for_filter entry proves only that "
        "the collector reconciled the source-reported records/pages for the stated scope. It "
        "does not prove that no record exists in another municipal, legislative, state, federal "
        "or sectoral system."
    )

    def add(self, entry: CoverageEntry) -> None:
        if entry.period_start and entry.period_start < self.period_start:
            raise ValueError("entry period starts before manifest period")
        if entry.period_end and entry.period_end > self.period_end:
            raise ValueError("entry period ends after manifest period")
        self.entries.append(entry)

    def extend(self, entries: Iterable[CoverageEntry]) -> None:
        for entry in entries:
            self.add(entry)

    @property
    def counts_by_status(self) -> dict[str, int]:
        counts = {status: 0 for status in sorted(VALID_STATUSES)}
        for entry in self.entries:
            counts[entry.status] += 1
        return counts

    @property
    def latest_source_as_of(self) -> str | None:
        dates = [entry.period_end for entry in self.entries if entry.period_end]
        return max(dates) if dates else None

    def to_dict(self) -> dict:
        return {
            "city_slug": self.city_slug,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "latest_source_as_of": self.latest_source_as_of,
            "methodology_note": self.methodology_note,
            "counts_by_status": self.counts_by_status,
            "entries": [asdict(entry) for entry in self.entries],
        }

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return path
