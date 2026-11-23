type Fields = Record<string, unknown>;
const fields = (v: unknown): Fields => v !== null && typeof v === 'object' && !Array.isArray(v) ? v as Fields : {};
const rows = (v: unknown): Fields[] => Array.isArray(v) ? v.map(fields) : [];
const stamp = (v: unknown): number => typeof v === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(v) ? Date.parse(v) : NaN;
const date = (v: unknown) => Number.isFinite(stamp(v)) ? new Date(stamp(v)).toISOString() : 'Unknown';
const number = (v: unknown) => typeof v === 'number' && Number.isFinite(v) ? v.toFixed(2) : 'Unknown';
const count = (v: unknown) => typeof v === 'number' && Number.isSafeInteger(v) && v >= 0 ? String(v) : 'Unknown';
const label = (v: unknown, allowed: Record<string,string>) => typeof v === 'string' ? allowed[v] ?? 'Unknown' : 'Unknown';
const tickerOf = (v: unknown) => typeof v === 'string' ? /^([A-Z][A-Z0-9]{0,5})\d{6}[CP]\d{8}$/.exec(v)?.[1] : undefined;
export default function ResearchDailyContext({data}: {data: unknown}) {
 const d=fields(data), history=rows(d.underlying_technicals), summary=fields(d.learning_summary), sources=fields(d.source_availability);
 const tickers=[...new Set(rows(d.observations).map(o=>tickerOf(o.contract)).filter((t): t is string=>!!t))].sort();
 return <>
  <section aria-label="Descriptive coverage" className="border border-slate-700 rounded-xl p-3 text-xs space-y-2">
   <h3 className="font-semibold">Descriptive coverage · not validated learning</h3>
   <p>{count(summary.covered_contract_count)} covered contracts · {count(summary.completed_bars_latest_per_contract)} completed option-minute bars (latest receipt per contract, not summed snapshots).</p>
   <p>Unequal observed windows; no approved horizon outcomes, trade P&amp;L or validated edge. Underlying daily history is separate from option follow-up.</p>
  </section>
  <section aria-label="Source availability" className="text-xs space-y-1">
   {(['discord','skylit'] as const).map(key=>{const source=fields(sources[key]); return <p key={key}>{key==='discord'?'Discord':'Skylit'}: {label(source.context_status,{UNAVAILABLE:'Unavailable',SAVED_CONTEXT_ONLY:'Saved context only',AVAILABLE:'Available'})} · {label(source.access_status,{HTTP_BLOCKED:'HTTP blocked',AVAILABLE:'Available',UNKNOWN:'Unknown'})}{source.http_status===403?' (403)':''} · {source.live_verified===true?'Live verified':'Live access not verified'}</p>;})}
   <p>Numeric GEX: Unknown · qualified numeric evidence absent. Next-session OI: Unknown. Source gaps do not reject the captured baseline.</p>
  </section>
  <section aria-label="Daily underlying context" className="space-y-3">
   <h3 className="font-semibold">DAILY underlying context</h3>
   <p className="text-xs text-amber-300">Provisional receipt-time context, not a discovery-time signal. Recorded history, not live quotes or a trade recommendation.</p>
   <div className="grid md:grid-cols-2 gap-3">{tickers.map(ticker=>{
    const candidates=history.filter(h=>h.ticker===ticker && h.research_timeframe==='DAILY' && Number.isFinite(stamp(h.received_at))).sort((a,b)=>stamp(b.received_at)-stamp(a.received_at));
    const latest=candidates[0] ?? {};
    const available=latest.status==='AVAILABLE' && latest.timeframe_approval==='PROVISIONAL_DESCRIPTIVE_ONLY' && latest.use==='RECEIPT_TIME_CONTEXT_NOT_DISCOVERY_TIME_SIGNAL' && Number.isFinite(stamp(latest.last_completed_at)) && stamp(latest.last_completed_at)<=stamp(latest.received_at);
    const ema=available?fields(latest.ema):{};
    const state=available ? latest.squeeze_on===true && latest.squeeze_off===false ? 'on' : latest.squeeze_off===true && latest.squeeze_on===false ? 'off' : 'Unknown' : 'Unknown';
    return <article key={ticker} aria-label={`${ticker} daily context`} className="border border-slate-700 rounded-xl p-3 text-xs space-y-2">
     <h4 className="font-semibold">{ticker} · DAILY · {available?'Provisional':'Insufficient data'}</h4>
     <p>{count(latest.underlying_completed_bars)} completed regular underlying bars · latest receipt only</p>
     <p>As of (last completed session): {date(latest.last_completed_at)} · Receipt: {date(latest.received_at)}</p>
     <p className="text-slate-400">Completion calendar-derived; provider observation time unavailable.</p>
     <div className="flex flex-wrap gap-x-4 gap-y-1">{[8,21,50,100,200].map(p=><span key={p}>EMA{p}: {number(ema[p])}</span>)}</div>
     <p>TTM variant: {available && latest.variant==='TTM-style BB20x2 KC20x1.5 SMA-TR LR20'?latest.variant:'Unknown'} · Squeeze: {state}</p>
     <p>Release: {available && typeof latest.release==='boolean'?(latest.release?'yes':'no'):'Unknown'} · Momentum: {number(available?latest.momentum:null)} · Slope: {number(available?latest.momentum_slope:null)}</p>
    </article>;
   })}</div>
  </section>
 </>;
}
