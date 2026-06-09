"""Prometheus HTTP API 조회 (read-only). 메트릭을 변경하지 않는다."""

from __future__ import annotations

import httpx

from operagent.config import settings


async def query_instant(promql: str) -> dict:
    """instant query. Prometheus /api/v1/query 호출."""
    url = f"{settings.prometheus_url}/api/v1/query"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params={"query": promql})
        resp.raise_for_status()
        return resp.json()


def first_value(result: dict) -> str | None:
    """instant query 결과에서 첫 스칼라 값을 꺼낸다(없으면 None)."""
    try:
        series = result["data"]["result"]
        if not series:
            return None
        return series[0]["value"][1]
    except (KeyError, IndexError, TypeError):
        return None


async def value_for(promql: str) -> str | None:
    """PromQL 한 줄을 던지고 첫 값을 문자열로 받는다. 실패 시 None."""
    try:
        return first_value(await query_instant(promql))
    except httpx.HTTPError:
        return None
