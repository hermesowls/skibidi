"""Analyst Style Learning Engine & Discord Category Auto-Discovery."""

import json
import logging
import os
import re
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from plugins.analyst_trader.db import AnalystDatabase
from plugins.analyst_trader.parser import DiscordBackfillEngine
from plugins.analyst_trader.technical_indicators import TechnicalIndicatorsEngine

logger = logging.getLogger(__name__)


class CategoryAutoDiscoverer:
    """Discovers channels inside the Discord 'alerts' category and auto-registers new analysts."""

    def __init__(self, db: Optional[AnalystDatabase] = None) -> None:
        self.db = db or AnalystDatabase()
        self.engine = DiscordBackfillEngine(self.db)

    def sync_from_channel_directory(self) -> List[Dict[str, Any]]:
        """Sync analyst channels directly from ~/.hermes/channel_directory.json."""
        dir_path = Path.home() / ".hermes" / "channel_directory.json"
        if not dir_path.exists():
            return []

        try:
            with open(dir_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            discord_channels = data.get("platforms", {}).get("discord", [])
            newly_registered = []

            for ch in discord_channels:
                ch_id = str(ch.get("id") or "")
                ch_name = str(ch.get("name") or "")
                if not ch_id or ":" in ch_id:
                    continue
                if "🌟" in ch_name or "alert" in ch_name.lower() or "analyst" in ch_name.lower():
                    existing = self.db.get_analyst_by_channel(ch_id)
                    if not existing:
                        clean_name = ch_name.replace("🌟｜", "").replace("🛎️｜", "").replace("-", " ").title().strip()
                        analyst = self.db.register_analyst(ch_id, ch_name, clean_name)
                        if analyst:
                            newly_registered.append(analyst)
                        logger.info("Auto-synced analyst channel: #%s (ID: %s)", ch_name, ch_id)

            return newly_registered
        except Exception as e:
            logger.warning("Failed to sync analyst channels from channel_directory.json: %s", e)
            return []

    def discover_and_register_channels(self, channels_payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process list of channel dicts (from Discord API) and register analyst channels under 'alerts' category."""
        category_ids = set()
        for ch in channels_payload:
            if ch.get("type") == 4 and "alert" in str(ch.get("name", "")).lower():
                category_ids.add(ch.get("id"))

        newly_registered = []
        for ch in channels_payload:
            ch_id_val = ch.get("id")
            if not ch_id_val:
                continue
            ch_id = str(ch_id_val)
            ch_name = str(ch.get("name") or "")
            parent_id = ch.get("parent_id")

            if (parent_id and parent_id in category_ids) or "🌟" in ch_name or "alert" in ch_name.lower() or "analyst" in ch_name.lower():
                existing = self.db.get_analyst_by_channel(ch_id)
                if not existing:
                    clean_name = ch_name.replace("🌟｜", "").replace("🛎️｜", "").replace("-", " ").title().strip()
                    analyst = self.db.register_analyst(ch_id, ch_name, clean_name)
                    if analyst:
                        newly_registered.append(analyst)
                    logger.info("Auto-discovered new analyst channel: #%s (ID: %s)", ch_name, ch_id)

        return newly_registered


class AnalystStyleLearner:
    """Analyzes historical trades, chat context, and technical chart indicators to learn each analyst's trading style and philosophy."""

    def __init__(self, db: Optional[Any] = None) -> None:
        if isinstance(db, str):
            from plugins.analyst_trader.db import AnalystDatabase
            self.db = AnalystDatabase(db)
        else:
            self.db = db or AnalystDatabase()
        self.ti_engine = TechnicalIndicatorsEngine()
        self._cboe_cache: Dict[str, List[Dict[str, Any]]] = {}

    def _fetch_cboe_bars(self, ticker: str) -> List[Dict[str, Any]]:
        """Fetch historical daily bars from CBOE, cached in-memory."""
        ticker_up = ticker.upper()
        if ticker_up in self._cboe_cache:
            return self._cboe_cache[ticker_up]
        try:
            url = f"https://cdn.cboe.com/api/global/delayed_quotes/charts/historical/{ticker_up}.json"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8")).get("data", [])
                self._cboe_cache[ticker_up] = data
                return data
        except Exception as e:
            logger.debug("Failed to fetch CBOE bars for %s: %s", ticker, e)
            self._cboe_cache[ticker_up] = []
            return []

    def _get_ta_at_date(self, ticker: str, date_str: str) -> Dict[str, Any]:
        """Sorted observed daily bars, excluding same-day and unavailable evidence.

        Identical duplicates collapse. Conflicting duplicates abstain rather than
        select a revision whose original availability cannot be established.
        """
        from plugins.analyst_trader.learning_evidence import aware_time, observed_number
        unknown = self.ti_engine.compute_technical_indicators([])
        try:
            cutoff = aware_time(date_str)
        except (ValueError, TypeError):
            return unknown
        observed = {}
        for bar in self._fetch_cboe_bars(ticker):
            try:
                stamp = aware_time(bar['date'])
                available = aware_time(bar['available_at'])
                if stamp.date() >= cutoff.date() or available >= cutoff or available < stamp:
                    continue
                close = observed_number(bar.get('close'))
                volume = observed_number(bar.get('volume'))
                if close is None or close <= 0:
                    return unknown
                value = (close, volume if volume is not None and volume >= 0 else None)
                if stamp in observed and observed[stamp] != value:
                    return unknown
                observed[stamp] = value
            except (KeyError, ValueError, TypeError):
                continue
        history = [observed[k] for k in sorted(observed)]
        volumes = [v for _, v in history[-20:]]
        rvol = None
        if len(volumes) == 20 and all(v is not None for v in volumes):
            total = sum(volumes)
            if total > 0:
                rvol = volumes[-1] / (total / 20)
        return self.ti_engine.compute_technical_indicators(
            [p for p, _ in history], rel_volume=rvol,
            intraday_volume=history[-1][1] if history else None)

    def _parse_chat_context(self, entry_message_id: Optional[str]) -> Dict[str, Any]:
        """Extract trade thesis, play type, sizing, and targets from raw_messages."""
        if not entry_message_id:
            return {"setup_type": "standard", "raw_thesis": "", "sizing_notes": "", "has_stop_loss": False, "targets": []}

        conn = self.db._get_connection()
        cur = conn.execute("SELECT content, embeds_json FROM raw_messages WHERE message_id = ?", (entry_message_id,))
        row = cur.fetchone()
        if not row:
            return {"setup_type": "standard", "raw_thesis": "", "sizing_notes": "", "has_stop_loss": False, "targets": []}

        content = row["content"] or ""
        embeds_json = row["embeds_json"] or ""
        text_corp = content

        if embeds_json:
            try:
                embeds = json.loads(embeds_json)
                for emb in embeds:
                    text_corp += " " + emb.get("title", "") + " " + emb.get("description", "")
                    for fld in emb.get("fields", []):
                        text_corp += " " + fld.get("name", "") + " " + fld.get("value", "")
            except Exception:
                pass

        text_lower = text_corp.lower()

        # Classify setup type
        setup_type = "standard"
        if "lotto" in text_lower or "er lotto" in text_lower:
            setup_type = "lotto"
        elif "swing" in text_lower or "starter swing" in text_lower or "light swing" in text_lower or "small swing" in text_lower:
            setup_type = "swing"
        elif "hedge" in text_lower:
            setup_type = "hedge"
        elif "day trade" in text_lower or "scalp" in text_lower:
            setup_type = "daytrade"
        elif "leap" in text_lower:
            setup_type = "leap"

        # Sizing notes
        sizing_notes = ""
        for pat in [r"\b(?:1/2|1/4|3/4|half)\s*(?:position|size|th position)\b", r"\bstarter\b", r"\brisk\s*free\b", r"\b\d+\s*c\b"]:
            m = re.search(pat, text_lower)
            if m:
                sizing_notes = m.group(0)
                break

        has_sl = bool(re.search(r"\b(sl|stop|stop loss|under|above|risking)\b", text_lower))
        targets = re.findall(r"\btp:?\s*([\d\s,]+)", text_lower)

        return {
            "setup_type": setup_type,
            "raw_thesis": text_corp.strip()[:200],
            "sizing_notes": sizing_notes,
            "has_stop_loss": has_sl,
            "targets": targets[0].strip() if targets else "",
        }

    def analyze_analyst(self, analyst_name: str, cutoff: Optional[str] = None) -> Dict[str, Any]:
        """Describe only legacy outcomes available at the explicit version cutoff.

        updated_at is the availability of the current mutable outcome revision,
        not its exit event time. Naive/missing legacy times remain unknown.
        """
        from datetime import timezone
        from .learning_evidence import observed_number, aware_time
        cutoff = cutoff or datetime.now(timezone.utc).isoformat()
        clock = aware_time(cutoff)
        positions = self.db.list_positions(analyst_name=analyst_name, limit=1000)
        retained = {}
        closed_pos = []
        conn = self.db._get_connection()
        try:
            for p in positions:
                quarantined = conn.execute('''SELECT 1 FROM notable_flow n
                    WHERE n.raw_message_id=? AND (COALESCE(n.is_quarantined,0)<>0 OR EXISTS
                    (SELECT 1 FROM flow_candidate_analytics a WHERE a.flow_id=n.flow_id AND COALESCE(a.is_quarantined,0)<>0))''',
                    (p.get('entry_message_id'),)).fetchone()
                reason = ('quarantined' if quarantined else
                          p['status'].lower() if p['status']!='CLOSED' else
                          'unknown_outcome' if observed_number(p.get('realized_pnl')) is None or observed_number(p.get('roi_pct')) is None else None)
                if reason is None:
                    try:
                        values = [p.get(k) for k in ('entry_time', 'exit_time', 'updated_at')]
                        if any(not isinstance(v, str) or len(v) <= 10 for v in values):
                            raise ValueError('Missing aware event/availability timestamp')
                        entry, exit, available = [aware_time(v) for v in values]
                        if not entry <= exit <= available:
                            reason = 'invalid_outcome_time_order'
                        elif available > clock:
                            reason = 'unavailable_at_cutoff'
                    except (ValueError, TypeError):
                        reason = 'unknown_outcome_time'
                if reason: retained[reason] = retained.get(reason,0)+1
                else: closed_pos.append(p)
        finally:
            conn.close()

        if not closed_pos:
            from .learning_store import digest
            import hashlib
            rules = {'classification': 'exploratory_unvalidated', 'validated_rules': [],
                     'high_conviction_setups': [], 'avg_holding_hours': None,
                     'ta_requirements': {'below_200_win_rate_pct': None},
                     'uncertainty': ['No available resolved legacy outcomes']}
            version = self.db.save_learning_version(dict(schema_version=1,
                code_identity=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                config_identity=digest({'minimum_bars': self.ti_engine.minimum_bars}),
                training_cutoff=cutoff, created_at=datetime.now(timezone.utc).isoformat(),
                source_mode='legacy_unknown', evidence_ids=[],
                dataset_selection={'analyst_name': analyst_name, 'retained': retained,
                    'availability_contract': 'aware entry <= exit <= updated_at <= cutoff'},
                uncertainty=rules['uncertainty'], classification='exploratory_unvalidated',
                profile={'analyst_name': analyst_name, 'rules': rules}))
            rules['profile_version'] = version
            return {
                "analyst_name": analyst_name,
                "total_trades": len(positions),
                "closed_trades": 0,
                "win_rate": None,
                "avg_roi_pct": None,
                "retained": retained,
                "preferred_tickers": [],
                "strategy_summary": "Insufficient trade data to establish trading philosophy.",
                "profile_version": version,
                "rules": rules,
            }

        total_trades = len(closed_pos)
        wins = [p for p in closed_pos if float(p["realized_pnl"]) > 0]
        win_rate = (len(wins) / total_trades) * 100.0 if total_trades > 0 else 0.0

        # Holding duration calculation
        durations_hours = []
        for p in closed_pos:
            if p.get("entry_time") and p.get("exit_time"):
                try:
                    t_in = datetime.fromisoformat(p["entry_time"])
                    t_out = datetime.fromisoformat(p["exit_time"])
                    dur = (t_out - t_in).total_seconds() / 3600.0
                    if dur >= 0:
                        durations_hours.append(dur)
                except Exception:
                    pass

        avg_holding_hours = (sum(durations_hours) / len(durations_hours)) if durations_hours else None

        # Average ROI
        rois = [float(p["roi_pct"]) for p in closed_pos if p.get("roi_pct") is not None]
        avg_roi_pct = (sum(rois) / len(rois)) if rois else 0.0

        # Ticker performance tracking
        ticker_perf: Dict[str, Dict[str, Any]] = {}
        # Setup type breakdown
        setup_perf: Dict[str, Dict[str, Any]] = {}
        # TA alignment breakdown
        ta_perf: Dict[str, Dict[str, Any]] = {
            "UNKNOWN": {"wins": 0, "total": 0, "roi_sum": 0.0},
            "TREND_ALIGNED": {"wins": 0, "total": 0, "roi_sum": 0.0},
            "COUNTER_TREND": {"wins": 0, "total": 0, "roi_sum": 0.0},
        }
        # 200 EMA status breakdown
        ema200_perf: Dict[str, Dict[str, Any]] = {
            "UNKNOWN": {"wins": 0, "total": 0, "roi_sum": 0.0},
            "ABOVE_200_EMA": {"wins": 0, "total": 0, "roi_sum": 0.0},
            "BELOW_200_EMA": {"wins": 0, "total": 0, "roi_sum": 0.0},
        }

        winning_dtes: List[int] = []

        for p in closed_pos:
            t = p["ticker"]
            roi = float(p.get("roi_pct") or 0.0)
            is_win = float(p.get("realized_pnl") or 0.0) > 0
            is_call = str(p.get("direction", "call")).lower() in ("call", "long")
            entry_date = (p.get("entry_time") or "")[:10]

            # Chat context
            chat_info = self._parse_chat_context(p.get("entry_message_id"))
            setup_t = chat_info.get("setup_type", "standard")

            # Chart TA at entry
            ta_info = self._get_ta_at_date(t, p.get("entry_time") or "")
            stack_state = ta_info.get("ema_stack_state", "")
            is_above_200 = ta_info.get("is_above_200_ema")

            # Determine TA alignment
            is_bull_stack = "BULLISH" in stack_state or stack_state == "FULL_BULLISH_STACK"
            is_bear_stack = "BEARISH" in stack_state or stack_state == "FULL_BEARISH_STACK"

            if is_above_200 is None:
                alignment = "UNKNOWN"
            elif (is_call and (is_bull_stack or is_above_200)) or (not is_call and (is_bear_stack or is_above_200 is False)):
                alignment = "TREND_ALIGNED"
            else:
                alignment = "COUNTER_TREND"

            # Ticker stats
            if t not in ticker_perf:
                ticker_perf[t] = {"wins": 0, "total": 0, "roi_sum": 0.0}
            ticker_perf[t]["total"] += 1
            ticker_perf[t]["roi_sum"] += roi
            if is_win:
                ticker_perf[t]["wins"] += 1

            # Setup stats
            if setup_t not in setup_perf:
                setup_perf[setup_t] = {"wins": 0, "total": 0, "roi_sum": 0.0}
            setup_perf[setup_t]["total"] += 1
            setup_perf[setup_t]["roi_sum"] += roi
            if is_win:
                setup_perf[setup_t]["wins"] += 1

            # TA alignment stats
            ta_perf[alignment]["total"] += 1
            ta_perf[alignment]["roi_sum"] += roi
            if is_win:
                ta_perf[alignment]["wins"] += 1

            # 200 EMA stats
            ema_key = "UNKNOWN" if is_above_200 is None else "ABOVE_200_EMA" if is_above_200 else "BELOW_200_EMA"
            ema200_perf[ema_key]["total"] += 1
            ema200_perf[ema_key]["roi_sum"] += roi
            if is_win:
                ema200_perf[ema_key]["wins"] += 1

            # DTE
            exp_str = p.get("expiration") or ""
            if exp_str and entry_date:
                try:
                    if len(exp_str) == 10:
                        exp_d = datetime.strptime(exp_str, "%Y-%m-%d")
                    elif "/" in exp_str:
                        parts = exp_str.split("/")
                        exp_d = datetime(2026, int(parts[0]), int(parts[1]))
                    else:
                        exp_d = None
                    if exp_d:
                        entry_d = datetime.fromisoformat(p["entry_time"].replace("Z", "+00:00")).replace(tzinfo=None)
                        dte = (exp_d - entry_d).days
                        if is_win and dte > 0:
                            winning_dtes.append(dte)
                except Exception:
                    pass

        # Sort preferred tickers by win rate & trade count
        sorted_tickers = sorted(
            ticker_perf.items(),
            key=lambda x: (x[1]["wins"] / max(1, x[1]["total"]), x[1]["total"]),
            reverse=True,
        )
        preferred_tickers = [t for t, _ in sorted_tickers[:5]]

        # Observed winning DTE range is descriptive, never an optimized rule.
        preferred_dte_min = min(winning_dtes) if winning_dtes else None
        preferred_dte_max = max(winning_dtes) if winning_dtes else None

        # Synthesize What Worked vs What Failed
        high_conviction_setups = []
        forbidden_setups = []


        # TA insights
        trend_tot = ta_perf["TREND_ALIGNED"]["total"]
        trend_wr = (ta_perf["TREND_ALIGNED"]["wins"] / trend_tot * 100.0) if trend_tot > 0 else 0.0
        counter_tot = ta_perf["COUNTER_TREND"]["total"]
        counter_wr = (ta_perf["COUNTER_TREND"]["wins"] / counter_tot * 100.0) if counter_tot > 0 else 0.0


        above_200_tot = ema200_perf["ABOVE_200_EMA"]["total"]
        above_200_wr = (ema200_perf["ABOVE_200_EMA"]["wins"] / above_200_tot * 100.0) if above_200_tot > 0 else 0.0
        below_200_tot = ema200_perf["BELOW_200_EMA"]["total"]
        below_200_wr = (ema200_perf["BELOW_200_EMA"]["wins"] / below_200_tot * 100.0) if below_200_tot > 0 else 0.0

        ta_requirements = {
            "require_above_200_for_calls": None,
            "preferred_ema_stacks": [],
            "trend_aligned_win_rate_pct": round(trend_wr, 1) if trend_tot else None,
            "counter_trend_win_rate_pct": round(counter_wr, 1) if counter_tot else None,
            "above_200_win_rate_pct": round(above_200_wr, 1) if above_200_tot else None,
            "below_200_win_rate_pct": round(below_200_wr, 1) if below_200_tot else None,
            "unknown_count": ema200_perf['UNKNOWN']['total'],
        }

        sizing_discipline = "Unknown; no validated sizing rule inferred."

        # Compile comprehensive rules dictionary
        rules = {
            "classification": "exploratory_unvalidated",
            "validated_rules": [],
            "hypotheses": [],
            "stated_beliefs": [],
            "uncertainty": ["legacy_source_mode_unknown", "costs_unobserved", "not_independent_or_validated"],
            "observed_behavior": {"closed_count": total_trades, "outcome_basis": "gross_before_unknown_costs"},
            "win_rate_pct": round(win_rate, 1),
            "avg_holding_hours": round(avg_holding_hours, 1) if avg_holding_hours is not None else None,
            "top_tickers": preferred_tickers,
            "avg_roi_pct": round(avg_roi_pct, 1),
            "trade_frequency": "high" if total_trades > 20 else "moderate",
            "optimal_dte_min": preferred_dte_min,
            "optimal_dte_max": preferred_dte_max,
            "high_conviction_setups": high_conviction_setups,
            "forbidden_setups": forbidden_setups,
            "ta_requirements": ta_requirements,
            "sizing_discipline": sizing_discipline,
            "setup_breakdown": {
                k: {
                    "win_rate_pct": round((v["wins"] / v["total"]) * 100.0, 1) if v["total"] > 0 else 0.0,
                    "avg_roi_pct": round(v["roi_sum"] / v["total"], 1) if v["total"] > 0 else 0.0,
                    "total_trades": v["total"],
                }
                for k, v in setup_perf.items()
            },
        }

        call_count = sum(1 for p in closed_pos if str(p.get("direction", "call")).lower() in ("call", "long"))
        put_count = len(closed_pos) - call_count
        if call_count > put_count:
            preferred_direction = "CALL"
        elif put_count > call_count:
            preferred_direction = "PUT"
        else:
            preferred_direction = "ANY"

        # Strategy narrative summary
        strategy_summary = (
            f"Exploratory description: {total_trades} resolved legacy positions; "
            f"{win_rate:.1f}% positive gross PNL, average gross ROI {avg_roi_pct:+.1f}%. "
            "Costs and source mode unknown. No calibrated probability, causal inference, "
            "validated trading edge or execution rule."
        )

        from datetime import timezone
        from .learning_store import digest
        import hashlib
        version = self.db.save_learning_version(dict(schema_version=1,
            code_identity=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            config_identity=digest({'minimum_bars': self.ti_engine.minimum_bars}),
            training_cutoff=cutoff, created_at=datetime.now(timezone.utc).isoformat(), source_mode='legacy_unknown',
            evidence_ids=[p['position_id'] for p in closed_pos],
            dataset_selection={'status':'CLOSED','analyst_name':analyst_name,'limit':1000,
                               'availability_contract':'aware entry <= exit <= updated_at <= cutoff',
                               'retained':retained},
            uncertainty=rules['uncertainty'], classification='exploratory_unvalidated',
            profile={'analyst_name':analyst_name,'rules':rules,'summary':strategy_summary}))
        rules['profile_version'] = version

        # Save to database
        self.db.save_analyst_style(
            analyst_name=analyst_name,
            preferred_tickers=preferred_tickers,
            avg_holding_hours=avg_holding_hours,
            win_rate=win_rate,
            avg_roi_pct=avg_roi_pct,
            preferred_dte_min=preferred_dte_min,
            preferred_dte_max=preferred_dte_max,
            strategy_summary=strategy_summary,
            rules=rules,
            total_trades=total_trades,
            preferred_direction=preferred_direction,
        )

        return {
            "analyst_name": analyst_name,
            "total_trades": total_trades,
            "profile_version": version,
            "closed_trades": total_trades,
            "retained": retained,
            "win_rate": round(win_rate, 1),
            "avg_roi_pct": round(avg_roi_pct, 1),
            "preferred_tickers": preferred_tickers,
            "strategy_summary": strategy_summary,
            "rules": rules,
        }

    def import_paper_outcomes(self):
        from .learning_store import import_outcomes
        return import_outcomes(self.db)

    def record_economic_correction(self, evidence):
        from .learning_store import record_correction
        return record_correction(self.db, evidence)

    def summarize_paper_learning(self, cohort, cutoff):
        from .learning_store import summarize
        return summarize(self.db, cohort, cutoff)

    def learn_all_analysts(self) -> Dict[str, Any]:
        """Execute post-market learning and attribution across all active analysts."""
        conn = self.db._get_connection()
        cur = conn.execute("SELECT DISTINCT analyst_name FROM positions WHERE status = 'CLOSED'")
        analysts = [r[0] for r in cur.fetchall() if r[0]]

        results = {}
        for a in analysts:
            logger.info("Executing attribution learning for analyst: %s", a)
            res = self.analyze_analyst(a)
            results[a] = res

        return {
            "total_analysts_analyzed": len(results),
            "analysts": results,
            "paper_outcomes": self.import_paper_outcomes(),
            "timestamp": datetime.now().isoformat(),
        }


# Canonical alias for imports
AnalystLearningEngine = AnalystStyleLearner
