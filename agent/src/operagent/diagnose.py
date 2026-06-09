"""alert → read-only 수집 → LLM 종합 → Slack. 단순 도구 호출 루프(LangGraph 아님)."""

from __future__ import annotations

import logging

from operagent import llm, slack
from operagent.config import settings
from operagent.models import Alert, AlertmanagerPayload
from operagent.tools import loki, promql

logger = logging.getLogger("operagent")

# 알림명 → 진단 시 볼 PromQL (read-only, 스칼라 위주)
ALERT_QUERIES: dict[str, list[tuple[str, str]]] = {
    "HighErrorRate": [
        ("5xx 비율", 'sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))'),
        ("전체 요청률(req/s)", "sum(rate(http_requests_total[1m]))"),
    ],
    "HighLatencyP95": [
        ("p95 지연(s)", "histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[1m])))"),
        ("전체 요청률(req/s)", "sum(rate(http_requests_total[1m]))"),
    ],
    "HighHeapMemory": [
        ("heap_inuse(bytes)", 'go_memstats_heap_inuse_bytes{job="demo-service"}'),
        ("goroutines", 'go_goroutines{job="demo-service"}'),
    ],
}

GENERIC_QUERIES: list[tuple[str, str]] = [
    ("전체 요청률(req/s)", "sum(rate(http_requests_total[1m]))"),
    ("5xx 비율", 'sum(rate(http_requests_total{status=~"5.."}[1m])) / sum(rate(http_requests_total[1m]))'),
    ("heap_inuse(bytes)", 'go_memstats_heap_inuse_bytes{job="demo-service"}'),
]

# 재전송 dedup (프로세스 수명 동안). fingerprint+status 단위.
_seen: set[str] = set()


async def handle_payload(payload: AlertmanagerPayload) -> None:
    """webhook payload의 alert들을 순회 진단. 개별 실패가 전체를 죽이지 않게 격리."""
    for alert in payload.alerts:
        key = f"{alert.fingerprint}:{alert.status}"
        if alert.fingerprint and key in _seen:
            continue
        _seen.add(key)
        try:
            await _handle_alert(alert)
        except Exception:  # noqa: BLE001 — 진단 1건 실패가 다른 alert을 막지 않게
            logger.exception("진단 실패: alertname=%s fp=%s", alert.alertname, alert.fingerprint)


async def _handle_alert(alert: Alert) -> None:
    if alert.status == "resolved":
        await _emit(
            f"✅ {alert.alertname} · {alert.service or 'demo-service'} (resolved)",
            f"*{alert.alertname}* 이(가) 해제되었습니다 (resolved).",
        )
        return

    context = await _gather(alert)
    if settings.llm_enabled:
        try:
            report = await llm.synthesize(context)
        except Exception:  # noqa: BLE001 — LLM 실패 시 수집 사실만이라도 게시
            logger.exception("LLM 종합 실패 — 수집 사실만 게시")
            report = _facts_only(context)
    else:
        report = _facts_only(context)

    header = f"🚨 {alert.alertname} · {alert.service or 'demo-service'} ({alert.status})"
    await _emit(header, report)


async def _gather(alert: Alert) -> str:
    """read-only 도구로 alert 맥락(메트릭·로그)을 수집해 컨텍스트 문자열로 만든다."""
    lines: list[str] = ["[ALERT]"]
    lines.append(f"alertname={alert.alertname} service={alert.service} status={alert.status}")
    lines.append(f"severity={alert.labels.get('severity', '')}")
    lines.append(f"summary={alert.annotations.get('summary', '')}")
    lines.append(f"description={alert.annotations.get('description', '')}")
    lines.append(f"startsAt={alert.starts_at}")

    lines.append("\n[METRICS] (read-only PromQL 조회)")
    for label, query in ALERT_QUERIES.get(alert.alertname, GENERIC_QUERIES):
        value = await promql.value_for(query)
        lines.append(f"- {label}: {value if value is not None else 'N/A'}")

    lines.append("\n[LOGS] (최근 5분, demo-service)")
    logs = await loki.query_range('{service="demo-service"}', minutes=5, limit=30)
    if logs:
        lines.extend(logs[:30])
    else:
        lines.append("(로그 없음 또는 조회 실패)")

    return "\n".join(lines)


def _facts_only(context: str) -> str:
    """LLM 없이 수집한 사실만 보여주는 폴백 리포트."""
    return "_(LLM 비활성/실패 — 수집한 사실만 표시)_\n```\n" + context[:2500] + "\n```"


async def _emit(header: str, report: str) -> None:
    """Slack에 게시. 실패하거나 미설정이면 stdout 로그로 폴백(silent swallow 아님)."""
    if settings.slack_enabled:
        try:
            await slack.post_report(header, report)
            return
        except Exception:  # noqa: BLE001 — Slack 실패는 진단 자체를 죽이지 않음
            logger.exception("Slack 게시 실패 — stdout로 대체")
    logger.info("=== 진단 리포트 ===\n%s\n%s", header, report)
