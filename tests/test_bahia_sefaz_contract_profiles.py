from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_contract_profiles import extract_contract_profiles


def test_extracts_only_requested_contract_profiles_without_publishing_cpf(tmp_path: Path):
    archive = tmp_path / "contratos.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_CONTRATOS.csv",
            "ANO;NUM_INSTRUMENTO_FORMATADO;NUM_PROCESSO_LICITACAO;NOM_ORGAO;NOME_FORNECEDOR;CPF_CNPJ;SITUACAO;OBJETO;MODALIDADE_LICITACAO;VALOR_CONTRATO\n"
            "2026;001/2026;PROC-10/2026;SEC A;Empresa A;12345678000100;Ativo;Serviço A;Pregão;1000,00\n"
            "2026;001-2026;PROC-10/2026;SEC A;Empresa A;12345678000100;Ativo;Serviço A;Pregão;1000,00\n"
            "2026;002/2026;PROC-11/2026;SEC B;Pessoa Física;12345678901;Ativo;Serviço B;Dispensa;500,00\n"
            "2026;003/2026;PROC-12/2026;SEC C;Empresa C;99999999000100;Ativo;Serviço C;Pregão;700,00\n",
        )

    result = extract_contract_profiles(
        archive,
        target_year=2026,
        instrument_ids=["0012026", "0022026"],
        member="VW_CONTRATOS.csv",
    )

    assert result["requested_instruments"] == 2
    assert result["matched_instruments"] == 2
    assert set(result["profiles"]) == {"0012026", "0022026"}

    company = result["profiles"]["0012026"]
    assert company["agency"] == "SEC A"
    assert company["supplier"] == {"cnpj": "12345678000100", "name": "Empresa A"}
    assert company["object"] == "Serviço A"
    assert company["statuses"] == ["Ativo"]
    assert company["modalities"] == ["Pregão"]
    assert company["contract_value"] == 1000.0
    assert company["contract_value_status"] == "single_official_value"

    person = result["profiles"]["0022026"]
    assert person["supplier"] is None
    assert person["has_private_person_supplier"] is True
    assert "12345678901" not in str(result)
    assert "Pessoa Física" not in str(result)
    assert "0032026" not in str(result)


def test_ambiguous_fields_are_not_resolved_arbitrarily(tmp_path: Path):
    archive = tmp_path / "contratos.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_CONTRATOS.csv",
            "ANO;NUM_INSTRUMENTO_FORMATADO;NOM_ORGAO;NOME_FORNECEDOR;CPF_CNPJ;OBJETO;VALOR_CONTRATO\n"
            "2026;001/2026;SEC A;Empresa A;12345678000100;Objeto A;1000,00\n"
            "2026;001/2026;SEC B;Empresa B;99999999000100;Objeto B;1200,00\n",
        )

    profile = extract_contract_profiles(
        archive,
        target_year=2026,
        instrument_ids=["001/2026"],
        member="VW_CONTRATOS.csv",
    )["profiles"]["0012026"]

    assert profile["agency"] is None
    assert profile["agency_variants"] == 2
    assert profile["supplier"] is None
    assert profile["supplier_cnpj_variants"] == 2
    assert profile["object"] is None
    assert profile["object_variants"] == 2
    assert profile["contract_value"] is None
    assert profile["contract_value_status"] == "conflicting_official_values"
