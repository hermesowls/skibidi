---
name: skylit-heatmap-capture-analysis
description: Use when capturing Skylit heatmaps for analysis.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [financial, skylit, heatseeker, screenshots, gex, vex]
    related_skills: [skylit-gex-vex-analysis, skylit-ai, financial-market-data]
---

# Skylit Heatmap Capture & Analysis QA

## Overview

Use this skill when a task requires opening Skylit, selecting a ticker/mode, capturing a GEX or VEX screenshot, and then analyzing the result. It complements `skylit-gex-vex-analysis` by focusing on workflow verification, no-data states, and honest output boundaries.

A screenshot workflow is only successful if the final artifact actually shows the requested ticker, requested mode, and usable strike/node grid. A captured Skylit screen with `No data` is still a real artifact, but it is not enough to produce King Node, Gatekeeper, floor/ceiling, target, or conviction analysis.

## When to Use

- User asks to take a Skylit screenshot and analyze it.
- User asks for GEX/VEX analysis and no screenshot/data was provided yet.
- The Skylit app returns access/login screens, stale ticker state, `$0.00`, or `No data` after ticker selection.
- You need to distinguish real Heatseeker node analysis from workflow/status reporting.

## Capture Verification Steps

1. **Confirm access state.** If the app shows `Access Required` or a login form, complete the available authorized login flow before attempting ticker analysis. Completion criterion: the Heatseeker workspace is visible.
2. **Select requested mode.** For GEX, ensure the GEX tab is selected. For VEX, ensure the VEX tab is selected. Completion criterion: the visible control bar shows the requested active mode.
3. **Select requested ticker.** Use Skylit ticker search/shortcut and wait for the UI to update. Completion criterion: the ticker label in the control bar matches the user’s requested ticker.
4. **Verify usable data.** Check for visible strike rows, expiration columns, node values, and nonzero/valid spot. Completion criterion: the screenshot contains a heatmap grid, not a blank/no-data state.
5. **Crop responsibly.** Crop out top navigation, left nav, banners, and user login identifiers when practical. Completion criterion: artifact focuses on the heatmap grid and relevant controls.
6. **Analyze only what is present.** If nodes are visible, hand off to the `skylit-gex-vex-analysis` framework. If nodes are missing, produce a no-data report instead of fabricated levels.

## No-Data / Empty Heatmap Handling

If Skylit loads a ticker but the grid says `No data`, `No data available`, `Select a symbol to view heatmap data`, shows `$0.00`, or lacks strike rows, treat it as a verified **no-data state**.

Required response behavior:

1. State that the screenshot was successfully captured.
2. Identify ticker, visible mode, visible price, and the exact no-data message when readable.
3. Do not invent King Nodes, Gatekeepers, floors, ceilings, targets, or conviction from a blank grid.
4. If an external spot check is available, label it as external market-price sanity checking, not Skylit heatmap data.
5. Mark Pattern, King Node, Gatekeepers, GEX/VEX confluence, and trade conviction as unavailable/no-read.
6. Attach or reference the screenshot so the user can see the no-data state.
7. Suggest a practical next step: rerun later, try another expiration/filter, confirm ticker coverage, or use Skylit API/live stream if credentials are available.

## Honest Output Boundary

Use this distinction in final replies:

- **Screenshot captured + node grid visible**: proceed with full GEX/VEX chart analysis.
- **Screenshot captured + no-data/blank grid**: report workflow success but analysis unavailable.
- **Login/access blocked**: report access blocker and do not pretend a chart was captured.
- **Ticker mismatch**: recapture before analysis.
- **Mode mismatch**: recapture or explicitly label the mode mismatch before analysis.

## Common Pitfalls

1. **Analyzing a no-data screen.** A no-data screenshot proves the automation ran, not that Heatseeker has usable structure.
2. **Trusting stale tickers.** Always verify the visible ticker label after search; the app can remain on the prior symbol if selection fails.
3. **Using external price as Skylit data.** External market data can sanity-check spot but cannot create GEX/VEX nodes.
4. **Forgetting the artifact.** If the user asked for a screenshot, include the image path/media in the final response.
5. **Overstating certainty.** If GEX/VEX companion mode or SPX/SPY/QQQ confluence was not checked, label it as not checked.

## Support Files

- `references/no-data-empty-heatmap.md` — concise decision rules for Skylit no-data screenshots.

## Verification Checklist

- [ ] Requested ticker visibly matches the chart.
- [ ] Requested GEX/VEX mode is visibly selected.
- [ ] Screenshot artifact path is included.
- [ ] Strike rows and node values are present before full analysis.
- [ ] If no-data, no trade levels are fabricated.
- [ ] External price checks are clearly labeled as external.
- [ ] Final response uses clean Kian-style labels and educational disclaimer when relevant.
