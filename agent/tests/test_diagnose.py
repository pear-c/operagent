import asyncio

from operagent import diagnose
from operagent.models import Alert, AlertmanagerPayload


def _alert(status="firing", fp="fp1", name="HighErrorRate"):
    return Alert.model_validate(
        {
            "status": status,
            "labels": {"alertname": name, "service": "demo-service", "severity": "critical"},
            "annotations": {"summary": "5xx 초과", "description": "5xx 40%"},
            "startsAt": "2026-06-09T07:37:59Z",
            "fingerprint": fp,
        }
    )


def test_gather_builds_context(monkeypatch):
    async def fake_value(query):
        return "0.408"

    async def fake_logs(logql, minutes=5, limit=50):
        return ["07:38 ERROR chaos injected error"]

    monkeypatch.setattr(diagnose.promql, "value_for", fake_value)
    monkeypatch.setattr(diagnose.loki, "query_range", fake_logs)

    ctx = asyncio.run(diagnose._gather(_alert()))
    assert "[ALERT]" in ctx and "HighErrorRate" in ctx
    assert "[METRICS]" in ctx and "0.408" in ctx
    assert "[LOGS]" in ctx and "chaos injected" in ctx


def test_dedup_skips_repeat(monkeypatch):
    calls = []

    async def fake_handle(alert):
        calls.append(alert.fingerprint)

    monkeypatch.setattr(diagnose, "_handle_alert", fake_handle)
    diagnose._seen.clear()

    payload = AlertmanagerPayload(alerts=[_alert(fp="dup"), _alert(fp="dup")])
    asyncio.run(diagnose.handle_payload(payload))
    assert calls == ["dup"]  # 같은 fingerprint:status 두 번째는 skip


def test_resolved_emits_without_llm(monkeypatch):
    emitted = {}

    async def fake_emit(header, report):
        emitted["header"] = header

    monkeypatch.setattr(diagnose, "_emit", fake_emit)
    asyncio.run(diagnose._handle_alert(_alert(status="resolved", fp="r1")))
    assert "resolved" in emitted["header"]
