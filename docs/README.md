# operagent 진행 문서

> 프로젝트 진행 기억. Phase별 PLAN(설계)·CONTEXT(결정·함정)·CHECKLIST(공정·검증)을 둔다.
> (워크스페이스의 Claude 오버레이 가드레일은 이 레포 밖 `.claude/rules/projects/operagent/`에 있으며 클론엔 따라오지 않는다 — 이 문서들은 그 진행 스냅샷.)

## 프로젝트 한 줄

operagent = 이미 발생한 alert을 받아 사람 대신 진단(triage→맥락수집→진단→대응제안→소통)하는 webhook 리시버형 LLM 운영 에이전트. 탐지는 LLM이 하지 않는다(Prometheus/Alertmanager가 탐지). MVP는 read-only.

## 3대 설계 축 (불변)
1. LLM에게 **탐지를 시키지 않는다** — 입력은 이미 발생한 alert
2. **Read/Write 칼분리** — MVP는 read-only, write는 단계적 개방(Phase 3 화이트리스트+승인+감사로그)
3. **멀티에이전트는 나중** — 초기엔 단일 에이전트 + 다중 도구

## Phase 로드맵

| Phase | 이름 | 상태 |
|-------|------|------|
| 0 | 장애 재현 환경 (docker-compose 8컨테이너, LLM 0줄) | ✅ 완료 |
| 1 | read-only 진단 코파일럿 (Python 에이전트, 액션 0) | ✅ 완료 (LLM+Slack 실연동은 `.env` 필요) |
| 2 | 지식 그라운딩 RAG (BGE-M3 + ChromaDB) | ⬜ 다음 |
| 3 | 승인형 액션 (HITL, 화이트리스트, 감사로그) + 클라우드 describe | ⬜ |
| 4 | 멀티에이전트 + 좁은 자동대응 + k8s | ⬜ |

## 문서

- [phase0/](phase0/) — PLAN · CONTEXT · CHECKLIST (장애 재현 환경)
- [phase1/](phase1/) — PLAN · CONTEXT · CHECKLIST (read-only 진단 에이전트)

## 빠른 시작

루트 [README.md](../README.md) 참조. 요약:
```bash
cp agent/.env.example .env   # 키 채우기 (ANTHROPIC_API_KEY · SLACK_*)
docker compose up --build -d --remove-orphans
make chaos-errors            # → 진단 → Slack
```
