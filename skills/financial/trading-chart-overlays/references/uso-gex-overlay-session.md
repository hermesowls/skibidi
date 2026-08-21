# Session Notes: USO GEX Interactive Overlay

## User corrections captured

The first interactive version was too hard to read because large labels sat over candles and the right price axis.

The corrected design moved detail out of the candle area, used thin semi-transparent lines, kept compact level tags, and placed the full trade map in a sidebar.

The user specifically asked for the current stock price on the right side of the chart, separate from the heatmap level labels.

The user then requested a feature to space out the y-axis. This became a required control for future interactive overlays.

## Recommended default UI

Header controls: `Zoom +`, `Zoom -`, `Y Space +`, `Y Space -`, `Reset`, `Toggle labels`.

Chart interactions: normal wheel/pinch zoom, drag-to-pan, Shift+wheel for Y-axis spacing.

Level overlays: thin, semi-transparent lines; small price-only tags; full explanations in a sidebar or small legend.

Current price: right-side tag near current price line, e.g. `USO $126.98`.

Sidebar: clean bullish path, invalidation, downside path, jump buttons, and legend.

## Implementation notes

Use an HTML page with the chart screenshot as a fixed-size background image. Create absolutely positioned divs for each level and zone. Calibrate level positions from the chart's visible right-axis labels.

For Y-axis spacing, keep horizontal scale separate from vertical stretch. In CSS transform terms, use separate x and y scaling such as `scale(scale, scale * yStretch)`.

Fit the full chart width by default to avoid clipping the right price axis, then let zoom/pan modify the view.

When exposing via Cloudflare, serve `/tmp` through a local HTTP server and point cloudflared at that port.