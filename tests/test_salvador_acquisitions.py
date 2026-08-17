from transparencia.collectors.salvador_acquisitions import normalize, stable_source_key
from transparencia.config import CityConfig

CITY = CityConfig(slug="salvador", name="Salvador", uf="BA", ibge_code="2927408")


def test_stable_key_ignores_ephemeral_api_id():
    base = {
        "id": "first-uuid", "nuProcesso": "0393522026", "nuModalidadeSigef": "2026ML000002",
        "nuAquisicao": "0001722025", "cdUnidadeGestora": "246002", "dtPublicacao": "17/06/2026",
        "vlAquisicao": "2.079,00", "dsObjeto": "Aquisição de maquina fragmentadora de papel mínimo 24 folhas.",
    }
    changed = {**base, "id": "another-uuid"}
    assert stable_source_key(base) == stable_source_key(changed)


def test_normalize_acquisition_keeps_official_fields_and_provenance():
    row = {
        "id": "observed-id", "nuProcesso": "0330912026", "nuModalidadeSigef": "2026ML000011",
        "nuAquisicao": "0000012026", "cdUnidadeGestora": "240002", "dsUnidadeGestora": "CASA CIVIL",
        "cdOrgao": "24000", "dsOrgao": "Casa Civil", "sgOrgao": "CASA CIVIL",
        "cdModalidadeLicitacao": "5", "dsModalidadeLicitacao": "Dispensa de Licitação",
        "dsTipoAquisica": "DISPENSA", "dsFundamentacaoCompraDireta": "Inciso II",
        "dtPublicacao": "09/04/2026", "dtAquisicao": "09/04/2026", "nuDom": "9245",
        "vlAquisicao": "18.090,86", "dsObjeto": "Aquisição de mobiliário",
    }
    out = normalize(row, CITY, observed_at="2026-08-17T00:00:00Z", snapshot_sha256="abc")
    assert out["process_number"] == "0330912026"
    assert out["modality_id"] == 5
    assert out["acquisition_type"] == "DISPENSA"
    assert out["published_at"] == "2026-04-09"
    assert out["acquisition_value"] == 18090.86
    assert out["source_record_id_observed"] == "observed-id"
    assert out["snapshot_sha256"] == "abc"
