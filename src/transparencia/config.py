from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CityConfig:
    slug: str
    name: str
    uf: str
    ibge_code: str
    municipality_cnpj: str | None = None

    @classmethod
    def from_path(cls, path: Path) -> "CityConfig":
        payload = json.loads(path.read_text(encoding="utf-8"))
        required = {"slug", "name", "uf", "ibge_code"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"configuração da cidade incompleta: {', '.join(missing)}")
        return cls(
            slug=str(payload["slug"]),
            name=str(payload["name"]),
            uf=str(payload["uf"]).upper(),
            ibge_code=str(payload["ibge_code"]),
            municipality_cnpj=(str(payload["municipality_cnpj"]) if payload.get("municipality_cnpj") else None),
        )


@dataclass(frozen=True)
class CityWorkspace:
    root: Path
    config: CityConfig
    sources: tuple[dict[str, str], ...]

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    @property
    def seed_dir(self) -> Path:
        return self.data_dir / "seed"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


def load_city(repo_root: Path, slug: str) -> CityWorkspace:
    city_root = repo_root / "cities" / slug
    if not city_root.is_dir():
        raise FileNotFoundError(f"cidade não encontrada: {slug} ({city_root})")
    config = CityConfig.from_path(city_root / "city.json")
    if config.slug != slug:
        raise ValueError(f"slug do diretório ({slug}) difere do city.json ({config.slug})")
    source_path = city_root / "sources.csv"
    sources: list[dict[str, str]] = []
    if source_path.exists():
        with source_path.open(encoding="utf-8", newline="") as handle:
            sources = list(csv.DictReader(handle))
    return CityWorkspace(city_root, config, tuple(sources))
