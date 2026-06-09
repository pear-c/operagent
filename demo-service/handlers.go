package main

import (
	"encoding/json"
	"log/slog"
	"math/rand/v2"
	"net/http"
	"sync"
	"time"
)

func healthz(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_, _ = w.Write([]byte(`{"status":"ok"}`))
}

// Order는 인메모리 주문. DB/ORM 없음(Phase 0 가드레일).
type Order struct {
	ID   int    `json:"id"`
	Item string `json:"item"`
	Qty  int    `json:"qty"`
}

type OrderStore struct {
	mu     sync.Mutex
	orders []Order
	nextID int
}

func NewOrderStore() *OrderStore {
	return &OrderStore{
		orders: []Order{{ID: 1, Item: "widget", Qty: 3}},
		nextID: 2,
	}
}

func (s *OrderStore) list(w http.ResponseWriter, _ *http.Request) {
	// DB 읽기를 흉내내기 위한 작은 인위적 지연(5~30ms)
	time.Sleep(time.Duration(5+rand.IntN(26)) * time.Millisecond)

	s.mu.Lock()
	out := make([]Order, len(s.orders))
	copy(out, s.orders)
	s.mu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(out)
	slog.Info("주문 목록 조회", "route", "/api/orders", "count", len(out), "status", 200)
}

func (s *OrderStore) create(w http.ResponseWriter, r *http.Request) {
	var in struct {
		Item string `json:"item"`
		Qty  int    `json:"qty"`
	}
	if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
		http.Error(w, `{"error":"invalid json body"}`, http.StatusBadRequest)
		return
	}
	s.mu.Lock()
	o := Order{ID: s.nextID, Item: in.Item, Qty: in.Qty}
	s.orders = append(s.orders, o)
	s.nextID++
	s.mu.Unlock()

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	_ = json.NewEncoder(w).Encode(o)
	slog.Info("주문 생성", "route", "/api/orders", "id", o.ID, "status", 201)
}
