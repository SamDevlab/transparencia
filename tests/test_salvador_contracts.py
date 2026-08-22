from datetime import date

from transparencia.collectors.salvador_contracts import (
    Window,
    _pages,
    _partition,
    _records,
    _request_body,
    _split,
    _stable_record_key,
    _window_complete,
)


def test_contract_payload_helpers_do_not_invent_field_semantics():
    payload = {"dados": [{"cdContrato": 1, "vlContrato": 10.0}], "paginacao": {"paginas": 3, "total": 1}}
    assert _records(payload) == [{"cdContrato": 1, "vlContrato": 10.0}]
    assert _pages(payload) == 3


def test_contract_internal_key_is_deterministic_not_source_id():
    row = {"b": 2, "a": 1}
    assert _stable_record_key(row) == _stable_record_key({"a": 1, "b": 2})


def test_contract_request_body_matches_official_generic_filter_shape():
    body = _request_body(Window(date(2026, 8, 1), date(2026, 8, 17)))
    assert body == {
        "dataInicio": "2026-08-01",
        "dataFim": "2026-08-17",
        "agrupamentos": [],
        "filtros": [],
    }


def test_adaptive_window_split_has_no_gap_or_overlap():
    parts = _split(Window(date(2026, 1, 1), date(2026, 1, 10)))
    assert parts is not None
    left, right = parts
    assert left.start == date(2026, 1, 1)
    assert left.end + (right.start - left.end) == right.start
    assert (right.start - left.end).days == 1
    assert right.end == date(2026, 1, 10)


def test_initial_partition_is_bounded_and_contiguous():
    windows = _partition(date(2026, 1, 1), date(2026, 3, 5), 31)
    assert windows == [
        Window(date(2026, 1, 1), date(2026, 1, 31)),
        Window(date(2026, 2, 1), date(2026, 3, 3)),
        Window(date(2026, 3, 4), date(2026, 3, 5)),
    ]
    for previous, current in zip(windows, windows[1:]):
        assert (current.start - previous.end).days == 1


def test_contract_window_requires_explicit_source_pagination_metadata():
    assert not _window_complete(
        error=None,
        pages_collected=1,
        records_received=0,
        reported_pages=None,
        reported_total=None,
    )
    assert _window_complete(
        error=None,
        pages_collected=3,
        records_received=25,
        reported_pages=3,
        reported_total=25,
    )
    assert not _window_complete(
        error=None,
        pages_collected=2,
        records_received=20,
        reported_pages=3,
        reported_total=25,
    )
    assert not _window_complete(
        error="ReadTimeout",
        pages_collected=3,
        records_received=25,
        reported_pages=3,
        reported_total=25,
    )
