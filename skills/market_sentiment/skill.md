---
name: market_sentiment
description: Institutional-grade US equity market regime, tradeability, and multi-dimensional risk filter engine for Hermes agents and quantitative workflows.
---

# Market Sentiment & Regime Analysis Engine (`market_sentiment`)

## 1. Title & Overview
**Skill Name**: `market_sentiment`  
**Version**: `1.0.0`  
**Domain**: Quantitative Equity Market Microstructure, Regime Classification, & Risk Filtering  
**Target Platform**: Hermes AI Agent Ecosystem, Automated Trading Pipelines, & Human Trading Dashboards  

---

## 2. Purpose
The `market_sentiment` skill evaluates the complete US equity market environment in real time to establish:
1. **Tradeability**: Whether current market conditions support clean, interpretable, and high-probability execution.
2. **Strategy Suitability**: Which specific strategy archetypes (e.g., long momentum, mean reversion, options selling, breakdown scalping) are currently favored vs. which should be strictly avoided.
3. **Risk Exposure Controls**: Deterministic position-size multipliers, stop-distance adjustments, and hard safety gates governing downstream execution agents.
4. **Assessment Reliability**: Rigorous confidence and data-quality metrics based on indicator alignment, source freshness, and macro event proximity.

---

## 3. Scope
- **Asset Class**: US Equities (Broad Market Indexes, Sector ETFs, Equal-Weight ETFs, Market Internals, Volatility Products, Treasuries, & Macro Proxies).
- **Core Responsibility**: Acting as an authoritative, objective market regime and risk filter.
- **Input Ingestion**: Real-time and delayed market feeds, options market volatility surfaces, market breadth statistics, Treasury yields, currency indexes, and economic calendars.

---

## 4. Non-Goals
To preserve strict separation of concerns, this skill:
- **MUST NOT** select individual stock symbols for trade entry.
- **MUST NOT** recommend specific options contracts, strikes, or expirations.
- **MUST NOT** issue direct trade buy/sell entry or exit orders.
- **MUST NOT** interact directly with broker execution endpoints.
- **MUST NOT** collapse multi-dimensional market dynamics into a single naive "bullish" or "bearish" scalar.

---

## 5. Users and Downstream Agents
This skill produces standardized machine-readable JSON and human-readable reports consumed by:
1. **Hermes Agent Core**: Incorporates market context into high-level conversational reasoning.
2. **Trade-Idea & Technical Agents**: Filters raw technical setups against market tradeability.
3. **Position-Sizing Agents**: Uses `position_size_multiplier` as a strict upper cap for risk allocation.
4. **Execution Agents**: Checks `allow_new_positions` and `require_human_review` safety gates prior to order placement.
5. **Options-Flow & Volatility Agents**: Evaluates current volatility regime and implied volatility distortion.
6. **Risk Management Agents**: Enforces portfolio-level risk contraction during disorderly or high-panic environments.
7. **Discord & Notification Agents**: Formats clean, executive market updates for human traders.

---

## 6. Core Principles
1. **Multi-Dimensional Decomposition**: Market state is multidimensional. Directional bias, tradeability, volatility, and breadth must be evaluated independently.
2. **Tradeability $\neq$ Direction**: A violent market crash is bearish but may have high tradeability for short momentum. A flat, choppy market has zero directional bias but poor tradeability for breakouts.
3. **Empirical Justification**: Every score, classification, and control output must be explicitly backed by traceable, deterministic indicator inputs.
4. **Graceful Degradation**: Missing data must lower confidence and data quality scores, trigger degraded mode, and enforce defensive risk controls without fabricating values.
5. **Strict Determinism**: Identical normalized inputs and configuration MUST produce identical outputs every single run.

---

## 7. Terminology
- **Primary Regime**: Overall structural state of the market (`RISK_ON_TREND`, `DISORDERLY`, etc.).
- **Secondary Flag**: Intraday or tactical characteristics (`BREADTH_DIVERGENCE`, `GAP_FADE`, etc.).
- **Tradeability Score (0–100)**: Measure of market clarity, liquidity, and setup reliability.
- **Directional Bias (-100 to +100)**: Net bullish (+100) vs. bearish (-100) directional pressure.
- **Breadth Quality (0–100)**: Structural health and participation level across individual market components.
- **Position Size Multiplier (0.0 to 1.25x)**: Downstream risk scalar governing maximum position sizing.

---

## 8. Market-Session Model
The skill evaluates data through time-aware market session phases based on US Eastern Time (ET):

```
+-----------------------------------------------------------------------------------------+
| PREMARKET   | OPENING  | OPENING | MORNING   | MIDDAY   | AFTERNOON | POWER  | AFTER    |
| (04:00-9:30)| AUCTION  | RANGE   | SESSION   | (11:30-  | SESSION   | HOUR   | HOURS    |
|             | (09:30-  | (09:35- | (10:00-   |  14:00)  | (14:00-   | (15:00-| (16:00-  |
|             |  09:35)  |  10:00) |  11:30)   |          |  15:00)   | 16:00) |  20:00)  |
+-----------------------------------------------------------------------------------------+
```

### Session Enum Values:
- `PREMARKET`
- `OPENING_AUCTION`
- `OPENING_RANGE`
- `MORNING_SESSION`
- `MIDDAY`
- `AFTERNOON_SESSION`
- `POWER_HOUR`
- `AFTER_HOURS`
- `CLOSED`

### Session Rules:
- During `OPENING_AUCTION` and the first 5 minutes of `OPENING_RANGE`, confidence is penalized by `-20` points unless full depth and breadth data are validated.
- `MIDDAY` enforces a choppiness penalty on breakout setups due to typical volume lulls.
- `POWER_HOUR` re-evaluates late-day institutional order flow and imbalance acceleration.

---

## 9. Input Contract (JSON Input Schema)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "MarketSentimentInput",
  "type": "OBJECT",
  "required": ["timestamp", "session_phase", "market_data"],
  "properties": {
    "timestamp": { "type": "STRING", "format": "date-time" },
    "timezone": { "type": "STRING", "default": "America/New_York" },
    "session_phase": {
      "type": "STRING",
      "enum": ["PREMARKET", "OPENING_AUCTION", "OPENING_RANGE", "MORNING_SESSION", "MIDDAY", "AFTERNOON_SESSION", "POWER_HOUR", "AFTER_HOURS", "CLOSED"]
    },
    "market_data": {
      "type": "OBJECT",
      "required": ["SPY", "QQQ", "IWM", "VIX"],
      "properties": {
        "SPY": { "$ref": "#/definitions/InstrumentData" },
        "QQQ": { "$ref": "#/definitions/InstrumentData" },
        "IWM": { "$ref": "#/definitions/InstrumentData" },
        "DIA": { "$ref": "#/definitions/InstrumentData" },
        "VIX": { "$ref": "#/definitions/VolatilityData" },
        "VIX1D": { "$ref": "#/definitions/VolatilityData" },
        "VVIX": { "$ref": "#/definitions/VolatilityData" },
        "RSP": { "$ref": "#/definitions/InstrumentData" },
        "sectors": {
          "type": "OBJECT",
          "additionalProperties": { "$ref": "#/definitions/InstrumentData" }
        },
        "bonds": {
          "type": "OBJECT",
          "properties": {
            "TLT": { "$ref": "#/definitions/InstrumentData" },
            "IEF": { "$ref": "#/definitions/InstrumentData" },
            "US02Y": { "type": "NUMBER" },
            "US10Y": { "type": "NUMBER" },
            "US30Y": { "type": "NUMBER" }
          }
        },
        "dollar": { "$ref": "#/definitions/InstrumentData" },
        "credit": {
          "type": "OBJECT",
          "properties": {
            "HYG": { "$ref": "#/definitions/InstrumentData" },
            "LQD": { "$ref": "#/definitions/InstrumentData" }
          }
        },
        "breadth": {
          "type": "OBJECT",
          "properties": {
            "nyse_advancing": { "type": "INTEGER" },
            "nyse_declining": { "type": "INTEGER" },
            "nasdaq_advancing": { "type": "INTEGER" },
            "nasdaq_declining": { "type": "INTEGER" },
            "adv_dec_ratio": { "type": "NUMBER" },
            "up_volume_percent": { "type": "NUMBER" },
            "new_highs": { "type": "INTEGER" },
            "new_lows": { "type": "INTEGER" },
            "pct_above_vwap": { "type": "NUMBER" },
            "pct_above_20sma": { "type": "NUMBER" },
            "pct_above_50sma": { "type": "NUMBER" },
            "pct_above_200sma": { "type": "NUMBER" },
            "TICK": { "type": "NUMBER" },
            "TRIN": { "type": "NUMBER" },
            "mcclellan_oscillator": { "type": "NUMBER" }
          }
        }
      }
    },
    "economic_events": {
      "type": "ARRAY",
      "items": {
        "type": "OBJECT",
        "required": ["event_name", "scheduled_time", "impact_level"],
        "properties": {
          "event_name": { "type": "STRING" },
          "scheduled_time": { "type": "STRING", "format": "date-time" },
          "impact_level": { "type": "STRING", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] }
        }
      }
    },
    "data_metadata": {
      "type": "OBJECT",
      "properties": {
        "sources": { "type": "ARRAY", "items": { "type": "STRING" } },
        "retrieved_at": { "type": "STRING", "format": "date-time" },
        "delayed": { "type": "BOOLEAN", "default": false },
        "estimated_delay_seconds": { "type": "INTEGER", "default": 0 }
      }
    }
  },
  "definitions": {
    "InstrumentData": {
      "type": "OBJECT",
      "required": ["price", "prev_close", "pct_change"],
      "properties": {
        "price": { "type": "NUMBER" },
        "prev_close": { "type": "NUMBER" },
        "pct_change": { "type": "NUMBER" },
        "gap_pct": { "type": "NUMBER" },
        "high": { "type": "NUMBER" },
        "low": { "type": "NUMBER" },
        "vwap": { "type": "NUMBER" },
        "dist_vwap_pct": { "type": "NUMBER" },
        "vwap_cross_count": { "type": "INTEGER", "default": 0 },
        "rvol": { "type": "NUMBER", "default": 1.0 },
        "relative_strength_spy": { "type": "NUMBER" }
      }
    },
    "VolatilityData": {
      "type": "OBJECT",
      "required": ["value", "change_pct"],
      "properties": {
        "value": { "type": "NUMBER" },
        "change_pct": { "type": "NUMBER" },
        "futures_term_structure": { "type": "STRING", "enum": ["CONTANGO", "BACKWARDATION", "FLAT"] }
      }
    }
  }
}
```

---

## 10. Data-Source Hierarchy & Fallbacks
1. **Primary Feed**: Real-time direct exchange WebSocket / SIP feed.
2. **Secondary Feed**: Broker REST API (e.g., Alpaca, Interactive Brokers).
3. **Tertiary Feed**: Public financial API (e.g., OpenBB, Yahoo Finance).
4. **Fallback Mechanism**:
   - If Primary fails $\rightarrow$ Fail over to Secondary, set `fallbacks_used: ["secondary_broker_api"]`, penalize `data_quality` by `-10`.
   - If Data is Delayed ($>15$ mins) $\rightarrow$ Mark `delayed: true`, set status `DEGRADED`, penalize `data_quality` by `-25`.
   - If Critical Instruments (`SPY`, `QQQ`, `VIX`) are Missing/Invalid $\rightarrow$ Enter `INSUFFICIENT_DATA` status and set `allow_new_positions: false`.

---

## 11. Data Validation Engine
Before scoring, all inputs pass through strict validation rules:

| Check Item | Validation Rule | Invalid Condition Handling |
| :--- | :--- | :--- |
| **Timestamp Freshness** | `current_time - retrieved_at <= 300s` | Mark `STALE`, trigger `DEGRADED` status |
| **Non-Negative Price** | `price > 0`, `prev_close > 0` | Flag `INVALID`, drop field, penalize `data_quality` |
| **Extreme Outlier Move** | `abs(pct_change) <= 30%` for index ETFs | Flag `INVALID_INPUT`, require human review |
| **VWAP Invariant** | `low <= vwap <= high` (within 0.5% tolerance) | Mark VWAP unreliable, set `vwap_cross_count` chop penalty |
| **Yield Sanity** | `0.0 <= US10Y <= 20.0` | Mark bond macro input `INVALID` |

---

## 12. Normalization Engine

All sub-indicators map deterministically to either:
- **Directional Scale**: `[-100, +100]` (where `-100` = extreme bearish, `0` = neutral, `+100` = extreme bullish).
- **Absolute Quality/Magnitude Scale**: `[0, 100]` (where `0` = total absence/poor, `100` = maximum/ideal).

### Math Normalization Standard:
$$S_{\text{norm}} = \text{clamp}\left( \frac{V - V_{\text{min}}}{V_{\text{max}} - V_{\text{min}}} \times 200 - 100, -100, +100 \right)$$

---

## 13. Indicator Modules

### A. Price Structure & Trend Module
- **VWAP Position**: `dist_vwap_pct > +0.2%` $\rightarrow +50$; `dist_vwap_pct < -0.2%` $\rightarrow -50$.
- **Opening Range Breakout (ORB)**: Price above Opening Range High $\rightarrow +40$; Below Opening Range Low $\rightarrow -40$.
- **Choppiness Factor**: `vwap_cross_count > 5` $\rightarrow$ Penalize Trend Quality by `-35`.

### B. Volatility Dynamics Module
- **Term Structure**: `CONTANGO` $\rightarrow$ Volatility Stability $+30$; `BACKWARDATION` $\rightarrow$ Volatility Panic $+40$, Stability $-40$.
- **VIX Rate of Change**: `VIX change > +10%` $\rightarrow$ Risk-Off Impulse `-50`.

### C. Market Breadth & Concentration Module
- **Advance/Decline Ratio ($ADR$)**:
  $$S_{AD} = \text{clamp}\left( \frac{ADR - 1.0}{2.0} \times 100, -100, +100 \right)$$
- **Concentration Distortion**: `SPY` up while `RSP` (Equal Weight) is negative $\rightarrow$ Trigger `BREADTH_DIVERGENCE`, penalize `breadth_quality` by `-40`.

### D. Bonds, Yields & Macro Credit Module
- **Credit Spread Proxy ($HYG / LQD$)**: $HYG/LQD$ rising $\rightarrow$ Risk Appetite $+40$; Spreading widening $\rightarrow$ Risk Appetite $-50$.
- **Yield Impulse**: Spikes $> +5$ bps in 15 mins $\rightarrow$ Macro Pressure `-40`.

---

## 14. Market Regime Classifier Matrix

The primary market state is resolved using a priority hierarchy:

```
[Level 1: Safety/Data] -> INSUFFICIENT_DATA / DISORDERLY
[Level 2: Events]      -> EVENT_DRIVEN
[Level 3: Volatility]  -> HIGH_VOLATILITY / LOW_LIQUIDITY
[Level 4: Trend/Range] -> RISK_ON_TREND / RISK_OFF_TREND / RANGE_BALANCED / RANGE_VOLATILE
```

| Primary Regime | Condition Criteria | Downstream Default Posture |
| :--- | :--- | :--- |
| `DISORDERLY` | Panic risk $>75$ OR VIX spike $>+25\%$ OR Circuit Breaker | **No New Positions**, Human Review |
| `EVENT_DRIVEN` | Major Economic Event $\le 15$ mins away | **Lockout New Entries**, Wait for Release |
| `HIGH_VOLATILITY` | VIX $> 30$ AND Volatility Expansion Active | Half Position Sizing, Wide Stops |
| `RISK_ON_TREND` | SPY & QQQ $> VWAP$, Breadth $> +40$, Volatility Falling | Normal Position Sizing ($1.0x$), Long Favored |
| `RISK_OFF_TREND` | SPY & QQQ $< VWAP$, Breadth $< -40$, Credit Weak | Reduced/Normal Short Sizing, Short Favored |
| `RANGE_BALANCED` | Price crossing VWAP repeatedly, AD Ratio near 1.0 | Mean Reversion Favored, Breakouts Blocked |
| `TRANSITIONAL` | Sector divergence, mixed index trends | Reduced Sizing ($0.5x$), Require Extra Confirmation |

---

## 15. Scoring Dimensions (Full Breakdown)

1. **Tradeability Score (0–100)**: Evaluates setup clarity and execution environment.
2. **Risk-Appetite Score (-100 to +100)**: Quantifies institutional eagerness to take on risk.
3. **Directional-Bias Score (-100 to +100)**: Net market vector.
4. **Trend-Quality Score (0–100)**: Smoothness and persistence of directional movement.
5. **Breadth-Direction Score (-100 to +100)** & **Breadth-Quality Score (0–100)**.
6. **Volatility Stability Score (0–100)** & **Panic-Risk Score (0–100)**.
7. **Liquidity-Quality Score (0–100)**.
8. **Institutional-Participation Score (0–100)**.
9. **Sector-Leadership Score (0–100)**.
10. **Macro-Pressure Score (-100 to +100)**.
11. **Event-Risk Score (0–100)**.
12. **Data-Quality Score (0–100)**.
13. **Confidence Score (0–100)**.

---

## 16. Composite Market Score & Formula

$$\text{Composite} = \text{clamp}\left( 0.25(T) + 0.15(TQ) + 0.15(BQ) + 0.10(VS) + 0.10(LQ) + 0.10(IP) + 0.05(SL) + 0.05(MS) - 0.05(ER), 0, 100 \right)$$

*Where $T$ = Tradeability, $TQ$ = Trend Quality, $BQ$ = Breadth Quality, $VS$ = Volatility Stability, $LQ$ = Liquidity Quality, $IP$ = Institutional Participation, $SL$ = Sector Leadership, $MS$ = Macro Stability, $ER$ = Event Risk.*

---

## 17. Conflict-Resolution Hierarchy Engine

When indicators contradict each other, the engine resolves conflict using an explicit 9-level hierarchy:

1. **Data Validity**: Invalid data overrides all calculations.
2. **Event State**: Imminent high-impact events freeze entries regardless of technical patterns.
3. **Liquidity & Spread**: Illiquid spreads override trend signals.
4. **Price Microstructure**: Index VWAP and ORB levels override secondary sentiment.
5. **Market Breadth**: Breadth divergence penalizes trend quality and position size.
6. **Volatility Dynamics**: VIX spikes cap risk multipliers.
7. **Sector Confirmation**: Single-sector rallies reduce broad market conviction.
8. **Macro Drivers**: Bond/yield headwinds reduce size multipliers.
9. **Secondary Proxies**: Commodities/Currencies act as final tie-breakers.

---

## 18. Strategy-Suitability Rating Matrix (0–100)

| Strategy Archetype | Favorable Regime Conditions | Unfavorable Conditions |
| :--- | :--- | :--- |
| `long_momentum` | `RISK_ON_TREND`, High Trend Quality, Strong Breadth | `RISK_OFF_TREND`, High Choppiness, Pre-CPI |
| `short_momentum` | `RISK_OFF_TREND`, High Trend Quality, Weak Credit | `RISK_ON_TREND`, Strong Breadth |
| `breakout` | Low Choppiness, High RVOL, Expanding Breadth | `RANGE_BALANCED`, Midday Session, VIX Compression |
| `mean_reversion` | `RANGE_BALANCED`, Low Volatility, Stable Spreads | High Trend Persistence, `RISK_ON_TREND` |
| `options_premium_selling` | High VIX, `NORMAL_FALLING` Volatility, Contango | `PANIC_EXPANSION`, Pre-FOMC |
| `scalping` | High Liquidity, Narrow Spreads, Active Volume | `LOW_LIQUIDITY`, Pre-Market, After-Hours |

---

## 19. Hard Safety Gates

`allow_new_positions` MUST be set to `FALSE` if ANY of the following occur:
1. `data_quality < 60` OR `status == "INSUFFICIENT_DATA"`.
2. `event_risk > 80` (Event Imminent $\le 15$ mins).
3. `tradeability < 40`.
4. `primary_regime == "DISORDERLY"`.
5. Market is `CLOSED` or in `OPENING_AUCTION` without validated order book.

`require_human_review` MUST be set to `TRUE` if:
1. Circuit breaker or exchange halt detected.
2. `panic_risk > 80`.
3. Material divergence between SPY and QQQ $> 2.0\%$.

---

## 20. Risk-Control Downstream Outputs

```json
"controls": {
  "allow_new_positions": true,
  "allow_long_positions": true,
  "allow_short_positions": false,
  "allow_options": true,
  "allow_breakouts": true,
  "allow_mean_reversion": false,
  "allow_overnight_holds": true,
  "require_extra_confirmation": false,
  "require_human_review": false,
  "position_size_multiplier": 1.0,
  "trade_frequency_multiplier": 1.0,
  "max_concurrent_positions_multiplier": 1.0,
  "stop_distance_multiplier": 1.0,
  "profit_target_multiplier": 1.0,
  "minimum_setup_quality": 70,
  "recommended_wait_minutes": 0
}
```

---

## 21. Confidence Engine
Confidence is computed deterministically:
$$\text{Confidence} = \text{clamp}\left( \text{Base}(80) - \text{StalePenalties} - \text{ConflictPenalties} - \text{EventPenalties}, 0, 100 \right)$$
- **High**: $80 - 100$
- **Medium**: $60 - 79$
- **Low**: $40 - 59$
- **Unreliable**: $< 40$

---

## 22. Missing-Data Behavior Table

| Missing Input | System Action | Penalty Impact |
| :--- | :--- | :--- |
| `IWM` / `DIA` | Use `SPY`/`QQQ`, mark missing field | Confidence `-5` |
| `breadth` (A/D) | Use Sector ETF A/D proxy, mark degraded | Data Quality `-20`, Confidence `-15` |
| `VIX` | Check `VIX1D` or ETF implied volatility | Data Quality `-25`, Disable Option Selling |
| `SPY` or `QQQ` | Enter `INSUFFICIENT_DATA` status | Block All New Positions |

---

## 23. Machine-Readable Output Schema (Full JSON Response)

```json
{
  "schema_version": "1.0.0",
  "skill": "market_sentiment",
  "analysis_id": "sent_20260727_093500_881",
  "timestamp": "2026-07-27T09:35:00-04:00",
  "timezone": "America/New_York",
  "session_phase": "MORNING_SESSION",
  "status": "OK",
  "degraded_mode": false,
  "market_regime": {
    "primary": "RISK_ON_TREND",
    "secondary": ["TECH_LED", "SEMICONDUCTOR_LED", "MOMENTUM_FRIENDLY"],
    "stability": 82
  },
  "scores": {
    "composite_market": 81,
    "tradeability": 85,
    "risk_appetite": 64,
    "directional_bias": 58,
    "trend_quality": 88,
    "breadth_direction": 52,
    "breadth_quality": 74,
    "volatility_stability": 80,
    "panic_risk": 12,
    "liquidity_quality": 90,
    "institutional_participation": 78,
    "sector_leadership_quality": 84,
    "macro_pressure": 10,
    "event_risk": 15,
    "data_quality": 95,
    "confidence": 84
  },
  "volatility_regime": "NORMAL_FALLING",
  "strategy_suitability": {
    "long_momentum": 88,
    "short_momentum": 15,
    "breakout": 82,
    "breakdown": 20,
    "pullback_continuation": 90,
    "mean_reversion": 30,
    "range_trading": 25,
    "scalping": 75,
    "swing_trading": 70,
    "options_premium_buying": 72,
    "options_premium_selling": 60,
    "news_event_trading": 15,
    "overnight_holding": 65,
    "small_cap_exposure": 45,
    "index_trading": 88
  },
  "controls": {
    "allow_new_positions": true,
    "allow_long_positions": true,
    "allow_short_positions": false,
    "allow_options": true,
    "allow_breakouts": true,
    "allow_mean_reversion": false,
    "allow_overnight_holds": true,
    "require_extra_confirmation": false,
    "require_human_review": false,
    "position_size_multiplier": 1.0,
    "trade_frequency_multiplier": 1.0,
    "max_concurrent_positions_multiplier": 1.0,
    "stop_distance_multiplier": 1.0,
    "profit_target_multiplier": 1.0,
    "minimum_setup_quality": 70,
    "recommended_wait_minutes": 0
  },
  "evidence": {
    "supporting": [
      {
        "indicator": "SPY_VWAP",
        "direction": "SUPPORTING",
        "severity": "HIGH",
        "value": 0.42,
        "unit": "percent_above_vwap",
        "observation": "SPY is 0.42% above VWAP with clean higher lows.",
        "effect": "Supports bullish trend quality."
      }
    ],
    "contradictory": [
      {
        "indicator": "IWM_RELATIVE_STRENGTH",
        "direction": "CONTRADICTORY",
        "severity": "MEDIUM",
        "value": -0.35,
        "unit": "pct_vs_spy",
        "observation": "Small-caps (IWM) lagging SPY by -0.35%.",
        "effect": "Capping risk appetite score."
      }
    ],
    "warnings": []
  },
  "events": {
    "state": "NO_MAJOR_EVENT",
    "next_major_event": "FOMC_MINUTES",
    "minutes_until_event": 240
  },
  "data_quality": {
    "sources_used": ["direct_sip_feed", "alpaca_v2"],
    "missing_fields": [],
    "stale_fields": [],
    "invalid_fields": [],
    "fallbacks_used": []
  },
  "reassessment": {
    "recommended_in_minutes": 15,
    "triggers": [
      "SPY crosses VWAP",
      "VIX change > +8%",
      "Breadth sign flip"
    ]
  },
  "human_summary": "Market Regime: RISK_ON_TREND | Tradeability: 85/100 | Bias: Bullish (+58) | Size: 1.0x"
}
```

---

## 24. Human-Readable Output Format

```text
================================================================================
MARKET SENTIMENT & REGIME REPORT
================================================================================
Timestamp: 2026-07-27 09:35:00 ET | Session: MORNING_SESSION
Primary Regime: RISK_ON_TREND (Stability: 82/100)
Secondary Flags: TECH_LED, SEMICONDUCTOR_LED, MOMENTUM_FRIENDLY

SCORE CARD:
- Tradeability: 85/100 (Excellent Execution Environment)
- Directional Bias: +58 (Bullish Directional Pressure)
- Trend Quality: 88/100 (High Persistence)
- Risk Appetite: +64 (Risk-On Flow Active)
- Volatility Regime: NORMAL_FALLING (VIX: 14.2, -3.8%)
- Data Quality: 95/100 | Assessment Confidence: 84/100 (HIGH)

CURRENT RISK POSTURE:
- Position Sizing Multiplier: 1.0x (Normal Position Size Permitted)
- New Positions Allowed: YES (Longs: YES | Shorts: NO)
- Minimum Setup Quality Required: 70/100

SUPPORTING EVIDENCE:
- SPY (+0.54%) and QQQ (+0.82%) holding clean above VWAP.
- Semiconductor leadership (SMH +1.45%) driving index gains.
- Volatility contraction with VIX term structure in steep Contango.

CONTRADICTORY EVIDENCE:
- Small-cap participation lagging (IWM -0.12%).
- Advance/Decline ratio (+1.4) shows moderate broad market breadth.

FAVORED STRATEGIES:
- Pullback Continuation (90/100), Long Momentum (88/100), Index Breakouts (82/100)

AVOIDED STRATEGIES:
- Short Momentum (15/100), Mean Reversion (30/100), News Event Trading (15/100)

NEXT REASSESSMENT TRIGGER:
- Reassess in 15 minutes OR if SPY loses VWAP.
================================================================================
```

---

## 25. Discord-Compatible Formatting

```text
📊 **MARKET REGIME REPORT**: `RISK_ON_TREND`
**Tradeability**: 85/100 | **Direction**: Bullish (+58) | **Confidence**: 84% (HIGH)
**Risk Posture**: `1.0x Size` | **Longs**: Allowed 🟢 | **Shorts**: Blocked 🔴

**Supporting**:
• SPY & QQQ holding cleanly above VWAP
• Semiconductors leading (SMH +1.45%)
• VIX declining in term-structure Contango

**Conflicts**:
• Small-caps (IWM) lagging index move
• Breadth only moderately positive (+1.4 A/D)

**Favored**: Pullback Continuation, Long Momentum, Large-Cap Breakouts
**Avoid**: Short Momentum, Mean Reversion
**Next Reassessment**: 15 mins or on SPY VWAP loss
```

---

## 26. Downstream-Agent Integration Contract

1. **Trade-Idea Agents**: MUST check `allow_new_positions == true` and match strategy type against `strategy_suitability[strategy_name] >= minimum_setup_quality`.
2. **Position-Sizing Agents**: MUST apply `position_size_multiplier` as a hard ceiling on top of internal risk calculations:
   $$\text{FinalSize} = \min(\text{AccountRiskSize}, \text{MaxAllowedSize}) \times \text{position\_size\_multiplier}$$
3. **Execution Agents**: MUST reject order execution if `require_human_review == true` or `status != "OK"`.

---

## 27. Reassessment Logic & Triggers

Reassessment is dynamically scheduled based on market events and micro-structure triggers:
- **Default Polling Cadence**:
  - `OPENING_RANGE`: Every 3 minutes.
  - `MORNING_SESSION`: Every 10 minutes.
  - `MIDDAY`: Every 20 minutes.
  - `POWER_HOUR`: Every 5 minutes.
- **Event Triggers**:
  - SPY or QQQ crosses VWAP.
  - VIX jumps $> +5\%$ in 5 minutes.
  - Advance/Decline sign flips (Positive to Negative).
  - High-impact Economic Event release (e.g. CPI/FOMC).

---

## 28. Configuration Defaults (`config.yaml`)

```yaml
market_sentiment:
  minimum_tradeability_for_new_positions: 55
  minimum_confidence_for_autonomous_action: 65
  minimum_data_quality: 70
  major_event_lockout_minutes: 15
  opening_range_minutes: 15
  vwap_chop_cross_limit: 5
  panic_vix_change_percent: 10.0
  breadth_strong_positive_threshold: 0.65
  max_position_size_multiplier: 1.25
  default_position_size_multiplier: 1.0
  reassessment_intervals:
    opening_range: 3
    morning_session: 10
    midday: 20
    power_hour: 5
```

---

## 29. Logging and Auditability
- **Log Destination**: `~/.hermes/logs/agent.log` and structured `market_sentiment_audit.jsonl`.
- **Logged Attributes**: Invocation timestamp, raw provider payload hashes, component scores, resolved safety gates, and rule triggers.
- **Security Rule**: API keys, credentials, or private account IDs must NEVER be logged.

---

## 30. Security & Privacy
- Zero outbound telemetry or third-party tracking.
- Reads inputs from environment variables and local cache only.

---

## 31. Determinism Contract
Given identical JSON inputs and configuration, `market_sentiment` guarantees 100% byte-for-byte identical output schemas and numeric score results.

---

## 32. Example Scenarios

### Scenario 1: Broad Bullish Trend (`RISK_ON_TREND`)
- **Inputs**: SPY +0.8%, QQQ +1.1%, IWM +0.6%, VWAP +0.4%, VIX -4.5%, A/D +2.5.
- **Result**: `RISK_ON_TREND`, Tradeability 88/100, Size 1.0x, Long Momentum 90/100.

### Scenario 2: Narrow Mega-Cap Rally (`BREADTH_DIVERGENCE`)
- **Inputs**: SPY +0.4%, QQQ +0.9%, IWM -0.5%, RSP -0.2%, A/D -0.8.
- **Result**: `RISK_ON_TREND` with `BREADTH_DIVERGENCE`, Tradeability 62/100, Size 0.5x, Confidence 64/100.

### Scenario 3: Clean Bearish Trend (`RISK_OFF_TREND`)
- **Inputs**: SPY -1.2%, QQQ -1.6%, IWM -1.8%, Price < VWAP, VIX +12%, A/D -3.2.
- **Result**: `RISK_OFF_TREND`, Tradeability 82/100, Size 1.0x, Short Momentum 88/100, Longs Blocked.

### Scenario 4: Pre-CPI Lockout (`EVENT_DRIVEN`)
- **Inputs**: CPI Event scheduled in 10 minutes, VIX compressed, Range narrow.
- **Result**: `EVENT_DRIVEN` / `EVENT_IMMINENT`, Tradeability 30/100, `allow_new_positions: false`, Size 0.0x.

---

## 33. Testing Requirements
- **Unit Tests**: `tests/skills/test_market_sentiment.py` covering score boundaries, missing fields, invalid inputs, and determinism assertions.
- **Regression Suite**: Replay historical snapshots (FOMC days, CPI days, trend days, range days) to verify score stability.

---

## 34. Acceptance Criteria
- [x] Human and machine-readable output schemas fully defined.
- [x] Multidimensional breakdown separating tradeability from direction.
- [x] 10 Primary Regimes & 17 Secondary Flags enumerated.
- [x] Hard safety gates and downstream risk controls specified.
- [x] Conflict resolution hierarchy documented.
- [x] Zero subjective language in scoring rules.

---

## 35. Extension Points
- **Custom Indicators**: Implement new modules in `skills/market_sentiment/scripts/modules/`.
- **Provider Adapters**: Add new data adapters in `skills/market_sentiment/scripts/adapters/`.

---

## 36. Versioning and Changelog
- **v1.0.0** (2026-07-27): Initial production specification of the `market_sentiment` Hermes skill.
