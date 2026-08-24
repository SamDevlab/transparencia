import json
from pathlib import Path

from transparencia.collectors.pncp_contracts import (
    agency_cnpjs_from_procurements,
    in_scope,
    normalize_record,
    pagination_metadata,
    query_complete,
)
from transparencia.config import CityConfig

CITY = CityConfig(slug="salvador", name="Salvador", uf="BA", ibge_code="2927408", municipality_cnpj="13927801000149")


def sample_contract() -> dict:
    return {
        "numeroControlePNCP": "13927801000149-2-000001/2026",
        "numeroControlePNCPCompra": "13927801000149-1-000001/2026",
        "numeroContratoEmpenho": "001/2026",
        "anoContrato": 2026,
        "sequencialContrato": 1,
        "tipoContratoId": 1,
        "tipoContratoNome": "Contrato",
        "processo": "123/2026",
        "objetoContrato": "Serviço teste",
        "orgaoEntidade": {"cnpj": "13927801000149", "razaoSocial": "MUNICIPIO DO SALVADOR", "esferaId": "M", "poderId": "E"},
        "unidadeOrgao": {"codigoUnidade": "1", "nomeUnidade": "PREFEITURA", "municipioId": 2927408, "municipioNome": "Salvador", "ufSigla": "BA"},
        "tipoPessoa": "PJ",
        "niFornecedor": "12345678000190",
        "nomeRazaoSocialFornecedor": "Fornecedor Teste",
        "valorInicial": 100.0,
        "valorGlobal": 120.0,
        "valorAcumulado": 20.0,
        "dataAssinatura": "2026-01-10",
        "dataVigenciaInicio": "2026-01-10",
        "dataVigenciaFim": "2026-12-31",
        "dataPublicacaoPncp": "2026-01-11T10:00:00",
    }


def test_contract_scope_and_normalization():
    raw = sample_contract()
    assert in_scope(raw, CITY, "executivo")
    assert not in_scope(raw, CITY, "legislativo")
    row = normalize_record(raw, CITY, "2026-08-17T12:00:00Z", "abc")
    assert row["supplier_document"] == "12345678000190"
    assert row["global_value"] == 120.0
    assert row["municipality_ibge"] == 2927408
    assert row["source_url"].endswith("/13927801000149/contratos/2026/1")
    assert row["pncp_contract_control_number"] == "13927801000149-2-000001/2026"
    assert row["pncp_procurement_control_number"] == "13927801000149-1-000001/2026"
    assert row["agency_document"] == "13927801000149"


def test_agency_cnpjs_from_procurements(tmp_path: Path):
    p = tmp_path / "p.jsonl"
    p.write_text("\n".join([
        json.dumps({"agency_cnpj": "13.927.801/0001-49"}),
        json.dumps({"agency_document": "13927801000149"}),
        json.dumps({"agency_cnpj": "123"}),
    ]), encoding="utf-8")
    assert agency_cnpjs_from_procurements([p]) == ("13927801000149",)


def test_pagination_metadata_accepts_common_pncp_shapes():
    assert pagination_metadata({
        "totalPaginas": 3,
        "totalRegistros": 205,
        "paginasRestantes": 2,
    }) == (3, 205, 2)
    assert pagination_metadata({
        "paginacao": {"totalPages": "4", "total": "301", "paginasRestantes": "1"}
    }) == (4, 301, 1)
    assert pagination_metadata([]) == (None, None, None)


def test_query_complete_requires_explicit_pagination_or_count_proof():
    assert query_complete(
        error=None,
        pages_collected=2,
        source_rows_received=150,
        reported_pages=2,
        reported_total=150,
    )
    assert not query_complete(
        error=None,
        pages_collected=2,
        source_rows_received=149,
        reported_pages=2,
        reported_total=150,
    )
    assert not query_complete(
        error=None,
        pages_collected=1,
        source_rows_received=10,
        reported_pages=None,
        reported_total=None,
    )
    assert query_complete(
        error=None,
        pages_collected=1,
        source_rows_received=0,
        reported_pages=0,
        reported_total=0,
        explicit_empty=True,
    )


def test_query_complete_never_hides_errors():
    assert not query_complete(
        error="HTTP 503 after retries",
        pages_collected=2,
        source_rows_received=150,
        reported_pages=2,
        reported_total=150,
    )
