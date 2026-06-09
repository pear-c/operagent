# ── build ──────────────────────────────────────────────
FROM golang:1.23-alpine AS build
ENV CGO_ENABLED=0
WORKDIR /src
COPY go.mod ./
COPY *.go ./
RUN go build -trimpath -ldflags="-s -w" -o /webhook-sink .

# ── run ────────────────────────────────────────────────
FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=build /webhook-sink /webhook-sink
EXPOSE 9000
ENTRYPOINT ["/webhook-sink"]
