---
name: dealer-level-chart-analysis
description: Use when reading dealer levels or plotting them on charts.
---

# Dealer-Level Chart Analysis

Use this skill when the user sends Skylit-style GEX/VEX heatmaps, ATLAS screenshots, or asks to plot dealer-derived levels on a TradingView/chart screenshot.

This supplements the protected `skylit-ai` skill when that bundled skill cannot be edited.

## Output style for this user

Keep reads simple, tradable, and level-driven. The user often wants confirmation of a thesis like: “as long as it holds 215, 220 should pop.” Validate, refine, and state the clean line.

Preferred compact structure:

**Ticker**: symbol if visible, otherwise say not visible.

**Current Price**: price from screenshot.

**Key Hold**: support/trigger that must hold.

**Trigger**: reclaim/acceptance level that improves probability.

**Target / Magnet**: next major GEX/ATLAS level.

**Invalidation**: level where the idea is wrong.

**Clean Read**: one sentence trading plan.

Avoid bloated explanations unless the user asks for teaching mode.

## GEX/VEX heatmap interpretation

**GEX**: best for intraday/0DTE pin, cushion, gamma walls, and premium-burn zones.

**VEX**: best for 1-week/swing volatility magnets and directional pressure.

**Positive yellow/green levels**: cushions, magnets, pin zones, or support shelves depending on price reaction.

**Negative purple levels**: slippery/danger zones where price may reject, accelerate, or behave less cleanly.

Always describe current spot relative to the nearest level, then map the path:

**Bullish path**: hold current support → reclaim trigger → target next magnet/wall.

**Bearish path**: lose current support → fail reclaim → target next lower magnet/cushion.

## ATLAS framework

ATLAS is treated as a live dealer-level map for SPXW/SPY/QQQ or other supported tickers. It combines a left ladder of option-derived levels with intraday charts on the right.

**Left ladder**: strike/price levels plus dollar exposure values.

**Current price marker**: active row/white marker showing where price sits relative to the ladder.

**Green/teal zones**: likely supportive or magnetic positive exposure; can act as cushions, pins, or targets.

**Purple zones**: likely negative/slippery exposure; can act as danger zones, failed holds, acceleration zones, or rejection areas.

**Yellow/gold highlight/dots**: important derived/king levels, magnets, walls, or high-priority dealer levels.

**Right charts**: live intraday candles reacting to the ladder levels. Use price action at these lines to decide whether a level is acting as support, resistance, or a break/reclaim trigger.

## ATLAS trade interpretation

**Bullish reclaim**: Price reclaims a ladder/ATLAS cluster and holds above it; next higher cluster becomes target.

**Bearish rejection**: Price rejects under a cluster or loses a purple/negative zone; next lower cluster becomes target.

**Cross-market confirmation**: SPY, QQQ, and SPXW agreeing improves confidence. Example: SPY reclaiming 773-774, QQQ reclaiming 721, and SPXW reclaiming 7755-7760 together is stronger than one ticker alone.

**Avoid zone**: Do not force trades in the middle between clusters without a clean reclaim/rejection. This is premium-burn/chop territory.

## Legibility handling

If the font is small, explicitly separate what is readable from what is uncertain. General structure, tickers, prices, selected modes, clusters, and chart reactions are usually readable; exact dollar values on tiny ladder badges may need a zoomed crop.

Best request format for ATLAS training: ask for one zoomed crop of the left ladder plus one normal full view of the right charts.

## Chart level plotting workflow

When the user asks to plot heatmap levels on a chart:

1. Inspect the chart screenshot and estimate the plot-area/right-axis scale from visible price labels.
2. Map heatmap levels to horizontal lines on the screenshot.
3. Use colors consistently:

**Green**: support / positive GEX cushion.

**Yellow**: magnet / pin target / wall.

**Purple**: negative GEX danger or deeper risk magnet.

**White**: current price / trigger / battle zone.

4. Create a static annotated image first when useful.
5. For interactive delivery, create an HTML overlay with the chart image as the background, absolutely positioned horizontal levels, hover/tap labels, shaded zones, and a side trade map.
6. Serve `/tmp` locally with `python3 -m http.server 8000 --directory /tmp` using Hermes background process handling, not shell `&` wrappers.
7. Expose the local page with a Cloudflare quick tunnel.
8. Verify the public URL returns HTTP 200 before sending.

## Interactive overlay final response

Final response should be concise and include the public Cloudflare link plus the trade map:

**Main Read**: hold/reclaim trigger → stepping stone → magnet/wall.

**Invalidation**: lose trigger/support → lower cushion → deeper risk magnet.

Do not overexplain after the artifact is live; the user wants the link and actionable levels.

## Pitfalls

Do not guess exact tiny ATLAS values if font is too small. Say what is readable and request a zoomed crop if precision matters.

Do not treat a bright upside magnet as an automatic long; check whether negative/slippery levels sit between spot and the magnet.

Do not chase calls/puts in the middle of a narrow gamma battleground. Require reclaim/rejection confirmation.

Do not present plotted levels as exact market data if they were mapped from a screenshot; call them accurate enough for visual decision support.
