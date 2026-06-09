from operagent.models import AlertmanagerPayload

SAMPLE = {
    "status": "firing",
    "receiver": "operagent",
    "groupLabels": {"alertname": "HighErrorRate"},
    "commonLabels": {
        "alertname": "HighErrorRate",
        "service": "demo-service",
        "severity": "critical",
    },
    "commonAnnotations": {"summary": "demo-service 5xx 에러율 10% 초과", "description": "5xx 40.82%"},
    "externalURL": "http://alertmanager:9093",
    "alerts": [
        {
            "status": "firing",
            "labels": {"alertname": "HighErrorRate", "service": "demo-service"},
            "annotations": {"summary": "demo-service 5xx 에러율 10% 초과"},
            "startsAt": "2026-06-09T07:37:59.197Z",
            "generatorURL": "http://prometheus:9090/graph?g0.expr=...",
            "fingerprint": "a486b5b835428f4e",
        }
    ],
}


def test_parse_payload():
    p = AlertmanagerPayload.model_validate(SAMPLE)
    assert p.status == "firing"
    assert p.common_labels["alertname"] == "HighErrorRate"
    assert len(p.alerts) == 1


def test_alert_fields_and_aliases():
    p = AlertmanagerPayload.model_validate(SAMPLE)
    alert = p.alerts[0]
    assert alert.alertname == "HighErrorRate"
    assert alert.service == "demo-service"
    assert alert.fingerprint == "a486b5b835428f4e"
    assert alert.starts_at == "2026-06-09T07:37:59.197Z"
    assert alert.generator_url.startswith("http://prometheus")


def test_empty_payload_defaults():
    p = AlertmanagerPayload.model_validate({})
    assert p.alerts == []
    assert p.common_labels == {}
