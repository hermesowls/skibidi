import { useEffect, useRef, useState } from "react";
import { RefreshCw, Zap, Shield, Search, Info } from "lucide-react";

interface NodeItem {
  id: string;
  name: string;
  community: string;
  val: number;
  color: string;
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
}

interface LinkItem {
  source: string;
  target: string;
}

interface CommunityItem {
  name: string;
  color: string;
  count: number;
  enabled: boolean;
}

export function GraphifyPage() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [nodes, setNodes] = useState<NodeItem[]>([]);
  const [links, setLinks] = useState<LinkItem[]>([]);
  const [communities, setCommunities] = useState<CommunityItem[]>([
    { name: "Tickers", color: "#6366f1", count: 4, enabled: true },
    { name: "Signals", color: "#f59e0b", count: 3, enabled: true },
    { name: "Portfolios", color: "#10b981", count: 2, enabled: true },
    { name: "Suppliers", color: "#06b6d4", count: 3, enabled: true },
    { name: "Sympathy", color: "#ec4899", count: 2, enabled: true },
    { name: "Active Trades", color: "#e11d48", count: 2, enabled: true },
  ]);

  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(false);

  // Fetch Live Graph Payload
  const loadGraphData = async () => {
    setLoading(true);
    try {
      const res = await fetch("/graph_data.json");
      if (res.ok) {
        const data = await res.json();
        if (data.nodes && data.links) {
          // Initialize positions randomly in canvas space
          const initializedNodes = data.nodes.map((n: NodeItem) => ({
            ...n,
            x: Math.random() * 600 + 100,
            y: Math.random() * 400 + 100,
            vx: (Math.random() - 0.5) * 1.5,
            vy: (Math.random() - 0.5) * 1.5,
          }));
          setNodes(initializedNodes);
          setLinks(data.links);
          if (data.communities) {
            setCommunities(
              data.communities.map((c: any) => ({ ...c, enabled: true }))
            );
          }
        }
      }
    } catch (e) {
      console.warn("Using fallback local node structure", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraphData();
  }, []);

  // Physics Force Simulation & Neural Web Rendering Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let animId: number;

    const enabledCommunities = new Set(
      communities.filter((c) => c.enabled).map((c) => c.name)
    );

    const activeNodes = nodes.filter((n) => enabledCommunities.has(n.community));
    const activeNodeIds = new Set(activeNodes.map((n) => n.id));
    const activeLinks = links.filter(
      (l) => activeNodeIds.has(l.source) && activeNodeIds.has(l.target)
    );

    const nodeMap = new Map(activeNodes.map((n) => [n.id, n]));

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // 1. Physics force calculations
      for (let i = 0; i < activeNodes.length; i++) {
        const n1 = activeNodes[i];
        if (!n1.x || !n1.y) continue;

        // Central gravity
        const cx = canvas.width / 2;
        const cy = canvas.height / 2;
        n1.vx = (n1.vx || 0) + (cx - n1.x) * 0.0003;
        n1.vy = (n1.vy || 0) + (cy - n1.y) * 0.0003;

        // Repulsion between nodes
        for (let j = i + 1; j < activeNodes.length; j++) {
          const n2 = activeNodes[j];
          if (!n2.x || !n2.y) continue;
          const dx = n2.x - n1.x;
          const dy = n2.y - n1.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / dist * 0.08;
            n1.vx -= dx * force * 0.05;
            n1.vy -= dy * force * 0.05;
            n2.vx = (n2.vx || 0) + dx * force * 0.05;
            n2.vy = (n2.vy || 0) + dy * force * 0.05;
          }
        }

        // Apply velocity & boundary dampening
        n1.x += n1.vx || 0;
        n1.y += n1.vy || 0;
        n1.vx *= 0.92;
        n1.vy *= 0.92;

        n1.x = Math.max(30, Math.min(canvas.width - 30, n1.x));
        n1.y = Math.max(30, Math.min(canvas.height - 30, n1.y));
      }

      // 2. Draw Neural Web Links / Connections
      ctx.lineWidth = 0.8;
      activeLinks.forEach((l) => {
        const s = nodeMap.get(l.source);
        const t = nodeMap.get(l.target);
        if (s && t && s.x && s.y && t.x && t.y) {
          ctx.beginPath();
          ctx.moveTo(s.x, s.y);
          ctx.lineTo(t.x, t.y);
          ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
          ctx.stroke();
        }
      });

      // 3. Draw Particle Nodes & Glow Rings
      activeNodes.forEach((n) => {
        if (!n.x || !n.y) return;
        const isMatch =
          searchTerm === "" ||
          n.name.toLowerCase().includes(searchTerm.toLowerCase());

        // Outer glow
        ctx.beginPath();
        ctx.arc(n.x, n.y, n.val + 4, 0, Math.PI * 2);
        ctx.fillStyle = isMatch ? n.color + "33" : "rgba(255,255,255,0.05)";
        ctx.fill();

        // Core particle
        ctx.beginPath();
        ctx.arc(n.x, n.y, isMatch ? n.val / 2 : 3, 0, Math.PI * 2);
        ctx.fillStyle = isMatch ? n.color : "#4b5563";
        ctx.fill();

        // Node Label
        if (isMatch) {
          ctx.font = "10px monospace";
          ctx.fillStyle = "#e5e7eb";
          ctx.textAlign = "center";
          ctx.fillText(n.name, n.x, n.y + n.val / 2 + 12);
        }
      });

      animId = requestAnimationFrame(render);
    };

    render();
    return () => cancelAnimationFrame(animId);
  }, [nodes, links, communities, searchTerm]);

  // Toggle all communities
  const toggleSelectAll = (checked: boolean) => {
    setCommunities((prev) => prev.map((c) => ({ ...c, enabled: checked })));
  };

  const toggleCommunity = (idx: number) => {
    setCommunities((prev) => {
      const next = [...prev];
      next[idx].enabled = !next[idx].enabled;
      return next;
    });
  };

  const allSelected = communities.every((c) => c.enabled);

  return (
    <div className="flex h-full w-full flex-col gap-4 font-mono text-text-primary">
      {/* Top Banner Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-current/20 pb-3">
        <div>
          <h1 className="text-lg font-bold tracking-wider text-midground uppercase flex items-center gap-2">
            <span>NEURAL WEB KNOWLEDGE GRAPH</span>
          </h1>
          <p className="text-xs text-text-tertiary">
            Real-time interactive market & strategy correlation web
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 rounded bg-black/40 px-3 py-1 border border-current/20 text-xs">
            <Zap className="h-3.5 w-3.5 text-emerald-400" />
            <span>GEX 0DTE: $1,000.00</span>
          </div>
          <div className="flex items-center gap-1.5 rounded bg-black/40 px-3 py-1 border border-current/20 text-xs">
            <Shield className="h-3.5 w-3.5 text-blue-400" />
            <span>VEX Swing: $1,000.00</span>
          </div>
          <button
            onClick={loadGraphData}
            disabled={loading}
            className="flex items-center gap-1.5 rounded bg-midground/20 hover:bg-midground/30 px-3 py-1 text-xs border border-midground text-midground font-bold transition-colors cursor-pointer"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>{loading ? "Refreshing..." : "Sync Live Data"}</span>
          </button>
        </div>
      </div>

      {/* Main Split Interface */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-[550px]">
        {/* Left 3-Cols: Canvas Neural Web */}
        <div className="lg:col-span-3 flex flex-col rounded border border-current/20 bg-[#0d0f17] relative overflow-hidden min-h-[480px]">
          {/* Top Search Bar Overlay */}
          <div className="absolute top-3 left-3 z-10 w-72">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-text-tertiary" />
              <input
                type="text"
                placeholder="Search ticker, flow, or strategy..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full rounded bg-black/80 pl-8 pr-3 py-1.5 text-xs text-text-primary border border-current/20 focus:outline-none focus:border-midground backdrop-blur-md"
              />
            </div>
          </div>

          {/* Interactive HTML5 Physics Canvas */}
          <canvas
            ref={canvasRef}
            width={850}
            height={520}
            className="w-full h-full cursor-grab active:cursor-grabbing"
          />
        </div>

        {/* Right 1-Col: Communities Checklist (Exact Match to User Screenshot) */}
        <div className="flex flex-col rounded border border-current/20 bg-[#121522] p-4 font-sans text-xs">
          <h2 className="font-bold tracking-widest text-text-secondary uppercase mb-4 border-b border-current/10 pb-2 text-[11px]">
            COMMUNITIES
          </h2>

          {/* Select All Checkbox */}
          <label className="flex items-center gap-2 mb-4 font-semibold text-text-primary cursor-pointer">
            <input
              type="checkbox"
              checked={allSelected}
              onChange={(e) => toggleSelectAll(e.target.checked)}
              className="rounded border-current/30 text-midground focus:ring-0 accent-midground cursor-pointer"
            />
            <span>Select All</span>
          </label>

          {/* List of Community Clusters */}
          <div className="flex flex-col gap-2.5 overflow-y-auto flex-1 pr-1">
            {communities.map((c, idx) => (
              <label
                key={c.name}
                className="flex items-center justify-between group hover:bg-black/20 px-1 py-1 rounded cursor-pointer transition-colors"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <input
                    type="checkbox"
                    checked={c.enabled}
                    onChange={() => toggleCommunity(idx)}
                    className="rounded border-current/30 text-midground focus:ring-0 accent-midground cursor-pointer"
                  />
                  <div
                    className="h-3 w-3 rounded-full shrink-0"
                    style={{ backgroundColor: c.color }}
                  />
                  <span className="truncate text-text-primary text-[12px]">
                    {c.name}
                  </span>
                </div>
                <span className="text-[11px] font-mono text-text-tertiary">
                  {c.count}
                </span>
              </label>
            ))}
          </div>

          {/* Footer Info */}
          <div className="border-t border-current/10 pt-3 mt-4 text-[10px] text-text-tertiary flex items-center gap-1.5">
            <Info className="h-3.5 w-3.5 shrink-0 text-midground" />
            <span>Updates dynamically from Skylit, Unusual Whales & Alpaca Journal.</span>
          </div>
        </div>
      </div>
    </div>
  );
}
