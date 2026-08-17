from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

VALID_STATUSES = {"complete_for_filter", "partial", "unavailable", "not_run"}


@dataclass(frozen=True)
class CoverageEntry:
    dataset: str
    source_system: str
    status: str
    period_start: str | None = None
    period_end: str | None = None
    records: int | None = None
    pages: int | None = None
    source_url: str | None = None
    evidence_path: str | None = None
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"invalid coverage status: {self.status}")
        if self.records is not None and self.records < 0:
            raise ValueError("records cannot be negative")
        if self.pages is not None and self.pages < 0:
            raise ValueError("pages cannot be negative")
        if self.status == "complete_for_filter" and not self.note:
            raise ValueError("complete_for_filter requires a scope note")


@dataclass
class CoverageManifest:
    city_slug: str
    period_start: str
    period_end: str
    entries: list[CoverageEntry] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    methodology_note: str = (
        "Coverage is source-and-filter specific. A complete_for_filter entry proves only that the "
        "collector received the count/pages reported by that source for the stated filter. It does "
        "not prove that no record exists in another municipal, legislative, federal or sectoral system."
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

    def to_dict(self) -> dict:
        return {
            "city_slug": self.city_slug,
            "period_start": self.period_start,
            "period_end": self.period_end,
            "generated_at": self.generated_at,
            "methodology_note": self.methodology_note,
            "counts_by_status": self.counts_by_status,
            "entries": [asdict(entry) for entry in self.entries],
        }

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path
