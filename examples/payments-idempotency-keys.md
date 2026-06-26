---
title: Idempotency keys on the payments API
type: reference
owner: payments
status: active
provenance_tier: verified
created: 2026-06-26
updated: 2026-06-26
last_verified: 2026-06-26
confidence: 0.9
half_life_kind: versioned
entities: [payments, idempotency, api]
relates: [payments-retry-policy]
source:
  - repo: payments-api
    path: src/payments/charge.py
    symbol: create_charge
    provenance: a1b2c3d
---

## Rule

Every `POST /charges` MUST carry an `Idempotency-Key` header. `create_charge`
stores the key for 24h and replays the original response on a repeat — so a client
retry never double-charges. One fact, one page; callers link here (`[[payments-idempotency-keys]]`)
instead of restating it.
