from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_files import (
    summarize_sefaz_licitacoes_zip,
    summarize_sefaz_revenues,
)


def test_revenues_keep_budget_stages_separate(tmp_path: Path):
    file = tmp_path / "receitas.csv"
    file.write_text(
        "ANO EXERCICIO;MES EXERCICIO;ORGAO;NATUREZA RECEITA;VALOR PREVISTO;VALOR ATUALIZADO;VALOR ARRECADADO\n"
        "2025;12;SEC A;Impostos;100,00;120,00;90,00\n"
        "2026;1;SEC A;Impostos;200,00;220,00;180,00\n"
        "2026;2;SEC B;Taxas;50,00;60,00;55,00\n",
        encoding="utf-8",
    )
    result = summarize_sefaz_revenues(file, target_year=2026)
    assert result["rows"] == 3
    assert result["rows_by_year"] == {"2025": 1, "2026": 2}
    assert result["selected_year_totals"] == {
        "forecast": 250.0,
        "updated": 280.0,
        "realized": 235.0,
    }
    assert result["schema"]["detected_fields"]["realized"] == "VALOR ARRECADADO"
    assert result["top_agencies_by_realized"][0]["name"] == "SEC A"
    assert [row["month"] for row in result["selected_year_monthly"]] == ["2026-01", "2026-02"]


def test_revenues_missing_stage_is_not_fabricated_as_observed_field(tmp_path: Path):
    file = tmp_path / "receitas.csv"
    file.write_text(
        "EXERCICIO;ORGAO;VALOR ARRECADADO\n"
        "2026;SEC A;10,00\n",
        encoding="utf-8",
    )
    result = summarize_sefaz_revenues(file, target_year=2026)
    assert result["schema"]["detected_fields"]["forecast"] is None
    assert result["schema"]["detected_fields"]["updated"] is None
    assert result["selected_year_totals"]["realized"] == 10.0


def test_licitacoes_zip_summarizes_related_tables_without_republishing_people(tmp_path: Path):
    archive = tmp_path / "licitacoes.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "licitacoes.csv",
            "ANO;ORGAO;MODALIDADE;SITUACAO;VALOR HOMOLOGADO\n"
            "2026;SEC A;Pregão;Homologada;1000,00\n"
            "2026;SEC B;Dispensa;Homologada;500,00\n"
            "2025;SEC A;Pregão;Encerrada;250,00\n",
        )
        zf.writestr(
            "participantes.csv",
            "ANO;CNPJ;NOME PARTICIPANTE;ORGAO\n"
            "2026;12345678000100;Empresa A;SEC A\n"
            "2026;99999999000100;Empresa B;SEC A\n",
        )
        zf.writestr(
            "VW_PROC_AQUISICAO_ITEM.csv",
            "ITEM;VAL_ITEM_ESTIMADO\n"
            "1;100,00\n"
            "2;200,00\n",
        )

    result = summarize_sefaz_licitacoes_zip(archive, target_year=2026)
    assert result["archive"]["tabular_members"] == 3
    assert result["total_rows_across_related_tables"] == 7
    assert result["selected_rows_across_filterable_tables"] == 4
    assert result["unfilterable_related_rows"] == 2
    assert result["table_classes"]["licitacoes"] == 1
    assert result["table_classes"]["participantes"] == 1
    assert result["table_classes"]["itens"] == 1
    lic = next(table for table in result["tables"] if table["classification"] == "licitacoes")
    assert lic["top_modalities"][0] == {"name": "Pregão", "rows": 1}
    assert lic["value_field_sums"]["VALOR HOMOLOGADO"]["sum"] == 1500.0
    assert result["primary_licitacoes"]["rows_selected_year"] == 2
    assert result["primary_licitacoes"]["homologated_value"]["sum"] == 1500.0
    itens = next(table for table in result["tables"] if table["classification"] == "itens")
    assert itens["selected_rows"] is None
    assert itens["scope_status"] == "year_not_filterable"
    serialized = str(result)
    assert "12345678000100" not in serialized
    assert "Empresa A" not in serialized
    participants = next(table for table in result["tables"] if table["classification"] == "participantes")
    assert "CNPJ" in participants["schema"]["privacy_sensitive_columns_present"]
