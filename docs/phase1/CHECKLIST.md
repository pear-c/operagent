# operagent Phase 1 — CHECKLIST (공정표)

> 2026-06-09 구현 완료. agent/(Python FastAPI) 가 webhook-sink를 교체.

---

## 작성 완료 (코드)
- [x] Step 1 패키지 골격 — pyproject(src layout) + config(env) + models(Alertmanager payload) + .env.example
- [x] Step 2 read-only 도구 — tools/promql.py(instant query) + tools/loki.py(range query)
- [x] Step 3 LLM — llm.py(AsyncAnthropic, claude-opus-4-8 env override, adaptive thinking, 스트리밍, 4블록 시스템 프롬프트)
- [x] Step 4 Slack — slack.py(chat.postMessage, Block Kit, 2900자 청크)
- [x] Step 5 오케스트레이션 — webhook.py(즉시 200 ack + BackgroundTask) + diagnose.py(gather→llm→slack + fingerprint dedup + graceful)
- [x] Step 6 컨테이너 — agent/Dockerfile(python:3.12-slim) + compose webhook-sink→operagent + alertmanager 라우팅 → operagent:9000/webhook
- [x] pytest 6건 통과 (파싱 3 + diagnose 3) / app import 스모크 / compose config 유효

## 런타임 검증 — 2026-06-09
- [x] operagent 빌드(컨테이너 pip install) + Up + /healthz ok
- [x] chaos-errors → alert → `POST /webhook 200` → operagent 진단 생성
- [x] **read-only 수집 동작**: PromQL 5xx 비율 0.44·15 req/s + Loki 실제 chaos 에러 로그 라인
- [x] graceful: 키 없을 때 수집 사실만 stdout 게시
- [ ] **LLM+Slack 실연동** — 사용자 `.env`(ANTHROPIC_API_KEY·SLACK_*) 필요 → claude-opus-4-8 4블록 → Slack. (코드 경로 검증 완료, 실 키 E2E는 사용자)
- [ ] chaos-latency / chaos-memory 진단 (기제 동일, 사용자 확인 권장)

---

## VERIFY 게이트
- [x] 게이트 1 Lint: app import 스모크 / gofmt 대응 = pytest
- [x] 게이트 2 Type: import 로드 성공 / pydantic 검증
- [x] 게이트 3 Policy: read-only 도구만(write 0) · LangGraph 0 · 탐지 로직 0 · 시크릿 평문 0(.env gitignore)
- [x] 게이트 4 Build: docker compose up operagent 성공
- [x] 게이트 5 Scope: Phase 1 범위 (RAG·승인·write 선반영 없음)

---

## 함정 발견 (conventions §7.10 박제)
- alertmanager가 **config 변경을 자동 reload 안 함** — alertmanager.yml 수정 후 `docker compose restart alertmanager` 필요. 안 하면 옛 receiver(webhook-sink) 호출 → `no such host`
- compose에서 서비스 제거 시 **orphan 컨테이너가 포트 점유** — `docker compose up --remove-orphans`로 정리

## 다음
- LLM+Slack 실연동 확인 후 → Phase 2 (RAG: 런북·회고를 BGE-M3+ChromaDB로 그라운딩)
