---
name: skylit-trading-cards
description: Use when producing Skylit heatmap trading cards.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [financial, trading, skylit, heatseeker, gex, vex, atlas]
    related_skills: [skylit-heatmap-analysis]
---

# Skylit Trading Cards

Use this skill when converting Skylit / Heatseeker / ATLAS GEX/VEX screenshots into copy/paste-friendly trading cards. This is the output-layer companion to general Skylit heatmap interpretation: it focuses on concise trader messaging, conditional levels, and user-specific card style preferences.

## Core Output Rules

Use plain text labels, not Markdown bold. Do not wrap routine card labels in `**` or add decorative asterisks when the output is meant to be copied into a chat.

Every heatmap or ATLAS card must include `My Trade Opinion`. Place it near the top immediately after `Bias`, not buried near the bottom. The actionable opinion layer must be obvious before the detailed level map.

If a field is not visible, say `not visible` or `unclear`; do not invent precision. If exact node values are visible, include the expiration date so front-expiry scalp context is separated from weekly/monthly swing context.

## Standard Card Template

```text
Ticker:
Spot / Underlying Price:
Current Move:
Mode:
Timeframe:
Bias:
My Trade Opinion:
Current Zone:
Key Hold Level:
Immediate Trigger Level:
King Node / Main Magnet:
Later-Expiry King Node / Major Cluster:
Gatekeeper / Wall:
Upside Targets:
Downside Trigger:
Bearish Targets:
Invalidation For Calls:
Invalidation For Puts:
Clean One-Liner:
```

Keep `My Trade Opinion` directly after `Bias` so it appears before the detailed level map and cannot be missed.

## Expiration Scan Discipline

Do not only read the front expiry. Scan the full visible expiration stack.

If a further expiration contains the largest absolute node or a material exposure cluster, include it and label it clearly as later-expiry / weekly / swing context.

Use language like:

```text
Later-Expiry King Node: $110 on 2026-10-16 around +$192.3M
Meaning: Major weekly/monthly magnet, not an immediate scalp entry. Price still has to clear $100 and $105-$106 first.
```

Separate immediate trade execution levels from later-expiry magnets. A far node can shape bias, but it is not the entry if gatekeepers stand in the way.

## King Node Discipline

King Node means destination / magnet / pin / decision zone, not automatic entry.

- King Node above price = potential upside magnet only after support holds and reclaim levels clear.
- King Node below price = potential downside magnet only after support fails and price accepts lower.
- Price sitting on a King Node = pin/chop/decision zone.
- Negative wall directly overhead blocks long-and-strong language until cleared.
- Positive support below price is a cushion only while it holds.

## Conditional Trade Logic

Always translate the map into simple trading logic:

```text
Hold X -> target Y
Reclaim X -> target Y/Z
Reject X -> fade to Y
Lose X -> downside opens to Z
Bullish above X / bearish below Y / neutral inside range
```

Avoid midpoint trades when price is trapped between nearby nodes. Say `wait for reclaim or breakdown` when the setup is not clean.

## My Trade Opinion Standard

`My Trade Opinion` should be practical and decisive but conditional. It should answer how to treat the setup, not just describe the map.

Good examples:

```text
My Trade Opinion: I’d lean cautiously bullish while it holds $95-$96, but I would not chase blindly after a +4.5% move. The clean long is $98 reclaim targeting $100. If $95 fails, I’d expect a pullback toward $92-$91 first.
```

```text
My Trade Opinion: I’d stay hands-off in the midpoint. Best long is reclaim/hold above $150. Best short is failed reclaim at $150 or clean loss of $145.
```

## Kian-Style Card Preferences

Kian prefers complete but trader-clean cards: no long theory unless asked, no Markdown decoration, and the actionable opinion near the top. Verify the ticker from the screenshot header; if the user label conflicts with the screenshot, call out the mismatch and correct the card.

For Kian-style reads, include full visible-expiration scanning and label later-expiry King Nodes as weekly/swing context rather than immediate scalp entries.

Detailed session refinements are preserved in `references/2026-09-kian-heatmap-card-lessons.md`.

## Accuracy Pitfalls

- Read the ticker carefully from the screenshot header before writing the card.
- If the visible tab/header is unclear or inconsistent with the hover label, label mode as unclear/mixed instead of pretending certainty.
- Include further-expiration King Nodes when visible, but do not shortcut price straight to them.
- Do not omit `My Trade Opinion`; put it immediately after `Bias` so it cannot be missed or clipped below the fold.
- Do not use Markdown asterisks in routine cards.
