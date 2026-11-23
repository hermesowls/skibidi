---
name: analyst-performance-report
description: Fetch and format analyst performance metrics, win rates, active open positions, and recent trades for Telegram, Discord, and messaging channels.
---

# Analyst Performance Report Skill

Use this skill whenever a user on Telegram, Discord, Slack, or CLI asks for:
- Analyst performance, win rates, or trading stats (e.g., "How is Eva performing?", "Show Kian's stats", "What's AB's win rate?", "analyst performance")
- Active open positions or trade breakdown for a specific analyst
- Overall analyst comparison or leaderboards

## Execution Instructions

Run the python report helper script using the `process` or `terminal` tool:

```bash
venv/bin/python skills/financial/analyst-performance-report/scripts/get_analyst_report.py --analyst <AnalystName>
```

- If a specific analyst is requested (e.g., "Eva", "Kian", "AB", "Jon"), pass `--analyst <name>`.
- If no analyst is specified (e.g., "show all analyst performance"), run without `--analyst` or pass `--analyst ""` to return all analysts.

## Output Formatting Guidance

When replying in Telegram or Discord:
- Render the exact Markdown formatted output returned by the script.
- Keep the clean emoji structure (`📊`, `🔥`, `🟢`, `🔴`, `🏁`).
- Highlight Win Rate %, Average Closed ROI %, Total Trades, and current open position badges.
