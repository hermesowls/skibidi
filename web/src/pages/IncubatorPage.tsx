import React, { useState } from "react";
import {
  FlaskConical,
  TrendingUp,
  TrendingDown,
  Sparkles,
  Zap,
  CheckCircle2,
  AlertCircle,
  Brain,
  Layers,
  Clock,
  Play,
  RefreshCw,
  Sliders,
  DollarSign,
  ArrowUpRight,
  ShieldAlert,
  Lightbulb
} from "lucide-react";

interface SubPortfolio {
  id: string;
  name: string;
  category: string;
  allocated_capital: number;
  cash: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_trades: number;
  winning_trades: number;
  win_rate: number;
  status: string;
  hypothesis: string;
  created_at: string;
}

interface ExperimentalTrade {
  trade_id: string;
  portfolio_id: string;
  symbol: string;
  side: string;
  qty: number;
  entry_price: number;
  exit_price?: number;
  status: string;
  pnl: number;
  pnl_percent: number;
  hypothesis: string;
  entry_reasoning: string;
  exit_reasoning?: string;
  timestamp: string;
}

interface EvolutionLog {
  evolution_id: string;
  timestamp: string;
  llm_reasoning: string;
  actions_taken: string[];
  new_hypotheses_added: string[];
}

const SEED_PORTFOLIOS: SubPortfolio[] = [
  {
    id: "exp_uw_flow",
    name: "Pure Institutional Flow Strategy",
    category: "UW_FLOW",
    allocated_capital: 1000.0,
    cash: 1000.0,
    realized_pnl: 142.50,
    unrealized_pnl: 35.00,
    total_trades: 5,
    winning_trades: 4,
    win_rate: 80.0,
    status: "ACTIVE",
    hypothesis: "High-conviction ask-side sweeps (> $250k premium) correlate with 15%+ intraday volatility expansion in tech megacaps.",
    created_at: "2026-07-25 09:00:00"
  },
  {
    id: "exp_skylit_gex",
    name: "Skylit GEX Zero-Gamma Pin Strategy",
    category: "SKYLIT_GEX",
    allocated_capital: 1000.0,
    cash: 1000.0,
    realized_pnl: 88.00,
    unrealized_pnl: 12.50,
    total_trades: 4,
    winning_trades: 3,
    win_rate: 75.0,
    status: "ACTIVE",
    hypothesis: "Dealer gamma flip strikes act as magnet pins during low-volume sessions and trend boundaries during high-volume sessions.",
    created_at: "2026-07-25 09:00:00"
  },
  {
    id: "exp_kian_ta",
    name: "Kian Technical Reversal Strategy",
    category: "KIAN_TA",
    allocated_capital: 1000.0,
    cash: 1000.0,
    realized_pnl: -24.00,
    unrealized_pnl: 0.00,
    total_trades: 3,
    winning_trades: 1,
    win_rate: 33.3,
    status: "ACTIVE",
    hypothesis: "9/21 EMA golden cross with RSI < 35 on 15-min charts signals high-probability mean reversion.",
    created_at: "2026-07-25 09:00:00"
  },
  {
    id: "exp_llm_vol_crush",
    name: "LLM Hypothesis: Post-Earnings IV Crush",
    category: "LLM_DISCOVERED",
    allocated_capital: 1000.0,
    cash: 1250.0,
    realized_pnl: 210.00,
    unrealized_pnl: 18.50,
    total_trades: 2,
    winning_trades: 2,
    win_rate: 100.0,
    status: "ACTIVE",
    hypothesis: "Autonomously generated strategy: Selling credit spreads 15 mins before market close on high IV earnings announcements.",
    created_at: "2026-07-27 16:00:00"
  }
];

const SEED_TRADES: ExperimentalTrade[] = [
  {
    trade_id: "trd_003",
    portfolio_id: "exp_llm_vol_crush",
    symbol: "TSLA",
    side: "BUY_PUT",
    qty: 1.0,
    entry_price: 242.00,
    status: "OPEN",
    pnl: 18.50,
    pnl_percent: 7.64,
    hypothesis: "Testing LLM earnings IV crush hypothesis",
    entry_reasoning: "Implied volatility percentile at 94th rank",
    timestamp: "2026-07-28 11:00:00"
  },
  {
    trade_id: "trd_002",
    portfolio_id: "exp_skylit_gex",
    symbol: "SPY",
    side: "BUY_CALL",
    qty: 2.0,
    entry_price: 548.20,
    exit_price: 551.10,
    status: "CLOSED",
    pnl: 58.00,
    pnl_percent: 10.58,
    hypothesis: "Skylit GEX zero-gamma pin identified at 550.00",
    entry_reasoning: "Dealer gamma squeeze toward pin level",
    exit_reasoning: "Hit dealer pin target",
    timestamp: "2026-07-28 09:30:00"
  },
  {
    trade_id: "trd_001",
    portfolio_id: "exp_uw_flow",
    symbol: "NVDA",
    side: "BUY_CALL",
    qty: 1.0,
    entry_price: 124.50,
    exit_price: 142.00,
    status: "CLOSED",
    pnl: 17.50,
    pnl_percent: 14.05,
    hypothesis: "Unusual Whales detected $1.2M sweep at 125 strike",
    entry_reasoning: "Strong institutional flow + tech sector momentum",
    exit_reasoning: "Reached profit target +14%",
    timestamp: "2026-07-27 10:15:00"
  }
];

const SEED_EVOLUTIONS: EvolutionLog[] = [
  {
    evolution_id: "evo_20260728_1300",
    timestamp: "Today at 13:00 PST",
    llm_reasoning: "Evaluated 4 active sub-portfolios. Pure UW Flow and LLM IV Crush are performing strongly (+14.2% & +21.0%). Kian TA Strategy struggled due to choppy range-bound action. Action: Tightened stop-loss on Kian TA to -4% and allocated +$250 to LLM IV Crush.",
    actions_taken: [
      "Adjusted Kian TA stop-loss to -4%",
      "Increased LLM IV Crush allocation to $1,250",
      "Incubating new strategy: Market Maker Liquidity Void Scalp"
    ],
    new_hypotheses_added: [
      "Market Maker Liquidity Void Scalp: Exploits bid-ask spread gaps in high-volatility midcap tech."
    ]
  }
];

export function IncubatorPage() {
  const [portfolios, setPortfolios] = useState<SubPortfolio[]>(SEED_PORTFOLIOS);
  const [trades, setTrades] = useState<ExperimentalTrade[]>(SEED_TRADES);
  const [evolutions, setEvolutions] = useState<EvolutionLog[]>(SEED_EVOLUTIONS);
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<string>("all");
  const [isEvolving, setIsEvolving] = useState(false);

  const runEvolutionCycle = () => {
    setIsEvolving(true);
    setTimeout(() => {
      const newEvo: EvolutionLog = {
        evolution_id: `evo_${Date.now()}`,
        timestamp: "Just now",
        llm_reasoning: "Autonomous Evolution Cycle completed. Analyzed execution logs across all sub-portfolios. Reinforced weighting on institutional flow sweeps. Zero-gamma pin tolerance calibrated to +/- 0.25%.",
        actions_taken: [
          "Calibrated GEX pin tolerance to +/- 0.25%",
          "Raised minimum UW sweep threshold to $300,000",
          "Generated new sub-portfolio: exp_llm_gamma_scalp"
        ],
        new_hypotheses_added: [
          "exp_llm_gamma_scalp: Scalping 0DTE options when market maker delta-hedging accelerates past GEX pivot."
        ]
      };
      setEvolutions([newEvo, ...evolutions]);
      setIsEvolving(false);
    }, 2000);
  };

  const filteredTrades = selectedPortfolioId === "all"
    ? trades
    : trades.filter((t) => t.portfolio_id === selectedPortfolioId);

  const totalPnL = portfolios.reduce((acc, p) => acc + p.realized_pnl + p.unrealized_pnl, 0);

  return (
    <div className="flex h-screen w-full bg-[#0b0e14] text-slate-100 overflow-hidden font-sans select-none">
      <div className="flex-1 flex flex-col h-full overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-slate-800/80 bg-[#111622]/90 backdrop-blur flex items-center justify-between sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-purple-500/10 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <FlaskConical className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-lg font-bold text-slate-100">Autonomous Strategy Incubator</h1>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20 font-mono">
                  SELF-EVOLVING LAB
                </span>
              </div>
              <p className="text-xs text-slate-400">Experimental Sub-Portfolios ($1k Each) + LLM Reasoned Strategy Evolution</p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 bg-[#1a202c] px-3 py-1.5 rounded-lg border border-slate-700/80">
              <DollarSign className="h-4 w-4 text-emerald-400" />
              <div>
                <span className="text-[10px] text-slate-400 font-mono block leading-none">Total Incubator PnL</span>
                <span className={`text-sm font-bold font-mono ${totalPnL >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                  {totalPnL >= 0 ? `+$${totalPnL.toFixed(2)}` : `-$${Math.abs(totalPnL).toFixed(2)}`}
                </span>
              </div>
            </div>

            <button
              onClick={runEvolutionCycle}
              disabled={isEvolving}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-xs transition-all shadow-lg ${
                isEvolving
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 cursor-wait"
                  : "bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white border border-purple-400/30"
              }`}
            >
              {isEvolving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
                  Evaluating Strategies...
                </>
              ) : (
                <>
                  <Brain className="h-4 w-4" />
                  Trigger Strategy Evolution Cycle
                </>
              )}
            </button>
          </div>
        </div>

        {/* Content Container */}
        <div className="p-6 space-y-8 max-w-[1600px] mx-auto w-full">
          {/* Sub-Portfolios Section */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-purple-400" />
                <h2 className="text-base font-semibold text-slate-100">Experimental Sub-Portfolios ($1,000 Allocation Each)</h2>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                {portfolios.length} Active Incubator Portfolios
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {portfolios.map((port) => {
                const combinedPnL = port.realized_pnl + port.unrealized_pnl;
                const isPositive = combinedPnL >= 0;

                return (
                  <div
                    key={port.id}
                    onClick={() => setSelectedPortfolioId(port.id === selectedPortfolioId ? "all" : port.id)}
                    className={`p-5 rounded-2xl border bg-gradient-to-b from-[#141a26] to-[#0d1117] cursor-pointer transition-all duration-200 shadow-xl ${
                      selectedPortfolioId === port.id
                        ? "ring-2 ring-purple-400 border-purple-500/50 scale-[1.02]"
                        : "border-slate-800 hover:border-slate-700 hover:scale-[1.01]"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/30">
                        {port.category}
                      </span>
                      <span className={`text-xs font-mono font-bold flex items-center gap-1 ${isPositive ? "text-emerald-400" : "text-rose-400"}`}>
                        {isPositive ? <ArrowUpRight className="h-3.5 w-3.5" /> : null}
                        {isPositive ? `+$${combinedPnL.toFixed(2)}` : `-$${Math.abs(combinedPnL).toFixed(2)}`}
                      </span>
                    </div>

                    <h3 className="text-sm font-bold text-slate-100 mb-2 leading-snug">{port.name}</h3>

                    <p className="text-xs text-slate-400 line-clamp-3 mb-4 leading-relaxed bg-[#080b10] p-2.5 rounded-xl border border-slate-800/80 italic">
                      "{port.hypothesis}"
                    </p>

                    <div className="grid grid-cols-2 gap-2 text-[11px] font-mono border-t border-slate-800/80 pt-3 text-slate-300">
                      <div>
                        <span className="text-[10px] text-slate-500 block">Win Rate</span>
                        <span className="font-bold text-emerald-400">{port.win_rate}% ({port.winning_trades}/{port.total_trades})</span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 block">Cap Allocated</span>
                        <span className="font-bold text-slate-200">${port.allocated_capital}</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Evolution Timeline & Reasoning History */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Brain className="h-4 w-4 text-purple-400" />
              <h2 className="text-base font-semibold text-slate-100">Autonomous LLM Strategy Evolution History</h2>
            </div>

            <div className="space-y-4">
              {evolutions.map((evo) => (
                <div key={evo.evolution_id} className="p-5 rounded-2xl bg-[#121722] border border-purple-500/20 shadow-xl relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3 border-b border-slate-800/80 pb-2">
                    <span className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                      <Sparkles className="h-3.5 w-3.5 text-purple-400" /> Evolution Cycle Record
                    </span>
                    <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                      <Clock className="h-3 w-3" /> {evo.timestamp}
                    </span>
                  </div>

                  <p className="text-xs text-slate-200 leading-relaxed mb-4 font-mono bg-[#090d14] p-3.5 rounded-xl border border-slate-800/80">
                    {evo.llm_reasoning}
                  </p>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                    <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                      <span className="font-semibold text-emerald-400 mb-2 block flex items-center gap-1">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Actions Taken & Parameter Tweaks
                      </span>
                      <ul className="space-y-1 text-slate-300">
                        {evo.actions_taken.map((act, i) => (
                          <li key={i} className="flex items-center gap-1.5 text-[11px]">
                            <span className="text-emerald-400">•</span> {act}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-800">
                      <span className="font-semibold text-purple-400 mb-2 block flex items-center gap-1">
                        <Lightbulb className="h-3.5 w-3.5" /> Newly Incubated Strategy Hypotheses
                      </span>
                      <ul className="space-y-1 text-slate-300">
                        {evo.new_hypotheses_added.map((hyp, i) => (
                          <li key={i} className="flex items-center gap-1.5 text-[11px]">
                            <span className="text-purple-400">•</span> {hyp}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Experimental Trades Explorer Table */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Zap className="h-4 w-4 text-amber-400" />
                <h2 className="text-base font-semibold text-slate-100">Experimental Strategy Executions</h2>
              </div>
              {selectedPortfolioId !== "all" && (
                <button
                  onClick={() => setSelectedPortfolioId("all")}
                  className="text-xs text-purple-400 hover:text-purple-300 font-mono underline"
                >
                  Show All Sub-Portfolios
                </button>
              )}
            </div>

            <div className="rounded-2xl border border-slate-800 bg-[#121722] overflow-hidden shadow-xl">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-slate-800 bg-[#171e2c] text-slate-400 font-mono text-[11px]">
                    <th className="p-4">Trade ID</th>
                    <th className="p-4">Sub-Portfolio</th>
                    <th className="p-4">Symbol</th>
                    <th className="p-4">Side</th>
                    <th className="p-4">Entry / Exit</th>
                    <th className="p-4">PnL ($ / %)</th>
                    <th className="p-4">Status</th>
                    <th className="p-4">LLM Reasoning / Hypothesis</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-200">
                  {filteredTrades.map((trd) => {
                    const isPositive = trd.pnl >= 0;
                    return (
                      <tr key={trd.trade_id} className="hover:bg-slate-800/40 transition-colors">
                        <td className="p-4 font-bold text-slate-400">{trd.trade_id}</td>
                        <td className="p-4 text-purple-300 font-semibold">{trd.portfolio_id}</td>
                        <td className="p-4 font-bold text-slate-100">{trd.symbol}</td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            trd.side.includes("BUY") ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30" : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          }`}>
                            {trd.side}
                          </span>
                        </td>
                        <td className="p-4 text-slate-300">
                          ${trd.entry_price} {trd.exit_price ? `→ $${trd.exit_price}` : "(Active)"}
                        </td>
                        <td className={`p-4 font-bold ${isPositive ? "text-emerald-400" : "text-rose-400"}`}>
                          {isPositive ? `+$${trd.pnl}` : `-$${Math.abs(trd.pnl)}`} ({trd.pnl_percent > 0 ? `+${trd.pnl_percent}%` : `${trd.pnl_percent}%`})
                        </td>
                        <td className="p-4">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                            trd.status === "OPEN" ? "bg-amber-500/10 text-amber-300 border border-amber-500/30 animate-pulse" : "bg-slate-800 text-slate-400"
                          }`}>
                            {trd.status}
                          </span>
                        </td>
                        <td className="p-4 text-slate-300 text-[11px] max-w-xs truncate">
                          {trd.entry_reasoning}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
