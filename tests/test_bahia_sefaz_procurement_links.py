from pathlib import Path
import zipfile

from transparencia.collectors.bahia_sefaz_procurement_links import extract_procurement_instrument_links


def test_extracts_only_exact_links_for_selected_year(tmp_path: Path):
    archive = tmp_path / "licitacoes.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(
            "VW_PROC_AQUISICAO_LIC_REQ.csv",
            "Processo de Aquisição;Ano da Aquisição\n"
            "PROC-1/2026;2026\n"
            "PROC-2/2026;2026\n"
            "PROC-3/2025;2025\n",
        )
        zf.writestr(
            "VW_PROC_AQUISICAO_ITEM_INSTRUMENTO.csv",
            "NUM_INST_FORMATADO;Processo_de_Aquisicao\n"
            "001/2026;PROC 1 2026\n"
            "002/2026;PROC-2/2026\n"
            "003/2025;PROC-3/2025\n"
            "999/2026;PROC-9/2026\n",
        )

    result = extract_procurement_instrument_links(archive, target_year=2026)
    assert result["primary_selected_rows"] == 2
    assert result["unique_processes_selected"] == 2
    assert result["exact_link_count"] == 2
    assert result["processes_with_instruments"] == 2
    assert result["unique_instruments"] == 2
    assert result["exact_links"] == [
        {"process_id": "PROC12026", "instrument_id": "0012026"},
        {"process_id": "PROC22026", "instrument_id": "0022026"},
    ]
    assert all(link["process_id"] != "PROC32025" for link in result["exact_links"])
    assert all(link["process_id"] != "PROC92026" for link in result["exact_links"])
