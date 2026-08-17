from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .collectors.pages import collect_known_pages
from .collectors.pncp import collect as collect_pncp
from .collectors.pncp_contracts import agency_cnpjs_from_procurements, collect as collect_pncp_contracts
from .config import load_city
from .db import build
from .salvador_project import run_salvador_project


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="transparencia")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--city", required=True, help="slug em cities/<slug>")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sources")
    p_pages = sub.add_parser("collect-pages")
    p_pages.add_argument("--out", type=Path)
    p_pncp = sub.add_parser("collect-pncp")
    p_pncp.add_argument("--start", type=parse_date, required=True)
    p_pncp.add_argument("--end", type=parse_date, required=True)
    p_pncp.add_argument("--scope", choices=["executivo", "legislativo", "municipal"], default="executivo")
    p_pncp.add_argument("--out", type=Path)
    p_contracts = sub.add_parser("collect-pncp-contracts")
    p_contracts.add_argument("--start", type=parse_date, required=True)
    p_contracts.add_argument("--end", type=parse_date, required=True)
    p_contracts.add_argument("--scope", choices=["executivo", "legislativo", "municipal"], default="executivo")
    p_contracts.add_argument("--from-procurements", type=Path, action="append", default=[])
    p_contracts.add_argument("--agency-cnpj", action="append", default=[])
    p_contracts.add_argument("--out", type=Path)
    p_db = sub.add_parser("build-db")
    p_db.add_argument("--db", type=Path)
    p_db.add_argument("--pncp", type=Path, action="append", default=[])
    p_db.add_argument("--contracts", type=Path, action="append", default=[])

    p_salvador = sub.add_parser("collect-salvador", help="pipeline de produção auditável de Salvador")
    p_salvador.add_argument("--start", type=parse_date, required=True)
    p_salvador.add_argument("--end", type=parse_date, required=True)
    p_salvador.add_argument("--out", type=Path)
    p_salvador.add_argument("--skip-pncp", action="store_true", help="não consulta o PNCP nesta execução")
    p_salvador.add_argument("--skip-cms-auxiliary", action="store_true", help="não coleta viagens/documentos/certames auxiliares da CMS")

    args = parser.parse_args()
    ws = load_city(args.repo_root, args.city)
    if args.command == "sources":
        print(json.dumps(ws.sources, ensure_ascii=False, indent=2))
    elif args.command == "collect-pages":
        print(json.dumps(collect_known_pages(ws.sources, args.out or ws.raw_dir / "pages"), ensure_ascii=False, indent=2))
    elif args.command == "collect-pncp":
        print(collect_pncp(ws.config, args.start, args.end, args.out or ws.raw_dir / "pncp", scope=args.scope))
    elif args.command == "collect-pncp-contracts":
        cnpjs = set(args.agency_cnpj)
        cnpjs.update(agency_cnpjs_from_procurements(args.from_procurements))
        if ws.config.municipality_cnpj:
            cnpjs.add(ws.config.municipality_cnpj)
        print(collect_pncp_contracts(ws.config, args.start, args.end, args.out or ws.raw_dir / "pncp_contracts", agency_cnpjs=cnpjs, scope=args.scope))
    elif args.command == "build-db":
        target = args.db or ws.data_dir / f"{ws.config.slug}.db"
        build(target, ws, args.pncp, args.contracts)
        print(target)
    elif args.command == "collect-salvador":
        if args.city != "salvador":
            parser.error("collect-salvador requires --city salvador")
        target = args.out or ws.data_dir / "runs" / args.end.isoformat()
        report = run_salvador_project(
            args.repo_root,
            start=args.start,
            end=args.end,
            out_dir=target,
            include_pncp=not args.skip_pncp,
            include_cms_auxiliary=not args.skip_cms_auxiliary,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
