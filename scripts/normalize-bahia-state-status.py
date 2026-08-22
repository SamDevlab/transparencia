#!/usr/bin/env python3
from __future__ import annotations

# Normalização leve: apenas metadados de cobertura; não baixa bases públicas novamente.
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = ROOT / "regions" / "bahia" / "data" / "state_transparency"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    latest_path = STATE_ROOT / "latest.json"
    latest = read_json(latest_path)
    snapshot = ROOT / latest["path"]
    coverage_path = snapshot / "coverage.json"
    coverage = read_json(coverage_path)

    sefaz = coverage.get("sefaz_data_summary") or latest.get("sefaz_data") or {}
    processed = int(sefaz.get("processed") or 0)
    expected = int(sefaz.get("expected") or 0)
    flow_processed = (coverage.get("money_flow") or {}).get("status") == "processed"

    if expected >= 5 and processed == expected:
        status = "complete_for_defined_collection"
        mode = "metadata_and_priority_data"
        note = (
            "As cinco bases prioritárias da SEFAZ/BA estão processadas e auditáveis: "
            "receitas, licitações, despesas, pagamentos e contratos. "
            + ("O fio do dinheiro por identificadores oficiais também está processado. " if flow_processed else "")
            + "TCE/BA permanece como fonte complementar com cobertura independente; sua indisponibilidade não rebaixa nem zera os dados SEFAZ."
        )
        coverage["status"] = status
        coverage["collection_mode"] = mode
        coverage["note"] = note
        latest["status"] = status
        latest["collection_mode"] = mode
        latest["sefaz_data"] = sefaz
        write_json(coverage_path, coverage)
        write_json(latest_path, latest)
        print(json.dumps({"status": status, "processed": processed, "expected": expected, "money_flow": flow_processed}))
        return 0

    print(json.dumps({"status": coverage.get("status"), "processed": processed, "expected": expected, "changed": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
