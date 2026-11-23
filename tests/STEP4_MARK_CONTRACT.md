# Step4 residual F3: mounted validated holding marks

The portfolio route returns both raw `open_positions` and
`statistics.holdings`, with `as_of == statistics.as_of`. The latter is the
backend validation authority. The frontend must join exact unique holding IDs
within this response, not use separately fetched strategy statistics, a raw
`current_price`, or wall-clock reinterpretation of rejected timestamps.

The API currently supplies validated `estimated_market_value`, not a validated
unit price. The UI divides that value by validated remaining quantity
(`initial_quantity - realized_quantity`) and the supported mode multiplier.
It first checks raw/validated portfolio, status, mode, timestamp, quantity,
market value and unrealized P&L consistency. Missing/duplicate/mismatched
identity or unavailable validated values remain Unknown. The API shape and all
Python economics remain unchanged. A stale snapshot disclosure is distinct
from server mark freshness and cannot promote Unknown to numeric.

## Permanent regression path

1. Under the inspected offline Python guard, run
   `test_step4_mark_contract`. This imports real entry, journal, statistics,
   authenticated ASGI route and disposable SQLite. It prints actual JSON as
   `MARK_API_SNAPSHOTS`; no positive trade outcome is invented.
2. Assemble the same response into the real mounted component harness:
   `python3 -I -B tests/step4_assemble_mark_fixture.py API_LOG OUTPUT_CJS`
3. Run the assembled CJS through the inspected installed-Node macOS sandbox
   runner (scrubbed HOME/HERMES_HOME, network and writes denied). Only API
   transport is replaced. Do not run against production databases or services.
4. Also run unchanged `tests/step4_temporal_render.cjs` (33 original cases),
   `test_step4_temporal`, the independent focused 11 probes, installed tsc and
   disposable Vite build. Do not invoke the product reconciler or Git.

The new mounted cases cover actual hour24 rejection; an actual microsecond
future rejection rendered after its observation time; persistence across
rerender; recovery only upon a new actual valid API response; raw nonnull plus
validated unknown; absent/wrong/duplicate identity; mismatched snapshot,
quantity/value/timestamp/status/mode/portfolio; observed zero; valid stale zero;
and explicit hour/minute/second/offset timestamp bounds for quote consumers.
The recovery case also refreshes back to the rejected snapshot and must lose
its numeric mark again. Corruption fixtures only remove trust from an actual
response; they do not invent accepted business outcomes.

Evidence for the implementation run (not independent acceptance):
`/Users/admin/.hermes/hardening/astra-remediation/step4-mark-fix-20260922-213508`

JSDOM is not browser E2E; in-process TestClient is not live HTTP. Duplicate and
missing identity probes intentionally elicit React key warnings. Parent review
is required. Step5 remains unauthorized.
