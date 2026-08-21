from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_contracts import normalize_identifier, summarize_sefaz_contracts_zip


def test_normalize_identifier_only_removes_formatting():
    assert normalize_identifier(" 123/2026-ABC ") == "1232026ABC"
    assert normalize_identifier("123-2026-abc") == "1232026ABC"
    assert normalize_identifier("124/2026-ABC") != normalize_identifier("123/2026-ABC")
    assert normalize_identifier("123/2026-ABD") != normalize_identifier("123/2026-ABC")
    assert normalize_identifier("") is None


def test_contracts_are_consolidated_by_unique_instrument_and_cpf_is_not_published(tmp_path: Path):
    archive = tmp_path / "contratos.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_CONTRATOS.csv",
            "ANO;NUM_INSTRUMENTO_FORMATADO;NUM_PROCESSO_LICITACAO;NOM_ORGAO;NOME_FORNECEDOR;CPF_CNPJ;SITUACAO;OBJETO;VALOR_CONTRATO\n"
            "2026;001/2026;PROC-10/2026;SEC A;Empresa A;12345678000100;Ativo;Serviço A;1000,00\n"
            "2026;001-2026;PROC-10/2026;SEC A;Empresa A;12345678000100;Ativo;Serviço A;1000,00\n"
            "2026;002/2026;PROC-11/2026;SEC B;Pessoa Física;12345678901;Ativo;Serviço B;500,00\n"
            "2025;003/2025;PROC-12/2025;SEC A;Empresa B;99999999000100;Encerrado;Serviço C;250,00\n",
        )
        zf.writestr(
            "VW_CONTRATOS_ADITIVOS.csv",
            "ANO;NUM_INSTRUMENTO_FORMATADO;VALOR_ADITIVO\n"
            "2026;001/2026;100,00\n",
        )

    result = summarize_sefaz_contracts_zip(archive, target_year=2026)
    primary = result["primary_table"]
    assert primary["member"] == "VW_CONTRATOS.csv"
    assert primary["selected_rows"] == 3
    assert primary["unique_instruments"] == 2
    assert primary["instrument_keys"] == ["0012026", "0022026"]
    assert primary["deduplication"]["raw_relation_rows"] == 3
    assert primary["deduplication"]["instruments_with_single_value"] == 2
    assert primary["deduplication"]["instruments_with_conflicting_values"] == 0
    assert primary["contract_value"]["deduplicated_sum"] == 1500.0
    assert primary["contract_value"]["raw_relation_sum_diagnostic_only"] == 2500.0
    assert primary["top_suppliers_cnpj_only"] == [
        {"cnpj": "12345678000100", "name": "Empresa A", "contracts": 1, "value": 1000.0}
    ]
    assert "12345678901" not in str(result)
    assert "Não há correspondência aproximada" in result["identity_rule"]
    addenda = next(table for table in result["tables"] if table["classification"] == "aditivos")
    assert addenda["selected_rows"] == 1
    assert result["archive"]["processed_tabular_members"] == 2


def test_conflicting_values_for_same_instrument_are_excluded_from_consolidated_sum(tmp_path: Path):
    archive = tmp_path / "contratos-conflito.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_CONTRATOS.csv",
            "ANO;NUM_INSTRUMENTO_FORMATADO;NOM_ORGAO;VALOR_CONTRATO\n"
            "2026;001/2026;SEC A;1000,00\n"
            "2026;001/2026;SEC A;1200,00\n"
            "2026;002/2026;SEC B;500,00\n",
        )

    result = summarize_sefaz_contracts_zip(archive, target_year=2026)
    primary = result["primary_table"]
    assert primary["unique_instruments"] == 2
    assert primary["deduplication"]["instruments_with_conflicting_values"] == 1
    assert primary["contract_value"]["deduplicated_sum"] == 500.0
    assert primary["contract_value"]["instruments_in_sum"] == 1
    assert primary["contract_value"]["conflicting_instruments_excluded"] == 1
