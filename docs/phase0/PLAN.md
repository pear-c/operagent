# operagent Phase 0 — 장애 재현 환경 (PLAN)

> 설계도. 목표·범위·구현 순서·아키텍처.
> 오버레이: `.claude/rules/projects/operagent/` (overview·conventions·policy-keywords)

---

## 1. 목표

**고장 버튼 한 번 누르면 → 1~2분 안에 대응 alert이 발화하고 → webhook이 더미 리시버에 도달한다.**

이 한 문장이 Phase 0의 유일한 완료 기준이다. **LLM은 한 줄도 들어가지 않는다.** Phase 0은 Phase 1(에이전트)이 올라탈 "장애 재현 무대"를 까는 작업.

부수 목표: demo-service를 Go로 작성하며 net/http·goroutine·mutex·client_golang을 딱 필요한 만큼 연습 (의도적으로 작게).

---

## 2. 범위

### 만든다
- `docker-compose.yml` — 7 컨테이너 스택
- `go/` — demo-service (비즈니스 API + 계측 + 고장 주입)
- `deploy/prometheus/` — scrape config + alert rule 3종
- `deploy/alloy/` — 로그 tail → Loki
- `deploy/grafana/` — 데이터소스 + 대시보드 provisioning
- `deploy/alertmanager/` — webhook 라우팅
- 더미 webhook 리시버 (Phase 1에서 에이전트로 교체될 placeholder)
- load-gen — 베이스라인 트래픽

### 안 만든다 (Phase 1+)
- `agent/` 로직 (디렉토리 자리만, 로직 0줄)
- LLM·Anthropic 호출
- 진단·Slack 전송
- write 액션·RAG·LangGraph

---

## 3. 아키텍처

```
load-gen ──▶ demo-service:8080 ──/metrics──▶ prometheus:9090 ──rule 발화──▶ alertmanager:9093 ──webhook──▶ dummy-receiver
                   │  (Go)                         │                                                          (Phase 1에 에이전트로 교체)
                   └─ 컨테이너 로그 ──▶ alloy ──▶ loki:3100 ◀── grafana:3000 (대시보드)
                                                              ◀── prometheus (대시보드)
   조작: POST /chaos/{latency,errors,memory,cpu} · GET /chaos/state · POST /chaos/reset
```

### demo-service 3표면
- **비즈니스**: `GET /healthz` · `GET /api/orders`(약간의 지연으로 DB 읽기 흉내) · `POST /api/orders`
- **계측**: `prometheus/client_golang` — `http_requests_total{method,route,status}`(카운터) · `http_request_duration_seconds`(히스토그램) · `http_inflight_requests`(게이지). 기본 레지스트리가 `go_memstats_*`·`go_goroutines`·`process_*` 공짜 제공
- **고장**: `POST /chaos/latency`(ms,pct) · `POST /chaos/errors`(rate) · `POST /chaos/memory`(mb) · `POST /chaos/cpu` · `GET /chaos/state` · `POST /chaos/reset`. 상태는 mutex 구조체, 미들웨어가 요청마다 읽어 주입

### alert rule 3종 (고장 3종과 1:1)
- 에러율: `rate(http_requests_total{status=~"5.."}[1m]) / rate(http_requests_total[1m]) > 0.1`
- 지연: p95(`http_request_duration_seconds`) `> 0.5s`
- 메모리: `go_memstats_heap_inuse_bytes` 임계 초과

---

## 4. 구현 순서 (각 단계 검증 후 다음으로)

| Step | 산출물 | 검증 |
|------|--------|------|
| **0** | 레포 초기화 (`operagent/`, git, `.gitignore`, `go.mod`, `README`) | `go mod` 동작, git remote = pear-c |
| **1** | demo-service 비즈니스 표면 (`/healthz`·`/api/orders`) | `go run` → curl 200 |
| **2** | 계측 표면 (client_golang 3종 메트릭 + 미들웨어) | `/metrics`에 3종 + go_memstats_* 노출 |
| **3** | 고장 표면 (`/chaos/*` mutex 구조체 + 미들웨어 주입) | latency/errors/memory 주입 → state 반영 → reset 원복 |
| **4** | docker-compose: demo-service + load-gen | `up` → load-gen 트래픽이 메트릭에 반영 |
| **5** | prometheus (scrape + rule 3종) | 타깃 UP, rule 로드됨 |
| **6** | loki + alloy (로그 수집) | demo-service 로그가 Loki에 적재 |
| **7** | grafana (데이터소스 + 대시보드) | 메트릭·로그 대시보드 표시 |
| **8** | alertmanager + 더미 webhook 리시버 | rule 발화 → webhook 도달 |
| **9** | E2E: 고장 → alert → webhook | **완료 기준 충족 확인** |

---

## 5. 영향 범위 (blast radius)

- 전부 신규 레포. 기존 워크스페이스 코드 영향 0
- 전부 로컬 docker-compose. 외부 네트워크·클라우드 영향 0
- LLM·외부 API 호출 0

---

## 6. 다음 Phase 연결

- 더미 webhook 리시버 → Phase 1에서 `agent/`의 FastAPI 에이전트로 교체
- 메트릭 3종·alert 3종은 Phase 1 에이전트 도구가 조회할 계약 (변경 시 동기 갱신)
