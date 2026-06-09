# operagent Phase 1 — read-only 진단 코파일럿 (PLAN)

> 설계도. webhook-sink(Go 로거)를 Python 에이전트로 교체.
> 오버레이: `.claude/rules/projects/operagent/`

---

## 1. 목표

alert webhook을 받아 **read-only 도구(PromQL·LogQL)로 맥락을 자동 수집**하고, **LLM 1회 호출로 "상황/원인 가설 A·B/근거/다음 확인할 것" 4블록 리포트를 만들어 Slack에 게시**한다. **액션 0개.**

완료 기준: `make chaos-errors` → alert → 에이전트가 메트릭·로그를 긁어 4블록 진단을 Slack에 올린다. write 액션 없음.

---

## 2. 범위

### 만든다 (`agent/`, Python)
- FastAPI webhook 리시버 (`POST /webhook`, 즉시 200 ack + 비동기 진단)
- read-only 도구 2개: PromQL 조회, LogQL 조회
- 결정론 수집 → LLM 1회 종합 (단순 도구루프, **LangGraph 아님**)
- Slack 게시 (chat.postMessage)
- docker-compose에서 webhook-sink → operagent 교체, alertmanager가 operagent로 webhook

### 안 만든다 (Phase 2+)
- write 도구·승인·감사로그 (Phase 3)
- RAG / ChromaDB (Phase 2)
- LangGraph (Phase 3~4)
- 배포 이력 도구 (로컬 docker엔 배포 시스템 없음 — 보류)
- Claude tool-use 루프 (지금은 결정론 수집)

---

## 3. 아키텍처

```
alertmanager ─POST /webhook─▶ operagent (FastAPI)
                               1. 200 ack 즉시 (재전송 방지)
                               2. 비동기 진단 (BackgroundTask):
                                  ├─ 알림별 PromQL 매핑 조회 (read-only)
                                  │   HighErrorRate→에러율·5xx추이 / HighLatencyP95→p95 / HighHeapMemory→heap·goroutines
                                  ├─ LogQL 조회: {service="demo-service"} 최근 5분 (에러 우선)
                                  ├─ 컨텍스트 조립 (alert + 메트릭값 + 로그라인)
                                  └─ LLM 1회 (claude-opus-4-8, adaptive thinking) → 4블록 리포트
                               3. Slack chat.postMessage (Block Kit)
```

### 4블록 리포트 (conventions §4.3)
1. 상황 — 어떤 alert이 언제, 어떤 서비스에
2. 원인 가설 — A/B (단정 금지, 가설로)
3. 근거 — 각 가설을 뒷받침하는 메트릭·로그 인용
4. 다음 확인할 것 — 사람이 이어서 볼 것 (액션 아님)

---

## 4. 파일 트리 (agent/)

```
agent/
├─ pyproject.toml              operagent 패키지 (src layout)
├─ Dockerfile                  python:3.12-slim, pip install
├─ .env.example                ANTHROPIC_API_KEY · SLACK_BOT_TOKEN · SLACK_CHANNEL_ID · PROMETHEUS_URL · LOKI_URL · OPERAGENT_MODEL
├─ src/operagent/
│  ├─ __init__.py
│  ├─ config.py                env 로딩 (pydantic-settings)
│  ├─ webhook.py               FastAPI app: POST /webhook → 200 ack → 비동기 진단
│  ├─ models.py                AlertmanagerPayload / Alert (Pydantic)
│  ├─ diagnose.py              gather(promql+loki) → llm → slack 오케스트레이션
│  ├─ tools/
│  │  ├─ __init__.py
│  │  ├─ promql.py             Prometheus HTTP API 조회 (read-only)
│  │  └─ loki.py               Loki HTTP API 조회 (read-only)
│  ├─ llm.py                   Anthropic 호출 → 4블록 리포트 (adaptive thinking)
│  └─ slack.py                 chat.postMessage
└─ tests/
   ├─ test_alert_parsing.py    Alertmanager payload 파싱
   └─ test_diagnose.py         결정론 수집 (LLM·Slack mock)
```

---

## 5. 구현 순서 (각 단계 검증 후)

| Step | 산출물 | 검증 |
|------|--------|------|
| 1 | 패키지 골격 + config + models (Alertmanager payload) | pytest 파싱 |
| 2 | read-only 도구 (promql/loki) | 떠있는 스택에 직접 조회 |
| 3 | llm.py (4블록, opus-4-8, adaptive thinking, 스트리밍) | 키 있으면 1회 호출 |
| 4 | slack.py (chat.postMessage) | 테스트 메시지 게시 |
| 5 | webhook.py + diagnose.py 오케스트레이션 | 로컬 mock webhook |
| 6 | Dockerfile + docker-compose 교체 (webhook-sink→operagent) | up |
| 7 | E2E: chaos-errors → 4블록 Slack | 완료 기준 |

---

## 6. 기술 결정 (확정 필요)

- **에이전트 방식**: 결정론 수집 → LLM 1회 종합 (사용자 결정)
- **도구**: PromQL + Loki 2개 (사용자 결정)
- **외부 자격**: Anthropic + Slack 둘 다 실연동 (사용자 결정)
- **모델**: `claude-opus-4-8` 기본 (claude-api 스킬 지침) — **env `OPERAGENT_MODEL`로 교체 가능**. alert마다 호출되므로 비용 고려 시 `claude-sonnet-4-6`(40% 저렴) 선택지. ← 사용자 확인 항목
- **추론**: adaptive thinking + effort high, max_tokens 16000 + 스트리밍(타임아웃 방지)
- **HTTP**: httpx (async). Slack도 httpx로 chat.postMessage (slack_sdk 미사용 — 경량)
- **가드레일**: read-only 도구만, write 0개, LangGraph 0

---

## 7. 위험·미해결
- Python 의존성 PyPI 설치가 사내 네트워크에서 되는지 (proxy.golang.org은 막혔음 — PyPI는 빌드 시 확인)
- Alertmanager 재전송 시 중복 진단 → alert fingerprint로 dedup (간단 in-memory set, TTL)
- LLM 호출 실패 시 graceful → 수집한 사실만이라도 Slack에 (conventions §2.2 graceful)
