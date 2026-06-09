# ── build ──────────────────────────────────────────────
FROM golang:1.23-alpine AS build
ENV GOFLAGS=-mod=mod CGO_ENABLED=0
WORKDIR /src
COPY go.mod ./
COPY *.go ./
# go.sum은 첫 빌드 시 -mod=mod로 자동 생성된다(오프라인 사전 핀 불필요).
RUN go build -trimpath -ldflags="-s -w" -o /demo-service .

# ── run (작은 이미지) ──────────────────────────────────
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /demo-service /demo-service
EXPOSE 8080
ENTRYPOINT ["/demo-service"]
