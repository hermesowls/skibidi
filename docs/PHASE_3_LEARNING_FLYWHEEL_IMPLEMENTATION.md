# Phase 3: The Holy Grail Learning Flywheel Implementation

## Overview
Phase 3 builds the post-market learning and attribution flywheel for the Owlfred market intelligence and trading engine:
1. **Historical Chat & TA Attribution**: Ingest closed positions across analysts (Eva, AB, Jon, Kian, Jon & Kian), join with `raw_messages` to parse chat theses, keywords, and sizing notes, and correlate with underlying chart TA (CBOE historical daily bars, EMA 8/21/50/100/200 stack, 200 EMA position, RVOL, and TTM squeeze).
2. **Attribution Synthesis ("What Worked & Why")**: Segment trades by setup type and TA alignment to derive empirical rules, populating `analyst_styles`.
3. **Notable Flow Case Studies**: Backfill all 603 notable flow records with MFE/MAE excursions, $\Delta$OI carryover, and case study autopsies in `flow_candidate_analytics`.
4. **Model Feedback Loop**: Wire Factor G (Analyst Style Attribution Modifier) into `flow_classifier.py` and `autonomous_risk_manager.py`.
5. **REST API**: Expose `/api/analyst-trader/analyst-styles` and `/api/analyst-trader/flow-candidates` in `hermes_cli/web_server.py`.
