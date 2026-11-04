# TR1 contract v1.0 (frozen 2026-11-04): usage and cost traceability

## Route

`GET /api/usage` (no parameters). Always 200, also with `BYLAW_LIVE=0` and with `BYLAW_READONLY=1`.

```json
{
  "price": {"model": "muse-spark-1.3", "input_per_1m": 1.25, "output_per_1m": 4.25,
            "source": "https://dev.meta.ai/docs/pricing-rate-limits", "read": "2026-11-01"},
  "recorded": {
    "entries": [
      {"id": "csdemo-audit", "stage": "audit", "label": "csdemo audit, Muse-guided search",
       "source": "reports/csdemo.json", "calls": 4, "input_tokens": null, "output_tokens": null,
       "tokens": 31630, "seconds": 14.33, "cost_usd": {"low": 0.0395, "high": 0.1344}}
    ],
    "total": {"calls": 0, "tokens": 0, "cost_usd": {"low": 0.0, "high": 0.0}}
  },
  "live": {"enabled": true, "model": "muse-spark-1.3", "sessions": 0,
           "input_tokens": 0, "output_tokens": 0, "tokens_used": 0, "token_cap": 300000, "cost_usd": 0.0}
}
```

- `stage` is one of `compile`, `audit`, `amend`, `bench`, `live`.
- `source`: a repository path of the committed file the figures come from.
- `calls`, `input_tokens`, `output_tokens`, `seconds` may be `null` when the source does not record them. `tokens` is never null.
- Cost (USD, rounded to 4 decimals):
  - input and output both known: `low == high == input*1.25/1e6 + output*4.25/1e6`;
  - only the total known: `low = tokens*1.25/1e6`, `high = tokens*4.25/1e6`.
- `recorded.total`: sum of entries (`calls` null counts as 0), `tokens`, `cost_usd.low`, `cost_usd.high` (each rounded to 4 decimals after summing).
- `recorded` comes from the committed ledger `reports/usage.json` (under `BYLAW_REPORTS_DIR`), with the same shape as `recorded` minus `total`, i.e. `{"entries": [...]}`; the route computes `cost_usd` and `total`. If the file is missing: `entries: []`, all totals 0.
- `live`: counters of this API process since start (the VZ3-C6 counters). `tokens_used == input_tokens + output_tokens`, equal to `tokens_used` of `GET /api/live/status`. `cost_usd = input_tokens*1.25/1e6 + output_tokens*4.25/1e6`, rounded to 4 decimals. `enabled`, `model`, `sessions`, `token_cap` equal the same fields of `/api/live/status`.
- `/api/live/status` is unchanged (VZ3-C6 v1.2).

## Requirements

- REQ-TR1-1: `GET /api/usage` answers 200 with keys `price`, `recorded` (`entries`, `total`) and `live`, shaped as above.
- REQ-TR1-2: `price.input_per_1m == 1.25`, `price.output_per_1m == 4.25`, `price.model == "muse-spark-1.3"`.
- REQ-TR1-3: every recorded entry's `cost_usd` follows the cost rule above.
- REQ-TR1-4: `recorded.total` equals the sum of the entries per the rule above.
- REQ-TR1-5: `live.tokens_used == live.input_tokens + live.output_tokens == /api/live/status tokens_used`; after one live turn whose stub model reports usage input X and output Y, `live.input_tokens` grows by X, `live.output_tokens` by Y, and `live.cost_usd` follows the rule.
- REQ-TR1-6: with `BYLAW_LIVE=0` the route answers 200 and `live.enabled` is false.
- REQ-TR1-7: with `BYLAW_REPORTS_DIR` pointing at a directory without `usage.json`, `recorded.entries == []` and every total is 0.
- REQ-TR1-8: in the committed `reports/usage.json`, every entry's `source` is an existing repository path, ids are unique, and `stage` is in the allowed set.
