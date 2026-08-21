import { useState, useRef, useEffect, useMemo, type MouseEvent } from "react";
import {
  Play,
  CheckCircle2,
  Zap,
  ShieldCheck,
  Sliders,
  RefreshCw,
  Clock,
  Layers,
  ArrowRight,
  Database,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Move
} from "lucide-react";

interface WorkflowNode {
  id: string;
  name: string;
  category: "ingestion" | "analytics" | "gate" | "strategy" | "execution" | "dispatch";
  badge: string;
  status: "success" | "active" | "idle" | "gated";
  x: number;
  y: number;
  summary: string;
  inputs: Record<string, any>;
  outputs: Record<string, any>;
  lastExecution: string;
  convictionScore?: number;
}

interface Connection {
  from: string;
  to: string;
}

interface PipelineDef {
  id: string;
  title: string;
  description: string;
  nodes: WorkflowNode[];
  connections: Connection[];
}

const PIPELINES: Record<string, PipelineDef> = {
  full: {
    id: "full",
    title: "Full Autonomous Trading Pipeline",
    description: "End-to-End Logic: UW Flow → Skylit AI → Market Sentiment → Sub-Portfolios → Alpaca Paper → Dispatcher",
    connections: [
      { from: "uw_flow", to: "skylit_nodes" },
      { from: "uw_flow", to: "sentiment_gate" },
      { from: "skylit_nodes", to: "strategy_router" },
      { from: "sentiment_gate", to: "strategy_router" },
      { from: "strategy_router", to: "alpaca_execution" },
      { from: "strategy_router", to: "graphify_sync" },
      { from: "alpaca_execution", to: "multi_dispatcher" },
      { from: "graphify_sync", to: "multi_dispatcher" }
    ],
    nodes: [
      {
        id: "uw_flow",
        name: "Unusual Whales Flow Scanner",
        category: "ingestion",
        badge: "🐋 INGESTION",
        status: "success",
        x: 80,
        y: 180,
        summary: "Scans top 10 notable institutional options sweeps & dark pool block trades in real-time.",
        inputs: {
          source: "Unusual Whales Native MCP Server",
          endpoint: "mcp__unusual_whales__get_market_state",
          scan_interval: "Real-time / On-Demand"
        },
        outputs: {
          top_flow_tickers: ["NVDA", "TSLA", "SPY", "AMD", "MSFT", "SMCI", "AAPL", "AMZN", "QQQ", "META"],
          sentiment_breakdown: { bullish_sweeps: "68%", bearish_hedges: "32%" },
          total_premium_scanned: "$24,500,000"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "skylit_nodes",
        name: "Skylit Volatility & Gamma Engine",
        category: "analytics",
        badge: "⚡ ANALYTICS",
        status: "success",
        x: 400,
        y: 100,
        summary: "Computes 0DTE GEX dealer gamma pin levels and 1-Week VEX volatility expansion nodes.",
        inputs: {
          tickers: ["SPY", "TSLA", "NVDA"],
          data_provider: "Skylit AI Heatmaps"
        },
        outputs: {
          gex_pin_level: "SPY @ 550.00 (Dealer Gamma Pin)",
          vex_node_target: "TSLA @ 245.00 (Volatility Expansion Target: 255.00)",
          intraday_range: "548.50 - 552.00"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "sentiment_gate",
        name: "Market Sentiment & Risk Gate",
        category: "gate",
        badge: "🏛️ RISK GATE",
        status: "success",
        x: 400,
        y: 280,
        summary: "Evaluates multi-dimensional market regime, volatility stability, and macro event risk.",
        inputs: {
          script: "market_sentiment/scripts/eval_sentiment.py",
          vix_level: 14.2,
          macro_calendar_risk: "NO_EVENT_90MIN"
        },
        outputs: {
          primary_regime: "RISK_ON_TREND",
          tradeability_score: 85,
          directional_bias: "+58 Bullish",
          allow_new_risk: true
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "strategy_router",
        name: "Sub-Portfolio Strategy Router",
        category: "strategy",
        badge: "🛡️ STRATEGY",
        status: "active",
        x: 720,
        y: 180,
        summary: "Assigns signals to sub-portfolios ($1,000 cap) with $150 GEX 0DTE / $250 VEX 1-Wk sizing.",
        inputs: {
          sub_portfolios: ["⚡ GEX 0DTE Intraday Scalp", "🛡️ VEX 1-Week Swing & UW Overlap"],
          starting_capital: "$1,000.00 per portfolio",
          trigger_threshold: "Conviction Score >= 80/100"
        },
        outputs: {
          gex_allocated_capital: "$150.00 (15% sizing)",
          vex_allocated_capital: "$250.00 (25% sizing)",
          gex_conviction: "98/100 🟢 High Conviction",
          vex_conviction: "88/100 🟢 High Conviction"
        },
        convictionScore: 98,
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "alpaca_execution",
        name: "Alpaca Paper API Execution",
        category: "execution",
        badge: "🚀 EXECUTION",
        status: "success",
        x: 1040,
        y: 100,
        summary: "Submits authenticated paper orders to Alpaca Trading API & tracks open positions.",
        inputs: {
          account_id: "75b49a31-e5f7-4b64-99c8-4cc5b2fc6588",
          trading_mode: "Paper Trading API (ALPACA_PAPER=true)",
          buying_power: "$398,939.46"
        },
        outputs: {
          order_id_1: "30615732 (SPY 0DTE Call/Put Pin)",
          order_id_2: "9c8087ba (TSLA 1-Wk Swing Calls)",
          execution_status: "VERIFIED & FILLED"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "graphify_sync",
        name: "Graphify Sympathy & Neural Graph",
        category: "dispatch",
        badge: "🕸️ GRAPHIFY",
        status: "success",
        x: 1040,
        y: 280,
        summary: "Dynamically updates 2D Canvas Physics Neural Web with active trade journal entries & sympathy targets.",
        inputs: {
          graph_data_path: "web/public/graph_data.json",
          physics_engine: "2D Canvas Physics Simulation"
        },
        outputs: {
          primary_target: "NVDA -> Sympathy: SMCI, AMD, AVGO",
          secondary_target: "TSLA -> Sympathy: RIVN, ALB",
          graph_url: "/graphify"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "multi_dispatcher",
        name: "Multi-Channel Alert Dispatcher",
        category: "dispatch",
        badge: "📬 DISPATCHER",
        status: "success",
        x: 1320,
        y: 180,
        summary: "Dispatches Discord Market Intelligence Briefings, iMessage trade alerts, and Telegram commands.",
        inputs: {
          discord_channel: "1511973061841391616",
          imessage_daemon: "Photon Spectrum Daemon",
          telegram_bot: "@Skibidihelperbot"
        },
        outputs: {
          discord_status: "DELIVERED (Pure Intelligence Stream)",
          imessage_status: "ACTIVE (Command & Trade Response)",
          telegram_status: "ACTIVE (@Skibidihelperbot)"
        },
        lastExecution: "Today at 06:30 PST"
      }
    ]
  },

  discord: {
    id: "discord",
    title: "Discord Market Intelligence Stream",
    description: "Token-Free Stream: Cron Scheduler → UW Sector Tide → OpenBB Sentiment → Markdown Formatter → Discord API",
    connections: [
      { from: "discord_cron", to: "uw_macro" },
      { from: "uw_macro", to: "openbb_regime" },
      { from: "openbb_regime", to: "discord_formatter" },
      { from: "discord_formatter", to: "discord_bot" }
    ],
    nodes: [
      {
        id: "discord_cron",
        name: "Discord Morning Cron Trigger",
        category: "ingestion",
        badge: "⏰ CRON TRIGGER",
        status: "success",
        x: 100,
        y: 180,
        summary: "Automated trigger firing daily at 06:30 AM PST before US Market Open.",
        inputs: {
          schedule: "0 6 * * 1-5 (Mon-Fri at 06:30 AM PST)",
          script_target: "skills/financial/autonomous-trader/scripts/discord_briefing.py",
          execution_mode: "Token-Free Native Python Dispatch"
        },
        outputs: {
          trigger_time: "2026-07-28 06:30:00 PST",
          status: "SUCCESSFUL_TRIGGER"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "uw_macro",
        name: "UW Sector Tide & Dark Pool Aggregator",
        category: "analytics",
        badge: "🐋 UW MACRO",
        status: "success",
        x: 420,
        y: 180,
        summary: "Fetches sector ETF flows (XLK, XLE, XLF) and institutional net gamma exposure.",
        inputs: {
          endpoint: "mcp__unusual_whales__get_sector_etfs",
          parameters: "{ range: '1D', include_darkpool: true }"
        },
        outputs: {
          top_gainer_sector: "XLK (+1.42% Net Options Flow)",
          dark_pool_block_vol: "$4.2B SPY Block Orders",
          sector_tide_score: "+64 Bullish"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "openbb_regime",
        name: "OpenBB Macro & Breadth Engine",
        category: "analytics",
        badge: "📊 OPENBB DATA",
        status: "success",
        x: 740,
        y: 180,
        summary: "Calculates market breadth, advance/decline ratios, and yield curve metrics.",
        inputs: {
          provider: "OpenBB Python SDK v4.4",
          metrics: ["equity_breadth", "vix_term_structure", "treasury_yields"]
        },
        outputs: {
          market_breadth: "72% Stocks Above 50-SMA",
          vix_contango: "+8.4% (Normal Volatility Curve)",
          regime: "STABLE_GROWTH"
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "discord_formatter",
        name: "Rich Embed Markdown Builder",
        category: "strategy",
        badge: "📝 FORMATTER",
        status: "success",
        x: 1060,
        y: 180,
        summary: "Formats raw analytics into beautifully styled Discord Markdown embeds with headers & emojis.",
        inputs: {
          template: "Market Intelligence Morning Briefing v2",
          embed_color: "#10b981 (Emerald)"
        },
        outputs: {
          formatted_title: "☀️ MORNING MARKET INTELLIGENCE BRIEFING",
          payload_size_bytes: 1840,
          sections: 4
        },
        lastExecution: "Today at 06:30 PST"
      },
      {
        id: "discord_bot",
        name: "Discord Channel Gateway Dispatch",
        category: "dispatch",
        badge: "💬 DISCORD BOT",
        status: "success",
        x: 1380,
        y: 180,
        summary: "Posts formatted intelligence briefing directly to Discord Channel ID 1511973061841391616.",
        inputs: {
          channel_id: "1511973061841391616",
          bot_token: "DISCORD_BOT_TOKEN",
          permission_scope: "SEND_MESSAGES, EMBED_LINKS"
        },
        outputs: {
          delivery_status: "DELIVERED_200_OK",
          message_id: "1391298402941"
        },
        lastExecution: "Today at 06:30 PST"
      }
    ]
  },

  kian: {
    id: "kian",
    title: "Kian Technical Analysis Scan",
    description: "Daily Technical Engine: Cron Trigger → Alpaca Bars → Moving Average & RSI Reversal → Conviction Filter → Direct Alert",
    connections: [
      { from: "kian_cron", to: "price_action" },
      { from: "price_action", to: "kian_ta" },
      { from: "kian_ta", to: "conviction_filter" },
      { from: "conviction_filter", to: "alert_dispatch" }
    ],
    nodes: [
      {
        id: "kian_cron",
        name: "Kian Technical Scan Trigger",
        category: "ingestion",
        badge: "⏰ SCAN TRIGGER",
        status: "success",
        x: 100,
        y: 180,
        summary: "Automated technical scan running daily at 06:35 AM PST.",
        inputs: {
          schedule: "5 6 * * 1-5 (Mon-Fri at 06:35 AM PST)",
          script_target: "skills/financial/autonomous-trader/scripts/kian_analysis.py"
        },
        outputs: {
          trigger_time: "2026-07-28 06:35:00 PST",
          status: "SUCCESSFUL_TRIGGER"
        },
        lastExecution: "Today at 06:35 PST"
      },
      {
        id: "price_action",
        name: "Alpaca Market Bar Data Aggregator",
        category: "analytics",
        badge: "📈 PRICE DATA",
        status: "success",
        x: 420,
        y: 180,
        summary: "Fetches historical 15-min and daily price bars for target tickers (SPY, QQQ, TSLA, NVDA).",
        inputs: {
          timeframe: "15Min & 1Day Bars",
          lookback_period: "60 Days"
        },
        outputs: {
          bars_fetched: 1440,
          current_spy_close: "$549.80",
          current_tsla_close: "$244.50"
        },
        lastExecution: "Today at 06:35 PST"
      },
      {
        id: "kian_ta",
        name: "Kian MA & RSI Reversal Classifier",
        category: "analytics",
        badge: "🧠 TA CLASSIFIER",
        status: "success",
        x: 740,
        y: 180,
        summary: "Applies 9/21 EMA crossover, 14-RSI oversold/overbought detection, and VWAP bounce algorithms.",
        inputs: {
          ema_short: 9,
          ema_long: 21,
          rsi_period: 14
        },
        outputs: {
          spy_setup: "Bullish 9/21 EMA Cross above VWAP",
          tsla_setup: "RSI Oversold (28.4) with Volume Spike",
          raw_signals_found: 2
        },
        lastExecution: "Today at 06:35 PST"
      },
      {
        id: "conviction_filter",
        name: "High Volume & Support Level Gate",
        category: "gate",
        badge: "🛡️ CONVICTION GATE",
        status: "success",
        x: 1060,
        y: 180,
        summary: "Gates technical signals on key support/resistance levels and minimum 1.5x relative volume.",
        inputs: {
          min_rvol: 1.5,
          conviction_gate: "Score >= 80/100"
        },
        outputs: {
          spy_conviction: "92/100 🟢 PASSED",
          tsla_conviction: "84/100 🟢 PASSED",
          approved_signals: 2
        },
        convictionScore: 92,
        lastExecution: "Today at 06:35 PST"
      },
      {
        id: "alert_dispatch",
        name: "Telegram & iMessage Direct Alert",
        category: "dispatch",
        badge: "📱 ALERT DISPATCH",
        status: "success",
        x: 1380,
        y: 180,
        summary: "Dispatches validated Kian Technical setups directly to Telegram (@Skibidihelperbot) and iMessage.",
        inputs: {
          recipients: ["Telegram: @Skibidihelperbot", "iMessage: Amar Direct"],
          include_chart_link: true
        },
        outputs: {
          telegram_delivery: "SUCCESS",
          imessage_delivery: "SUCCESS"
        },
        lastExecution: "Today at 06:35 PST"
      }
    ]
  }
};

export function WorkflowsPage() {
  const [activePipelineKey, setActivePipelineKey] = useState<string>("full");
  const activePipeline = PIPELINES[activePipelineKey] || PIPELINES.full;

  const [selectedNode, setSelectedNode] = useState<WorkflowNode>(activePipeline.nodes[0]);
  const [isRunningSim, setIsRunningSim] = useState(false);
  const parseDTE = (expiry: string, dateStr?: string): number => {
    if (!expiry) return 0;
    const expUpper = expiry.toUpperCase().trim();
    if (expUpper.includes("0DTE")) return 0;
    if (expUpper.includes("1-WK") || expUpper.includes("1WK")) return 7;
    
    try {
      const expDate = new Date(expiry);
      if (!isNaN(expDate.getTime())) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        const diffMs = expDate.getTime() - today.getTime();
        return Math.ceil(diffMs / (1000 * 60 * 60 * 24));
      }
    } catch (e) {}

    if (dateStr) {
      try {
        const recDate = new Date(dateStr);
        if (!isNaN(recDate.getTime())) {
          const today = new Date();
          today.setHours(0, 0, 0, 0);
          const diffMs = recDate.getTime() - today.getTime();
          const dte = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
          if (dte < 0) return dte;
        }
      } catch (e) {}
    }
    return 0;
  };

  const [watchlistTab, setWatchlistTab] = useState<"active" | "verified" | "historical">("active");
  const [watchlistSearch, setWatchlistSearch] = useState<string>("");
  const [watchlistSort, setWatchlistSort] = useState<"dte_asc" | "premium" | "ask_ratio" | "date">("dte_asc");
  const [hideExpired, setHideExpired] = useState<boolean>(true);
  const [watchlistPage, setWatchlistPage] = useState<number>(1);
  const pageSize = 15;

  const [liveData, setLiveData] = useState<{
    strategies: any[];
    positions: any[];
    actions: any[];
    active_watchlist: any[];
    verified_oi_watchlist: any[];
    historical_archive: any[];
    flow_counts: { active: number; verified: number; historical: number; total: number };
  }>({
    strategies: [],
    positions: [],
    actions: [],
    active_watchlist: [],
    verified_oi_watchlist: [],
    historical_archive: [],
    flow_counts: { active: 0, verified: 0, historical: 0, total: 0 }
  });
  const [isSavingStrategy, setIsSavingStrategy] = useState(false);

  const rawList = watchlistTab === "active"
    ? liveData.active_watchlist
    : watchlistTab === "verified"
    ? liveData.verified_oi_watchlist
    : liveData.historical_archive;

  const filteredWatchlist = useMemo(() => {
    let list = [...(rawList || [])];

    if (hideExpired) {
      list = list.filter((i: any) => {
        const dte = parseDTE(i.expiry, i.date);
        return dte >= 0 && i.status !== "STORED_HISTORICAL";
      });
    }

    if (watchlistSearch.trim()) {
      const q = watchlistSearch.toLowerCase();
      list = list.filter((i: any) =>
        (i.ticker || "").toLowerCase().includes(q) ||
        String(i.strike || "").includes(q) ||
        (i.option_type || "").toLowerCase().includes(q)
      );
    }

    list.sort((a: any, b: any) => {
      if (watchlistSort === "dte_asc") {
        const dteA = parseDTE(a.expiry, a.date);
        const dteB = parseDTE(b.expiry, b.date);
        return dteA - dteB;
      }
      if (watchlistSort === "premium") return (b.total_premium || 0) - (a.total_premium || 0);
      if (watchlistSort === "ask_ratio") return (b.ask_ratio || 0) - (a.ask_ratio || 0);
      return (b.date || "").localeCompare(a.date || "");
    });
    return list;
  }, [rawList, watchlistSearch, watchlistSort, hideExpired]);

  const totalPages = Math.ceil(filteredWatchlist.length / pageSize) || 1;
  const paginatedWatchlist = useMemo(() => {
    const start = (watchlistPage - 1) * pageSize;
    return filteredWatchlist.slice(start, start + pageSize);
  }, [filteredWatchlist, watchlistPage]);

  // Poll /api/workflows/state dynamically
  const fetchWorkflowsState = async () => {
    try {
      const res = await fetch("/api/workflows/state");
      if (res.ok) {
        const data = await res.json();
        if (data.ok) {
          setLiveData({
            strategies: data.strategies || [],
            positions: data.positions || [],
            actions: data.actions || [],
            active_watchlist: data.active_watchlist || [],
            verified_oi_watchlist: data.verified_oi_watchlist || [],
            historical_archive: data.historical_archive || [],
            flow_counts: data.flow_counts || { active: 0, verified: 0, historical: 0, total: 0 }
          });
        }
      }
    } catch (e) {
      console.warn("Workflows live state fetch note:", e);
    }
  };

  useEffect(() => {
    fetchWorkflowsState();
    const interval = setInterval(fetchWorkflowsState, 10000);
    return () => clearInterval(interval);
  }, []);

  // 2-Way Parameter Update Handler
  const handleSaveStrategyTune = async (strategyId: string, updates: any) => {
    setIsSavingStrategy(true);
    try {
      const res = await fetch("/api/workflows/update-strategy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ strategy_id: strategyId, updates })
      });
      if (res.ok) {
        await fetchWorkflowsState();
      }
    } catch (e) {
      console.error("Failed to update strategy 2-way:", e);
    } finally {
      setIsSavingStrategy(false);
    }
  };

  // Dynamic Node Payload Synthesis from live backend state
  const dynamicNodes = useMemo(() => {
    return activePipeline.nodes.map((node) => {
      if (node.id === "strategy_router" && liveData.strategies && liveData.strategies.length > 0) {
        const stratInputs: Record<string, any> = {};
        const stratOutputs: Record<string, any> = {};
        liveData.strategies.forEach((s: any) => {
          const sId = s.strategy_id || s.id;
          stratInputs[sId] = `${s.name || sId} (v${s.version || "1.0.0"})`;
          stratOutputs[`${sId}_gate`] = `>= ${s.conviction_threshold}/100 (Capital: $${s.allocated_capital})`;
        });
        return {
          ...node,
          summary: `Dynamically routing signals across ${liveData.strategies.length} active registered strategies.`,
          inputs: stratInputs,
          outputs: stratOutputs
        };
      }
      if (node.id === "alpaca_execution" && liveData.positions && liveData.positions.length > 0) {
        const posOutputs: Record<string, any> = {};
        liveData.positions.forEach((p: any, idx: number) => {
          posOutputs[`position_${idx + 1}`] = `${p.ticker} (${p.mode}): Conviction ${p.conviction_score}/100 | ${p.target_price}`;
        });
        return {
          ...node,
          summary: `Submits paper orders & tracks ${liveData.positions.length} active positions in SQLite Store.`,
          outputs: posOutputs
        };
      }
      return node;
    });
  }, [activePipeline, liveData]);

  // Pan & Zoom State
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [isPanning, setIsPanning] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Dynamic Node Positions per Pipeline
  const [nodePositions, setNodePositions] = useState<Record<string, { x: number; y: number }>>({});

  // When active pipeline changes, reset positions & selected node
  useEffect(() => {
    const initialPos: Record<string, { x: number; y: number }> = {};
    activePipeline.nodes.forEach((n) => {
      initialPos[n.id] = { x: n.x, y: n.y };
    });
    setNodePositions(initialPos);
    setSelectedNode(activePipeline.nodes[0]);
    setPan({ x: 0, y: 0 });
    setZoom(1);
  }, [activePipelineKey]);

  // Node Dragging State
  const [draggingNodeId, setDraggingNodeId] = useState<string | null>(null);
  const [nodeOffset, setNodeOffset] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);

  const runSimulation = () => {
    setIsRunningSim(true);
    setTimeout(() => {
      setIsRunningSim(false);
    }, 2500);
  };

  // Canvas Pan Handlers
  const handleMouseDown = (e: MouseEvent<HTMLDivElement>) => {
    if (draggingNodeId) return;
    setIsPanning(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: MouseEvent<HTMLDivElement>) => {
    if (draggingNodeId) {
      setNodePositions((prev) => ({
        ...prev,
        [draggingNodeId]: {
          x: (e.clientX - pan.x - nodeOffset.x) / zoom,
          y: (e.clientY - pan.y - nodeOffset.y) / zoom,
        },
      }));
      return;
    }

    if (isPanning) {
      setPan({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsPanning(false);
    setDraggingNodeId(null);
  };

  // Node Drag Handlers
  const handleNodeMouseDown = (e: MouseEvent<HTMLDivElement>, nodeId: string) => {
    e.stopPropagation();
    const found = activePipeline.nodes.find((n) => n.id === nodeId);
    if (found) setSelectedNode(found);
    setDraggingNodeId(nodeId);
    const pos = nodePositions[nodeId] || { x: 0, y: 0 };
    setNodeOffset({
      x: e.clientX - pan.x - pos.x * zoom,
      y: e.clientY - pan.y - pos.y * zoom,
    });
  };

  const resetView = () => {
    setPan({ x: 0, y: 0 });
    setZoom(1);
    const initial: Record<string, { x: number; y: number }> = {};
    activePipeline.nodes.forEach((n) => { initial[n.id] = { x: n.x, y: n.y }; });
    setNodePositions(initial);
  };

  const getCategoryColor = (cat: WorkflowNode["category"]) => {
    switch (cat) {
      case "ingestion": return "from-cyan-500/20 to-blue-500/20 border-cyan-500/50 text-cyan-400";
      case "analytics": return "from-amber-500/20 to-yellow-500/20 border-amber-500/50 text-amber-400";
      case "gate": return "from-purple-500/20 to-indigo-500/20 border-purple-500/50 text-purple-400";
      case "strategy": return "from-emerald-500/20 to-teal-500/20 border-emerald-500/50 text-emerald-400";
      case "execution": return "from-blue-500/20 to-indigo-500/20 border-blue-500/50 text-blue-400";
      case "dispatch": return "from-fuchsia-500/20 to-pink-500/20 border-fuchsia-500/50 text-fuchsia-400";
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#0b0e14] text-slate-100 overflow-hidden select-none font-sans">
      {/* Main Workflow Visual Canvas */}
      <div className="flex-1 flex flex-col h-full border-r border-slate-800/80 relative">
        {/* Top Workflow Toolbar */}
        <div className="h-16 border-b border-slate-800/80 bg-[#111622]/90 backdrop-blur px-6 flex items-center justify-between z-20">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-semibold text-slate-100">{activePipeline.title}</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono flex items-center gap-1">
                  <Move className="h-3 w-3" /> ACTIVE WORKFLOW
                </span>
              </div>
              <p className="text-xs text-slate-400">{activePipeline.description}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Canvas Zoom & Reset Controls */}
            <div className="flex items-center gap-1 bg-[#1a202c] p-1 rounded-lg border border-slate-700/80 text-slate-300">
              <button
                onClick={() => setZoom((z) => Math.min(1.8, z + 0.15))}
                className="p-1 hover:bg-slate-700/50 rounded"
                title="Zoom In"
              >
                <ZoomIn className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
                className="p-1 hover:bg-slate-700/50 rounded"
                title="Zoom Out"
              >
                <ZoomOut className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={resetView}
                className="p-1 hover:bg-slate-700/50 rounded"
                title="Reset View & Positions"
              >
                <RotateCcw className="h-3.5 w-3.5 text-amber-400" />
              </button>
              <span className="text-[10px] font-mono px-2 text-slate-400">{Math.round(zoom * 100)}%</span>
            </div>

            {/* Workflow Pipeline Selector */}
            <select
              value={activePipelineKey}
              onChange={(e) => setActivePipelineKey(e.target.value)}
              className="bg-[#1a202c] border border-emerald-500/50 text-xs font-semibold text-emerald-300 rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-400"
            >
              <option value="full">🟢 Full Autonomous Trading Pipeline</option>
              <option value="discord">🟣 Discord Market Intelligence Stream</option>
              <option value="kian">🟡 Kian Technical Analysis Scan</option>
            </select>

            <button
              onClick={runSimulation}
              disabled={isRunningSim}
              className={`flex items-center gap-2 px-4 py-1.5 rounded-lg font-medium text-xs transition-all ${
                isRunningSim
                  ? "bg-amber-500/20 text-amber-400 border border-amber-500/40 cursor-wait"
                  : "bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40"
              }`}
            >
              {isRunningSim ? (
                <>
                  <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                  Simulating Flow...
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 fill-current" />
                  Test Flow
                </>
              )}
            </button>
          </div>
        </div>

        {/* N8N Draggable & Pannable Interactive Grid Canvas */}
        <div
          ref={containerRef}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          className={`flex-1 relative overflow-hidden bg-[#0b0e14] ${
            isPanning ? "cursor-grabbing" : "cursor-grab"
          }`}
          style={{
            backgroundImage: "radial-gradient(#1e293b 1px, transparent 1px)",
            backgroundSize: `${24 * zoom}px ${24 * zoom}px`,
            backgroundPosition: `${pan.x}px ${pan.y}px`,
          }}
        >
          <div
            className="absolute inset-0 origin-top-left transition-transform duration-75"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
            }}
          >
            {/* Dynamic SVG Connection Lines */}
            <svg className="absolute inset-0 w-[2400px] h-[1200px] pointer-events-none z-0">
              <defs>
                <linearGradient id="flow-grad" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#10b981" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.9" />
                </linearGradient>
              </defs>
              {activePipeline.connections.map((conn, idx) => {
                const fromPos = nodePositions[conn.from];
                const toPos = nodePositions[conn.to];
                if (!fromPos || !toPos) return null;

                const startX = fromPos.x + 230;
                const startY = fromPos.y + 50;
                const endX = toPos.x;
                const endY = toPos.y + 50;
                const controlX1 = startX + (endX - startX) / 2;

                return (
                  <g key={idx}>
                    <path
                      d={`M ${startX} ${startY} C ${controlX1} ${startY}, ${controlX1} ${endY}, ${endX} ${endY}`}
                      fill="none"
                      stroke="#1e293b"
                      strokeWidth="3.5"
                    />
                    <path
                      d={`M ${startX} ${startY} C ${controlX1} ${startY}, ${controlX1} ${endY}, ${endX} ${endY}`}
                      fill="none"
                      stroke="url(#flow-grad)"
                      strokeWidth="2.5"
                      strokeDasharray={isRunningSim ? "8 8" : "none"}
                      className={isRunningSim ? "animate-dash" : ""}
                      opacity="0.9"
                    />
                  </g>
                );
              })}
            </svg>

            {/* Draggable Canvas Interactive Nodes */}
            <div className="relative w-[2400px] h-[1200px] p-8 z-10">
              {dynamicNodes.map((node) => {
                const isSelected = selectedNode.id === node.id;
                const colorClasses = getCategoryColor(node.category);
                const pos = nodePositions[node.id] || { x: node.x, y: node.y };

                return (
                  <div
                    key={node.id}
                    onMouseDown={(e) => handleNodeMouseDown(e, node.id)}
                    style={{ left: `${pos.x}px`, top: `${pos.y}px` }}
                    className={`absolute w-[230px] rounded-xl border bg-gradient-to-b ${colorClasses} p-4 cursor-move transition-all duration-75 shadow-2xl ${
                      isSelected
                        ? "ring-2 ring-emerald-400 scale-[1.03] z-30"
                        : "hover:scale-[1.01] hover:border-slate-400 z-20"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[10px] font-mono font-bold tracking-wider opacity-90">
                        {node.badge}
                      </span>
                      {node.status === "success" && (
                        <span className="flex items-center gap-1 text-[10px] text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/30 font-mono">
                          <CheckCircle2 className="h-3 w-3" /> OK
                        </span>
                      )}
                      {node.status === "active" && (
                        <span className="flex items-center gap-1 text-[10px] text-amber-300 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30 font-mono animate-pulse">
                          <Zap className="h-3 w-3" /> TRIGGER
                        </span>
                      )}
                    </div>

                    <h3 className="text-xs font-semibold text-slate-100 mb-1 leading-snug">
                      {node.name}
                    </h3>

                    <p className="text-[11px] text-slate-400 line-clamp-2 mb-3">
                      {node.summary}
                    </p>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-2 border-t border-slate-800/80 font-mono">
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3 text-slate-500" />
                        {node.lastExecution.split("at ")[1] || "06:30 PST"}
                      </span>
                      {node.convictionScore && (
                        <span className="text-emerald-400 font-bold">
                          {node.convictionScore}/100
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Right Drawer: Node Logic & Execution Inspector */}
      <div className="w-[420px] bg-[#111622] border-l border-slate-800/80 flex flex-col h-full z-30">
        {/* Drawer Header */}
        <div className="p-5 border-b border-slate-800/80 flex items-center justify-between bg-[#151b28]">
          <div className="flex items-center gap-2">
            <Sliders className="h-4 w-4 text-emerald-400" />
            <h2 className="text-sm font-semibold text-slate-100">Node Logic Inspector</h2>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
            ID: {selectedNode.id}
          </span>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-5 space-y-6">
          {/* Node Summary Header */}
          <div>
            <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider">
              {selectedNode.badge}
            </span>
            <h3 className="text-base font-bold text-slate-100 mt-0.5">{selectedNode.name}</h3>
            <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">{selectedNode.summary}</p>
          </div>

          {/* Execution Metrics */}
          <div className="grid grid-cols-2 gap-3 p-3.5 bg-[#0d1117] rounded-xl border border-slate-800/80">
            <div>
              <span className="text-[10px] text-slate-500 font-mono uppercase">Last Run</span>
              <p className="text-xs font-semibold text-slate-200 mt-0.5">{selectedNode.lastExecution}</p>
            </div>
            <div>
              <span className="text-[10px] text-slate-500 font-mono uppercase">Execution Status</span>
              <p className="text-xs font-semibold text-emerald-400 mt-0.5 flex items-center gap-1">
                <CheckCircle2 className="h-3.5 w-3.5" /> Verified
              </p>
            </div>
          </div>

          {/* Input Schema Payload */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <Database className="h-3.5 w-3.5 text-cyan-400" /> Node Inputs (Inbound)
              </span>
              <span className="text-[10px] font-mono text-slate-500">JSON</span>
            </div>
            <pre className="p-3 bg-[#080b10] rounded-xl border border-slate-800/80 text-[11px] font-mono text-cyan-300 overflow-x-auto">
              {JSON.stringify(selectedNode.inputs, null, 2)}
            </pre>
          </div>

          {/* Output Payload & Logic */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                <ArrowRight className="h-3.5 w-3.5 text-emerald-400" /> Node Outputs (Outbound Signals)
              </span>
              <span className="text-[10px] font-mono text-slate-500">JSON</span>
            </div>
            <pre className="p-3 bg-[#080b10] rounded-xl border border-slate-800/80 text-[11px] font-mono text-emerald-300 overflow-x-auto">
              {JSON.stringify(selectedNode.outputs, null, 2)}
            </pre>
          </div>

          {/* 2-Way Live Strategy Parameter Tuning Panel */}
          {liveData.strategies && liveData.strategies.length > 0 && (
            <div className="p-4 bg-[#141b29] rounded-xl border border-slate-700/80 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-400 flex items-center gap-1.5">
                  <Sliders className="h-4 w-4" /> 2-Way Live Parameter Tuning
                </span>
                <span className="text-[10px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                  REALTIME SYNC
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Edits saved here immediately update backend strategy configuration files (`strategies/*.json`) and sync to the engine database without code breakage.
              </p>
              <div className="space-y-2 pt-1">
                {liveData.strategies.map((strat: any) => (
                  <div key={strat.strategy_id || strat.id} className="p-3 bg-[#0a0d14] rounded-lg border border-slate-800 flex items-center justify-between gap-2">
                    <div>
                      <span className="text-xs font-bold text-slate-200">{strat.name || strat.id}</span>
                      <div className="text-[11px] font-mono text-slate-400 mt-0.5">
                        Gate: <span className="text-amber-400 font-bold">{strat.conviction_threshold}/100</span> | Capital: ${strat.allocated_capital}
                      </div>
                    </div>
                    <button
                      onClick={() => {
                        const newGate = prompt(`Enter new Conviction Gate Threshold (0-100) for ${strat.strategy_id || strat.id}:`, String(strat.conviction_threshold));
                        if (newGate && !isNaN(Number(newGate))) {
                          handleSaveStrategyTune(strat.strategy_id || strat.id, { conviction_threshold: Number(newGate) });
                        }
                      }}
                      disabled={isSavingStrategy}
                      className="px-2.5 py-1 bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 text-xs font-medium rounded border border-amber-500/40 transition-colors"
                    >
                      {isSavingStrategy ? "Saving..." : "Edit Rule"}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Enhanced Interactive Notable Flow Watchlist Table */}
          <div className="p-4 bg-slate-900/80 rounded-xl border border-slate-800 space-y-3 shadow-xl">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-cyan-400 flex items-center gap-1.5">
                <Zap className="h-4 w-4" /> OWLs Notable Flow Watchlist
              </h4>
              <span className="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
                Total DB: {liveData.flow_counts.total} entries
              </span>
            </div>

            {/* Search, Sort, and Hide Expired Controls */}
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={watchlistSearch}
                  onChange={(e) => { setWatchlistSearch(e.target.value); setWatchlistPage(1); }}
                  placeholder="Search ticker, strike, or type..."
                  className="flex-1 px-2.5 py-1.5 bg-[#0a0d14] text-xs text-slate-200 rounded border border-slate-800 focus:outline-none focus:border-cyan-500 font-mono"
                />
                <select
                  value={watchlistSort}
                  onChange={(e: any) => setWatchlistSort(e.target.value)}
                  className="px-2 py-1.5 bg-[#0a0d14] text-xs text-slate-300 rounded border border-slate-800 focus:outline-none font-mono"
                >
                  <option value="dte_asc">Sort: Closest DTE ⏳</option>
                  <option value="premium">Sort: Highest Premium 💲</option>
                  <option value="ask_ratio">Sort: Ask Buy % 📊</option>
                  <option value="date">Sort: Newest Date 📅</option>
                </select>
              </div>

              {/* Hide Expired Toggle */}
              <div className="flex items-center justify-between px-1">
                <label className="flex items-center gap-2 text-[11px] text-slate-300 font-mono cursor-pointer select-none">
                  <input
                    type="checkbox"
                    checked={hideExpired}
                    onChange={(e) => { setHideExpired(e.target.checked); setWatchlistPage(1); }}
                    className="rounded bg-slate-800 border-slate-700 text-cyan-500 focus:ring-0 h-3.5 w-3.5"
                  />
                  <span>Hide Expired / Negative DTE</span>
                </label>
                <span className="text-[10px] text-slate-500 font-mono">
                  Showing {filteredWatchlist.length} active
                </span>
              </div>
            </div>

            {/* Tab Controls */}

            {/* Tab Controls */}
            <div className="flex items-center gap-1 bg-[#0a0d14] p-1 rounded-lg border border-slate-800 text-[11px] font-medium">
              <button
                onClick={() => { setWatchlistTab("active"); setWatchlistPage(1); }}
                className={`flex-1 py-1 px-2 rounded text-center transition-colors ${
                  watchlistTab === "active"
                    ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🟢 Active ({liveData.flow_counts.active})
              </button>
              <button
                onClick={() => { setWatchlistTab("verified"); setWatchlistPage(1); }}
                className={`flex-1 py-1 px-2 rounded text-center transition-colors ${
                  watchlistTab === "verified"
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                ⚡ 05:00 AM Verified ({liveData.flow_counts.verified})
              </button>
              <button
                onClick={() => { setWatchlistTab("historical"); setWatchlistPage(1); }}
                className={`flex-1 py-1 px-2 rounded text-center transition-colors ${
                  watchlistTab === "historical"
                    ? "bg-purple-500/20 text-purple-400 border border-purple-500/40 font-bold"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                🗄️ Archive ({liveData.flow_counts.historical})
              </button>
            </div>

            {/* Interactive Flow Table */}
            <div className="space-y-1.5 max-h-[340px] overflow-y-auto pr-1">
              {paginatedWatchlist.length === 0 ? (
                <div className="p-4 text-center text-xs text-slate-500 font-mono">
                  No matching contracts found for this filter.
                </div>
              ) : (
                paginatedWatchlist.map((item: any, idx: number) => {
                  const isCall = (item.option_type || "CALL").toUpperCase() === "CALL";
                  const dteVal = parseDTE(item.expiry, item.date);
                  return (
                    <div key={idx} className="p-2.5 bg-[#0a0d14] rounded-lg border border-slate-800/80 flex items-center justify-between text-xs font-mono hover:border-slate-700 transition-colors">
                      <div className="space-y-0.5">
                        <div className="flex items-center gap-1.5">
                          <span className="font-bold text-slate-100 text-sm">{item.ticker}</span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${isCall ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30" : "bg-purple-500/20 text-purple-300 border border-purple-500/30"}`}>
                            ${item.strike} {item.option_type}
                          </span>
                          <span className={`text-[10px] px-1.5 py-0.2 rounded font-bold ${
                            dteVal < 0
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : dteVal === 0
                              ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                              : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                          }`}>
                            {dteVal < 0 ? "Expired" : dteVal === 0 ? "0DTE" : `${dteVal}DTE`}
                          </span>
                        </div>
                        <div className="text-[10px] text-slate-400">
                          Prem: <span className="text-slate-200 font-bold">${((item.total_premium || 0)).toLocaleString()}</span> | Vol: {(item.volume || 0).toLocaleString()} | OI: {(item.open_interest || 0).toLocaleString()}
                        </div>
                      </div>

                      <div className="text-right space-y-0.5">
                        <div className="text-emerald-400 font-bold text-xs">
                          {Math.round((item.ask_ratio || 0.75) * 100)}% Ask Buy
                        </div>
                        <div className="text-[10px] text-slate-500 flex items-center gap-1 justify-end">
                          <span>{item.date}</span>
                          {item.oi_confirmed_matched && (
                            <span className="text-cyan-400 font-bold">✓ Match</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-1 border-t border-slate-800 text-[11px] font-mono">
                <button
                  onClick={() => setWatchlistPage((p) => Math.max(1, p - 1))}
                  disabled={watchlistPage === 1}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 rounded"
                >
                  ◀ Prev
                </button>
                <span className="text-slate-400">
                  Page <span className="text-slate-200 font-bold">{watchlistPage}</span> of {totalPages}
                </span>
                <button
                  onClick={() => setWatchlistPage((p) => Math.min(totalPages, p + 1))}
                  disabled={watchlistPage === totalPages}
                  className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-300 rounded"
                >
                  Next ▶
                </button>
              </div>
            )}
          </div>

          {/* Workflow Strategy Posture */}
          <div className="p-4 bg-emerald-500/5 rounded-xl border border-emerald-500/20">
            <h4 className="text-xs font-semibold text-emerald-400 mb-1 flex items-center gap-1.5">
              <ShieldCheck className="h-4 w-4" /> Strategy Logic Verification
            </h4>
            <p className="text-xs text-slate-300 leading-relaxed">
              Every signal step in this workflow is evaluated deterministically. Signals only advance to the execution engine when the conviction threshold passes the Risk Gate.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
