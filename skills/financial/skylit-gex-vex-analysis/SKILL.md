---
name: skylit-gex-vex-analysis
description: Use when analyzing Skylit Heatseeker GEX/VEX charts.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [financial, skylit, heatseeker, gex, vex, gamma, vanna, options-flow]
    related_skills: [skylit-ai, financial-market-data, unusual-whales]
---

# Skylit Heatseeker GEX/VEX Chart Analysis

## Overview

Use this skill to analyze **Skylit Heatseeker** charts and API heatmap data for **GEX / Gamma Exposure** and **VEX / Vanna Exposure**. It is grounded in the official Skylit docs at `https://docs.skylit.ai/introduction` and the API reference at `https://docs.skylit.ai/api-reference/introduction`.

Heatseeker visualizes dealer exposure by strike and expiration. Each strike is a node with a positive or negative value and a Skylit node classification. The core edge is not simply color or sign; it is the **absolute size of exposure**, the node's location relative to spot, the freshness of the level, and confluence with price action, other heatmaps, and related indices.

## When to Use

Load this skill when the user asks to:

- Interpret or summarize a Skylit / Heatseeker screenshot, chart, heatmap, GEX view, VEX view, or API response.
- Identify King Nodes, Gatekeeper Nodes, Pika/Barney zones, floors, ceilings, air pockets, hedge nodes, range edges, or reshuffles.
- Compare **GEX vs VEX** for intraday and swing context.
- Build a trade thesis, conviction score, support/resistance map, target, invalidation, or Kian-style card from Skylit data.
- Explain dealer-positioning mechanics at a high-school level.

Do **not** use Heatseeker as a standalone buy/sell signal. The official docs repeatedly frame it as contextual intelligence that must be confirmed by price action, market structure, liquidity, and risk-to-reward.

## Official Source Map

Primary documentation pages reviewed:

- Introduction: product overview, participant model, Pika/Barney node behavior, trending/choppy/volatile scenarios.
- Intended Audience: serious traders using Heatseeker to improve timing and build disciplined market reads; not a guaranteed signal bot.
- Core Concepts: node hierarchy, magnets, King/Gatekeeper/Midpoint, retests, rate-of-change, hedge nodes, air pockets, OPEX.
- Navigating Skylit Web App: ticker switching, GEX/VEX tabs, keyboard shortcuts, Trinity-style index confluence.
- How to Read and Use Heatseeker: five-step framework.
- Best Practices, Limitations, Common Pitfalls, FAQs.
- Examples & Case Studies and Patternpedia: Whipsaw, Rainbow Road, Gatekeeper, speculative/decoy nodes, Trend, Rug Setup, Ten Commandments, topping/bottoming with VEX.
- API Reference: live heatmap, historical replay, SSE stream, authentication, credits, rate limits.

## GEX vs VEX Mode Selection

| User Request | Skylit Metric | Typical Label | Horizon | Primary Read |
| --- | --- | --- | --- | --- |
| GEX, gamma, intraday, 0DTE, today, pin, scalp | `gamma` | GEX | Intraday / same session | Pin levels, deflections, gamma floors/ceilings, late-day settlement, volatility expansion/compression |
| VEX, vanna, swing, week, next few days, positioning ahead | `vanna` | VEX | Multi-day / weekly | Dealer vanna posture, upside/downside accumulation, stair-step targets, higher-timeframe topping/bottoming |

When the user only says “Skylit chart,” infer mode from the visible tab or data. If mode is unknown, produce a chart-read that explicitly labels the mode as unknown and avoids hard GEX/VEX conclusions.

## Core Node Vocabulary

### Node

A strike/expiration area where dealers have exposure. Nodes act like dynamic magnets and walls: price may be attracted toward them as it approaches, then reject/deflect when it interacts.

### Absolute Value Rule

The official docs emphasize this: the most important factor is **absolute value**, not color or positive/negative sign. Larger absolute values exert stronger pull or pressure.

### Positive Exposure / Pika / Yellow-Green

Positive exposure generally creates lower-volatility interactions. Bright yellow “Pika” nodes can behave like a **magnetic pillow**: price may slow, pin, compress, or reverse around the zone.

### Negative Exposure / Barney / Blue-Purple

Negative exposure generally creates higher-volatility, wicky movement. Dark purple “Barney” nodes can act like **gasoline on a fire**: once price enters, it can move fast, overshoot, trap retail, then reverse.

### King Node

The highest absolute-value node on the heatmap. It represents where market makers hold the greatest exposure and where price can gravitate near expiration. It may be yellow or purple; color does not define it.

King Node behavior:

- Late session / near expiration: often becomes an EOD/EOW settlement or pin target.
- Early in the day: if price reaches it too early, dealers may drive price away to avoid defending the level all day.
- On SPX, allow a **5–10 point interaction zone**; do not demand cent-perfect reactions.

### Gatekeeper Node

A high-value node between spot and a larger destination node. It acts like a bouncer, blocking or delaying price from reaching the King Node. Failed tests and early-day rejections at Gatekeepers often precede reshuffles or directional change.

### Midpoint

The center of a range between meaningful floor/ceiling nodes. Direction is uncertain here and risk-to-reward is usually poor. Unless using option/spread-selling logic, avoid directional trades in the midpoint. Official shorthand: **do not diddle in the middle**.

### Cluster / Double-Stacked Nodes

Multiple large values grouped together. Clusters can increase pinning/chop or create strong bounce/rejection zones. Compare cluster size to surrounding nodes and to spot distance.

### Hedge Node

Large nodes that appear around major catalysts such as FOMC, CPI, JOLTS, NFP, earnings, or OPEX. They may sit far from price and move throughout the day. Closer and larger hedge nodes exert more influence; far OTM hedge nodes require skepticism.

### Air Pocket

A zone with low volume or small nodes where price may move easily due to lack of resistance/activity. Confirm with price action, technical structure, and cross-index confluence before assuming a clean travel lane.

### OPEX Node

Monthly expiration can alter the reliability of nodes as exposure rolls off. During OPEX weeks or major rebalancing, short-term node influence can weaken or reshuffle quickly.

## Five-Step Analysis Framework

Follow this exact sequence before producing a thesis.

### 1. Identify the Magnets

Find the largest absolute-value nodes near and away from spot. Mark them as zones, not exact lines. Completion criterion: at least the strongest upside node, strongest downside node, and nearest large node to spot are named.

### 2. Spot the King Node

Locate the highest absolute-value node in the visible heatmap. Decide whether it is a likely EOD/EOW destination, a too-early drive-off risk, or too far/decoy-like. Completion criterion: King Node strike, side of spot, distance from spot, and freshness are stated.

### 3. Define the Range

Identify upper and lower boundaries where price has repeatedly reversed or where major nodes sit. Avoid midpoint trades unless the setup is explicitly range/premium-selling. Completion criterion: range high, range low, midpoint/no-trade zone, and preferred fade edge are named.

### 4. Watch Gatekeepers

Find high-value blocking nodes between spot and the target. Gatekeeper rejection can invalidate a continuation thesis or trigger a reshuffle. Completion criterion: the nearest gatekeeper in the trade direction and the reaction needed to continue are stated.

### 5. Map the Flow / Reshuffle Risk

Assess whether nodes are accumulating, dissipating, or reshuffling. In API data, use live `velocityPct` when available. In screenshots, compare visible timestamps/frames if supplied. Completion criterion: the thesis names whether structure is stable, accumulating, dissipating, or unclear.

## GEX Analysis Playbook

Use GEX for same-day / 0DTE / intraday reads.

Priorities:

1. Spot current price relative to the largest absolute GEX nodes.
2. Identify King Node and whether it is a late-day pin candidate or early-day drive-off risk.
3. Mark floor and ceiling nodes; avoid midpoint entries.
4. Watch negative gamma zones for fast, wicky overshoots and possible sharp reversals.
5. Watch positive gamma zones for lower-volatility pinning/compression.
6. Use SPX/SPY/QQQ confluence for index trades; if they disagree, lower confidence or stand aside.
7. For 0DTE options, be extra strict on midpoint avoidance and asymmetric R:R because theta and chop can erase premiums quickly.

GEX thesis labels:

- **Neutral Pin**: spot is between strong positive nodes or near a King Node with no strong directional accumulation.
- **Bullish Deflection**: price tests a strong floor/gatekeeper/king zone below spot and confirms a bounce with price action.
- **Bearish Deflection**: price tests a strong ceiling/gatekeeper/king zone above spot and confirms rejection.
- **Momentum / Air Pocket**: price breaks through a gatekeeper and enters a low-node zone toward the next magnet.
- **Rug Risk**: yellow/positive ceiling stacked above purple/negative exposure with little/no floor below.

## VEX Analysis Playbook

Use VEX for vanna / weekly / swing / sessions-ahead reads.

Priorities:

1. Identify whether vanna exposure is stair-stepping up or down over the next days/week.
2. Compare upside accumulation vs downside accumulation. Lack of accumulation in one direction matters as much as strong accumulation in the other.
3. Treat VEX as higher-timeframe posture, not an immediate entry trigger.
4. Use node rejections and price action for entries while VEX supplies directional context.
5. For topping/bottoming reads, look for multiple resistance/support levels, little/no continuation accumulation beyond them, and confirmation across SPY/QQQ/SPX.
6. Invalidation is the opposite of formation: higher accumulation at higher strikes for bearish thesis invalidation, or lower accumulation at lower strikes for bullish thesis invalidation, plus dissipation of the thesis nodes.

VEX thesis labels:

- **Bullish Stair-Step**: higher nodes remain or grow while counter-direction nodes are weak; enter on pullbacks only if price action and R:R support.
- **Bearish Stair-Step**: lower nodes remain or grow while upside accumulation is weak; short pops/rejections or wait for downside floor targets.
- **Toppy**: strong gatekeeper/resistance, minimal higher-strike accumulation, prior delivery from an upper node, and cross-index confirmation.
- **Bottoming**: strong lower support/floor, minimal lower-strike continuation, bounce confirmation, and cross-index confirmation.
- **Decoy / Speculative Node**: far OTM node with unrealistic required move, multiple gatekeepers in the way, weak supporting accumulation, or prior extended move.

## Patternpedia Recognition Rules

### Whipsaw

Wide range bounded by at least two high-value nodes with few prominent nodes between. Best approach: fade range edges; avoid initiating in the middle, especially with 0DTE options.

### Rainbow Road

Many prominent positive and negative nodes spread across a broad area without a clear range. Expect choppy/erratic price action. Best approach: avoid trading until a clearer setup forms.

### Gatekeeper

A high-value node blocks price from reaching further high-value nodes. Mark it, scale out as price approaches, and consider reversal only if price action confirms. Compare gatekeeper value against the next highest node.

### Trend

Price fixates on a distant King Node with comparatively little counter-directional skew. As price travels, it can select the next node in stair-step fashion. Enter on pullbacks; chase only when asymmetric R:R remains favorable.

### Rug Setup

A yellow node stacked above a purple node with little/no obvious floor below. Negative gamma can accelerate rejection from the positive gamma ceiling. Look for no upside accumulation and growing downside nodes across SPX/SPY/QQQ.

### Speculative / Decoy Node

Far OTM node that looks large but is unlikely due to distance, time remaining, intervening gatekeepers, lack of supporting nodes, or an already extended move. Treat with skepticism; do not turn it into a target without chart confirmation.

### Topping / Bottoming Pattern

Primarily a VEX read. For topping: little/no upside accumulation, resistance/gatekeeper above, stair-step lower exposure, and cross-index confluence. Invalidation is fresh higher-strike accumulation, dissipation of lower nodes, or stronger positioning closer to the money in the opposite direction.

## Confluence Hierarchy

Use this order when ranking conviction:

1. **Price Action**: primary confirmation; node reaction, rejection wick, bounce, reclaim/loss of level.
2. **Heatseeker Node Context**: King/Gatekeeper/cluster, value magnitude, freshness, proximity, rate-of-change.
3. **Asymmetric Risk-to-Reward**: skip 1:1 midpoint trades; prefer edge fades or clean air-pocket travel.
4. **GEX/VEX Overlap**: when gamma and vanna zones align, probability of holding/reversing improves.
5. **Index Trinity**: SPX, SPY, and QQQ agreement materially increases confidence for index trades. Divergence lowers confidence.
6. **External Context**: news, catalyst calendar, earnings, macro events, OPEX/rebalancing, liquidity period.

If confluence is weak, label the read as low confidence and recommend waiting for confirmation rather than forcing a trade.

## Freshness and Retest Rules

Node influence weakens after repeated interaction.

| Touch | Reaction Strength | Practical Use |
| --- | --- | --- |
| First touch | Strongest | Highest-quality deflection/bounce candidate |
| Second touch | Moderate | Tradable only with confirmation; often double top/bottom behavior |
| Third+ touch | Weakest | Lower probability; avoid unless strong new accumulation appears |

If price has already been delivered from a node, do not chase reversion back to it. Prefer the freshest relevant node with clean R:R.

## API Usage Notes

Official base URL: `https://api.skylit.ai`

Authentication:

- Send `Authorization: Bearer $SKYLIT_API_KEY` on every request.
- `X-API-Key: $SKYLIT_API_KEY` is accepted if bearer auth is inconvenient.
- Never expose or commit keys.

Live heatmap:

```bash
curl "https://api.skylit.ai/v1/heatmap?symbols=SPY,SPX,QQQ&metric=gamma&maxStrikes=92" \
  -H "Authorization: Bearer $SKYLIT_API_KEY"
```

Historical replay:

```bash
curl "https://api.skylit.ai/v1/historical?symbols=SPY&metric=vanna&at=2026-03-05T10:01:00Z&maxStrikes=92" \
  -H "Authorization: Bearer $SKYLIT_API_KEY"
```

Live SSE stream:

```bash
curl -N "https://api.skylit.ai/v1/stream?symbol=SPY&metric=gamma&maxStrikes=92" \
  -H "Authorization: Bearer $SKYLIT_API_KEY"
```

API facts from official docs:

- `/v1/heatmap`: current per-strike heatmap, supports comma-separated symbols, includes live `velocityPct`, costs 1 credit.
- `/v1/historical`: nearest snapshot at `at`, up to 365 days back, no `velocityPct`, costs 5 credits.
- `/v1/stream`: SSE updates for one symbol per connection, costs 1 credit on connect and 1 credit per minute open, max 5 concurrent streams per customer per pod.
- Metrics: `gamma` for GEX and `vanna` for VEX.
- Default `maxStrikes` is 92; allowed 1–400.
- Successful responses have `data` and `meta`; errors have `error`.
- Credits appear in `X-Credits-Remaining`; rate-limit headers include `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`.
- Rate ceiling: 600 requests/minute; 429 requires backing off using `Retry-After`.
- Node types include `king`, `gatekeeper`, `pika`, `barney`, `significant`, and `normal`.

## Screenshot / Chart Analysis Procedure

When analyzing an image:

1. Load the image with vision tooling if a screenshot/path/URL is provided.
2. Identify visible mode: GEX/Gamma or VEX/Vanna. If not visible, label as unknown.
3. Read ticker, current price/spot, timestamp, expiration row/column if visible.
4. Extract meaningful strikes by visual prominence: King Node, Gatekeepers, large clusters, floors, ceilings, air pockets.
5. Classify pattern: Whipsaw, Rainbow Road, Gatekeeper, Trend, Rug, Topping/Bottoming, Decoy, Neutral Pin, or unclear.
6. Cross-check with any supplied GEX/VEX companion chart; overlap zones raise confidence.
7. Produce a trade-context read with targets and invalidation only if the chart supports it.
8. If the screenshot lacks spot, time, or mode, state the limitation and avoid pretending precision.

Completion criterion: final output names the key zones, current spot relationship, likely behavior, invalidation, and confidence level.

## Kian-Style Output Template

Use the user’s preferred clean card style: no bullets inside polished trading cards; use bold labels line-by-line.

```markdown
✨ **SKYLIT HEATSEEKER [GEX/VEX] READ — KIAN PROCESS**

**Ticker**: [TICKER]
**Spot / Underlying Price**: $[SPOT]
**Mode**: [GEX gamma / VEX vanna]
**Horizon**: [Intraday / 0DTE / Weekly swing]
**Pattern**: [Whipsaw / Gatekeeper / Trend / Rug / Neutral Pin / etc.]
**King Node**: $[STRIKE] ([above/below spot], [fresh/tested/unknown])
**Gatekeeper Zones**: $[STRIKES]
**Key Support / Floor**: $[STRIKE]
**Key Resistance / Ceiling**: $[STRIKE]
**Air Pocket / Travel Zone**: $[ZONE or none visible]
**GEX/VEX Confluence**: [Aligned / Mixed / Not checked]
**SPX/SPY/QQQ Confluence**: [Aligned / Mixed / Not checked]
**Conviction**: [High / Moderate / Low] [Bullish / Bearish / Neutral]
**Primary Target**: $[TARGET]
**Invalidation**: [Level/reaction/reshuffle condition]
**Trade Quality**: [Asymmetric / 1:1 skip / wait for confirmation]

### 🏫 Plain-English Dealer Read
[Explain in 2–4 short paragraphs. Yellow/positive = magnetic pillow/pin/compression. Purple/negative = gasoline/volatility/overshoot. Tie the explanation to the actual visible nodes and risk.] 

*Disclaimer: Educational market-structure analysis only, not financial advice. Confirm with price action and manage risk.*
```

If delivering to Discord/Telegram with the `skylit-ai` automation workflow, attach the cropped heatmap screenshot and obey that skill’s stricter formatting/cropping laws.

## Common Pitfalls

1. **Treating Heatseeker as a signal bot.** It is context, not an entry system. Require price action confirmation.
2. **Ranking by color instead of magnitude.** King Nodes are defined by absolute value, not yellow/purple.
3. **Forcing exact levels.** Use zones. On SPX, 5–10 points from a King Node can still be a valid interaction.
4. **Trading the midpoint.** Midpoint directional trades usually have poor R:R and high chop/theta risk.
5. **Ignoring reshuffles.** A new map means new structure. Pause and re-evaluate; old levels may no longer matter.
6. **Missing cross-index influence.** For index trades, SPX, SPY, and QQQ can support or block each other. Mixed maps lower confidence.
7. **Chasing stale nodes.** Repeatedly tested nodes lose freshness and probability.
8. **Believing far OTM nodes blindly.** Large distant nodes can be speculative or decoy-like when required move/time/context is unrealistic.
9. **Ignoring catalysts and OPEX.** News, earnings, macro releases, rebalancing, and OPEX can alter dealer flows and reduce clarity.
10. **Oversizing because the heatmap looks clean.** Risk management and asymmetric R:R remain mandatory.

## Verification Checklist

Before finalizing a Skylit analysis, verify:

- [ ] Mode is identified as GEX/gamma, VEX/vanna, or explicitly unknown.
- [ ] Ticker, spot/current price, and timeframe/horizon are stated or marked unavailable.
- [ ] King Node is identified by largest absolute value, not color.
- [ ] Gatekeeper(s), floor(s), ceiling(s), range/midpoint, and air pockets are considered.
- [ ] Freshness/retest status is considered where visible.
- [ ] GEX/VEX overlap is checked when both views are available.
- [ ] SPX/SPY/QQQ confluence is checked for index trades when data is available.
- [ ] Trade thesis includes invalidation and does not overstate certainty.
- [ ] Limitations are stated when image/API data is incomplete.
- [ ] Final card uses the user’s clean formatting style and includes an educational disclaimer.
