# Skylit No-Data / Empty Heatmap Handling

## Trigger

Use this reference when Skylit accepts a requested ticker but the heatmap does not populate usable strike/node data.

Common visible states:

- `No data`
- `No data available`
- `Select a symbol to view heatmap data`
- Spot/underlying price displays `$0.00`
- Control bar shows the requested ticker/mode but the grid has no strike rows or node values

## Required Output Boundary

A no-data screenshot is a valid proof that the workflow ran, but it is not an analyzable heatmap. Do not infer GEX/VEX structure from a blank grid.

Do not produce:

- King Node
- Gatekeeper zones
- Support/resistance floors/ceilings from Skylit
- Primary targets
- Conviction scores
- Pattern names beyond `No-data / unavailable`

Unless actual node rows and values are visible.

## Recommended Final Response Shape

```markdown
MEDIA:/path/to/screenshot.png

✨ **SKYLIT HEATSEEKER [GEX/VEX] READ — KIAN PROCESS**

**Ticker**: [TICKER]
**Spot / Underlying Price on Skylit**: [$0.00 or visible]
**External Market Price Check**: [$PRICE if checked; label external]
**Mode**: [GEX/VEX]
**Screenshot Artifact**: `/path/to/screenshot.png`
**Skylit Status**: No data available
**Visible Message**: “[exact visible message]”
**Pattern**: Not analyzable from Skylit because no node grid loaded
**King Node**: Unavailable
**Gatekeeper Zones**: Unavailable
**Key Support / Floor**: Unavailable from Skylit
**Key Resistance / Ceiling**: Unavailable from Skylit
**GEX/VEX Confluence**: Not available
**Conviction**: No-trade / no-read due to missing Skylit data

### 🏫 Plain-English Dealer Read
[Say the workflow succeeded but the chart did not return nodes, so a real heatmap thesis cannot be generated.]
```

## Practical Next Steps

- Rerun later after Skylit refreshes.
- Try a different expiration/filter if the UI supports it.
- Confirm Skylit coverage for the symbol.
- Use Skylit API if credentials are available and the app grid is not loading.
- Analyze another ticker with populated GEX/VEX data.
