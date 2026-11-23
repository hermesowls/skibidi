import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router";
import {
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  DollarSign,
  Layers,
  Radio,
  RefreshCw,
  Search,
  TrendingUp,
  X,
  Zap,
  ShieldCheck,
  ImageIcon,
  BookOpen,
  ChevronDown,
  ChevronUp,
  ArrowUpDown
} from "lucide-react";
import { api } from "@/lib/api";
import ResearchProfiles from './ResearchProfiles';
import ResearchWatchlist from './ResearchWatchlist';

interface NotableFlowItem {
  flow_id: string;
  source: string;
  ticker: string;
  asset_type: string;
  strike: number;
  call_put: string;
  expiration: string;
  dte: number;
  premium_usd: number;
  premium_raw: string;
  raw_message_id?: string;
  channel_id?: string;
  chart_url?: string;
  local_chart_path?: string;
  llm_review_status?: string;
  llm_reasoning?: string;
  trade_timestamp: string;
  created_at?: string;
  research_candidates?: RecordedResearchDecision[];
  research_history?: { total: number; omitted: number; invalid: number };
}

interface RecordedResearchDecision {
  decision_id?: string; profile_name?: string; policy_version?: string; policy_hash?: string;
  otm_fraction?: number | null; max_otm_fraction?: number | null;
  origin?: string; filter_provenance?: Record<string, string> | null;
  baseline_status?: string; baseline_reasons?: string[]; enhancement_unknowns?: string[];
}

// Only saved candidate fields. The profile editor and live quotes cannot relabel history.
function RecordedResearchCards({ candidates, history }: { candidates?: RecordedResearchDecision[]; history?: { total: number; omitted: number; invalid: number } }) {
  const fraction = (v: unknown) => typeof v === 'number' && Number.isFinite(v) ? `${Number((v * 100).toFixed(6))}%` : 'Unknown';
  const text = (v: unknown) => typeof v === 'string' && v ? v : 'Unknown';
  const strings = (v: unknown): v is string[] => Array.isArray(v) && v.every(x => typeof x === 'string');
  const safe = Array.isArray(candidates) ? candidates.filter(c => c && typeof c === 'object') : [];
  return <div aria-label="Recorded research decisions" className="text-xs whitespace-normal max-w-lg space-y-2 mt-2">
    <p>History: visible source only — not all operational decisions. {history ? `${safe.length} shown of ${history.total}; ${history.omitted} omitted by limits; ${history.invalid} invalid records unavailable. Limits: 10 per source, 100 total.` : 'Counts unknown.'}</p>
    {!safe.length ? <p>Recorded research profile: Unknown — no saved decision</p> : safe.map((c, i) =>
      <article key={typeof c.decision_id === 'string' ? c.decision_id : i} className="border border-slate-700 rounded p-2">
        <p>Profile: {text(c.profile_name)}</p>
        <p>Decision: {text(c.decision_id)}</p>
        <p>Policy: {text(c.policy_version)} · Hash: {text(c.policy_hash)}</p>
        <p>OTM distance: {fraction(c.otm_fraction)} · OTM cap: {c.max_otm_fraction === null ? 'Unlimited' : fraction(c.max_otm_fraction)}</p>
        <p>Policy provenance: {text(c.origin)}</p>
        <p>Filter provenance: {c.filter_provenance && typeof c.filter_provenance === 'object' && !Array.isArray(c.filter_provenance) && Object.values(c.filter_provenance).every(v => typeof v === 'string') ? JSON.stringify(c.filter_provenance) : 'Unknown'}</p>
        <p>Baseline: {text(c.baseline_status)}</p>
        <p>Reasons: {strings(c.baseline_reasons) && c.baseline_reasons.length ? c.baseline_reasons.join(', ') : c.baseline_status === 'QUALIFIED' && strings(c.baseline_reasons) ? 'None recorded' : 'Unknown'}</p>
        <p>Unknowns: {strings(c.enhancement_unknowns) && c.enhancement_unknowns.length ? c.enhancement_unknowns.join(', ') : 'Unknown'}</p>
        <p>Recorded TEST research only; not verified buying, a confirmed setup or execution permission.</p>
      </article>)}
  </div>;
}

// Explicit timezone and calendar validation; never substitute fetch completion.
function evidenceAge(value: unknown): number {
  if (typeof value !== 'string') return NaN;
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(?:Z|[+-](\d{2}):(\d{2}))$/.exec(value);
  if (!parts) return NaN;
  const year = Number(parts[1]), month = Number(parts[2]), day = Number(parts[3]);
  if (month < 1 || month > 12 || day < 1 || day > new Date(Date.UTC(year, month, 0)).getUTCDate()
      || Number(parts[4]) > 23 || Number(parts[5]) > 59 || Number(parts[6]) > 59
      || Number(parts[7] ?? 0) > 23 || Number(parts[8] ?? 0) > 59) return NaN;
  const age = Date.now() - Date.parse(value);
  return age >= 0 ? age : NaN;
}

// Use only the portfolio response's validated economics, never raw current_price
// or the separately fetched strategies snapshot. Unknown is sticky for this
// snapshot: passing wall-clock time cannot make rejected evidence valid.
function validatedHoldingMark(portfolio: any, holding: any) {
  const view = portfolio?.statistics;
  const id = holding.holding_id;
  if (typeof id !== 'string' || !id || !Array.isArray(view?.holdings)
      || typeof portfolio.as_of !== 'string' || view.as_of !== portfolio.as_of
      || portfolio.open_positions.filter((h: any) => h.holding_id === id).length !== 1) return null;
  const matches = view.holdings.filter((h: any) => h.holding_id === id);
  if (matches.length !== 1) return null;
  const sample = matches[0];
  const quantity = sample.initial_quantity - sample.realized_quantity;
  const multiplier = sample.mode === 'paper_options' ? 100 : sample.mode === 'paper_underlying' ? 1 : null;
  if (sample.portfolio_id !== portfolio.portfolio_id || holding.portfolio_id !== portfolio.portfolio_id
      || sample.holding_status !== holding.status || !['OPEN', 'TRIMMED'].includes(sample.holding_status)
      || (sample.mode === 'paper_options') !== (holding.asset_type === 'option')
      || !['fresh', 'stale'].includes(sample.mark_freshness)
      || typeof sample.mark_as_of !== 'string' || sample.mark_as_of !== holding.last_price_updated_at
      || !Number.isFinite(sample.initial_quantity) || !Number.isFinite(sample.realized_quantity)
      || !Number.isFinite(quantity) || quantity <= 0 || quantity !== holding.quantity || multiplier === null
      || !Number.isFinite(sample.estimated_market_value) || !Number.isFinite(sample.estimated_unrealized_pnl)
      || sample.estimated_market_value !== holding.market_value
      || sample.estimated_unrealized_pnl !== holding.unrealized_pnl) return null;
  return { price: sample.estimated_market_value / (quantity * multiplier),
    asOf: sample.mark_as_of, freshness: sample.mark_freshness };
}

export default function NotableFlowPage() {
  const navigate = useNavigate();
  const [flows, setFlows] = useState<NotableFlowItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [flowError, setFlowError] = useState<string | null>(null);
  const [quoteStatus, setQuoteStatus] = useState('Quotes unknown');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [showLegend, setShowLegend] = useState(true);

  // Live Stock & Contract Price State
  const [liveQuotes, setLiveQuotes] = useState<Record<string, { price: number; change_pct: number | null; is_extended_hours?: boolean; source?: string; as_of?: string }>>({});
  const [evidenceClock, refreshEvidenceClock] = useState(0);
  const currentQuotes = Object.fromEntries(Object.entries(liveQuotes).filter(([, q]) => {
    const age = evidenceAge(q.as_of);
    return Number.isFinite(age) && age >= 0 && age <= 60000;
  }));
  const consumedQuoteStatus = Object.keys(currentQuotes).length < Object.keys(liveQuotes).length
    ? 'Stale quotes — unavailable for current marks' : quoteStatus;
  useEffect(() => {
    const expiries = Object.values(liveQuotes).map(q => Date.parse(q.as_of ?? '') + 60001)
      .filter(at => Number.isFinite(at) && at > Date.now());
    if (!expiries.length) return;
    const timer = setTimeout(() => refreshEvidenceClock(n => n + 1), Math.min(...expiries) - Date.now());
    return () => clearTimeout(timer);
  }, [liveQuotes, evidenceClock]);
  const [showExpired, setShowExpired] = useState<boolean>(false);

  // Independent Tracking view; never changes the tape's baseline filters.
  const [activeTab, setActiveTab] = useState<"tape" | "validator" | "strategies" | "tracking">("tape");
  const [portfolioData, setPortfolioData] = useState<{ copy_trader?: any; autonomous_ai?: any } | null>(null);
  const [portfolioLoading, setPortfolioLoading] = useState<boolean>(false);
  const [strategiesList, setStrategiesList] = useState<any[]>([]);

  const fetchPortfolio = async () => {
    setPortfolioLoading(true);
    setPortfolioData(null);
    setStrategiesList([]);
    setHoldingStatistics(null);
    setPortfolioError(null);
    setStrategyError(null);
    const [portfolio, strategies] = await Promise.allSettled([
      api.getPortfolioSummary(), api.getRecordedStrategies(),
    ]);
    if (portfolio.status === 'fulfilled' && portfolio.value?.ok) {
      setPortfolioData(portfolio.value.portfolios);
    } else {
      setPortfolioError('Portfolio refresh failed — current values unavailable');
    }
    if (strategies.status === 'fulfilled' && strategies.value?.ok) {
      setStrategiesList(strategies.value.strategies ?? []);
      setHoldingStatistics(strategies.value.statistics ?? null);
    } else {
      setStrategyError('Strategy refresh failed — current statistics unavailable');
    }
    setPortfolioLoading(false);
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const [holdingStatistics, setHoldingStatistics] = useState<any>(null);
  const [portfolioError, setPortfolioError] = useState<string | null>(null);
  const [strategyError, setStrategyError] = useState<string | null>(null);
  const getStrategyStats = (stratKey: string) => {
    const stats = holdingStatistics?.by_archetype?.[stratKey];
    return {
      winRate: stats?.gross_win_rate_pct != null ? `${stats.gross_win_rate_pct.toFixed(1)}% Gross Win Rate` : 'Insufficient data',
      sampleText: stats ? `${stats.closed_count} closed holdings; ${stats.open_count} open; ${stats.excluded_count} excluded; ${stats.unknown_cost_count} costs unknown` : 'No eligible holding statistics',
    };
  };
  const moneyText = (value: unknown) => typeof value === 'number' && Number.isFinite(value)
    ? `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : 'Unknown';
  const snapshotText = (value: string | undefined) => {
    const age = evidenceAge(value);
    return !Number.isFinite(age) || age < 0 ? 'Unknown timestamp' : `${value}${age > 60000 ? ' (stale snapshot)' : ''}`;
  };

  // Filters State (Multi-Select Support)
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedOrigins, setSelectedOrigins] = useState<string[]>([]);
  const [selectedFlowTags, setSelectedFlowTags] = useState<string[]>([]);
  const [selectedDtes, setSelectedDtes] = useState<string[]>([]);
  const [selectedConvictions, setSelectedConvictions] = useState<string[]>([]);
  const [optionTypeFilter, setOptionTypeFilter] = useState<"ALL" | "CALL" | "PUT">("ALL");
  const [assetFilter, setAssetFilter] = useState<"ALL" | "EQUITY" | "ETF">("ALL");
  const [minPremiumFilter, setMinPremiumFilter] = useState<number>(0);
  const [chartFilter, setChartFilter] = useState<"ALL" | "WITH_CHART" | "NO_CHART">("ALL");
  
  // Active Popover Dropdown
  const [activeDropdown, setActiveDropdown] = useState<string | null>(null);

  // Sort State
  const [sortField, setSortField] = useState<"ticker" | "strike" | "dte" | "premium_usd" | "flow_score" | "trade_timestamp">("trade_timestamp");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");

  const [selectedChartModal, setSelectedChartModal] = useState<NotableFlowItem | null>(null);

  // Dynamic DTE calculation relative to real-time clock
  const getDynamicDte = (expiration: string, fallbackDte?: number): number => {
    if (!expiration) return fallbackDte ?? 0;
    try {
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const expDate = new Date(expiration);
      expDate.setHours(0, 0, 0, 0);
      const diffTime = expDate.getTime() - today.getTime();
      return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    } catch {
      return fallbackDte ?? 0;
    }
  };

  // Live Option Contract Pricing Model (Mark-to-market per-share and total contract)
  const getOptionContractPrice = (item: NotableFlowItem, stockPrice?: number): { perShare: number | null; totalContract: number | null } => {
    if (stockPrice == null || !Number.isFinite(stockPrice) || stockPrice <= 0 || !Number.isFinite(item.strike) || item.strike <= 0) return {perShare: null, totalContract: null};
    const isCall = item.call_put?.toUpperCase().startsWith("C");
    const spot = stockPrice;
    const dte = Math.max(1, getDynamicDte(item.expiration, item.dte));
    const t = dte / 365.0;
    const iv = 0.42;

    const intrinsic = isCall ? Math.max(0, spot - item.strike) : Math.max(0, item.strike - spot);
    const denom = spot * iv * Math.sqrt(t) + 1e-5;
    const extrinsic = spot * iv * Math.sqrt(t) * 0.3989 * Math.exp(-0.5 * Math.pow((spot - item.strike) / denom, 2));
    const perShare = Math.max(0.10, Math.round((intrinsic + extrinsic) * 100) / 100);
    
    return {
      perShare,
      totalContract: Math.round(perShare * 100)
    };
  };

  const getOriginBadge = (source: string, assetType?: string) => {
    const s = (source || "").toLowerCase();
    const isEtf = (assetType || "").toLowerCase() === "etf" || s.includes("etf");

    if (s.includes("notable_etf") || (s.includes("discord") && isEtf)) {
      return {
        id: "DISCORD_ETF",
        label: "Discord #notable-etf-flow",
        badge: "Discord ETF",
        icon: "📊",
        color: "bg-indigo-500/20 text-indigo-300 border-indigo-500/40",
        description: "Macro / sector ETF sweep from Discord options tape",
      };
    }
    if (s.includes("notable_flow") || s.includes("discord")) {
      return {
        id: "DISCORD_EQUITY",
        label: "Discord #notable-flow",
        badge: "Discord Equities",
        icon: "💬",
        color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
        description: "Single-stock institutional whale sweep from Discord options tape",
      };
    }
    if (s.includes("flowseeker") || s.includes("skylit")) {
      return {
        id: "FLOWSEEKER",
        label: "Skylit Flowseeker",
        badge: "Flowseeker",
        icon: "🔍",
        color: "bg-purple-500/20 text-purple-300 border-purple-500/40",
        description: "Proprietary OFI algorithmic multi-exchange scanner",
      };
    }
    if (s.includes("whale") || s.includes("unusual")) {
      return {
        id: "UNUSUAL_WHALES",
        label: "Unusual Whales API",
        badge: "Unusual Whales",
        icon: "🐳",
        color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/40",
        description: "Aggregated institutional cross-exchange options tape",
      };
    }
    return {
      id: "SCANNER",
      label: source || "Tape Scanner",
      badge: "Tape Scanner",
      icon: "📡",
      color: "bg-slate-700/40 text-slate-300 border-slate-600",
      description: "Direct real-time options tape feed",
    };
  };

  const getFlowTags = (item: NotableFlowItem) => {
    const isCall = item.call_put?.toUpperCase().startsWith("C");
    const tags: Array<{ id: string; label: string; color: string; border: string; bg: string }> = [];
    const quote = currentQuotes[item.ticker?.toUpperCase()];
    const spot = quote && quote.price > 0 ? quote.price : 0;

    // 1. Primary Direction (Crossing the Ask)
    if (isCall) {
      tags.push({
        id: "CALLS",
        label: "CALLS — side unknown",
        color: "text-emerald-300",
        border: "border-emerald-500/30",
        bg: "bg-emerald-500/15",
      });
    } else {
      tags.push({
        id: "PUTS",
        label: "PUTS — side unknown",
        color: "text-rose-300",
        border: "border-rose-500/30",
        bg: "bg-rose-500/15",
      });
    }

    // 2. TRUE Dynamic Moneyness Check (OTM vs Near-Money ATM [<=5% ITM] vs Deep ITM [>5% ITM])
    if (spot > 0) {
      if (isCall) {
        const distPct = ((item.strike - spot) / spot) * 100;
        if (distPct > 0.0) {
          tags.push({
            id: "OTM_CALLS",
            label: "OTM CALLS",
            color: "text-teal-300",
            border: "border-teal-500/30",
            bg: "bg-teal-500/15",
          });
        } else if (distPct >= -5.0) {
          tags.push({
            id: "ATM_NEAR_MONEY",
            label: "ATM CALLS (≤5% ITM)",
            color: "text-cyan-300",
            border: "border-cyan-500/30",
            bg: "bg-cyan-500/15",
          });
        } else {
          tags.push({
            id: "DEEP_ITM",
            label: "ITM CALLS (>5% ITM)",
            color: "text-amber-300",
            border: "border-amber-500/30",
            bg: "bg-amber-500/15",
          });
        }
      } else {
        const distPct = ((spot - item.strike) / spot) * 100;
        if (distPct > 0.0) {
          tags.push({
            id: "OTM_PUTS",
            label: "OTM PUTS",
            color: "text-pink-300",
            border: "border-pink-500/30",
            bg: "bg-pink-500/15",
          });
        } else if (distPct >= -5.0) {
          tags.push({
            id: "ATM_NEAR_MONEY",
            label: "ATM PUTS (≤5% ITM)",
            color: "text-cyan-300",
            border: "border-cyan-500/30",
            bg: "bg-cyan-500/15",
          });
        } else {
          tags.push({
            id: "DEEP_ITM",
            label: "ITM PUTS (>5% ITM)",
            color: "text-amber-300",
            border: "border-amber-500/30",
            bg: "bg-amber-500/15",
          });
        }
      }
    } else {
      // Default placeholder before live quotes load
      tags.push({
        id: "MONEYNESS_UNKNOWN",
        label: "MONEYNESS UNKNOWN",
        color: isCall ? "text-teal-300" : "text-pink-300",
        border: isCall ? "border-teal-500/30" : "border-pink-500/30",
        bg: isCall ? "bg-teal-500/15" : "bg-pink-500/15",
      });
    }

    // 3. Horizon / Macro Accumulation
    const dte = getDynamicDte(item.expiration, item.dte);
    if (dte >= 90) {
      tags.push({
        id: "MACRO_ACCUMULATION",
        label: "MACRO ACCUMULATION",
        color: "text-indigo-300",
        border: "border-indigo-500/30",
        bg: "bg-indigo-500/15",
      });
    } else if (dte > 0 && dte < 20) {
      tags.push({
        id: "GAMMA_ACCELERATOR",
        label: "GAMMA ACCELERATOR",
        color: "text-amber-300",
        border: "border-amber-500/30",
        bg: "bg-amber-500/15",
      });
    }

    // 4. Whale Sweep Tier ($1M+)
    if ((item.premium_usd || 0) >= 1_000_000) {
      tags.push({
        id: "WHALE_SWEEP",
        label: "WHALE SWEEP",
        color: "text-cyan-300",
        border: "border-cyan-500/30",
        bg: "bg-cyan-500/15",
      });
    }

    return tags;
  };

  const fetchLiveQuotes = async (currentFlows: NotableFlowItem[]) => {
    setLiveQuotes({});
    setQuoteStatus('Loading quotes…');
    if (!currentFlows?.length) { setQuoteStatus('Quotes unknown — no symbols'); return; }
    const uniqueTickers = Array.from(new Set(currentFlows.map((f) => f.ticker.toUpperCase())));
    try {
      const res = await api.getLiveQuotes(uniqueTickers.slice(0, 80));
      if (!res?.ok || !res.quotes) throw new Error('Quotes unavailable');
      const fresh: typeof liveQuotes = {};
      let stale = false;
      for (const [ticker, q] of Object.entries(res.quotes)) {
        const age = evidenceAge(q.as_of);
        if (q.source && q.as_of && q.price != null && Number.isFinite(q.price) && q.price >= 0 && age >= 0 && age <= 60000) {
          fresh[ticker] = { ...q, price: q.price };
        } else if (Number.isFinite(age) && age > 60000) stale = true;
      }
      setLiveQuotes(fresh);
      setQuoteStatus(stale ? 'Stale quotes — unavailable for current marks' : Object.keys(fresh).length ? 'Observed underlying quotes; timestamps shown per symbol' : 'Quotes unknown — source/time evidence missing');
    } catch {
      setLiveQuotes({});
      setQuoteStatus('Quote refresh failed — current marks unknown');
    }
  };

  const fetchFlows = async () => {
    setLoading(true);
    setFlowError(null);
    setLiveQuotes({});
    try {
      // Fetch all notable flows (broad limit) so all column filters & sorts operate client-side with zero latency
      const res = await api.getNotableFlows({
        limit: 500,
      });
      if (res?.ok && Array.isArray(res.flows)) {
        setFlows(res.flows);
        fetchLiveQuotes(res.flows);
      } else throw new Error('Flow response unavailable');
      setLastRefreshed(new Date());
    } catch {
      setFlows([]);
      setLiveQuotes({});
      setFlowError('Flow refresh failed — current tape unavailable');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFlows();
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchFlows();
    }, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh]);

  const getFlowseekerScore = (item: NotableFlowItem): { score: number; label: string; color: string } => {
    const prem = item.premium_usd || 0;
    let score = 50;

    if (prem >= 5_000_000) score += 35;
    else if (prem >= 1_000_000) score += 28;
    else if (prem >= 300_000) score += 20;
    else if (prem >= 100_000) score += 12;

    const dte = getDynamicDte(item.expiration, item.dte);
    if (dte >= 20 && dte <= 60) score += 15;
    else if (dte >= 14 && dte <= 90) score += 10;

    score = Math.min(99, Math.max(45, score));

    if (score >= 85) return { score, label: "Diamond Whale", color: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" };
    if (score >= 70) return { score, label: "Strong Institutional", color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30" };
    return { score, label: "Notable Momentum", color: "bg-purple-500/20 text-purple-300 border-purple-500/30" };
  };

const ORIGIN_OPTIONS = [
  { value: "DISCORD_EQUITY", label: "Discord Equities (#notable-flow)", badge: "Equities", icon: "💬" },
  { value: "DISCORD_ETF", label: "Discord ETF (#notable-etf-flow)", badge: "ETF", icon: "📊" },
  { value: "FLOWSEEKER", label: "Skylit Flowseeker", badge: "Flowseeker", icon: "🔍" },
  { value: "UNUSUAL_WHALES", label: "Unusual Whales", badge: "Unusual Whales", icon: "🐳" },
];

const FLOW_TAG_OPTIONS = [
  { value: "OTM_CALLS", label: "OTM CALLS (>0% OTM)", icon: "⚡" },
  { value: "OTM_PUTS", label: "OTM PUTS (>0% OTM)", icon: "⚡" },
  { value: "ATM_NEAR_MONEY", label: "ATM / NEAR-MONEY (≤5% ITM)", icon: "🔷" },
  { value: "DEEP_ITM", label: "DEEP ITM (>5% ITM)", icon: "⚠️" },
  { value: "CALLS", label: "CALLS (side unknown)", icon: "🟢" },
  { value: "PUTS", label: "PUTS (side unknown)", icon: "🔴" },
  { value: "MACRO_ACCUMULATION", label: "MACRO ACCUMULATION (90d+)", icon: "🚀" },
  { value: "WHALE_SWEEP", label: "WHALE SWEEP ($1M+)", icon: "💎" },
  { value: "GAMMA_ACCELERATOR", label: "GAMMA ACCELERATOR (<20d)", icon: "⚡" },
];

const DTE_OPTIONS = [
  { value: "LEAP", label: "LEAP (90d+ Long-Term)", icon: "🚀" },
  { value: "SWING", label: "SWING (20–89d Multi-Week)", icon: "⏳" },
  { value: "SHORT_DTE", label: "SHORT-DTE (<20d Tactical)", icon: "⚡" },
];

const CONVICTION_OPTIONS = [
  { value: "DIAMOND", label: "Diamond Whale (Score 85+)", icon: "💎" },
  { value: "STRONG", label: "Strong Inst. (Score 70–84)", icon: "🔷" },
  { value: "NOTABLE", label: "Notable Momentum (Score <70)", icon: "⚡" },
];

function MultiSelectFilterDropdown({
  id,
  label,
  icon,
  accentBorder = "hover:border-indigo-500/50",
  options,
  selectedValues,
  onChange,
  activeDropdown,
  setActiveDropdown,
}: {
  id: string;
  label: string;
  icon: string;
  accentBorder?: string;
  options: Array<{ value: string; label: string; icon?: string }>;
  selectedValues: string[];
  onChange: (newValues: string[]) => void;
  activeDropdown: string | null;
  setActiveDropdown: (id: string | null) => void;
}) {
  const isOpen = activeDropdown === id;
  const count = selectedValues.length;

  const getPluralLabel = (lbl: string) => {
    const clean = lbl.trim();
    if (clean.toLowerCase().endsWith("tags") || clean.toLowerCase().endsWith("s")) {
      return `All ${clean}`;
    }
    return `All ${clean}s`;
  };

  const toggleOption = (val: string) => {
    if (selectedValues.includes(val)) {
      onChange(selectedValues.filter((v) => v !== val));
    } else {
      onChange([...selectedValues, val]);
    }
  };

  return (
    <div className={`relative space-y-1 ${isOpen ? "z-50" : "z-10"}`}>
      <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
        <span className="flex items-center gap-1">
          <span>{icon}</span> {label}
        </span>
        {count > 0 && (
          <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-emerald-500/20 text-emerald-300 font-mono font-bold">
            {count}
          </span>
        )}
      </label>

      <button
        type="button"
        onClick={() => setActiveDropdown(isOpen ? null : id)}
        className={`w-full bg-[#0B0F17] border ${
          count > 0 ? "border-emerald-500/70 text-emerald-300 shadow-sm shadow-emerald-500/10" : `border-slate-800 ${accentBorder}`
        } rounded-xl px-2.5 py-2 text-xs font-semibold text-left text-slate-200 focus:outline-none transition-all flex items-center justify-between gap-1 cursor-pointer`}
      >
        <span className="truncate">
          {count === 0
            ? getPluralLabel(label)
            : count === 1
            ? options.find((o) => o.value === selectedValues[0])?.label.split(" ")[0] || "1 Selected"
            : `${count} Selected`}
        </span>
        <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOpen ? "rotate-180 text-emerald-400" : ""}`} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40 bg-black/10"
            onClick={() => setActiveDropdown(null)}
          />
          <div className="absolute left-0 top-full mt-1.5 z-50 w-64 max-h-80 overflow-y-auto bg-[#0E131D] border border-slate-700/90 rounded-xl p-2 shadow-2xl space-y-1 backdrop-blur-2xl animate-in fade-in slide-in-from-top-1">
            <div className="flex items-center justify-between pb-1.5 mb-1 border-b border-slate-800 px-1 text-[10px] font-bold text-slate-400">
              <span>{label} (Multi-Select)</span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => onChange(options.map((o) => o.value))}
                  className="text-emerald-400 hover:underline"
                >
                  All
                </button>
                <span className="text-slate-600">•</span>
                <button
                  type="button"
                  onClick={() => onChange([])}
                  className="text-rose-400 hover:underline"
                >
                  Clear
                </button>
              </div>
            </div>

            <div className="space-y-0.5">
              {options.map((opt) => {
                const checked = selectedValues.includes(opt.value);
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => toggleOption(opt.value)}
                    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs font-medium text-left transition-colors ${
                      checked
                        ? "bg-emerald-500/15 text-emerald-300 border border-emerald-500/30"
                        : "hover:bg-slate-800 text-slate-300 border border-transparent"
                    }`}
                  >
                    <div
                      className={`w-3.5 h-3.5 rounded border flex items-center justify-center text-[9px] font-bold ${
                        checked
                          ? "bg-emerald-500 border-emerald-400 text-black"
                          : "border-slate-600 bg-slate-900"
                      }`}
                    >
                      {checked && "✓"}
                    </div>
                    {opt.icon && <span>{opt.icon}</span>}
                    <span className="truncate flex-1">{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

  // Multi-Column Filtering and Sorting Engine
  const filteredAndSortedFlows = useMemo(() => {
    const result = flows.filter((f) => {
      // 0. Filter Out Expired (Negative / 0 DTE) unless showExpired is enabled
      const dynamicDte = getDynamicDte(f.expiration, f.dte);
      if (!showExpired && dynamicDte <= 0) {
        return false;
      }

      // 1. Ticker / Expiration / Strike Search
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toUpperCase();
        const matchesTicker = f.ticker.toUpperCase().includes(q);
        const matchesStrike = String(f.strike).includes(q);
        const matchesExp = (f.expiration || "").includes(q);
        const matchesSource = (f.source || "").toUpperCase().includes(q);
        if (!matchesTicker && !matchesStrike && !matchesExp && !matchesSource) return false;
      }

      // 2. Multi-Select Origin Filter
      if (selectedOrigins.length > 0) {
        const src = (f.source || "").toLowerCase();
        const matchesOrigin = selectedOrigins.some((orig) => {
          if (orig === "DISCORD_EQUITY") return src.includes("discord") && !src.includes("etf");
          if (orig === "DISCORD_ETF") return src.includes("etf");
          if (orig === "FLOWSEEKER") return src.includes("flowseeker") || src.includes("skylit");
          if (orig === "UNUSUAL_WHALES") return src.includes("unusual") || src.includes("whale");
          return false;
        });
        if (!matchesOrigin) return false;
      }

      // 3. Asset Class Filter
      if (assetFilter !== "ALL") {
        const isEtf = f.asset_type?.toLowerCase() === "etf" || (f.source || "").includes("etf");
        if (assetFilter === "ETF" && !isEtf) return false;
        if (assetFilter === "EQUITY" && isEtf) return false;
      }

      // 4. Option Direction Filter
      if (optionTypeFilter !== "ALL") {
        const cp = f.call_put?.toUpperCase() || "";
        if (optionTypeFilter === "CALL" && !cp.startsWith("C")) return false;
        if (optionTypeFilter === "PUT" && !cp.startsWith("P")) return false;
      }

      // 5. Multi-Select Expiration Horizon / DTE Filter
      if (selectedDtes.length > 0) {
        const matchesDte = selectedDtes.some((dte) => {
          if (dte === "LEAP") return dynamicDte >= 90;
          if (dte === "SWING") return dynamicDte >= 20 && dynamicDte < 90;
          if (dte === "SHORT_DTE") return dynamicDte > 0 && dynamicDte < 20;
          return false;
        });
        if (!matchesDte) return false;
      }

      // 6. Multi-Select Flow Tags / Moneyness Filter
      if (selectedFlowTags.length > 0) {
        const itemTagIds = getFlowTags(f).map((t) => t.id);
        const matchesAnyTag = selectedFlowTags.some((tagId) => itemTagIds.includes(tagId));
        if (!matchesAnyTag) return false;
      }

      // 7. Minimum Premium Filter
      if (minPremiumFilter > 0 && (f.premium_usd || 0) < minPremiumFilter) {
        return false;
      }

      // 8. Multi-Select Conviction Tier Filter
      if (selectedConvictions.length > 0) {
        const badge = getFlowseekerScore(f);
        const matchesConviction = selectedConvictions.some((c) => {
          if (c === "DIAMOND") return badge.score >= 85;
          if (c === "STRONG") return badge.score >= 70 && badge.score < 85;
          if (c === "NOTABLE") return badge.score < 70;
          return false;
        });
        if (!matchesConviction) return false;
      }

      // 9. Chart Attachment Filter
      if (chartFilter !== "ALL") {
        const hasChart = Boolean(f.chart_url || f.local_chart_path);
        if (chartFilter === "WITH_CHART" && !hasChart) return false;
        if (chartFilter === "NO_CHART" && hasChart) return false;
      }

      return true;
    });

    // Interactive Column Sorting
    result.sort((a, b) => {
      let valA: any = 0;
      let valB: any = 0;

      if (sortField === "ticker") {
        valA = a.ticker || "";
        valB = b.ticker || "";
        return sortOrder === "asc" ? valA.localeCompare(valB) : valB.localeCompare(valA);
      } else if (sortField === "strike") {
        valA = a.strike || 0;
        valB = b.strike || 0;
      } else if (sortField === "dte") {
        valA = getDynamicDte(a.expiration, a.dte);
        valB = getDynamicDte(b.expiration, b.dte);
      } else if (sortField === "premium_usd") {
        valA = a.premium_usd || 0;
        valB = b.premium_usd || 0;
      } else if (sortField === "flow_score") {
        valA = getFlowseekerScore(a).score;
        valB = getFlowseekerScore(b).score;
      } else if (sortField === "trade_timestamp") {
        valA = new Date(a.trade_timestamp || 0).getTime();
        valB = new Date(b.trade_timestamp || 0).getTime();
      }

      if (valA < valB) return sortOrder === "asc" ? -1 : 1;
      if (valA > valB) return sortOrder === "asc" ? 1 : -1;
      return 0;
    });

    return result;
  }, [flows, searchQuery, selectedOrigins, assetFilter, optionTypeFilter, selectedDtes, selectedFlowTags, minPremiumFilter, selectedConvictions, chartFilter, showExpired, sortField, sortOrder]);

  const expiredCount = useMemo(() => {
    return flows.filter((f) => getDynamicDte(f.expiration, f.dte) <= 0).length;
  }, [flows]);

  const activeFiltersCount = useMemo(() => {
    let count = 0;
    if (searchQuery.trim()) count++;
    count += selectedOrigins.length;
    count += selectedFlowTags.length;
    count += selectedDtes.length;
    count += selectedConvictions.length;
    if (assetFilter !== "ALL") count++;
    if (optionTypeFilter !== "ALL") count++;
    if (minPremiumFilter > 0) count++;
    if (chartFilter !== "ALL") count++;
    if (showExpired) count++;
    return count;
  }, [searchQuery, selectedOrigins, selectedFlowTags, selectedDtes, selectedConvictions, assetFilter, optionTypeFilter, minPremiumFilter, chartFilter, showExpired]);

  const handleResetFilters = () => {
    setSearchQuery("");
    setSelectedOrigins([]);
    setSelectedFlowTags([]);
    setSelectedDtes([]);
    setSelectedConvictions([]);
    setAssetFilter("ALL");
    setOptionTypeFilter("ALL");
    setMinPremiumFilter(0);
    setChartFilter("ALL");
    setShowExpired(false);
  };

  const handleSort = (field: "ticker" | "strike" | "dte" | "premium_usd" | "flow_score" | "trade_timestamp") => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
    }
  };

  // Key Aggregations based on filtered items
  const stats = useMemo(() => {
    const totalCount = filteredAndSortedFlows.length;
    const callCount = filteredAndSortedFlows.filter((f) => f.call_put?.toUpperCase().startsWith("C")).length;
    const putCount = filteredAndSortedFlows.filter((f) => f.call_put?.toUpperCase().startsWith("P")).length;
    const totalPremium = filteredAndSortedFlows.reduce((acc, f) => acc + (f.premium_usd || 0), 0);
    const etfCount = filteredAndSortedFlows.filter((f) => f.asset_type?.toLowerCase() === "etf" || (f.source || "").includes("etf")).length;
    const callRatio = totalCount > 0 ? (callCount / totalCount) * 100 : 50;

    return { totalCount, callCount, putCount, totalPremium, etfCount, callRatio };
  }, [filteredAndSortedFlows]);

  const formatPremiumDisplay = (prem: number, raw?: string) => {
    if (raw && (raw.includes("M") || raw.includes("K") || raw.includes("$"))) return raw;
    if (prem >= 1_000_000) return `$${(prem / 1_000_000).toFixed(1)}M`.replace(".0M", "M");
    if (prem >= 1_000) return `$${(prem / 1_000).toFixed(0)}K`;
    return `$${prem.toLocaleString()}`;
  };

  const [syncing, setSyncing] = useState(false);
  const [syncToast, setSyncToast] = useState<string | null>(null);

  const handleSyncPipeline = async () => {
    setSyncing(true);
    try {
      const res = await api.backfillNotableFlow(100);
      if (res && res.ok) {
        const saved = res.stats?.new_flows_saved || 0;
        const total = res.stats?.total_processed || 0;
        setSyncToast(`✓ Pipeline Ingested: ${total} msgs checked (${saved} new flows saved).`);
        fetchFlows();
      } else {
        setSyncToast("Sync completed.");
        fetchFlows();
      }
    } catch {
      setSyncToast("Pipeline sync failed.");
    } finally {
      setSyncing(false);
      setTimeout(() => setSyncToast(null), 5000);
    }
  };

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 p-4 sm:p-6 space-y-6 font-sans">
      {/* Toast Notification */}
      {syncToast && (
        <div className="fixed top-4 right-4 z-50 bg-emerald-950/90 border border-emerald-500/40 text-emerald-200 px-4 py-2.5 rounded-xl shadow-2xl flex items-center gap-2 text-xs font-semibold backdrop-blur-md animate-in fade-in slide-in-from-top-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          {syncToast}
        </div>
      )}

      <ResearchProfiles />
      {/* Top Banner & Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-950/40 via-indigo-950/30 to-purple-950/40 border border-emerald-500/20 p-6 shadow-2xl backdrop-blur-xl">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl shadow-lg shadow-emerald-500/30">
                <Radio className="w-6 h-6 text-white animate-pulse" />
              </div>
              <div>
                <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white flex items-center gap-2">
                  Notable Flow Watchlist
                </h1>
                <p className="text-xs sm:text-sm text-slate-400">
                  Live Institutional Whale Scanner (Discord #notable-flow, #notable-etf-flow, Unusual Whales & Skylit Flowseeker).
                </p>
              </div>
            </div>
          </div>

          {/* Refresh & Sync Controls */}
          <div className="flex items-center gap-2.5">
            <div className="text-right hidden sm:block">
              <div className="text-[11px] text-slate-400 flex items-center gap-1.5 justify-end">
                <Clock className="w-3.5 h-3.5 text-emerald-400" />
                Tape fetched {lastRefreshed?.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }) ?? 'Unknown'} · {loading ? 'Loading' : flowError ?? consumedQuoteStatus}
              </div>
              <div className="text-[10px] text-slate-500 font-mono">
                {autoRefresh ? "10s Live Auto-Polling" : "Auto-Polling Paused"}
              </div>
            </div>

            <button
              onClick={handleSyncPipeline}
              disabled={syncing}
              className="flex items-center gap-1.5 px-3.5 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-xl text-xs font-bold shadow-lg shadow-emerald-600/20 transition-all active:scale-95 disabled:opacity-50"
              title="Trigger on-demand Discord flow pipeline backfill"
            >
              <Zap className={`w-3.5 h-3.5 text-amber-300 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "Ingesting..." : "Sync Pipeline"}
            </button>

            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`px-3 py-2 rounded-xl text-xs font-bold transition-all border ${
                autoRefresh
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                  : "bg-slate-800 text-slate-400 border-slate-700 hover:text-slate-200"
              }`}
            >
              {autoRefresh ? "● Live Polling" : "○ Paused"}
            </button>

            <button
              onClick={fetchFlows}
              disabled={loading}
              className="p-2.5 bg-slate-800/80 hover:bg-slate-700 text-slate-200 rounded-xl transition-all border border-slate-700 shadow-md"
              title="Refresh Notable Flow"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin text-emerald-400" : ""}`} />
            </button>
          </div>
        </div>

        {/* View Switcher Tabs (Non-destructive) */}
        <div className="relative z-10 mt-5 pt-4 border-t border-emerald-500/20 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2 bg-slate-900/80 p-1.5 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab("tape")}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "tape"
                  ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Radio className="w-3.5 h-3.5" />
              Whale Flow Tape
            </button>
            <button
              onClick={() => setActiveTab("tracking")}
              aria-pressed={activeTab === "tracking"}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${activeTab === "tracking" ? "bg-emerald-500 text-white shadow-lg shadow-emerald-500/20" : "text-slate-400 hover:text-white"}`}
            >
              <Clock className="w-3.5 h-3.5" /> Tracking
            </button>
            <button
              onClick={() => {
                setActiveTab("validator");
                fetchPortfolio();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "validator"
                  ? "bg-indigo-600 text-white shadow-lg shadow-indigo-600/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-amber-300" />
              Strategy Validator (Paper Portfolio)
            </button>
            <button
              onClick={() => {
                setActiveTab("strategies");
                fetchPortfolio();
              }}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all ${
                activeTab === "strategies"
                  ? "bg-purple-600 text-white shadow-lg shadow-purple-600/20"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              <TrendingUp className="w-3.5 h-3.5" />
              Strategy Alpha & Learnings
            </button>
          </div>

          <div className="text-xs text-slate-400 flex items-center gap-2 font-medium">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span>Paper simulation viewer: <strong className="text-emerald-300 font-bold">Execution status not established</strong></span>
          </div>
        </div>
      </div>

      {activeTab === "tracking" && <ResearchWatchlist />}

      {activeTab === "tape" && (
        <>
          {/* KPI Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Captured Flow */}
        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Flow Orders</span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-100 flex items-center gap-2">
              <span>{stats.totalCount} Orders</span>
              <span className="text-xs text-slate-400 font-normal">({stats.etfCount} ETFs)</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">Institutional Block & Sweep Candidates</p>
          </div>
        </div>

        {/* Total Notional Premium Deployed */}
        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Gross Notional</span>
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-indigo-400 tracking-tight">
              {formatPremiumDisplay(stats.totalPremium)}
            </div>
            <p className="text-xs text-slate-400 mt-1">Total Institutional Capital</p>
          </div>
        </div>

        {/* Bullish / Bearish Sentiment Bar */}
        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Flow Bias (C/P)</span>
            <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline justify-between text-xs font-bold mb-1">
              <span className="text-emerald-400">{stats.callRatio.toFixed(0)}% Call</span>
              <span className="text-rose-400">{(100 - stats.callRatio).toFixed(0)}% Put</span>
            </div>
            <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden flex">
              <div className="bg-emerald-500 h-full transition-all" style={{ width: `${stats.callRatio}%` }} />
              <div className="bg-rose-500 h-full transition-all" style={{ width: `${100 - stats.callRatio}%` }} />
            </div>
          </div>
        </div>

        {/* Shadow Quant Bridge */}
        <div className="bg-[#131924]/80 border border-purple-500/30 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-purple-300 uppercase tracking-wider">Shadow Quant</span>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <Zap className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-white tracking-tight">OWLFRED AI</div>
            <p className="text-xs text-purple-300/80 mt-1">1-Click Directional Alpha</p>
          </div>
        </div>
      </div>

      {/* Interactive Plain-English Tag & Origin Legend */}
      <div className="bg-[#131924]/80 border border-slate-800/80 rounded-2xl p-4 shadow-xl backdrop-blur-xl transition-all">
        <div className="flex items-center justify-between cursor-pointer" onClick={() => setShowLegend(!showLegend)}>
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-white flex items-center gap-2">
                Watchlist Legend & Tag Guide (Plain English)
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                  Tags, Conviction & Data Origins
                </span>
              </h3>
            </div>
          </div>
          <button
            type="button"
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 transition-colors"
          >
            <span>{showLegend ? "Collapse Guide" : "Expand Guide"}</span>
            {showLegend ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {showLegend && (
          <div className="mt-4 pt-4 border-t border-slate-800/80 grid grid-cols-1 md:grid-cols-4 gap-4 text-xs animate-in fade-in slide-in-from-top-1">
            {/* Column 1: Moneyness & Directional Tags */}
            <div className="bg-[#0E131D]/80 border border-slate-800/70 rounded-xl p-3.5 space-y-2.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-teal-400 flex items-center gap-1.5">
                <span>🎯</span> Moneyness & Live Badges
              </div>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-teal-500/20 text-teal-300 border border-teal-500/30 whitespace-nowrap">
                    OTM CALLS
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">Out-of-the-Money</strong>: Bullish/bearish sweeps positioned above (Calls) or below (Puts) current market spot.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 whitespace-nowrap">
                    ATM (≤5% ITM)
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">Near-Money / ATM</strong>: High-conviction strikes within 5% of market spot (analyst sweet spot).
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap">
                    EXT
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">Extended Hours</strong>: Live pre-market (4:00–9:30 AM ET) or after-hours (4:00–8:00 PM ET) electronic trade price.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-gradient-to-r from-emerald-500/20 via-slate-800/40 to-rose-500/20 border border-slate-700/80 whitespace-nowrap flex items-center gap-1 shadow-sm">
                    <span className="text-emerald-400">BIG</span>
                    <span className="text-rose-400">ASK</span>
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">Crossing the Ask (Calls & Puts)</strong>: Sweeps executed aggressively over the offer price indicating maximum urgency.
                  </p>
                </div>
              </div>
            </div>

            {/* Column 2: Whale Conviction Tiers */}
            <div className="bg-[#0E131D]/80 border border-slate-800/70 rounded-xl p-3.5 space-y-2.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <span>💎</span> Whale Conviction Tiers
              </div>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 whitespace-nowrap">
                    Diamond Whale
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">$1M+ Premium (Score 85+)</strong>: Mega-cap institutional block sweeps. Highest confidence institutional commitment.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 whitespace-nowrap">
                    Strong Inst.
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">$300K–$1M Premium (Score 70–84)</strong>: Heavy hedge fund / desk positioning with high volume.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 whitespace-nowrap">
                    Notable Flow
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">$75K–$300K Premium</strong>: Rapid tape velocity or unusual volume surge in mid-cap / high-beta tickers.
                  </p>
                </div>
              </div>
            </div>

            {/* Column 3: Expiration Horizon Tags */}
            <div className="bg-[#0E131D]/80 border border-slate-800/70 rounded-xl p-3.5 space-y-2.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-purple-400 flex items-center gap-1.5">
                <span>⏳</span> Expiration Horizon (DTE)
              </div>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30 whitespace-nowrap">
                    LEAP
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">90–365+ Days (Long-Term)</strong>: Long-Term Equity Anticipation. Macro positioning anticipating multi-quarter fundamentals.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 whitespace-nowrap">
                    SWING
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">20–89 Days (Multi-Week)</strong>: Mid-term plays positioned for earnings or seasonal product cycles.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 whitespace-nowrap">
                    SHORT-DTE
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">&lt; 20 Days (Tactical)</strong>: Fast-moving gamma breakout or immediate catalyst momentum.
                  </p>
                </div>
              </div>
            </div>

            {/* Column 4: Ingestion Origins */}
            <div className="bg-[#0E131D]/80 border border-slate-800/70 rounded-xl p-3.5 space-y-2.5">
              <div className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 flex items-center gap-1.5">
                <span>📡</span> Data Origins & Feeds
              </div>
              <div className="space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 whitespace-nowrap">
                    💬 Discord Equities
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">#notable-flow</strong>: Single-stock equity whale prints ingested from institutional Discord channels.
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 whitespace-nowrap">
                    📊 Discord ETF
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">#notable-etf-flow</strong>: Index & Sector ETF whale blocks (SPY, QQQ, SMH, IBIT, GLD, etc.).
                  </p>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-[10px] px-1.5 py-0.5 rounded font-bold bg-purple-500/20 text-purple-300 border border-purple-500/40 whitespace-nowrap">
                    🔍 Flowseeker / Whales
                  </span>
                  <p className="text-[11px] text-slate-300 leading-relaxed">
                    <strong className="text-white">Skylit & Unusual Whales</strong>: Cross-market options tape filters and Level-2 order flow intensity.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Filter Control Center */}
      <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-xl space-y-4 relative z-30">
        {/* Row 1: Search, Summary, and Reset */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-3 pb-3 border-b border-slate-800/80">
          <div className="relative w-full md:max-w-md">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search ticker, strike, or source..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0B0F17] border border-slate-800 hover:border-emerald-500/50 focus:border-emerald-500 rounded-xl pl-9 pr-8 py-2 text-xs font-medium text-slate-200 placeholder-slate-500 focus:outline-none transition-all"
            />
          </div>

          <div className="flex items-center gap-2.5">
            <div className="text-xs text-slate-400 font-medium mr-2">
              <strong className="text-emerald-400">{filteredAndSortedFlows.length}</strong> Results
            </div>

            {expiredCount > 0 && (
              <button
                onClick={() => setShowExpired(!showExpired)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-all border ${
                  showExpired
                    ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                    : "bg-slate-800 text-slate-400 border-slate-700"
                }`}
              >
                {showExpired ? "Hide Expired" : "Show Expired"} ({expiredCount})
              </button>
            )}

            {activeFiltersCount > 0 && (
              <button
                onClick={handleResetFilters}
                className="px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 border border-rose-500/30 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm active:scale-95"
              >
                <X className="w-3.5 h-3.5" /> Reset {activeFiltersCount} Filter{activeFiltersCount > 1 ? "s" : ""}
              </button>
            )}
          </div>
        </div>

        {/* Row 2: Multi-Select Filter Selectors */}
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2.5 text-xs">
          <MultiSelectFilterDropdown
            id="origin"
            label="Origin"
            icon="📡"
            accentBorder="hover:border-indigo-500/50"
            options={ORIGIN_OPTIONS}
            selectedValues={selectedOrigins}
            onChange={setSelectedOrigins}
            activeDropdown={activeDropdown}
            setActiveDropdown={setActiveDropdown}
          />

          <MultiSelectFilterDropdown
            id="flow_tags"
            label="Flow Tags"
            icon="🏷️"
            accentBorder="hover:border-teal-500/50"
            options={FLOW_TAG_OPTIONS}
            selectedValues={selectedFlowTags}
            onChange={setSelectedFlowTags}
            activeDropdown={activeDropdown}
            setActiveDropdown={setActiveDropdown}
          />

          <MultiSelectFilterDropdown
            id="dte"
            label="Horizon"
            icon="⏳"
            accentBorder="hover:border-purple-500/50"
            options={DTE_OPTIONS}
            selectedValues={selectedDtes}
            onChange={setSelectedDtes}
            activeDropdown={activeDropdown}
            setActiveDropdown={setActiveDropdown}
          />

          <MultiSelectFilterDropdown
            id="conviction"
            label="Conviction"
            icon="💎"
            accentBorder="hover:border-emerald-500/50"
            options={CONVICTION_OPTIONS}
            selectedValues={selectedConvictions}
            onChange={setSelectedConvictions}
            activeDropdown={activeDropdown}
            setActiveDropdown={setActiveDropdown}
          />

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <span>🎯</span> Direction
            </label>
            <select
              value={optionTypeFilter}
              onChange={(e) => setOptionTypeFilter(e.target.value as any)}
              className="w-full bg-[#0B0F17] border border-slate-800 hover:border-emerald-500/50 focus:border-emerald-500 rounded-xl px-2.5 py-2 text-xs font-semibold text-slate-200 focus:outline-none transition-all cursor-pointer"
            >
              <option value="ALL">Calls & Puts</option>
              <option value="CALL">Calls Only 🟢</option>
              <option value="PUT">Puts Only 🔴</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <span>🏢</span> Asset Class
            </label>
            <select
              value={assetFilter}
              onChange={(e) => setAssetFilter(e.target.value as any)}
              className="w-full bg-[#0B0F17] border border-slate-800 hover:border-cyan-500/50 focus:border-cyan-500 rounded-xl px-2.5 py-2 text-xs font-semibold text-slate-200 focus:outline-none transition-all cursor-pointer"
            >
              <option value="ALL">All Assets</option>
              <option value="EQUITY">Equities</option>
              <option value="ETF">Index & Sector ETFs</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <span>💰</span> Min Premium
            </label>
            <select
              value={minPremiumFilter}
              onChange={(e) => setMinPremiumFilter(Number(e.target.value))}
              className="w-full bg-[#0B0F17] border border-slate-800 hover:border-emerald-500/50 focus:border-emerald-500 rounded-xl px-2.5 py-2 text-xs font-semibold text-slate-200 focus:outline-none transition-all cursor-pointer"
            >
              <option value={0}>All Sizes</option>
              <option value={75000}>$75K+</option>
              <option value={150000}>$150K+</option>
              <option value={250000}>$250K+</option>
              <option value={500000}>$500K+</option>
              <option value={1000000}>$1.0M+</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider flex items-center gap-1">
              <span>🖼️</span> Tape Chart
            </label>
            <select
              value={chartFilter}
              onChange={(e) => setChartFilter(e.target.value as any)}
              className="w-full bg-[#0B0F17] border border-slate-800 hover:border-cyan-500/50 focus:border-cyan-500 rounded-xl px-2.5 py-2 text-xs font-semibold text-slate-200 focus:outline-none transition-all cursor-pointer"
            >
              <option value="ALL">All Flows</option>
              <option value="WITH_CHART">Has Tape</option>
              <option value="NO_CHART">No Chart</option>
            </select>
          </div>
        </div>

        {/* Row 3: Active Filter Chips Ribbon */}
        {activeFiltersCount > 0 && (
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-800/80 text-xs">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1 flex items-center gap-1">
              <span>⚡</span> Active:
            </span>

            {searchQuery && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-slate-800 text-slate-200 border border-slate-700 text-xs font-semibold">
                Search: "{searchQuery}"
                <button onClick={() => setSearchQuery("")} className="hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {selectedOrigins.map((orig) => {
              const opt = ORIGIN_OPTIONS.find((o) => o.value === orig);
              return (
                <span
                  key={orig}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 text-xs font-semibold"
                >
                  <span>{opt?.icon || "📡"}</span>
                  <span>{opt?.badge || orig}</span>
                  <button
                    onClick={() => setSelectedOrigins(selectedOrigins.filter((o) => o !== orig))}
                    className="hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}

            {selectedFlowTags.map((tagId) => {
              const opt = FLOW_TAG_OPTIONS.find((o) => o.value === tagId);
              return (
                <span
                  key={tagId}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-teal-500/20 text-teal-300 border border-teal-500/40 text-xs font-semibold"
                >
                  <span>{opt?.icon || "🏷️"}</span>
                  <span>{opt?.label.split(" ")[0] || tagId}</span>
                  <button
                    onClick={() => setSelectedFlowTags(selectedFlowTags.filter((t) => t !== tagId))}
                    className="hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}

            {selectedDtes.map((dte) => {
              const opt = DTE_OPTIONS.find((o) => o.value === dte);
              return (
                <span
                  key={dte}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-purple-500/20 text-purple-300 border border-purple-500/40 text-xs font-semibold"
                >
                  <span>{opt?.icon || "⏳"}</span>
                  <span>{opt?.label.split(" ")[0] || dte}</span>
                  <button
                    onClick={() => setSelectedDtes(selectedDtes.filter((d) => d !== dte))}
                    className="hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}

            {selectedConvictions.map((c) => {
              return (
                <span
                  key={c}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold"
                >
                  <span>💎</span>
                  <span>{c}</span>
                  <button
                    onClick={() => setSelectedConvictions(selectedConvictions.filter((x) => x !== c))}
                    className="hover:text-rose-400"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </span>
              );
            })}

            {optionTypeFilter !== "ALL" && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 text-xs font-semibold">
                Direction: {optionTypeFilter}
                <button onClick={() => setOptionTypeFilter("ALL")} className="hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {assetFilter !== "ALL" && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold">
                Asset: {assetFilter}
                <button onClick={() => setAssetFilter("ALL")} className="hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {minPremiumFilter > 0 && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-semibold">
                Min: {formatPremiumDisplay(minPremiumFilter)}+
                <button onClick={() => setMinPremiumFilter(0)} className="hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            {chartFilter !== "ALL" && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 text-xs font-semibold">
                {chartFilter === "WITH_CHART" ? "Has Tape" : "No Chart"}
                <button onClick={() => setChartFilter("ALL")} className="hover:text-rose-400">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}

            <button
              onClick={handleResetFilters}
              className="text-[11px] font-bold text-rose-400 hover:text-rose-300 underline ml-2 cursor-pointer"
            >
              Clear All
            </button>
          </div>
        )}
      </div>

      {/* Main Flow Table */}
      <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl backdrop-blur-xl">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-[#0E131D] text-xs font-semibold uppercase tracking-wider text-slate-400">
                {/* Ticker & Live Stock Price */}
                <th
                  onClick={() => handleSort("ticker")}
                  className="py-3.5 px-4 cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Ticker & Live Price</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "ticker" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Contract Details & Live Mark */}
                <th
                  onClick={() => handleSort("strike")}
                  className="py-3.5 px-4 cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Contract & Estimated Mark</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "strike" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Horizon / DTE */}
                <th
                  onClick={() => handleSort("dte")}
                  className="py-3.5 px-4 cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Horizon / DTE</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "dte" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Notional Premium */}
                <th
                  onClick={() => handleSort("premium_usd")}
                  className="py-3.5 px-4 text-right cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center justify-end gap-1.5">
                    <span>Notional Premium</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "premium_usd" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Flow Tags */}
                <th className="py-3.5 px-4">Institutional Flow Tags</th>

                {/* Flowseeker Score */}
                <th
                  onClick={() => handleSort("flow_score")}
                  className="py-3.5 px-4 cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Flowseeker Score</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "flow_score" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Timestamp */}
                <th
                  onClick={() => handleSort("trade_timestamp")}
                  className="py-3.5 px-4 cursor-pointer hover:text-white transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Timestamp</span>
                    <ArrowUpDown className={`w-3.5 h-3.5 ${sortField === "trade_timestamp" ? "text-emerald-400" : "text-slate-600"}`} />
                  </div>
                </th>

                {/* Chart / Tape */}
                <th className="py-3.5 px-4 text-center">Chart / Tape</th>

                {/* Shadow Quant Bridge */}
                <th className="py-3.5 px-4 text-right">Shadow Quant Bridge</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-sm font-normal text-slate-300">
              {filteredAndSortedFlows.length === 0 ? (
                <tr>
                  <td colSpan={9} className="py-16 text-center text-slate-500">
                    <div className="flex flex-col items-center justify-center gap-2">
                      <Radio className="w-8 h-8 text-slate-600 animate-pulse" />
                      <p className="text-sm font-medium">No matching notable flows captured for current filters.</p>
                      <button
                        onClick={handleResetFilters}
                        className="mt-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-emerald-400 rounded-lg text-xs font-semibold"
                      >
                        Reset All Filters
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredAndSortedFlows.map((item) => {
                  const isCall = item.call_put?.toUpperCase().startsWith("C");
                  const badge = getFlowseekerScore(item);
                  const isEtf = item.asset_type?.toLowerCase() === "etf" || (item.source || "").includes("etf");
                  const origin = getOriginBadge(item.source, item.asset_type);
                  const dynamicDte = getDynamicDte(item.expiration, item.dte);
                  const isExpired = dynamicDte <= 0;
                  const quote = currentQuotes[item.ticker.toUpperCase()];
                  const contractPrice = getOptionContractPrice(item, quote?.price);

                  return (
                    <tr
                      key={item.flow_id}
                      className={`hover:bg-slate-800/30 transition-colors group ${isExpired ? "opacity-60 bg-slate-900/40" : ""}`}
                    >
                      {/* Ticker & Live Stock Price */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <div className={`p-2 rounded-xl ${isCall ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "bg-rose-500/10 text-rose-400 border border-rose-500/20"}`}>
                            {isCall ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => setSearchQuery(item.ticker)}
                                className="font-bold text-white text-base tracking-wide hover:text-emerald-400 transition-colors text-left"
                                title="Click to filter by this ticker"
                              >
                                ${item.ticker}
                              </button>
                              {quote && quote.price >= 0 && (
                                <div className="flex items-center gap-1 text-xs font-bold text-slate-200 bg-[#0B0F17] border border-slate-700/80 px-2 py-0.5 rounded-lg shadow-sm">
                                  <span>Observed {moneyText(quote.price)} · {quote.source} · {quote.as_of}</span>
                                  <span className="text-[10px] font-bold">
                                    {quote.change_pct == null ? 'Change unknown' : `${quote.change_pct.toFixed(2)}%`}
                                  </span>
                                  {quote.is_extended_hours && (
                                    <span className="text-[9px] px-1 py-0.2 rounded bg-amber-500/20 text-amber-300 font-mono" title="Pre-Market / Post-Market Live Extended Hours Quote">
                                      EXT
                                    </span>
                                  )}
                                </div>
                              )}
                              {isEtf && (
                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-semibold">
                                  ETF
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1 mt-1">
                              <button
                                onClick={() =>
                                  setSelectedOrigins((prev) =>
                                    prev.includes(origin.id) ? prev.filter((x) => x !== origin.id) : [...prev, origin.id]
                                  )
                                }
                                className={`text-[10px] px-1.5 py-0.5 rounded border font-semibold flex items-center gap-1 hover:opacity-80 transition-opacity ${origin.color}`}
                                title={`Click to toggle filter for origin: ${origin.label}`}
                              >
                                <span>{origin.icon}</span>
                                <span>{origin.badge}</span>
                              </button>
                            </div>
                          </div>
                        </div>
                        <RecordedResearchCards candidates={item.research_candidates} history={item.research_history} />
                      </td>

                      {/* Contract Details & Live Mark */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="font-bold text-white text-sm">
                            ${item.strike} {isCall ? "CALL" : "PUT"}
                          </div>
                          {quote && quote.price > 0 && (
                            (() => {
                              const spot = quote.price;
                              const isOtm = isCall ? item.strike > spot : spot > item.strike;
                              const distPct = isCall ? ((item.strike - spot) / spot) * 100 : ((spot - item.strike) / spot) * 100;
                              return (
                                <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold border ${
                                  isOtm
                                    ? isCall ? "bg-teal-500/15 text-teal-300 border-teal-500/30" : "bg-pink-500/15 text-pink-300 border-pink-500/30"
                                    : "bg-amber-500/15 text-amber-300 border-amber-500/30"
                                }`}>
                                  {isOtm ? `+${Math.abs(distPct).toFixed(1)}% OTM` : `-${Math.abs(distPct).toFixed(1)}% ITM`}
                                </span>
                              );
                            })()
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-1">
                          <div className="text-[11px] font-bold text-emerald-400 flex items-center gap-1 bg-emerald-500/10 border border-emerald-500/25 px-2 py-0.5 rounded-md">
                            <span>Estimated mark: {moneyText(contractPrice.perShare)}</span>
                            <span className="text-[9px] text-slate-400 font-normal">({moneyText(contractPrice.totalContract)}/ct; assumed IV 42%; nonexecutable)</span>
                          </div>
                          <span className="text-xs text-slate-400">
                            Exp: {item.expiration}
                          </span>
                        </div>
                      </td>

                      {/* Moneyness / DTE */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          {isExpired ? (
                            <span className="text-[10px] px-2 py-0.5 rounded font-bold bg-slate-800 text-slate-400 border border-slate-700">
                              EXPIRED ({dynamicDte}d)
                            </span>
                          ) : (
                            <>
                              <span className="text-xs font-semibold text-slate-300">
                                {dynamicDte} DTE
                              </span>
                              <button
                                onClick={() => {
                                  const targetDte = dynamicDte >= 90 ? "LEAP" : dynamicDte >= 20 ? "SWING" : "SHORT_DTE";
                                  setSelectedDtes((prev) =>
                                    prev.includes(targetDte) ? prev.filter((x) => x !== targetDte) : [...prev, targetDte]
                                  );
                                }}
                                className={`text-[10px] px-1.5 py-0.5 rounded font-bold hover:opacity-80 transition-opacity ${
                                  dynamicDte >= 90
                                    ? "bg-purple-500/20 text-purple-300"
                                    : dynamicDte >= 20
                                    ? "bg-cyan-500/20 text-cyan-300"
                                    : "bg-amber-500/20 text-amber-300"
                                }`}
                                title="Click to toggle filter for this horizon"
                              >
                                {dynamicDte >= 90 ? "LEAP" : dynamicDte >= 20 ? "SWING" : "SHORT-DTE"}
                              </button>
                            </>
                          )}
                        </div>
                      </td>

                      {/* Notional Premium */}
                      <td className="py-4 px-4 whitespace-nowrap text-right">
                        <div className="font-bold text-base text-emerald-400">
                          {formatPremiumDisplay(item.premium_usd, item.premium_raw)}
                        </div>
                        <div className="text-[10px] text-slate-500">
                          {item.premium_usd ? `$${item.premium_usd.toLocaleString()}` : "Institutional Block"}
                        </div>
                      </td>

                      {/* Flow Tags */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex flex-wrap items-center gap-1">
                          {getFlowTags(item).map((tag) => (
                            <button
                              key={tag.id}
                              onClick={() =>
                                setSelectedFlowTags((prev) =>
                                  prev.includes(tag.id) ? prev.filter((x) => x !== tag.id) : [...prev, tag.id]
                                )
                              }
                              className={`text-[10px] px-2 py-0.5 rounded-md font-bold border transition-all hover:scale-105 cursor-pointer ${
                                selectedFlowTags.includes(tag.id)
                                  ? "ring-2 ring-emerald-400 shadow-md"
                                  : ""
                              } ${tag.color} ${tag.bg} ${tag.border}`}
                              title={`Click to toggle filter for ${tag.label}`}
                            >
                              {tag.label}
                            </button>
                          ))}
                        </div>
                      </td>

                      {/* Flowseeker Score */}
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => setSelectedConvictions([badge.score >= 85 ? "DIAMOND" : badge.score >= 70 ? "STRONG" : "NOTABLE"])}
                            className={`text-xs font-bold px-2 py-0.5 rounded-md border hover:opacity-80 transition-opacity ${badge.color}`}
                            title="Click to filter by this conviction tier"
                          >
                            ★ {badge.score}
                          </button>
                          <span className="text-xs text-slate-400 hidden sm:inline">
                            {badge.label}
                          </span>
                        </div>
                      </td>

                      {/* Timestamp */}
                      <td className="py-4 px-4 whitespace-nowrap text-xs text-slate-400">
                        {item.trade_timestamp ? item.trade_timestamp.replace("T", " ").substring(0, 16) : "Live"}
                      </td>

                      {/* Chart Preview Button */}
                      <td className="py-4 px-4 whitespace-nowrap text-center">
                        <button
                          onClick={() => setSelectedChartModal(item)}
                          className="p-1.5 bg-slate-800/90 hover:bg-indigo-600/30 text-cyan-400 hover:text-cyan-200 rounded-lg transition-all border border-slate-700 hover:border-cyan-500/50 shadow-sm flex items-center gap-1 mx-auto"
                          title="View Technical Tape & Candlestick Chart"
                        >
                          <ImageIcon className="w-4 h-4" />
                          <span className="text-[10px] font-bold font-mono">TAPE</span>
                        </button>
                      </td>

                      {/* 1-Click Shadow Quant Bridge */}
                      <td className="py-4 px-4 whitespace-nowrap text-right">
                        <button
                          onClick={() => navigate(`/quant-shadow?ticker=${item.ticker.toUpperCase()}`)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-bold shadow-lg shadow-purple-600/20 transition-all active:scale-95"
                          title={`Evaluate $${item.ticker} in Dynamic Shadow Quant`}
                        >
                          <Zap className="w-3.5 h-3.5 text-amber-300" />
                          Analyze Quant
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
        </>
      )}

      {activeTab === "validator" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
          <p role="status">{portfolioLoading ? 'Loading portfolio…' : portfolioError ?? `Paper simulation — as of ${snapshotText(portfolioData?.autonomous_ai?.as_of)}; estimated marks are nonexecutable. All paper cohorts, including test/legacy; not validated performance.`}</p>
          {strategyError && <p role="alert">{strategyError}</p>}
          {/* Portfolio Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="bg-[#131924]/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur-md">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Total Portfolio Value</div>
              <div className="text-2xl font-black text-white mt-1 font-mono">
                {moneyText(portfolioData?.autonomous_ai?.open_positions?.some((h: any) => !validatedHoldingMark(portfolioData.autonomous_ai, h)) ? null : portfolioData?.autonomous_ai?.total_value)}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Paper cash plus estimated holding value · nonexecutable{portfolioData?.autonomous_ai?.open_positions?.some((h: any) => validatedHoldingMark(portfolioData.autonomous_ai, h)?.freshness === 'stale') ? ' · stale historical marks (over 60s), not current equity' : ''}</div>
            </div>

            <div className="bg-[#131924]/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur-md">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Available Cash</div>
              <div className="text-2xl font-black text-emerald-400 mt-1 font-mono">
                {moneyText(portfolioData?.autonomous_ai?.cash_balance)}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Uncommitted Validation Capital</div>
            </div>

            <div className="bg-[#131924]/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur-md">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Realized P&L</div>
              <div className={`text-2xl font-black mt-1 font-mono ${Number(portfolioData?.autonomous_ai?.realized_pnl || 0) >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                {moneyText(portfolioData?.autonomous_ai?.realized_pnl)}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Gross, including trims; net {moneyText(portfolioData?.autonomous_ai?.net_realized_pnl)}</div>
            </div>

            <div className="bg-[#131924]/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur-md">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Active Shadow Trades</div>
              <div className="text-2xl font-black text-indigo-400 mt-1 font-mono">
                {portfolioData?.autonomous_ai?.active_positions_count ?? 'Unknown'} Open
              </div>
              <div className="text-[11px] text-slate-500 mt-1">Committed paper holdings; not live execution</div>
            </div>

            <div className="bg-[#131924]/90 border border-slate-800 rounded-xl p-4 shadow-lg backdrop-blur-md">
              <div className="text-xs text-slate-400 font-medium uppercase tracking-wider">Gross Win Rate (Descriptive)</div>
              <div className="text-2xl font-black text-amber-400 mt-1 font-mono">
                {portfolioData?.autonomous_ai?.win_rate_pct != null && portfolioData?.autonomous_ai?.closed_positions_count > 0 ? `${portfolioData.autonomous_ai.win_rate_pct}%` : "Awaiting Data"}
              </div>
              <div className="text-[11px] text-slate-500 mt-1">{portfolioData?.autonomous_ai?.closed_positions_count ?? 'Unknown'} Closed Positions Logged</div>
            </div>
          </div>

          {/* Active Validating Positions Table */}
          <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl">
                  <Zap className="w-5 h-5 text-amber-300" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    Active Validating Positions (Portfolio B: Autonomous AI)
                  </h3>
                  <p className="text-xs text-slate-400">
                    Paper simulation only; each holding identifies options contracts versus underlying shares. Not live broker execution.
                  </p>
                </div>
              </div>
              <button
                onClick={fetchPortfolio}
                disabled={portfolioLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-bold transition-all border border-slate-700"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${portfolioLoading ? "animate-spin text-emerald-400" : ""}`} />
                Refresh Positions
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-3">Ticker / Direction</th>
                    <th className="py-3 px-3">OCC Contract</th>
                    <th className="py-3 px-3">Strategy Archetype</th>
                    <th className="py-3 px-3">Contracts / Cost</th>
                    <th className="py-3 px-3">Entry Price</th>
                    <th className="py-3 px-3">Mark Price</th>
                    <th className="py-3 px-3">Dynamic Targets (TP1 / TP2)</th>
                    <th className="py-3 px-3">Stop Loss</th>
                    <th className="py-3 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {(!portfolioData?.autonomous_ai?.open_positions || portfolioData.autonomous_ai.open_positions.length === 0) ? (
                    <tr>
                      <td colSpan={9} className="py-12 text-center text-slate-500 font-sans">
                        <div className="flex flex-col items-center justify-center gap-2">
                          <Radio className="w-6 h-6 text-slate-600 animate-pulse" />
                          <p className="text-sm font-semibold text-slate-400">{Array.isArray(portfolioData?.autonomous_ai?.open_positions) ? 'No Open Paper Positions' : 'Positions Unknown'}</p>
                          <p className="text-xs text-slate-500">Paper execution requires separate explicit authorization; alerts do not authorize trades.</p>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    portfolioData.autonomous_ai.open_positions.map((h: any) => {
                      const entry = h.average_cost ?? h.entry_price;
                      const mark = validatedHoldingMark(portfolioData.autonomous_ai, h);
                      const isCall = (h.direction || "").toLowerCase().includes("call");
                      return (
                        <tr key={h.holding_id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-white text-sm font-sans">${h.ticker}</span>
                              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${isCall ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-rose-500/20 text-rose-300 border border-rose-500/30"}`}>
                                {h.asset_type !== 'option' ? 'UNDERLYING' : isCall ? 'CALL' : 'PUT'}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-slate-300 text-xs">
                            {h.asset_type !== 'option' ? 'Paper shares' : h.occ_symbol || `${h.ticker} ${h.strike}${isCall ? "C" : "P"} ${h.expiration}`}
                          </td>
                          <td className="py-3 px-3">
                            <span className="text-[10px] px-2 py-0.5 rounded-full font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 font-sans">
                              {h.strategy_name || "Unknown strategy"}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-300">
                            {h.quantity} {h.asset_type === 'option' ? 'contracts' : 'shares'} ({moneyText(entry == null ? null : entry * Number(h.quantity) * (h.asset_type === 'option' ? 100 : 1))})
                          </td>
                          <td className="py-3 px-3 text-slate-300 font-bold">{moneyText(entry)}</td>
                          <td className="py-3 px-3">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-white">Estimated {moneyText(mark?.price)} · {mark?.asOf ?? 'validated mark unavailable'} · {mark?.freshness === 'stale' ? 'stale · ' : evidenceAge(portfolioData.autonomous_ai.as_of) > 60000 ? 'snapshot stale · ' : ''}nonexecutable</span>
                            </div>
                          </td>
                          <td className="py-3 px-3 text-slate-300">
                            <span className="text-emerald-400">TP1: {moneyText(h.target_tp1)}</span>
                            <span className="text-slate-500 mx-1">·</span>
                            <span className="text-cyan-400">TP2: {moneyText(h.target_tp2)}</span>
                          </td>
                          <td className="py-3 px-3 text-rose-400 font-bold">
                            {h.status === "TRIMMED" ? (
                              <span className="text-teal-300 bg-teal-500/20 px-1.5 py-0.5 rounded border border-teal-500/30">
                                Stop {moneyText(h.target_sl)}
                              </span>
                            ) : (
                              moneyText(h.target_sl)
                            )}
                          </td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase font-sans ${
                              h.status === "TRIMMED"
                                ? "bg-teal-500/20 text-teal-300 border border-teal-500/40"
                                : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                            }`}>
                              {h.status === "TRIMMED" ? "Trimmed" : "Open"}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Closed Validations Journal */}
          <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/10 text-purple-400 rounded-xl">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Closed Strategy Validations Journal</h3>
                  <p className="text-xs text-slate-400">Recent closed holdings for display only; full-history statistics above use the economic journal. Gross outcomes, not observed-cost net performance.</p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px]">
                    <th className="py-3 px-3">Closed Date</th>
                    <th className="py-3 px-3">Ticker / Contract</th>
                    <th className="py-3 px-3">Strategy Archetype</th>
                    <th className="py-3 px-3">Entry Price</th>
                    <th className="py-3 px-3">Exit Price</th>
                    <th className="py-3 px-3">Outcome</th>
                    <th className="py-3 px-3 text-right">Realized Return</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-mono">
                  {(!portfolioData?.autonomous_ai?.recent_closed_positions || portfolioData.autonomous_ai.recent_closed_positions.length === 0) ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                        {Array.isArray(portfolioData?.autonomous_ai?.recent_closed_positions) ? 'No closed strategy validations recorded yet.' : 'Closed holdings unknown.'}
                      </td>
                    </tr>
                  ) : (
                    portfolioData.autonomous_ai.recent_closed_positions.map((ch: any) => {
                      const economic = holdingStatistics?.holdings?.find((s: any) => s.holding_id === ch.holding_id);
                      const pnl = economic?.status === 'resolved' ? economic.gross_pnl : null;
                      return (
                        <tr key={ch.holding_id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-3 text-slate-400">{ch.closed_at ? new Date(ch.closed_at).toLocaleString() : "Unknown"}</td>
                          <td className="py-3 px-3 font-bold text-white">${ch.ticker} {ch.occ_symbol || ""}</td>
                          <td className="py-3 px-3">
                            <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700 font-sans">
                              {ch.strategy_name || "Unknown strategy"}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-slate-300">{moneyText(ch.average_cost)}</td>
                          <td className="py-3 px-3 text-slate-300">{moneyText(ch.current_price)}</td>
                          <td className="py-3 px-3">
                            <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold font-sans ${pnl >= 0 ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30" : "bg-rose-500/20 text-rose-300 border border-rose-500/30"}`}>
                              {pnl == null ? 'Unknown / excluded' : pnl > 0 ? 'GROSS WIN' : pnl < 0 ? 'GROSS LOSS' : 'BREAKEVEN'}
                            </span>
                          </td>
                          <td className={`py-3 px-3 text-right font-bold ${pnl >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {moneyText(pnl)}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === "strategies" && (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-2">
          <p role="status">{portfolioLoading ? 'Loading statistics…' : strategyError ?? `Full-history paper holdings — as of ${snapshotText(holdingStatistics?.as_of)}. Gross outcomes; costs and exclusions shown. All paper cohorts, including test/legacy. Descriptive only, not live qualification.`}</p>
          <p>Cohorts: {holdingStatistics?.by_cohort ? Object.entries(holdingStatistics.by_cohort).map(([name, value]: [string, any]) => `${name}: ${value.holding_count} holdings, ${value.excluded_count} excluded`).join('; ') || 'Empty history' : 'Unknown'}</p>
          {/* Strategy Scorecards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="bg-[#131924]/90 border border-amber-500/30 rounded-2xl p-5 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-300 uppercase tracking-wider">A+ Dream Setup</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-200 border border-amber-500/40">Tier 2 Asymmetric</span>
              </div>
              <div className="text-2xl font-black text-white mt-3 font-mono">{getStrategyStats("DREAM").winRate}</div>
              <p className="text-[11px] text-amber-400 font-mono mt-0.5">{getStrategyStats("DREAM").sampleText}</p>
              <p className="text-xs text-slate-400 mt-1">Multi-whale confluence + EMA stack + GEX breakout above key node.</p>
              <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs">
                <span className="text-slate-400">Target TP1: <strong className="text-emerald-400">+25%</strong></span>
                <span className="text-slate-400">Target TP2: <strong className="text-cyan-400">+60%</strong></span>
              </div>
            </div>

            <div className="bg-[#131924]/90 border border-purple-500/30 rounded-2xl p-5 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-300 uppercase tracking-wider">GEX Gamma Squeeze</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-200 border border-purple-500/40">Volatility Expansion</span>
              </div>
              <div className="text-2xl font-black text-white mt-3 font-mono">{getStrategyStats("GAMMA").winRate}</div>
              <p className="text-[11px] text-purple-400 font-mono mt-0.5">{getStrategyStats("GAMMA").sampleText}</p>
              <p className="text-xs text-slate-400 mt-1">Negative gamma regime with aggressive call sweep velocity crossing ask.</p>
              <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs">
                <span className="text-slate-400">Target TP1: <strong className="text-emerald-400">+20%</strong></span>
                <span className="text-slate-400">Target TP2: <strong className="text-cyan-400">+50%</strong></span>
              </div>
            </div>

            <div className="bg-[#131924]/90 border border-emerald-500/30 rounded-2xl p-5 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-emerald-300 uppercase tracking-wider">EMA Stack Breakout</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-200 border border-emerald-500/40">Trend Following</span>
              </div>
              <div className="text-2xl font-black text-white mt-3 font-mono">{getStrategyStats("EMA").winRate}</div>
              <p className="text-[11px] text-emerald-400 font-mono mt-0.5">{getStrategyStats("EMA").sampleText}</p>
              <p className="text-xs text-slate-400 mt-1">Bullish 8 &gt; 21 &gt; 50 &gt; 100 &gt; 200 EMA alignment with zero 200 EMA traps.</p>
              <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs">
                <span className="text-slate-400">Target TP1: <strong className="text-emerald-400">+20%</strong></span>
                <span className="text-slate-400">Target TP2: <strong className="text-cyan-400">+45%</strong></span>
              </div>
            </div>

            <div className="bg-[#131924]/90 border border-cyan-500/30 rounded-2xl p-5 shadow-xl backdrop-blur-xl">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-cyan-300 uppercase tracking-wider">Inst. Whale Sweep</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-cyan-500/20 text-cyan-200 border border-cyan-500/40">Capital Clustering</span>
              </div>
              <div className="text-2xl font-black text-white mt-3 font-mono">{getStrategyStats("WHALE").winRate}</div>
              <p className="text-[11px] text-cyan-400 font-mono mt-0.5">{getStrategyStats("WHALE").sampleText}</p>
              <p className="text-xs text-slate-400 mt-1">&gt;$200k/$500k repeat cluster accumulation with Vol/OI &ge; 2.5x surge.</p>
              <div className="mt-4 pt-3 border-t border-slate-800 flex justify-between text-xs">
                <span className="text-slate-400">Target TP1: <strong className="text-emerald-400">+20%</strong></span>
                <span className="text-slate-400">Target TP2: <strong className="text-cyan-400">+45%</strong></span>
              </div>
            </div>
          </div>

          {/* Quantitative Event Stream */}
          <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl p-5 shadow-xl backdrop-blur-xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-xl">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Quantitative Strategy Trace Ledger</h3>
                  <p className="text-xs text-slate-400">Nightly learning telemetry recorded to SQLite for strategy optimization and machine learning.</p>
                </div>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse font-mono">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-400 uppercase tracking-wider text-[11px] font-sans">
                    <th className="py-3 px-3">Trace ID</th>
                    <th className="py-3 px-3">Ticker</th>
                    <th className="py-3 px-3">Strategy Name</th>
                    <th className="py-3 px-3">Directional Bias</th>
                    <th className="py-3 px-3">Action</th>
                    <th className="py-3 px-3">Status</th>
                    <th className="py-3 px-3">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {strategiesList.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                        No recorded strategy traces found in database.
                      </td>
                    </tr>
                  ) : (
                    strategiesList.map((st: any) => (
                      <tr key={st.trace_id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="py-3 px-3 text-slate-400 text-[11px]">{st.trace_id}</td>
                        <td className="py-3 px-3 font-bold text-white font-sans">${st.ticker}</td>
                        <td className="py-3 px-3 text-amber-300 font-sans">{st.strategy_name}</td>
                        <td className={`py-3 px-3 font-medium ${st.directional_bias === "BEARISH" ? "text-rose-400" : (st.directional_bias === "BULLISH" ? "text-emerald-400" : "text-slate-400")}`}>{st.directional_bias || "NEUTRAL"}</td>
                        <td className="py-3 px-3 text-slate-300">{st.action}</td>
                        <td className="py-3 px-3">
                          <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-sans">
                            {st.status}
                          </span>
                        </td>
                        <td className="py-3 px-3 text-slate-400">{st.timestamp ? new Date(st.timestamp).toLocaleString() : ""}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Chart Screenshot & Technical Tape Modal */}
      {selectedChartModal && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#131924] border border-slate-700 rounded-2xl max-w-4xl w-full p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-xl">
                  <ImageIcon className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white flex items-center gap-2">
                    <span>${selectedChartModal.ticker}</span>
                    <span className="text-sm font-mono text-emerald-400">
                      ${selectedChartModal.strike} {selectedChartModal.call_put?.toUpperCase().startsWith("C") ? "CALL" : "PUT"}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                      {selectedChartModal.expiration}
                    </span>
                  </h3>
                  <p className="text-xs text-slate-400">
                    Institutional Flow Tape & Technical Candlestick Analysis ({selectedChartModal.premium_raw} Premium)
                  </p>
                </div>
              </div>
              <button
                onClick={() => setSelectedChartModal(null)}
                className="p-2 bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white rounded-xl transition-all"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="bg-[#0B0F17] border border-slate-800 rounded-xl overflow-hidden flex items-center justify-center min-h-[350px] max-h-[550px] relative p-2">
              <img
                src={`/api/analyst-trader/flow-chart/${selectedChartModal.flow_id}?v=${encodeURIComponent(selectedChartModal.local_chart_path || selectedChartModal.trade_timestamp || "latest")}`}
                onError={(e) => {
                  const target = e.currentTarget;
                  if (selectedChartModal.chart_url && target.src !== selectedChartModal.chart_url) {
                    target.src = selectedChartModal.chart_url;
                  }
                }}
                alt={`Technical Chart & Tape for $${selectedChartModal.ticker}`}
                className="w-full h-full object-contain rounded-lg"
              />
            </div>

            <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-slate-300">Origin:</span>
                <span>{getOriginBadge(selectedChartModal.source, selectedChartModal.asset_type).label}</span>
                {selectedChartModal.local_chart_path && (
                  <span className="text-[10px] text-slate-500 font-mono hidden sm:inline">
                    ({selectedChartModal.local_chart_path.split("/").pop()})
                  </span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => {
                    navigate(`/quant-shadow?ticker=${selectedChartModal.ticker.toUpperCase()}`);
                    setSelectedChartModal(null);
                  }}
                  className="px-3 py-1.5 bg-purple-600/30 hover:bg-purple-600/50 text-purple-200 border border-purple-500/40 rounded-xl font-bold transition-all flex items-center gap-1.5"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-300" />
                  Open in Quant Shadow
                </button>
                <button
                  onClick={() => setSelectedChartModal(null)}
                  className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-bold transition-all"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
