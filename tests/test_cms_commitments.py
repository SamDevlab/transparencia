from pathlib import Path

from transparencia.collectors.cms_commitments import (
    _navigation_payload,
    attach_verified_official_matches,
    parse_visible_commitments,
    to_expense_event,
)


def test_scriptcase_navigation_payload_uses_observed_f3_contract():
    html = '''
    <form class="x" name="F3" method="post" action="./">
      <input type="hidden" name="nmgp_opcao" value="">
      <input type="hidden" name="nmgp_parms" value="">
      <input type="hidden" name="nmgp_orig_pesq" value="">
      <input type="hidden" name="nmgp_url_saida" value="">
      <input type="hidden" name="nmgp_outra_jan" value="">
      <input type="hidden" name="script_case_init" value="3101">
    </form>
    '''
    payload = _navigation_payload(html, "avanca")
    assert payload["nmgp_opcao"] == "avanca"
    assert payload["nmgp_parms"] == "SC_null"
    assert payload["script_case_init"] == "3101"


def _sample(note: str, creditor: str, value: str, document: str, process: str) -> str:
    return (
        f"Empenho: {note} Modalidade: Ordinário Tipo: Original "
        f"Data de Emissão: 17/08/2026 Valor R$: {value} CNPJCPF: {document} "
        f"Credor: {creditor} Fonte de Recurso: Recursos não vinculados de impostos "
        "Poder: Orgão: Unidade: Função: Sub Função: Programa: Projeto Atividade: "
        "Categoria Econômica: Grupo de Despesa: Modelo de Aplicação: Elemento de Despesa: "
        f"DESPESAS REFERENTES A VERBA COMPENSATÓRIA DE ATIVIDADE PARLAMENTAR. PROCESSO Nº {process}. "
    )


def test_commitment_parser_keeps_stage_masks_cpf_and_parses_every_block():
    text = _sample("2026NE000605", "Carlos da Silva Muniz", "34.150,00", "567.884.955-72", "1716/2026")
    text += _sample("2026NE000606", "Fornecedor Ltda", "1.000,00", "12.345.678/0001-90", "1717/2026")
    rows = parse_visible_commitments(text, source_url="https://example", observed_at="now", snapshot_sha256="abc")
    assert [row["commitment_number"] for row in rows] == ["2026NE000605", "2026NE000606"]
    assert rows[0]["committed_value"] == 34150.0
    assert rows[0]["creditor_document"] == "***.***.***-72"
    assert rows[1]["creditor_document"] == "12345678000190"
    assert rows[0]["process_number"] == "1716/2026"
    assert rows[0]["is_parliamentary_compensatory_allowance"] is True

    event = to_expense_event(rows[0])
    assert event["stage"] == "commitment"
    assert event["gross_value"] == 34150.0
    assert event["net_value"] is None


def test_identity_matching_never_uses_name_similarity(tmp_path: Path):
    seed = tmp_path / "cities/salvador/data/seed"
    seed.mkdir(parents=True)
    (seed / "officials.csv").write_text(
        "name,office,party,legislature,source_url,observed_at\n"
        "Tiago Queiroz,Vereador(a),PP,20ª,https://cms.example/tiago,2026-08-17\n",
        encoding="utf-8",
    )
    rows = [{"creditor_name": "Tiago José Queiroz dos Santos"}]
    attach_verified_official_matches(rows, tmp_path)
    assert rows[0]["matched_official_name"] is None
    assert rows[0]["official_match_type"] is None
