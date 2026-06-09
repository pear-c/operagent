# operagent — Phase 0: 장애 재현 환경

> 더 큰 프로젝트 **"LLM 기반 장애 대응 운영 에이전트"** 의 0단계.
> 이 단계의 목적은 단 하나 — **버튼 하나로 메모리/지연/에러 장애를 재현하고, 그게 메트릭/로그에 드러나고, Prometheus alert이 발화해서 webhook으로 떨어지는 루프**를 완성하는 것.
>
> 이 단계엔 **LLM도, 에이전트도, 자동 대응(write) 액션도 없다.** 관측 → 고장 주입 → 탐지 → 알림 전달까지가 전부다.
> `webhook-sink`는 그냥 로거이며, **Phase 1에서 이 자리를 Python 에이전트(진단 두뇌)로 교체**한다.

---

## 아키텍처

```
load-gen ─▶ demo-service(Go) ─/metrics─▶ prometheus ─rule 발화─▶ alertmanager ─webhook─▶ webhook-sink(로거)
                 │  3표면                     │  (5s 주기)                                    └ Phase 1에 에이전트로 교체
                 └─ stdout 로그 ─▶ alloy ─▶ loki ◀── grafana (대시보드 + Explore)
                                                  ◀── prometheus
  조작: POST /chaos/{latency,errors,memory,cpu} · GET /chaos/state · POST /chaos/reset
```

- **demo-service (Go)** — 유일하게 직접 만든 감시 대상. 비즈니스 / 계측(`prometheus/client_golang`) / 고장 주입 3표면
- **prometheus / alertmanager / loki / alloy / grafana** — 기성품. 직접 구현하지 않음
- 로그 수집기는 **Grafana Alloy** (promtail은 2026-03-02 EOL — 사용 안 함)
- Kubernetes/Helm 없음. 순수 docker-compose

### 포트

| 서비스 | URL |
|--------|-----|
| demo-service | http://localhost:8080 |
| prometheus | http://localhost:9090 |
| alertmanager | http://localhost:9093 |
| loki | http://localhost:3100 |
| grafana | http://localhost:3000 (익명 Admin 접근, 또는 admin/admin) |
| alloy (UI) | http://localhost:12345 |
| webhook-sink | http://localhost:9000 |

---

## 사전 요구사항

- Docker Desktop (또는 Docker Engine) + `docker compose`
- (선택) `make` — Windows는 git-bash/WSL에서. 없으면 README의 `curl` 명령을 직접 사용

---

## 빠른 시작

```bash
# 전체 빌드 + 기동
docker compose up --build -d        # 또는: make up

# 상태 확인
docker compose ps
```

- Grafana 대시보드: <http://localhost:3000> → **ops overview** (요청률·에러%·p95·heap·goroutines)
- 약 30초~1분이면 load-gen 베이스라인 트래픽이 대시보드에 보인다
- Loki 로그: Grafana → **Explore** → 데이터소스 `Loki` → `{service="demo-service"}`

종료:

```bash
docker compose down -v              # 또는: make down
```

---

## 데모 — 고장 주입 → alert → webhook

webhook-sink 로그를 한 창에 띄워두고:

```bash
docker compose logs -f webhook-sink   # 또는: make logs-sink
```

다른 창에서 고장을 주입한다 (`make` 또는 `curl`):

| 장애 | make | curl |
|------|------|------|
| 에러율 50% | `make chaos-errors` | `curl -XPOST localhost:8080/chaos/errors -d '{"rate":0.5}'` |
| 지연 800ms | `make chaos-latency` | `curl -XPOST localhost:8080/chaos/latency -d '{"ms":800,"pct":100}'` |
| 메모리 200MB | `make chaos-memory` | `curl -XPOST localhost:8080/chaos/memory -d '{"mb":200}'` |
| CPU 4 workers | `make chaos-cpu` | `curl -XPOST localhost:8080/chaos/cpu -d '{"workers":4,"seconds":0}'` |
| 상태 조회 | `make state` | `curl localhost:8080/chaos/state` |
| 전체 해제 | `make reset` | `curl -XPOST localhost:8080/chaos/reset` |

흐름: 고장 주입 → 메트릭에 반영 → rule `for: 30s` 충족 → Alertmanager 발화 → **webhook-sink 로그에 Alertmanager payload가 정렬되어 찍힌다.** (대략 30~90초)

진행 상황은 Prometheus <http://localhost:9090/alerts> 에서 `Pending → Firing` 전이로도 볼 수 있다.

---

## 완료 기준 (자가 점검 체크리스트)

```
[ ] 1. docker compose up 한 번으로 모든 서비스가 정상 기동 (docker compose ps 전부 Up)
[ ] 2. http://localhost:3000 대시보드에 load-gen 트래픽이 실시간으로 보인다
[ ] 3. Grafana Explore에서 Loki로 demo-service 로그가 조회된다 ({service="demo-service"})
[ ] 4. make chaos-errors → ~90초 내 HighErrorRate 발화 → webhook-sink 로그에 payload
[ ] 5. make chaos-latency → HighLatencyP95 발화 / make chaos-memory → HighHeapMemory 발화
[ ] 6. make reset 후 시스템 정상 복귀 + alert resolved (webhook-sink에 resolved payload)
```

> 검증 팁: alert이 안 뜨면 ① load-gen이 떠 있는지(`docker compose ps load-gen`) — 트래픽이 없으면 에러율 rule이 `0/0`이 되어 발화하지 않는다. ② Prometheus <http://localhost:9090/targets> 에서 `demo-service` 타깃이 `UP` 인지 확인.

---

## 가드레일 (Phase 0에서 하지 않은 것)

- ❌ 자동 대응/실행(write) 액션 — Phase 0는 관측·트리거·알림까지만
- ❌ LLM/에이전트 로직 — `webhook-sink`는 그냥 로거
- ❌ promtail (EOL) — Alloy 사용
- ❌ Kubernetes/Helm — 순수 docker-compose
- ❌ demo-service에 DB/ORM/인증/무거운 프레임워크

---

## 트러블슈팅

- **Alloy가 로그를 못 가져옴 (Windows)** — Alloy는 docker 소켓(`/var/run/docker.sock`)을 마운트해 컨테이너 로그를 tail한다. Docker Desktop에서는 보통 동작하지만, 안 되면 Settings → "Expose daemon on tcp..." 또는 WSL2 백엔드를 확인. alloy UI(<http://localhost:12345>)에서 컴포넌트 상태 확인 가능.
- **메모리 alert이 안 뜸** — 기본 임계값 150MB. `make chaos-memory`(200MB 주입)면 넘는다. baseline heap이 임계 근처면 `prometheus/rules.yml`의 `HighHeapMemory` 임계값을 조정.
- **포트 충돌** — 위 포트 표의 포트를 이미 쓰는 프로세스가 있으면 `docker-compose.yml`의 `ports` 좌측 값을 변경.
- **줄바꿈(CRLF)로 설정 파싱 실패** — `.gitattributes`가 `*.yml`·`*.alloy`·`*.sh`를 LF로 강제한다. 직접 편집 시 LF 유지.

---

## Phase 1 — 진단 에이전트 (read-only 코파일럿)

`webhook-sink`(Go 로거) → **`agent/` (Python FastAPI)** 로 교체됨. Alertmanager가 `operagent:9000/webhook`으로 alert을 보내면:

```
alert → operagent: 즉시 200 ack → 비동기 진단
  ├─ PromQL·LogQL(read-only)로 메트릭·로그 자동 수집
  ├─ LLM 1회 종합(claude-opus-4-8) → "상황 / 원인 가설 A·B / 근거 / 다음 확인할 것" 4블록
  └─ Slack 게시 (액션 0개)
```

### 실연동 설정 (LLM + Slack)

`agent/.env.example`을 `.env`로 복사해 레포 루트에 두고 키를 채운다:

```bash
cp agent/.env.example .env   # 레포 루트에 .env (gitignore)
# ANTHROPIC_API_KEY=sk-ant-...
# SLACK_BOT_TOKEN=xoxb-...   (Bot을 채널에 /invite 해둘 것)
# SLACK_CHANNEL_ID=C...
# OPERAGENT_MODEL=claude-opus-4-8   (비용 절감 시 claude-sonnet-4-6)
```

`.env`가 없어도 동작한다 — **graceful degrade**: LLM·Slack을 건너뛰고 수집한 사실(메트릭·로그)만 operagent stdout에 출력. `docker compose logs -f operagent`로 확인.

### 실행

```bash
docker compose up --build -d --remove-orphans   # operagent 빌드 + 옛 webhook-sink orphan 정리
docker compose logs -f operagent                 # 진단 출력 확인
make chaos-errors                                # → alert → 진단
```

> ⚠️ **alertmanager.yml(라우팅)을 바꾸면 `docker compose restart alertmanager` 필요** — alertmanager는 config를 자동 reload하지 않는다. 안 하면 옛 receiver로 보내 `no such host`.

### 가드레일 (Phase 1)
- read-only 도구만 (PromQL·LogQL). **write 액션 0개** — Phase 3 전까지.
- LLM은 탐지하지 않음 (입력 = 이미 발생한 alert). 원인은 가설로.
- LangGraph 없음 (결정론 수집 → LLM 1회). 시크릿은 `.env`만.

## 다음 — Phase 2

런북·과거 장애 회고·서비스 오너십 문서를 **BGE-M3 + ChromaDB**로 임베딩 → 일반론이 아닌 "이 시스템 특화" 진단. write 액션은 여전히 0.
