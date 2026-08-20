from __future__ import annotations

import math
import time
from dataclasses import dataclass
from typing import Any, Iterable

import httpx

COMEX_API_BASE = "https://api-comexstat.mdic.gov.br"
RETRYABLE = {429, 500, 502, 503, 504}


class ComexStatError(RuntimeError):
    """Falha explícita de consulta ao Comex Stat."""


def _number(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(" ", "")
    if not text:
        return 0.0
    # A API normalmente devolve número JSON. Este fallback evita quebrar em
    # representações textuais sem interpretar pontos de milhar de forma cega.
    try:
        return float(text)
    except ValueError:
        if text.count(",") == 1 and text.count(".") == 0:
            try:
                return float(text.replace(",", "."))
            except ValueError:
                return 0.0
        return 0.0


def unwrap_list(payload: Any) -> list[dict[str, Any]]:
    """Extrai somente linhas de dados sem presumir ausência quando a estrutura muda."""
    if not isinstance(payload, dict):
        raise ComexStatError("Resposta do Comex Stat não é um objeto JSON")
    data = payload.get("data")
    if isinstance(data, dict):
        rows = data.get("list")
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    rows = payload.get("list")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    if payload.get("success") is False:
        raise ComexStatError(str(payload.get("message") or "Comex Stat informou falha"))
    raise ComexStatError("Resposta do Comex Stat não contém data.list")


def metric(row: dict[str, Any], key: str = "metricFOB") -> float:
    return _number(row.get(key))


def _code(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def _label(row: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return "Não informado"


def _month_key(row: dict[str, Any]) -> str:
    year = _code(row, "year", "coYear", "CO_ANO")
    month = _code(row, "monthNumber", "month", "coMonth", "CO_MES")
    if month.isdigit():
        month = month.zfill(2)
    return f"{year}-{month}" if year and month else year or month or "não informado"


def _heading(row: dict[str, Any]) -> tuple[str, str]:
    code = _code(row, "headingCode", "heading_code", "sh4", "SH4", "coHeading")
    label = _label(row, "heading", "headingName", "heading_name", "sh4Name", "description")
    # Algumas respostas trazem apenas o texto em `heading`. Se começar por 4 dígitos,
    # preservamos esse código como SH4 sem inventar uma classificação.
    if not code:
        raw = str(row.get("heading") or "").strip()
        prefix = raw[:4]
        if len(prefix) == 4 and prefix.isdigit():
            code = prefix
    return code, label


def _country(row: dict[str, Any]) -> tuple[str, str]:
    return (
        _code(row, "countryCode", "country_code", "coCountry", "CO_PAIS"),
        _label(row, "country", "countryName", "country_name"),
    )


def summarize_flows(export_rows: Iterable[dict[str, Any]], import_rows: Iterable[dict[str, Any]]) -> dict[str, float]:
    exports = sum(metric(row) for row in export_rows)
    imports = sum(metric(row) for row in import_rows)
    return {
        "exports_fob": exports,
        "imports_fob": imports,
        "trade_flow_fob": exports + imports,
        "balance_fob": exports - imports,
    }


def aggregate_monthly(export_rows: Iterable[dict[str, Any]], import_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, float]] = {}
    for flow, rows in (("exports_fob", export_rows), ("imports_fob", import_rows)):
        for row in rows:
            key = _month_key(row)
            item = values.setdefault(key, {"exports_fob": 0.0, "imports_fob": 0.0})
            item[flow] += metric(row)
    result = []
    for month, item in values.items():
        result.append({
            "month": month,
            **item,
            "trade_flow_fob": item["exports_fob"] + item["imports_fob"],
            "balance_fob": item["exports_fob"] - item["imports_fob"],
        })
    return sorted(result, key=lambda row: row["month"])


def aggregate_countries(export_rows: Iterable[dict[str, Any]], import_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for flow, rows in (("exports_fob", export_rows), ("imports_fob", import_rows)):
        for row in rows:
            code, label = _country(row)
            key = code or label
            item = values.setdefault(key, {"country_code": code, "country": label, "exports_fob": 0.0, "imports_fob": 0.0})
            item[flow] += metric(row)
    total_exports = sum(item["exports_fob"] for item in values.values())
    total_imports = sum(item["imports_fob"] for item in values.values())
    result = []
    for item in values.values():
        exports = item["exports_fob"]
        imports = item["imports_fob"]
        result.append({
            **item,
            "balance_fob": exports - imports,
            "export_share": exports / total_exports if total_exports else 0.0,
            "import_share": imports / total_imports if total_imports else 0.0,
        })
    return sorted(result, key=lambda row: row["exports_fob"] + row["imports_fob"], reverse=True)


def aggregate_products(export_rows: Iterable[dict[str, Any]], import_rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    products: dict[str, dict[str, Any]] = {}

    def add(rows: Iterable[dict[str, Any]], flow: str) -> None:
        for row in rows:
            code, label = _heading(row)
            key = code or label
            product = products.setdefault(key, {
                "sh4": code,
                "product": label,
                "exports_fob": 0.0,
                "imports_fob": 0.0,
                "export_kg": 0.0,
                "import_kg": 0.0,
                "export_countries": {},
                "import_countries": {},
            })
            value = metric(row)
            kg = metric(row, "metricKG")
            product[f"{flow}_fob"] += value
            product[f"{flow}_kg"] += kg
            country_code, country_label = _country(row)
            country_key = country_code or country_label
            if country_key:
                bucket = product[f"{flow}_countries"]
                current = bucket.get(country_key) or {"country_code": country_code, "country": country_label, "fob": 0.0}
                current["fob"] += value
                bucket[country_key] = current

    add(export_rows, "export")
    add(import_rows, "import")
    total_exports = sum(item["exports_fob"] for item in products.values())
    total_imports = sum(item["imports_fob"] for item in products.values())
    result = []
    for product in products.values():
        exports = product.pop("export_countries")
        imports = product.pop("import_countries")
        export_partners = sorted(exports.values(), key=lambda row: row["fob"], reverse=True)
        import_partners = sorted(imports.values(), key=lambda row: row["fob"], reverse=True)
        import_total = product["imports_fob"]
        import_shares = [row["fob"] / import_total for row in import_partners] if import_total else []
        result.append({
            **product,
            "balance_fob": product["exports_fob"] - product["imports_fob"],
            "export_share": product["exports_fob"] / total_exports if total_exports else 0.0,
            "import_share": product["imports_fob"] / total_imports if total_imports else 0.0,
            "top_export_country": export_partners[0] if export_partners else None,
            "top_import_country": import_partners[0] if import_partners else None,
            "import_country_top_share": import_shares[0] if import_shares else 0.0,
            "import_country_hhi": sum(share * share for share in import_shares),
        })
    return sorted(result, key=lambda row: row["exports_fob"] + row["imports_fob"], reverse=True)


def _scaled_log(value: float, reference: float) -> float:
    if value <= 0 or reference <= 0:
        return 0.0
    return min(1.0, math.log1p(value) / math.log1p(reference))


def productive_screening_score(
    *,
    imports_fob: float,
    exports_fob: float,
    import_growth: float | None,
    import_country_top_share: float,
    import_scale_reference: float,
) -> dict[str, Any]:
    """Heurística explicável de triagem; não é recomendação econômica."""
    imports_fob = max(0.0, float(imports_fob or 0))
    exports_fob = max(0.0, float(exports_fob or 0))
    deficit = max(0.0, imports_fob - exports_fob)
    scale = 30.0 * _scaled_log(imports_fob, max(import_scale_reference, imports_fob))
    deficit_ratio = deficit / imports_fob if imports_fob else 0.0
    deficit_score = 25.0 * min(1.0, deficit_ratio)
    if import_growth is None:
        growth_score = 0.0
    else:
        growth_score = 15.0 * min(1.0, max(0.0, float(import_growth)) / 0.5)
    concentration_score = 15.0 * min(1.0, max(0.0, float(import_country_top_share)))
    related_capacity_score = 15.0 if exports_fob > 0 else 0.0
    total = round(min(100.0, scale + deficit_score + growth_score + concentration_score + related_capacity_score), 2)
    if total >= 70:
        label = "triagem_alta"
    elif total >= 45:
        label = "triagem_media"
    else:
        label = "triagem_baixa"
    return {
        "score": total,
        "label": label,
        "components": {
            "import_scale": round(scale, 2),
            "trade_deficit": round(deficit_score, 2),
            "import_growth": round(growth_score, 2),
            "country_concentration": round(concentration_score, 2),
            "related_export_capacity": round(related_capacity_score, 2),
        },
        "inputs": {
            "imports_fob": imports_fob,
            "exports_fob": exports_fob,
            "deficit_fob": deficit,
            "import_growth": import_growth,
            "import_country_top_share": import_country_top_share,
        },
        "interpretation": "Prioridade para estudo econômico adicional; não é recomendação de investimento, substituição de importações ou política industrial.",
    }


def attach_yoy_and_screening(current: list[dict[str, Any]], previous: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_by_key = {(row.get("sh4") or row.get("product")): row for row in previous}
    max_imports = max((float(row.get("imports_fob") or 0) for row in current), default=0.0)
    result = []
    for row in current:
        key = row.get("sh4") or row.get("product")
        old = previous_by_key.get(key) or {}
        old_imports = float(old.get("imports_fob") or 0)
        new_imports = float(row.get("imports_fob") or 0)
        growth = None if old_imports <= 0 else (new_imports - old_imports) / old_imports
        screening = productive_screening_score(
            imports_fob=new_imports,
            exports_fob=float(row.get("exports_fob") or 0),
            import_growth=growth,
            import_country_top_share=float(row.get("import_country_top_share") or 0),
            import_scale_reference=max_imports or 1.0,
        )
        result.append({**row, "previous_imports_fob": old_imports, "import_growth_yoy": growth, "screening": screening})
    return sorted(result, key=lambda row: row["screening"]["score"], reverse=True)


@dataclass(frozen=True)
class LastUpdate:
    year: int
    month: int
    updated: str | None = None


class ComexStatClient:
    def __init__(self, client: httpx.Client | None = None, *, max_retries: int = 4, timeout: float = 90.0):
        self._owns_client = client is None
        self.client = client or httpx.Client(
            base_url=COMEX_API_BASE,
            headers={"Accept": "application/json", "User-Agent": "transparencia-municipal/0.3"},
            timeout=timeout,
            follow_redirects=True,
        )
        self.max_retries = max_retries

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def __enter__(self) -> "ComexStatClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        response: httpx.Response | None = None
        for attempt in range(self.max_retries + 1):
            response = self.client.request(method, path, **kwargs)
            if response.status_code not in RETRYABLE:
                response.raise_for_status()
                return response
            if attempt >= self.max_retries:
                break
            retry_after = response.headers.get("retry-after")
            try:
                delay = float(retry_after) if retry_after else min(2 ** (attempt + 1), 20)
            except ValueError:
                delay = min(2 ** (attempt + 1), 20)
            time.sleep(max(0.5, min(delay, 30.0)))
        assert response is not None
        raise ComexStatError(f"Comex Stat respondeu HTTP {response.status_code} após retentativas")

    def get_last_update(self, scope: str = "general") -> LastUpdate:
        if scope not in {"general", "cities"}:
            raise ValueError("scope deve ser 'general' ou 'cities'")
        response = self._request("GET", f"/{scope}/dates/updated")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise ComexStatError("Comex Stat não informou data de atualização")
        try:
            return LastUpdate(year=int(data["year"]), month=int(data["monthNumber"]), updated=data.get("updated"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ComexStatError("Campos year/monthNumber ausentes na atualização do Comex Stat") from exc

    @staticmethod
    def query_body(
        *, flow: str, start: str, end: str, filters: list[dict[str, Any]], details: list[str] | None = None,
        month_detail: bool = True,
    ) -> dict[str, Any]:
        if flow not in {"export", "import"}:
            raise ValueError("flow deve ser export ou import")
        return {
            "flow": flow,
            "monthDetail": month_detail,
            "period": {"from": start, "to": end},
            "filters": filters,
            "details": details or ["country", "heading"],
            "metrics": ["metricFOB", "metricKG"],
        }

    def query_general(self, **kwargs: Any) -> tuple[dict[str, Any], httpx.Response]:
        body = self.query_body(**kwargs)
        response = self._request("POST", "/general", params={"language": "pt"}, json=body)
        return response.json(), response

    def query_cities(self, **kwargs: Any) -> tuple[dict[str, Any], httpx.Response]:
        body = self.query_body(**kwargs)
        response = self._request("POST", "/cities", params={"language": "pt"}, json=body)
        return response.json(), response

    def get_hs_headings(self, *, per_page: int = 500) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        page = 1
        while True:
            response = self._request("GET", "/tables/hs", params={"language": "pt", "page": page, "perPage": per_page})
            payload = response.json()
            batch = unwrap_list(payload)
            rows.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
            if page > 100:
                raise ComexStatError("Paginação da tabela SH excedeu o limite de segurança")
        return rows
