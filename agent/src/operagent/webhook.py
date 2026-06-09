"""FastAPI webhook 리시버. Alertmanager가 여기로 POST한다.

★ Phase 0의 webhook-sink(Go 로거)를 대체하는 자리. 즉시 200 ack 후 비동기 진단.
"""

from __future__ import annotations

import logging

from fastapi import BackgroundTasks, FastAPI

from operagent.diagnose import handle_payload
from operagent.models import AlertmanagerPayload

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="operagent", version="0.1.0")


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(payload: AlertmanagerPayload, background: BackgroundTasks) -> dict[str, str]:
    # 즉시 200 ack → Alertmanager 재전송 방지. 진단은 백그라운드에서.
    background.add_task(handle_payload, payload)
    return {"status": "accepted", "alerts": str(len(payload.alerts))}
