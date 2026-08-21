from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_finance import (
    summarize_sefaz_expenses_zip,
    summarize_sefaz_payments_zip,
)


def test_expenses_keep_commitment_liquidation_and_payment_separate(tmp_path: Path):
    archive = tmp_path / "despesas.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "despesas_principal.csv",
            "ANO EXERCICIO;ORGAO;FUNCAO;VALOR EMPENHADO;VALOR LIQUIDADO;VALOR PAGO;CNPJ CREDOR\n"
            "2026;SAUDE;Saúde;1000,00;800,00;700,00;12345678000100\n"
            "2026;EDUCACAO;Educação;500,00;400,00;350,00;99999999000100\n"
            "2025;SAUDE;Saúde;250,00;200,00;180,00;11111111000100\n",
        )
        zf.writestr(
            "despesas_auxiliar.csv",
            "CHAVE;VALOR EMPENHADO;VALOR LIQUIDADO;VALOR PAGO\n"
            "1;9999,00;9999,00;9999,00\n",
        )

    result = summarize_sefaz_expenses_zip(archive, target_year=2026)
    primary = result["primary_table"]
    assert primary["member"] == "despesas_principal.csv"
    assert primary["selected_rows"] == 2
    assert primary["stage_totals"]["committed"]["sum"] == 1500.0
    assert primary["stage_totals"]["liquidated"]["sum"] == 1200.0
    assert primary["stage_totals"]["paid"]["sum"] == 1050.0
    aux = next(row for row in result["tables"] if row["member"] == "despesas_auxiliar.csv")
    assert aux["selected_rows"] == 0
    serialized = str(result)
    assert "12345678000100" not in serialized
    assert "99999999000100" not in serialized


def test_payments_use_only_year_scoped_primary_table(tmp_path: Path):
    archive = tmp_path / "pagamentos.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "pagamentos_principal.csv",
            "ANO EXERCICIO;ORGAO;DATA PAGAMENTO;VALOR PAGAMENTO;CPF_CNPJ_FAVORECIDO\n"
            "2026;SAUDE;01/02/2026;100,00;12345678000100\n"
            "2026;EDUCACAO;02/02/2026;200,00;99999999000100\n"
            "2025;SAUDE;01/02/2025;50,00;11111111000100\n",
        )
        zf.writestr(
            "pagamentos_auxiliar.csv",
            "CHAVE;VALOR PAGAMENTO\n"
            "1;9999,00\n",
        )

    result = summarize_sefaz_payments_zip(archive, target_year=2026)
    primary = result["primary_table"]
    assert primary["member"] == "pagamentos_principal.csv"
    assert primary["selected_rows"] == 2
    assert result["selected_year_payment"] == {
        "source_field": "VALOR PAGAMENTO",
        "sum": 300.0,
        "numeric_rows": 2,
    }
    aux = next(row for row in result["tables"] if row["member"] == "pagamentos_auxiliar.csv")
    assert aux["selected_rows"] == 0
    serialized = str(result)
    assert "12345678000100" not in serialized
    assert "99999999000100" not in serialized
