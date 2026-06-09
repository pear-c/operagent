# ── build ──────────────────────────────────────────────
FROM golang:1.23-alpine AS build
ENV CGO_ENABLED=0
WORKDIR /src
# 의존성을 vendor/에 박제 → 빌드 시 네트워크 0 (모듈 프록시 불필요, 폐쇄망 친화).
COPY go.mod go.sum ./
COPY vendor/ ./vendor/
COPY *.go ./
RUN go build -mod=vendor -trimpath -ldflags="-s -w" -o /demo-service .

# ── run (작은 이미지) ──────────────────────────────────
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /demo-service /demo-service
EXPOSE 8080
ENTRYPOINT ["/demo-service"]
