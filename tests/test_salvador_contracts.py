from datetime import date

from transparencia.collectors.salvador_contracts import Window, _pages, _records, _split, _stable_record_key


def test_contract_payload_helpers_do_not_invent_field_semantics():
    payload = {"dados": [{"cdContrato": 1, "vlContrato": 10.0}], "paginacao": {"paginas": 3, "total": 1}}
    assert _records(payload) == [{"cdContrato": 1, "vlContrato": 10.0}]
    assert _pages(payload) == 3


def test_contract_internal_key_is_deterministic_not_source_id():
    row = {"b": 2, "a": 1}
    assert _stable_record_key(row) == _stable_record_key({"a": 1, "b": 2})


def test_adaptive_window_split_has_no_gap_or_overlap():
    parts = _split(Window(date(2026, 1, 1), date(2026, 1, 10)))
    assert parts is not None
    left, right = parts
    assert left.start == date(2026, 1, 1)
    assert left.end + (right.start - left.end) == right.start
    assert (right.start - left.end).days == 1
    assert right.end == date(2026, 1, 10)
