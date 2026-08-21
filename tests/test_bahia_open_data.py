from pathlib import Path

from transparencia.collectors.bahia_open_data import (
    normalize_ckan_package,
    summarize_hash_csv,
    summarize_tce_expenses,
)


def test_normalize_ckan_package_keeps_only_public_metadata():
    payload = {
        "success": True,
        "result": {
            "id": "abc",
            "name": "despesas",
            "title": "Despesas",
            "notes": "Dados do FIPLAN",
            "metadata_created": "2026-01-01",
            "metadata_modified": "2026-08-20",
            "organization": {"title": "SEFAZ"},
            "resources": [
                {
                    "id": "r1",
                    "name": "Despesas.zip",
                    "format": "ZIP",
                    "mimetype": "application/zip",
                    "url": "https://example.test/despesas.zip",
                    "size": 123,
                    "hash": "abc123",
                    "last_modified": "2026-08-20",
                    "metadata_modified": "2026-08-20",
                    "state": "active",
                    "ignored": "não deve vazar para o catálogo",
                }
            ],
        },
    }
    result = normalize_ckan_package(payload)
    assert result["name"] == "despesas"
    assert result["organization"] == "SEFAZ"
    assert result["resources"] == [{
        "id": "r1",
        "name": "Despesas.zip",
        "format": "ZIP",
        "mimetype": "application/zip",
        "url": "https://example.test/despesas.zip",
        "size": 123,
        "hash": "abc123",
        "last_modified": "2026-08-20",
        "metadata_modified": "2026-08-20",
        "state": "active",
    }]


def test_summarize_tce_expenses_separates_commitment_and_payment(tmp_path: Path):
    file = tmp_path / "despesas.csv"
    file.write_text(
        "SECRETARIA/ÓRGÃO;NOME DO CREDOR;VALOR DO EMPENHO;PAGAMENTO COM RETENÇÕES;PAGAMENTO LÍQUIDO AO CREDOR\n"
        "SAUDE;Fornecedor A;1.000,00;800,00;750,00\n"
        "SAUDE;Fornecedor B;500,00;500,00;475,00\n"
        "EDUCACAO;Fornecedor A;200,00;100,00;95,00\n",
        encoding="utf-8",
    )
    result = summarize_tce_expenses(file)
    assert result["totals"] == {
        "rows": 3,
        "committed": 1700.0,
        "gross_paid": 1400.0,
        "net_paid": 1320.0,
    }
    assert result["by_agency"][0]["agency"] == "SAUDE"
    assert result["by_agency"][0]["gross_paid"] == 1300.0
    assert result["by_creditor"][0]["creditor"] == "Fornecedor A"


def test_hash_csv_does_not_persist_raw_rows_or_documents(tmp_path: Path):
    file = tmp_path / "contratos.csv"
    file.write_text(
        "ÓRGÃO CONTRATANTE#CNPJ#CONTRATADO#VALOR ATUAL\n"
        "SEC A#12345678000100#Empresa A#1.000,00\n"
        "SEC A#99999999000100#Empresa B#500,00\n"
        "SEC B#11111111000100#Empresa C#250,00\n",
        encoding="utf-8",
    )
    result = summarize_hash_csv(file, value_headers=("VALOR ATUAL",))
    assert result["rows"] == 3
    assert result["declared_value_sum"] == 1750.0
    assert result["top_agencies_by_rows"][0] == {"agency": "SEC A", "rows": 2}
    serialized = str(result)
    assert "12345678000100" not in serialized
    assert "Empresa A" not in serialized
    assert "sample" not in result
