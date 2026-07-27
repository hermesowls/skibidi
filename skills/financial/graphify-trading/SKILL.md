---
name: graphify-trading
description: Graphify Knowledge Graph engine mapping ticker supply-chains, market correlations, and sympathy trading signals across financial workflows.
---

# Graphify Trading Knowledge Graph Skill

Use this skill whenever requested via **Telegram**, **iMessage**, **CLI**, or **TUI** to analyze ticker knowledge graph nodes, supply-chain correlations, and secondary sympathy trade opportunities.

---

## 🕸️ KEY GRAPH CAPABILITIES

1. **Supply-Chain Dependency Mapping**: Connects hardware suppliers, fab partners, and enterprise buyers.
2. **Sympathy Trade Detection**: When institutional flow hits a primary node (e.g. `NVDA`), Graphify scans secondary nodes (`TSMC`, `SMCI`, `AMD`) for sympathy setups.
3. **Local AST & Multi-File Parser**: Uses PyPI `graphifyy` engine for zero-API local graph traversal.

---

## ⛔ FORMATTING LAWS (TELEGRAM & iMESSAGE)

> [!CAUTION]
> 1. **BAN ON BULLET POINTS (`•`, `-`, `*`)**: Format all output lines with bold label prefixes: `**Target Ticker**: NVDA`.
> 2. **BAN ON `<sub>` HTML TAGS**: Use clean markdown italics for disclaimers.

---

## 🛠️ Execution Command

```bash
python3 skills/financial/graphify-trading/scripts/market_graph.py NVDA
```
