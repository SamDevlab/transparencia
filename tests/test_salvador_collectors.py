from transparencia.collectors.cms import parse_certames, parse_document_links, parse_travel_entries
from transparencia.collectors.pncp_contracts import in_scope, normalize_record
from transparencia.collectors.webapp_discovery import _candidates
from transparencia.config import CityConfig

CITY = CityConfig(slug="salvador", name="Salvador", uf="BA", ibge_code="2927408", municipality_cnpj="13927801000149")


def test_cms_travel_parser_preserves_process_and_value():
    html = "<div>Data: 03/06/2026</div><div>Tipo: Diária</div><div>Usuário: MARIA TESTE</div><div>Valor: R$ 3150.00</div><div>Localidade: FOZ DO IGUAÇU/PR</div><div>Justificativa: EVENTO. PROCESSO Nº 800/2026.</div><footer>Transparência</footer>"
    rows = parse_travel_entries(html, source_url="https://example", observed_at="now", snapshot_sha256="abc")
    assert len(rows) == 1
    assert rows[0]["value_brl"] == 3150.0
    assert rows[0]["process_number"] == "800/2026"


def test_cms_document_and_certame_parsers():
    docs = parse_document_links('<a href="/transparencia/uploads/prestacao-contas/x.pdf">RAZÃO SIGA</a>', section="prestacao", page_url="https://www.cms.ba.gov.br/transparencia/prestacao-contas", observed_at="now", snapshot_sha256="abc")
    assert docs[0]["document_url"].endswith("x.pdf")
    html = "<div>Modalidade: Dispensa Eletrônica</div><div>Número: 17/2026</div><div>Horário Previsto: 25/06/2026 08:00</div><div>Última Atualização: 06/08/2026 11:25</div><div>REGISTRO DE PREÇOS para café</div><div>Valor Estimado:</div>"
    rows = parse_certames(html, source_url="https://example", observed_at="now", snapshot_sha256="abc")
    assert rows[0]["notice_number"] == "17/2026"


def test_webapp_candidates_are_transparency_related():
    rows = _candidates('const a="/api/despesas"; const b="/assets/logo.png"; const c="https://x.test/api/receita";')
    assert "/api/despesas" in rows
    assert "https://x.test/api/receita" in rows
    assert "/assets/logo.png" not in rows


def test_contract_scope_and_normalization():
    raw = {
        "numeroControlePNCP": "13927801000149-2-000001/2026",
        "numeroControlePNCPCompra": "13927801000149-1-000001/2026",
        "numeroContratoEmpenho": "001/2026", "anoContrato": 2026, "sequencialContrato": 1,
        "orgaoEntidade": {"cnpj": "13927801000149", "razaoSocial": "MUNICIPIO DO SALVADOR", "esferaId": "M", "poderId": "E"},
        "unidadeOrgao": {"municipioId": 2927408, "municipioNome": "Salvador", "ufSigla": "BA"},
        "niFornecedor": "12345678000190", "nomeRazaoSocialFornecedor": "Fornecedor Teste", "valorGlobal": 120.0,
    }
    assert in_scope(raw, CITY, "executivo")
    row = normalize_record(raw, CITY, "2026-08-17T12:00:00Z", "abc")
    assert row["supplier_document"] == "12345678000190"
    assert row["global_value"] == 120.0
