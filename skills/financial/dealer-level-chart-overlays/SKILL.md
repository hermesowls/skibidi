---
name: dealer-level-chart-overlays
description: Use when plotting dealer levels onto chart screenshots.
---

# Dealer-Level Chart Overlays

Use this skill when the user asks to plot options-derived dealer levels from Skylit, GEX, VEX, ATLAS, or heatmap screenshots onto a price chart, or when converting a chart screenshot into an interactive level map.

## Core Goal

Make the chart easier to trade from. The candle chart must stay readable. The overlay should clarify levels without covering price action, candles, or the right-side price scale.

## Static Image Overlay Workflow

1. Identify ticker, timeframe, visible current price, and chart source if visible.
2. Extract levels from the heatmap or user-provided list, keeping their meaning separate: `support/cushion`, `magnet/pin`, `negative gamma/danger`, `trigger/current battle zone`.
3. Calibrate the chart screenshot by matching visible right-axis price labels to pixel Y positions.
4. Draw horizontal levels using a linear price-to-Y mapping from the visible axis.
5. Use color semantics: `green = support/cushion`, `yellow = magnet/pin/wall`, `purple/red = negative gamma/danger`, `white = current price/trigger`.
6. Verify the output visually before sending.

## Interactive Cloudflare Overlay Workflow

1. Build an HTML page in `/tmp` with the chart screenshot as the base image.
2. Add level lines/zones as absolutely positioned overlays.
3. Add zoom controls, wheel/pinch zoom, drag-to-pan, reset, and label toggle.
4. Serve from `/tmp` with `python3 -m http.server 8000 --directory /tmp` using a tracked background process.
5. Expose with `cloudflared tunnel --url http://localhost:8000`.
6. Verify the public `trycloudflare.com` link returns HTTP 200 before sending.
7. Keep the same public link updated if the existing tunnel/server is still running.

## Legibility Rules From User Correction

Do not put big labels directly on the right price axis. They block TradingView prices and make the chart hard to read.

Do not stack labels on top of candles. Use a side legend, floating compact legend, hover/tap labels, or small price-only tags instead.

Make overlay lines thin and semi-transparent by default. Use very low-opacity shaded zones. Strong color is okay, but the candle bodies/wicks must remain visible.

Stop level lines before the right price scale when possible so the native price labels remain readable.

Default to clean mode: small tags or hidden labels, with full explanations in the sidebar/trade map. Add a label toggle for users who want an even cleaner chart.

## Trade Map Output Style

Keep the final read simple and actionable:

**Ticker**: [ticker]
**Current Price**: [price]
**Main Plan**: Hold/reclaim [trigger] → [step] → [target]
**Upside Magnet / Wall**: [level]
**Trigger Zone**: [level/zone]
**Support Zone**: [level/zone]
**Deeper Risk Magnet**: [level]
**Invalidation**: Lose [level]

## ATLAS Usage Notes

When plotting ATLAS levels, treat the left ladder as the source of option-derived exposure levels and the right chart as the live reaction map. For SPXW/SPY/QQQ ATLAS, prefer cross-market confirmation: a bullish setup is cleaner when all three reclaim key ATLAS levels together; bearish is cleaner when all three reject or lose their key levels together.

If ATLAS font is too small, say so directly and avoid quoting exact exposure values. Ask for a closer crop of the ladder only if exact values are required.
