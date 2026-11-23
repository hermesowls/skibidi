---
name: skylit-heatmap-analysis
description: Use when reading Skylit GEX/VEX heatmaps.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [financial, trading, skylit, heatseeker, gex, vex, gamma, vanna, atlas]
---

# Skylit Heatmap Analysis

Use this skill when the user sends a Skylit / Heatseeker / ATLAS screenshot or asks for a GEX, VEX, OPEX node, King Node, or market-structure read.

## Core Principle

Heatmap nodes are **context**, not entries. A node can be a magnet, pin, floor, wall, danger zone, or acceleration pocket. A trade requires confirmation from price action, level acceptance/rejection, market context, flow, and risk/reward.

## Kian Style Rules

Keep the answer trader-clean, actionable, complete, and easy to copy/paste. Do not use Markdown bold asterisks around labels in routine Telegram heatmap cards; use plain `Label: value` lines instead. Avoid tables and long theory unless the user explicitly asks for education.

Every read should include:

Ticker
Spot / Underlying Price
Mode: GEX / VEX / ATLAS / unknown
Bias
Key Hold Level
Trigger / Reclaim Level
King Node / Target Magnet
Gatekeeper / Wall
Danger Zone
Targets
Invalidation
My Trade Opinion
Clean One-Liner

`My Trade Opinion` is required because the user explicitly wants the actionable opinion layer, not just mapped levels.

Use conditional logic the user prefers:

Hold/reclaim X → target Y
Reject X → fade to Y
Lose X → downside opens to Z
Bullish above X / bearish below Y / neutral inside range

## King Node Rules

King Node = largest visible absolute exposure node / destination / magnet / pin zone. It is **not automatically bullish or bearish**.

- King Node above price = potential upside magnet, but long only if price holds support/reclaims structure and tape confirms.
- King Node below price = potential downside magnet, but short only if price loses support/accepts lower.
- Price sitting on King Node = pin/chop/decision zone, not an entry by itself.
- Massive negative wall directly overhead blocks “long-and-strong” language until cleared.
- Large negative node under/at spot is a danger/slippery zone; if lost, downside can accelerate.
- Positive node below spot can act as cushion only while it holds; once lost, reassess.

## GEX vs VEX

**GEX / Gamma**: Intraday, 0DTE, pinning, same-day magnets, dealer gamma battlegrounds, scalp context.

**VEX / Vanna**: Weekly/swing posture, volatility pressure, stair-step accumulation, larger expiration gravity.

Combined conviction improves when GEX and VEX agree. If they conflict, label the read mixed and require stricter confirmation.

## OPEX Nodes

OPEX nodes are expiration gravity, not automatic entries.

- Before expiration: can attract/pin price.
- At expiration: can create battle/chop/pinning.
- After expiration: node can disappear, release, or reshuffle.
- Positive OPEX GEX = cushion/pin/magnetic pillow if respected.
- Negative OPEX GEX = slippery/acceleration/danger if accepted into.

## ATLAS / Market Context

Use ATLAS/TRINITY as broader market confluence for SPXW, SPY, QQQ, and VIX.

Before giving high-conviction ticker longs, check whether the market is supportive when ATLAS context is supplied. If SPXW/SPY/QQQ are under reclaim levels or VIX is elevated, lower ticker-long conviction and prefer sniper-only setups.

## Screenshot Procedure

1. Inspect image with vision tooling.
2. Identify mode from visible tab/header; if unclear, say unknown.
3. Read ticker, spot, current move, visible expirations where readable.
4. Extract prominent levels by absolute exposure magnitude near spot and key upper/lower zones.
5. Identify King Node, nearest gatekeeper/wall, current pin/decision zone, support, downside danger, and air pocket if visible.
6. Convert into Kian conditional logic with targets and invalidation.
7. Mark uncertainty when values are too small or blurry; never invent precision.
8. Keep Telegram responses complete and not overlong. If a prior answer was clipped or the user asks “where is the rest,” resend the full concise card immediately, not just an apology.

## Compact Card Template

```text
✨ SKYLIT HEATSEEKER [GEX/VEX/ATLAS] READ — [TICKER]

Ticker: [ticker]
Spot / Underlying Price: [spot]
Mode: [mode]
Bias: [bias]
Current Zone: [pin/decision/range]
Key Hold Level: [level]
Trigger / Reclaim: [level]
King Node / Magnet: [level + visible value if readable]
Gatekeeper / Wall: [level]
Danger Zone: [level]
Targets: [target path]
Invalidation: [level/reaction]
My Trade Opinion: [short actionable view; required]
Clean One-Liner: [hold/reclaim/lose logic]
```

## Pitfalls

- Do not equate King Node above price with “long and strong.”
- Do not call spot-on-node setups entries; call them pin/chop/decision zones.
- Do not chase midpoint trades between nearby nodes.
- Do not treat far OTM magnets as immediate targets if gatekeepers stand in the way.
- Do not ignore massive negative walls directly overhead.
- Do not overstate exact values from small fonts; label uncertainty.
- Do not add Markdown asterisks/bold markers to routine heatmap cards; the user wants clean copy/paste text.
- Do not omit `My Trade Opinion`; the user explicitly wants it in the card.

## Reference Files

- `references/kian-session-rules.md` contains session-specific lessons and examples from Kian’s heatmap workflow.
