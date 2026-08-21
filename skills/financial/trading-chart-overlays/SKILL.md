---
name: trading-chart-overlays
description: Use when plotting trading levels on chart screenshots.
---

# Trading Chart Overlays

Use this skill when the user sends a TradingView/chart screenshot and wants GEX, VEX, ATLAS, flow, support/resistance, or price levels plotted on top of it as a static or interactive artifact.

## Core workflow

1. Identify the ticker, timeframe, current price, and visible right-axis price scale from the chart screenshot.
2. Calibrate the screenshot y-axis using two or more visible right-axis price labels when possible.
3. Map each requested level to a horizontal line on the chart.
4. Use clear color semantics.
5. Generate a static annotated image first if the user wants quick markup.
6. Generate an interactive HTML artifact when the user asks for zooming, sharing, or Cloudflare delivery.
7. Verify the artifact visually before sending the final link.

## Color semantics

**Green**: support, positive GEX cushion, lower bounce shelf.

**Yellow**: magnet, pin target, upside wall.

**Purple**: negative GEX, slippery zone, danger/rejection, deeper risk magnet.

**White**: current price, trigger, active battle zone.

## Interactive artifact requirements

The interactive version should include zoom, free drag-to-pan, reset, label toggle, jump-to-level buttons, and a right-side current stock price tag. The chart viewport should be a fixed-height clipped container: zoom/pan changes the rendered chart layer inside the viewport, not the viewport's page footprint. Fully zoomed out should show the full selected chart range with dynamic y-range margins; do not lock the latest candle to the right edge — allow side padding and free pan whitespace on both sides. Keep chart title and level legend as fixed HUD overlays outside the transformed chart shell, with the legend defaulting to the top-right of the chart area so zooming cannot push either offscreen. If lower studies are included, render Volume, VWAP, and TTM as separate fixed containers/panes under the price chart rather than one merged screenshot strip.

Add Y-axis spacing controls so the user can stretch/compress **overlay price-level spacing** independently from normal zoom. Use buttons like `Y Space +` and `Y Space -`; Shift+mouse wheel is a useful optional shortcut.

Critical implementation rule: Y-axis spacing must behave like changing the chart's price scale, not like moving only overlays and not like stretching every UI label. Do **not** use CSS `scaleY()` or `scale(x, y)` on the whole chart shell. Split the artifact into layers: (1) a fixed-height clipped price pane, (2) lower volume/TTM/indicator panes that stay static and do not move, (3) overlay levels/zones, and (4) a custom re-rendered y-axis/tick-label layer. Y Space may vertically transform only the clipped price-pane bitmap around the current-price anchor so candles and moving averages plot to the widened price scale, but all text labels, y-axis ticks, level tags, sidebar text, and lower indicators must remain normal geometry. Store calibrated base top percentages/prices and apply the same `spacedTop = anchor + (baseTop - anchor) * yStretch` mapping to overlay levels, zones, custom y-axis ticks, and price tags so levels stay aligned with widened tick spacing.

Clean-edge caveat: if the source is only a screenshot bitmap, vertically stretching candle pixels will always introduce some blur/soft edges. First mitigation: cap normal zoom at the screenshot's native 1:1 scale and keep further inspection as crop/pan, not bitmap upscaling; also cap Y Stretch to a moderate range. Best implementation: fetch/export OHLC data and rebuild the price pane as SVG/canvas primitives (candles, wicks, moving averages) at transformed coordinates while keeping lower volume/TTM panes static if only screenshot data is available for them. This makes Y Space redraw coordinates instead of stretching pixels, preserving clean candle edges. Do not promise clean re-rendered candles from a screenshot alone; use OHLC/export data or a charting data API for exact candle reconstruction.

Serve the HTML and chart image from `/tmp` using a local HTTP server, then expose with Cloudflare Tunnel when the user asks for a shareable link.

## Legibility rules from user correction

Candle visibility comes first. Do not cover candles or the right price axis with large labels.

Default to thin, semi-transparent lines with small price-only tags.

Keep full explanations in a sidebar or compact legend instead of directly on top of the chart.

Do not place GEX/VEX labels on the right price axis. The right side should primarily show the current stock price tag.

Default view should fit the full chart width so the right price axis is visible before zooming.

## ATLAS-related overlay notes

Skylit ATLAS appears to combine a left strike/price ladder with live intraday charts for products like SPXW, SPY, and QQQ. The ladder shows option-derived pressure levels and the chart shows real-time reaction to those levels.

When ATLAS screenshots are used as a source, treat green/yellow levels as likely cushions, pins, magnets, or walls; treat purple/magenta levels as likely negative/slippery zones, danger areas, or rejection/breakdown zones. State uncertainty when the font is too small for exact dollar values.

## Pitfalls

If labels are still hard to read, remove most in-chart text and move detail into the sidebar.

If nearby levels crowd together, use Y-axis spacing instead of making labels larger.

If the price axis is clipped, adjust default scale to fit the chart width before applying zoom/pan.

If current price is important, add a clean stock price tag on the right side near the current price line, separate from heatmap labels.

*Disclaimer: Trading chart overlays are for research and education only; they are not financial advice.*
