# operagent Phase 1 — CONTEXT (시방서)

> 결정 이력·제약. 세션 재개 시 PLAN·CHECKLIST와 함께 먼저 읽는다.

---

## 1. 한 줄

webhook-sink(Go 로거) → **Python(FastAPI) 진단 에이전트**. alert 받아 read-only 도구로 맥락 수집 → LLM 4블록 리포트 → Slack. 액션 0개.

---

## 2. 결정 이력

| 일자 | 결정 | 근거 |
|------|------|------|
| 2026-06-09 | 에이전트 방식 = 결정론 수집 → LLM 1회 종합 | 단순·예측가능·디버깅 쉬움. tool-use 루프는 Phase 3~4 |
| 2026-06-09 | 도구 = PromQL + Loki 2개 | 실제 가진 신호원. 배포이력은 로컬 docker엔 없어 보류 |
| 2026-06-09 | Anthropic + Slack 둘 다 실연동 | 사용자 키·토큰 준비됨 |
| 2026-06-09 | 모델 기본 `claude-opus-4-8` + env override | claude-api 스킬 지침(임의 다운그레이드 금지). 비용은 사용자 결정 → OPERAGENT_MODEL |
| 2026-06-09 | adaptive thinking + 스트리밍 | claude-api 스킬: 추론 작업·high max_tokens는 스트리밍 권장 |

---

## 3. 제약 (불변, 가드레일 유지)

- **read-only 도구만** — write 부작용 도구는 구현 안 함 (Phase 3 전까지)
- **LLM은 탐지 안 함** — 입력은 이미 발생한 alert
- **LangGraph 없음** — Phase 3~4
- **demo-service chaos를 에이전트가 호출하지 않음** — chaos는 데모 장치지 에이전트 도구 아님
- 외부 호출은 env + 동의 게이트 — `ANTHROPIC_API_KEY` 없으면 graceful (수집 사실만 Slack)

## 4. 정책 변경
(없음 — Phase 1 시작)

---

## 5. claude-api 핵심 (이번 구현 적용)
- Python SDK `anthropic`, `AsyncAnthropic()` (env `ANTHROPIC_API_KEY` 자동)
- 모델 ID `claude-opus-4-8` (날짜 suffix 금지). 비용 고려 시 `claude-sonnet-4-6`
- adaptive thinking: `thinking={"type":"adaptive"}` + `output_config={"effort":"high"}`
- 스트리밍: `async with client.messages.stream(...) as s: msg = await s.get_final_message()` (high max_tokens 타임아웃 방지)
- max_tokens 16000 (thinking 토큰 포함하므로 헤드룸)

## 6. 미해결·확인 필요
- [ ] **모델 = opus-4-8(기본) vs sonnet-4-6** (alert마다 호출 → 비용) ← 사용자 확인
- [ ] PyPI가 사내 네트워크에서 빌드 시 설치되는지
- [ ] Slack: Bot이 채널에 초대돼 있는지 (`not_in_channel` 함정 — feed-it §7.6)
- [ ] Alertmanager 재전송 dedup (fingerprint in-memory TTL)
