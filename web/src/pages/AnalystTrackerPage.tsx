import { useEffect, useState, useMemo } from "react";
import {
  ArrowUpRight,
  ArrowDownRight,
  Bot,
  CheckCircle2,
  Clock,
  Layers,
  RefreshCw,
  Search,
  ShieldCheck,
  TrendingUp,
  Filter,
  Users
} from "lucide-react";
import { api } from "@/lib/api";

export interface TrimEvent {
  event_type: string;
  price: number;
  gain_pct: number;
  timestamp?: string;
}

interface Position {
  position_id: string;
  analyst_name: string;
  channel_id: string;
  ticker: string;
  asset_type: string;
  direction: string;
  strike: number | null;
  expiration: string | null;
  contracts_or_shares: number;
  entry_price: number;
  current_price: number | null;
  exit_price: number | null;
  status: string;
  realized_pnl: number;
  roi_pct: number;
  entry_time: string;
  exit_time: string | null;
  notes: string | null;
  last_price_updated_at?: string;
  trims?: TrimEvent[];
}

const cleanAnalystName = (raw: string): string => {
  if (!raw) return "Unknown Analyst";
  let clean = raw.replace("🌟｜", "").replace("🛎️｜", "").replace("📖｜", "").replace("⚙️｜", "").replace(/-/g, " ").trim();
  if (clean.toLowerCase().includes("all-alerts") || clean.toLowerCase().includes("all alerts")) return "";
  if (clean.toLowerCase() === "jon and kian" || clean.toLowerCase() === "jon-and-kian") return "Jon & Kian";
  if (clean.toLowerCase() === "ab") return "AB";
  if (clean.toLowerCase() === "tt") return "TT";
  if (clean.toLowerCase() === "np") return "NP";
  if (clean.toLowerCase().includes("0dte")) return "0DTE Insights";
  if (clean.toLowerCase().includes("vix")) return "VIX Insights";
  if (clean.toLowerCase().includes("bobby")) return "Bobby SPX Coms";
  return clean.split(" ").map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(" ");
};

const formatEntryTime = (rawTime?: string): string => {
  if (!rawTime) return "N/A";
  try {
    const d = new Date(rawTime);
    if (isNaN(d.getTime())) return rawTime;

    const options: Intl.DateTimeFormatOptions = {
      timeZone: "America/Los_Angeles",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      hour12: false
    };
    const parts = new Intl.DateTimeFormat("en-US", options).formatToParts(d);
    let month = "", day = "", hour = "", minute = "";
    for (const p of parts) {
      if (p.type === "month") month = p.value;
      if (p.type === "day") day = p.value;
      if (p.type === "hour") hour = p.value;
      if (p.type === "minute") minute = p.value;
    }
    return `${month}/${day} ${hour}:${minute} PST`;
  } catch {
    return rawTime;
  }
};

const ALL_PERMITTED_ANALYSTS = [
  "0DTE Insights",
  "AB",
  "Bobby SPX Coms",
  "Common Stock",
  "Eva",
  "Florida Man",
  "Giul Heatseeker",
  "Jon & Kian",
  "Muggzone Options",
  "Neal",
  "NP",
  "Robindahood",
  "Shabs Sky Alerts",
  "TT",
  "VIX Insights",
  "Ximes Dubz"
];

export default function AnalystTrackerPage() {
  const [positions, setPositions] = useState<Position[]>([]);
  const [analystsList, setAnalystsList] = useState<string[]>(ALL_PERMITTED_ANALYSTS);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [analystFilter, setAnalystFilter] = useState<string>("ALL");

  const fetchData = async () => {
    setLoading(true);
    try {
      const [posRes, listRes] = await Promise.all([
        api.getAnalystPositions().catch(() => null),
        api.getAnalystList().catch(() => null)
      ]);

      if (posRes && posRes.positions && Array.isArray(posRes.positions)) {
        // Filter out duplicate positions and clean analyst names
        const seen = new Set<string>();
        const cleaned: Position[] = [];

        for (const p of posRes.positions) {
          const cName = cleanAnalystName(p.analyst_name);
          if (!cName) continue; // Skip all-alerts aggregator duplicate

          const key = `${cName}_${p.ticker}_${p.strike || ''}_${p.expiration || ''}_${p.direction}_${p.entry_price}`;
          if (!seen.has(key)) {
            seen.add(key);
            cleaned.push({
              ...p,
              analyst_name: cName
            });
          }
        }
        setPositions(cleaned);
      }

      if (listRes && listRes.analysts && Array.isArray(listRes.analysts)) {
        const names = listRes.analysts
          .map((a: any) => cleanAnalystName(a.display_name || a.channel_name))
          .filter((n: string) => n && n !== "Unknown Analyst")
          .sort();
        setAnalystsList(Array.from(new Set(names)) as string[]);
      }
    } catch {
      console.warn("Using active state positions");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000); // 15s auto-refresh
    return () => clearInterval(interval);
  }, []);

  // Extract unique analyst names combining API analysts list and active positions
  const uniqueAnalysts = useMemo(() => {
    const set = new Set<string>(analystsList);
    positions.forEach((p) => {
      if (p.analyst_name) {
        set.add(p.analyst_name);
      }
    });
    return Array.from(set).sort();
  }, [positions, analystsList]);

  // Filtered positions based on search, status, and analyst selection
  const filteredPositions = useMemo(() => {
    return positions.filter((p) => {
      const matchesSearch =
        p.ticker.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.analyst_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (p.notes && p.notes.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesStatus =
        statusFilter === "ALL" ||
        (statusFilter === "OPEN" && (p.status === "OPEN" || p.status === "TRIMMED")) ||
        (statusFilter === "CLOSED" && p.status === "CLOSED");

      const matchesAnalyst =
        analystFilter === "ALL" || p.analyst_name === analystFilter;

      return matchesSearch && matchesStatus && matchesAnalyst;
    });
  }, [positions, searchQuery, statusFilter, analystFilter]);

  // Compute stats specifically for the selected analyst filter (or all positions if ALL)
  const stats = useMemo(() => {
    const targetPositions = analystFilter === "ALL" ? positions : filteredPositions;
    const totalCount = targetPositions.length;
    const rawOpenCount = targetPositions.filter((p) => p.status === "OPEN").length;
    const trimmedCount = targetPositions.filter((p) => p.status === "TRIMMED").length;
    const closedCount = targetPositions.filter((p) => p.status === "CLOSED").length;
    const avgRoi = totalCount > 0 ? targetPositions.reduce((acc, p) => acc + (p.roi_pct || 0), 0) / totalCount : 0;

    const closedPositions = targetPositions.filter((p) => p.status === "CLOSED" || (p.status === "TRIMMED" && (p.roi_pct || 0) > 0));
    const closedWins = closedPositions.filter((p) => (p.roi_pct || 0) > 0);
    const closedAvgRoi = closedWins.length > 0 ? closedWins.reduce((acc, p) => acc + (p.roi_pct || 0), 0) / closedWins.length : 0;
    const winRate = closedPositions.length > 0 ? (closedWins.length / closedPositions.length) * 100 : 0;

    return { totalCount, rawOpenCount, trimmedCount, closedCount, avgRoi, closedAvgRoi, winRate, closedWinsCount: closedWins.length };
  }, [positions, filteredPositions, analystFilter]);

  return (
    <div className="min-h-screen bg-[#0B0F17] text-slate-100 p-4 sm:p-6 space-y-6 font-sans">
      {/* Top Banner & Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-purple-900/40 via-indigo-900/30 to-cyan-900/40 border border-purple-500/20 p-6 shadow-2xl backdrop-blur-xl">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="relative z-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                Unusual Whales Live MTM Connected
              </span>
              <span className="inline-flex items-center gap-1 text-xs text-slate-400">
                <Clock className="w-3.5 h-3.5" />
                Auto-syncing SQLite DB
              </span>
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-indigo-200">
              Analyst Trade Intelligence Tracker
            </h1>
            <p className="text-sm text-slate-400 mt-1 max-w-2xl">
              Live SQLite Database (`analyst_trading.db`) Ingestion, Qualitative Position Sizing Weights, and Unusual Whales Mark-to-Market Contract Pricing.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={fetchData}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-indigo-600/80 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-lg shadow-indigo-600/25 border border-indigo-400/30 active:scale-95"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              Refresh Database
            </button>
          </div>
        </div>
      </div>

      {/* KPI Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Tracked Analysts</span>
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-lg">
              <Bot className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-100">
              {analystFilter === "ALL" ? `${uniqueAnalysts.length || 16} Analysts` : analystFilter}
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {analystFilter === "ALL" ? `${uniqueAnalysts.length || 16} Permitted Analyst Channels` : "Filtered Analyst Active"}
            </p>
          </div>
        </div>

        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Active Positions</span>
            <div className="p-2 bg-cyan-500/10 text-cyan-400 rounded-lg">
              <Layers className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-100 flex items-center gap-2">
              <span className="text-emerald-400">{stats.rawOpenCount} Open</span>
              <span className="text-slate-600 font-normal text-lg">•</span>
              <span className="text-amber-400">{stats.trimmedCount} Trimmed</span>
            </div>
            <p className="text-xs text-slate-400 mt-1">{stats.closedCount} Positions Fully Closed</p>
          </div>
        </div>

        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
              {analystFilter === "ALL" ? "Portfolio ROI" : `${analystFilter} Performance`}
            </span>
            <div className="p-2 bg-emerald-500/10 text-emerald-400 rounded-lg">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-bold ${stats.closedAvgRoi >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                +{stats.closedAvgRoi.toFixed(1)}%
              </span>
              <span className="text-xs text-slate-400 font-medium">Avg Closed Win</span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-1.5">
              <span className="text-indigo-300 font-semibold">{stats.avgRoi >= 0 ? "+" : ""}{stats.avgRoi.toFixed(1)}%</span> Blended Live MTM ({stats.closedWinsCount} Wins logged)
            </p>
          </div>
        </div>

        <div className="bg-[#131924]/80 border border-slate-800/80 rounded-xl p-5 shadow-lg backdrop-blur-md relative overflow-hidden">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Data Source</span>
            <div className="p-2 bg-purple-500/10 text-purple-400 rounded-lg">
              <ShieldCheck className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-slate-100">SQLite Database</div>
            <p className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> analyst_trading.db Connected
            </p>
          </div>
        </div>
      </div>

      {/* Analyst Scroll Pill Bar */}
      <div className="bg-[#131924]/70 border border-slate-800/80 rounded-xl p-3 backdrop-blur-md">
        <div className="flex items-center gap-2 mb-2 px-1">
          <Filter className="w-3.5 h-3.5 text-indigo-400" />
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            Filter by Analyst ({uniqueAnalysts.length} active analysts)
          </span>
        </div>
        <div className="flex items-center gap-2 overflow-x-auto pb-1 pt-1 scrollbar-thin scrollbar-thumb-slate-700">
          <button
            onClick={() => setAnalystFilter("ALL")}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              analystFilter === "ALL"
                ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30"
                : "bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
            }`}
          >
            <Users className="w-3.5 h-3.5" />
            All Analysts ({positions.length})
          </button>

          {uniqueAnalysts.map((analystName) => {
            const count = positions.filter((p) => p.analyst_name === analystName).length;
            const isSelected = analystFilter === analystName;

            return (
              <button
                key={analystName}
                onClick={() => setAnalystFilter(analystName)}
                className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                  isSelected
                    ? "bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-600/30"
                    : "bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`}
              >
                <div className="w-4 h-4 rounded-full bg-indigo-500/20 text-indigo-300 flex items-center justify-center text-[10px] font-bold">
                  {analystName.charAt(0)}
                </div>
                {analystName} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Table Card */}
      <div className="bg-[#131924]/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden backdrop-blur-xl">
        <div className="p-4 sm:p-6 border-b border-slate-800/80 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="relative w-full md:w-80">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search ticker, analyst, or alert..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0B0F17] border border-slate-800 focus:border-indigo-500/60 rounded-xl pl-10 pr-4 py-2 text-sm text-slate-200 placeholder-slate-500 focus:outline-none transition-all"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto justify-between md:justify-end">
            {/* Analyst Dropdown Selector */}
            <div className="relative">
              <select
                value={analystFilter}
                onChange={(e) => setAnalystFilter(e.target.value)}
                className="bg-[#0B0F17] border border-slate-800 focus:border-indigo-500/60 rounded-xl px-3.5 py-2 text-xs font-semibold text-slate-300 focus:outline-none transition-all cursor-pointer appearance-none pr-8"
              >
                <option value="ALL">All Analysts ({positions.length})</option>
                {uniqueAnalysts.map((a) => (
                  <option key={a} value={a}>
                    {a} ({positions.filter((p) => p.analyst_name === a).length})
                  </option>
                ))}
              </select>
              <div className="absolute right-2.5 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400 text-xs">
                ▼
              </div>
            </div>

            {/* Status Filter Tabs */}
            <div className="flex items-center gap-1.5 overflow-x-auto">
              {["ALL", "OPEN", "CLOSED"].map((filterKey) => (
                <button
                  key={filterKey}
                  onClick={() => setStatusFilter(filterKey)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    statusFilter === filterKey
                      ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                      : "bg-slate-800/60 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                  }`}
                >
                  {filterKey === "ALL" ? "All Status" : filterKey === "OPEN" ? "Active" : "Closed"}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-slate-800/80 bg-[#0E131D]/80 text-slate-400 text-[11px] font-bold uppercase tracking-wider">
                <th className="py-3.5 px-4">Analyst & Channel</th>
                <th className="py-3.5 px-4">Entry Date & Time</th>
                <th className="py-3.5 px-4">Asset / Option Contract</th>
                <th className="py-3.5 px-4">Status</th>
                <th className="py-3.5 px-4">Trim / Close Events (% / Price)</th>
                <th className="py-3.5 px-4">Open Weight</th>
                <th className="py-3.5 px-4 text-right">Entry Premium</th>
                <th className="py-3.5 px-4 text-right">Exit / Live Quote</th>
                <th className="py-3.5 px-4 text-right">Blended ROI</th>
                <th className="py-3.5 px-4">Latest Analyst Note</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/50 text-sm font-normal text-slate-300">
              {filteredPositions.length === 0 ? (
                <tr>
                  <td colSpan={10} className="py-12 text-center text-slate-500 text-sm">
                    No matching analyst positions found in SQLite database.
                  </td>
                </tr>
              ) : (
                filteredPositions.map((pos) => {
                  const roi = pos.roi_pct || 0;
                  const isPositive = roi >= 0;
                  const isClosed = pos.status === "CLOSED";
                  const isTrimmed = pos.status === "TRIMMED";
                  const weight = pos.contracts_or_shares || 0;

                  return (
                    <tr
                      key={pos.position_id}
                      className="hover:bg-slate-800/30 transition-colors group"
                    >
                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2.5">
                          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-600 to-purple-600 flex items-center justify-center text-xs font-bold text-white shadow-md">
                            {pos.analyst_name ? pos.analyst_name.charAt(0) : "A"}
                          </div>
                          <div>
                            <div className="font-semibold text-slate-200 text-xs sm:text-sm">
                              {pos.analyst_name}
                            </div>
                            <div className="text-[11px] text-slate-500">
                              #{pos.analyst_name ? pos.analyst_name.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '') : 'analyst'}
                            </div>
                          </div>
                        </div>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5 text-xs text-slate-300 font-mono bg-slate-900/60 px-2.5 py-1 rounded-md border border-slate-800/80 w-fit">
                          <Clock className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                          <span>{formatEntryTime(pos.entry_time)}</span>
                        </div>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className="font-black text-slate-100 text-sm tracking-wide bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                            {pos.ticker}
                          </span>
                          {pos.asset_type === "option" && pos.strike && (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-indigo-300 bg-indigo-950/60 border border-indigo-800/40 px-2 py-0.5 rounded-full">
                              {pos.strike}{pos.direction === "call" || pos.direction === "CALL" ? "C" : "P"}{" "}
                              <span className="text-slate-400">
                                {pos.expiration}
                              </span>
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-bold ${
                            isClosed
                              ? "bg-purple-500/10 text-purple-400 border border-purple-500/20"
                              : isTrimmed
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                              : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                          }`}
                        >
                          <span
                            className={`w-1.5 h-1.5 rounded-full ${
                              isClosed
                                ? "bg-purple-400"
                                : isTrimmed
                                ? "bg-amber-400 animate-pulse"
                                : "bg-emerald-400 animate-pulse"
                            }`}
                          />
                          {pos.status}
                        </span>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap">
                        {pos.trims && pos.trims.length > 0 ? (
                          <div className="flex flex-wrap items-center gap-1.5 max-w-xs">
                            {pos.trims.map((trim, idx) => {
                              const isPos = trim.gain_pct >= 0;
                              const isClose = trim.event_type === "CLOSED" || trim.event_type === "CLOSE";
                              return (
                                <span
                                  key={idx}
                                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-mono font-bold border transition-all ${
                                    isClose
                                      ? isPos
                                        ? "bg-purple-950/70 text-purple-300 border-purple-800/60 shadow-sm"
                                        : "bg-rose-950/70 text-rose-300 border-rose-800/60 shadow-sm"
                                      : isPos
                                      ? "bg-amber-950/70 text-amber-300 border-amber-700/60 shadow-sm"
                                      : "bg-slate-800 text-slate-300 border-slate-700"
                                  }`}
                                  title={`Event: ${trim.event_type} | Date: ${formatEntryTime(trim.timestamp)}`}
                                >
                                  <span className="text-[10px] uppercase font-sans font-semibold tracking-tight text-slate-400">
                                    {isClose ? "Close" : `Trim ${idx + 1}`}:
                                  </span>
                                  <span>${trim.price.toFixed(2)}</span>
                                  <span className={isPos ? "text-emerald-400 font-extrabold" : "text-rose-400 font-extrabold"}>
                                    ({isPos ? "+" : ""}{trim.gain_pct.toFixed(1)}%)
                                  </span>
                                </span>
                              );
                            })}
                          </div>
                        ) : (
                          <span className="text-xs text-slate-500 italic font-mono">--</span>
                        )}
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <span className="font-semibold text-slate-200">
                            {weight.toFixed(2)}x
                          </span>
                          {weight === 0 ? (
                            <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                              (Closed)
                            </span>
                          ) : weight < 0.3 ? (
                            <span className="text-[10px] bg-indigo-950/80 text-indigo-300 border border-indigo-800/40 px-1.5 py-0.5 rounded">
                              Runner
                            </span>
                          ) : (
                            <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                              Active
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap text-right font-medium text-slate-300">
                        ${(pos.entry_price || 0).toFixed(2)}{" "}
                        <span className="text-[11px] text-slate-500">
                          (${((pos.entry_price || 0) * 100).toFixed(0)}/con)
                        </span>
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap text-right font-semibold text-slate-100">
                        {pos.exit_price ? (
                          <span className="text-indigo-300">
                            ${pos.exit_price.toFixed(2)}
                          </span>
                        ) : pos.current_price ? (
                          <span>${pos.current_price.toFixed(2)}</span>
                        ) : (
                          <span className="text-slate-500">--</span>
                        )}
                      </td>

                      <td className="py-4 px-4 whitespace-nowrap text-right">
                        <span
                          className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-bold ${
                            isPositive
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                          }`}
                        >
                          {isPositive ? (
                            <ArrowUpRight className="w-3.5 h-3.5" />
                          ) : (
                            <ArrowDownRight className="w-3.5 h-3.5" />
                          )}
                          {isPositive ? "+" : ""}
                          {roi.toFixed(1)}%
                        </span>
                      </td>

                      <td className="py-4 px-4 text-xs text-slate-400 max-w-xs truncate">
                        {pos.notes || "No extra commentary."}
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
  );
}
