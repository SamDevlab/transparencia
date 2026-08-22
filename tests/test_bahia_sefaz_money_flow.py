from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_money_flow import (
    build_exact_money_flow,
    extract_payment_instrument_index,
)


def _payments_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_PAINEL_PAGAMENTO_NOTA_ORDEM_BANCARIA.csv",
            "Data do Pagamento;num_instrumento_formatado;Nº do Processo de Licitação/Inexigibilidade/Dispensa;Nº do Pagamento Formatado;Nº do Empenho;Nº da Liquidação;Valor do Pagamento;Recebedor;CPF/CNPJ Credor do Pagamento\n"
            "10/01/2026;001/2026;PROC-1/2026;PG-1;EMP-1;LIQ-1;100,00;Empresa A;12345678000100\n"
            "11/01/2026;001/2026;PROC-1/2026;PG-2;EMP-1;LIQ-2;50,00;Empresa A;12345678000100\n"
            "12/01/2026;002/2026;PROC-2/2026;PG-3;EMP-2;LIQ-3;200,00;Pessoa;12345678901\n"
            "12/01/2026;;PROC-9/2026;PG-4;EMP-9;LIQ-9;25,00;Sem instrumento;99999999000100\n"
            "12/01/2025;001/2026;PROC-1/2026;PG-5;EMP-1;LIQ-5;900,00;Empresa A;12345678000100\n",
        )


def _procurement_zip(path: Path) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_PROC_AQUISICAO_LIC_REQ.csv",
            "Processo de Aquisição;Ano da Aquisição\n"
            "PROC-1/2026;2026\n"
            "PROC-2/2026;2026\n"
            "PROC-3/2026;2026\n",
        )
        zf.writestr(
            "VW_PROC_AQUISICAO_ITEM_INSTRUMENTO.csv",
            "NUM_INST_FORMATADO;Processo_de_Aquisicao\n"
            "001/2026;PROC-1/2026\n"
            "002/2026;PROC-2/2026\n"
            "003/2026;PROC-3/2026\n",
        )


def test_payment_index_keeps_only_administrative_aggregates(tmp_path: Path):
    archive = tmp_path / "pagamentos.zip"
    _payments_zip(archive)
    result = extract_payment_instrument_index(archive, target_year=2026)
    assert result["selected_rows"] == 4
    assert result["selected_payment_value"] == 375.0
    assert result["rows_with_instrument"] == 3
    assert result["payment_value_with_instrument"] == 350.0
    assert result["unique_instruments"] == 2
    first = result["instrument_index"][0]
    assert first == {
        "instrument_id": "0012026",
        "payment_rows": 2,
        "payment_value": 150.0,
        "payment_ids": 2,
        "commitment_ids": 1,
        "liquidation_ids": 2,
        "process_ids": ["PROC12026"],
    }
    serialized = str(result)
    assert "Empresa A" not in serialized
    assert "12345678901" not in serialized
    assert "12345678000100" not in serialized
    assert "CPF" not in str(result["instrument_index"])


def test_builds_end_to_end_only_with_exact_official_instrument_ids(tmp_path: Path):
    payments = tmp_path / "pagamentos.zip"
    procurement = tmp_path / "licitacoes.zip"
    _payments_zip(payments)
    _procurement_zip(procurement)

    result = build_exact_money_flow(
        procurement,
        payments,
        ["001/2026", "002-2026", "999/2026"],
        target_year=2026,
    )
    summary = result["summary"]
    assert summary["procurement_instrument_exact_links"] == 3
    assert summary["contract_unique_instruments"] == 3
    assert summary["instruments_procurement_to_contract"] == 2
    assert summary["instruments_contract_to_payment"] == 2
    assert summary["instruments_end_to_end"] == 2
    assert summary["payment_value_linked_to_contracts"] == 350.0
    assert summary["payment_value_end_to_end"] == 350.0
    assert [row["instrument_id"] for row in result["top_end_to_end"]] == ["0022026", "0012026"]
    assert "identificador oficial" in result["identity_rule"]
    assert "similaridade textual" in result["identity_rule"]
