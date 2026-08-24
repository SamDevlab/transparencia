from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .reconcile import normalize_identifier


@dataclass(frozen=True)
class ComparableSnapshot:
    source_system: str
    as_of: str
    rows: tuple[dict, ...]
    complete_for_filter: bool

    @classmethod
    def from_rows(
        cls,
        *,
        source_system: str,
        as_of: str,
        rows: Iterable[dict],
        complete_for_filter: bool,
    ) -> "ComparableSnapshot":
        return cls(source_system, as_of, tuple(rows), complete_for_filter)


def _identity(row: dict, identity_fields: Sequence[str]) -> tuple[str, ...] | None:
    parts: list[str] = []
    for field in identity_fields:
        value = normalize_identifier(row.get(field))
        if not value:
            return None
        parts.append(value)
    return tuple(parts)


def diff_snapshots(
    previous: ComparableSnapshot,
    current: ComparableSnapshot,
    *,
    identity_fields: Sequence[str],
    tracked_fields: Sequence[str],
) -> list[dict]:
    """Return exact temporal changes between two comparable complete snapshots.

    The snapshots must come from the same source system and both must be complete for
    their declared filter. Rows without a complete exact identity are excluded rather
    than heuristically linked.
    """
    if not previous.complete_for_filter or not current.complete_for_filter:
        raise ValueError("history requires two complete_for_filter snapshots")
    if previous.source_system != current.source_system:
        raise ValueError("history requires the same source_system")
    if previous.as_of >= current.as_of:
        raise ValueError("current snapshot must be newer than previous snapshot")
    if not identity_fields:
        raise ValueError("at least one identity field is required")

    def build_index(rows: tuple[dict, ...]) -> dict[tuple[str, ...], dict]:
        index: dict[tuple[str, ...], dict] = {}
        duplicates: set[tuple[str, ...]] = set()
        for row in rows:
            key = _identity(row, identity_fields)
            if key is None:
                continue
            if key in index:
                duplicates.add(key)
            else:
                index[key] = row
        for key in duplicates:
            index.pop(key, None)
        return index

    before = build_index(previous.rows)
    after = build_index(current.rows)
    events: list[dict] = []

    for key in sorted(before.keys() | after.keys()):
        old = before.get(key)
        new = after.get(key)
        identity = dict(zip(identity_fields, key, strict=True))
        if old is None:
            events.append({"type": "added", "identity": identity, "as_of": current.as_of})
            continue
        if new is None:
            events.append({"type": "removed", "identity": identity, "as_of": current.as_of})
            continue

        changes = {
            field: {"before": old.get(field), "after": new.get(field)}
            for field in tracked_fields
            if old.get(field) != new.get(field)
        }
        if changes:
            events.append(
                {
                    "type": "changed",
                    "identity": identity,
                    "from": previous.as_of,
                    "to": current.as_of,
                    "changes": changes,
                }
            )
    return events
