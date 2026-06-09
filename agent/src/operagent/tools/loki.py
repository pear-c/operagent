"""Loki HTTP API 조회 (read-only). 로그를 변경하지 않는다."""

from __future__ import annotations

import time

import httpx

from operagent.config import settings


async def query_range(logql: str, minutes: int = 5, limit: int = 50) -> list[str]:
    """최근 N분 로그 라인을 최신순으로 반환. 실패 시 빈 리스트."""
    end_ns = int(time.time() * 1_000_000_000)
    start_ns = end_ns - minutes * 60 * 1_000_000_000
    url = f"{settings.loki_url}/loki/api/v1/query_range"
    params = {
        "query": logql,
        "start": str(start_ns),
        "end": str(end_ns),
        "limit": str(limit),
        "direction": "backward",
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError:
        return []

    lines: list[str] = []
    for stream in data.get("data", {}).get("result", []):
        for _ts, line in stream.get("values", []):
            lines.append(line)
    return lines
