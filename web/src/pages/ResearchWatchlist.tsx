import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import ResearchDailyContext from './ResearchDailyContext';

type Fields = Record<string, unknown>;
interface Observation { event_id: string; raw_hash: string; contract: string; first_seen_at?: string; executed_at?: string; source_hash?: string; record?: Fields }
interface Snapshot extends Fields { contract: string }
interface WatchlistData { observations: Observation[]; snapshots: Snapshot[]; observation_count: number; contract_count: number }
const fields = (value: unknown): Fields => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Fields : {};
const text = (value: unknown): string => typeof value === 'string' && value.length ? value : typeof value === 'number' && Number.isFinite(value) ? String(value) : 'Unknown';
const time = (value: unknown): number => typeof value === 'string' && /(?:Z|[+-]\d{2}:\d{2})$/.test(value) && Number.isFinite(Date.parse(value)) ? Date.parse(value) : Infinity;
function validData(value: unknown): value is WatchlistData {
  const d = fields(value);
  return Array.isArray(d.observations) && Array.isArray(d.snapshots) && d.observations.every(r => typeof r?.contract === 'string' && typeof r?.event_id === 'string' && typeof r?.raw_hash === 'string') && d.snapshots.every(s => typeof s?.contract === 'string');
}
function contractTitle(contract: string) {
  const match = /^([A-Z][A-Z0-9]{0,5})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$/.exec(contract);
  return match ? `${match[1]} · 20${match[2]}-${match[3]}-${match[4]} · $${Number(match[6]) / 1000} · ${match[5] === 'C' ? 'Call' : 'Put'}` : `Unknown contract identity · ${contract}`;
}
function observedRange(snapshot: Snapshot | undefined) {
  const path = fields(snapshot?.observed_mark_path), low = path.observed_min_price, high = path.observed_max_price;
  return typeof low === 'number' && typeof high === 'number' && Number.isFinite(low) && Number.isFinite(high) && low >= 0 && high >= low ? `${low.toFixed(2)}–${high.toFixed(2)}` : 'Unknown';
}
function OriginalFields({event}: {event: Observation}) {
  const record = fields(event.record), raw = fields(record.raw), evidence = fields(record.evidence);
  return <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
    {Object.entries({'Original premium (provider raw)': raw.premium, 'Original trade size (provider raw)':raw.size, 'Volume (session aggregate)':raw.volume ?? evidence.volume, 'Open interest':raw.open_interest ?? evidence.open_interest}).map(([label,value]) => <div key={label}><dt className="text-slate-400">{label}</dt><dd>{text(value)}</dd></div>)}
  </dl>;
}
export function WatchlistView({data}: {data: unknown}) {
  const [query, setQuery] = useState('');
  const [coverage, setCoverage] = useState('all');
  if (!validData(data)) return <p role="alert">Research watchlist unavailable: invalid response. No records hidden as an empty cohort.</p>;
  const groups = new Map<string, Observation[]>();
  for (const event of data.observations) groups.set(event.contract, [...(groups.get(event.contract) ?? []), event]);
  const contracts = [...groups.entries()].map(([contract, events]) => {
    events.sort((a,b) => time(a.first_seen_at) - time(b.first_seen_at) || a.event_id.localeCompare(b.event_id) || a.raw_hash.localeCompare(b.raw_hash));
    return {contract,events,snapshots:data.snapshots.filter(s => s.contract === contract)};
  }).sort((a,b) => time(a.events[0].first_seen_at) - time(b.events[0].first_seen_at) || a.contract.localeCompare(b.contract));
  const visible = contracts.filter(c => `${c.contract} ${contractTitle(c.contract)}`.toLowerCase().includes(query.trim().toLowerCase()) && (coverage === 'all' || (coverage === 'recorded' ? c.snapshots.length > 0 : c.snapshots.length === 0)));
  return <section aria-label="Research tracking" className="border border-slate-700 bg-slate-900/60 rounded-xl p-4 space-y-4 text-slate-200">
    <h2 className="text-lg font-bold">Tracking · captured research cohort</h2>
    <p className="text-sm">{data.observations.length} original observations · {contracts.length} contracts · {visible.length} shown</p>
    <p className="text-sm text-amber-300">Prioritization not yet validated. No learned edge, verified buys, fills or execution permission.</p>
    <p className="text-xs text-slate-400">Manually refined baseline retained; learning compares this captured cohort, not the whole market. Stale, incomplete and enhancement-rejected observations remain visible. Contract groups are not a single whale or a combined trade. Raw premium/size semantics are not certified.</p>
    <ResearchDailyContext data={data} />
    <section aria-label="Research lifecycle and outcomes" className="space-y-3 text-xs">
      <h3 className="font-semibold">Research lifecycle and descriptive outcomes · {text(fields(data).mode)}</h3>
      <p>Priority is an evidence-coverage heuristic, not learned edge. Mark returns are not fills or trade P&amp;L. Configuration is not operating approval.</p>
      <p>Adaptive ranking: {text(fields(fields(fields(data).outcome_research).adaptive_ranking).status)}</p>
      {(Array.isArray(fields(data).research_requests) ? fields(data).research_requests as unknown[] : []).map((value, i) => {
        const r = fields(value);
        return <p key={i}>Ticket {text(r.ticket_id)} · Setup {text(r.setup_id)} · {text(r.ticker)} · Lifecycle: {text(r.state)} · Timeframe: {text(r.timeframe)}</p>;
      })}
      {(Array.isArray(fields(fields(data).outcome_research).candidates) ? fields(fields(data).outcome_research).candidates as unknown[] : []).map((value, i) => {
        const c = fields(value), priority = fields(c.priority);
        return <div key={i} className="border-t border-slate-700 pt-2"><p>{text(c.contract)} · {text(fields(c.inputs).event_id ?? c.event_id)} · Outcome: {text(c.status)} · Priority: {text(priority.score)} (coverage heuristic)</p>
          {(Array.isArray(c.outcomes) ? c.outcomes : []).map((value, j) => { const o = fields(value); return <p key={j}>Horizon: {text(o.minutes ?? o.horizon_minutes)} minutes · {text(o.status)} · Observed mark return: {typeof o.mark_return_pct === 'number' && Number.isFinite(o.mark_return_pct) ? `${o.mark_return_pct}%` : 'Unknown'} · {text(o.coverage)}</p>; })}
        </div>;
      })}
      {!fields(data).outcome_research && <p>Outcomes: Unknown — configuration or reader deployment pending.</p>}
    </section>
    <div className="flex flex-wrap gap-3 items-center">
      <label className="text-xs">Search ticker or contract <input aria-label="Search ticker or contract" value={query} onChange={e => setQuery(e.target.value)} className="ml-2 bg-slate-800 border border-slate-700 rounded-lg p-2" /></label>
      <label className="text-xs">Coverage <select aria-label="Coverage" value={coverage} onChange={e => setCoverage(e.target.value)} className="ml-2 bg-slate-800 border border-slate-700 rounded-lg p-2"><option value="all">All coverage</option><option value="pending">Pending snapshot</option><option value="recorded">Recorded snapshot (not live)</option></select></label>
      <span className="text-xs text-slate-400">First seen ascending · descriptive, not edge ranking</span>
    </div>
    {!contracts.length && <p>No captured research observations yet.</p>}
    {!!contracts.length && !visible.length && <p>No matching contracts. Clear search or select All coverage to restore the cohort.</p>}
    {visible.map(({contract,events,snapshots}) => {
      const first = events[0], record = fields(first.record), evidence = fields(record.evidence);
      const latest = [...snapshots].sort((a,b) => (Number.isFinite(time(b.received_at)) ? time(b.received_at) : -Infinity) - (Number.isFinite(time(a.received_at)) ? time(a.received_at) : -Infinity) || text(a.id).localeCompare(text(b.id)))[0];
      return <article data-testid="tracking-contract" key={contract} className="border border-slate-700 rounded-xl p-4 space-y-3">
        <h3 className="font-semibold">{contractTitle(contract)}</h3><p className="text-xs text-slate-400 font-mono">{contract}</p>
        <div className="grid md:grid-cols-3 gap-4">
          <div><p className="text-xs text-slate-400 mb-2">Earliest captured event (not summed)</p><OriginalFields event={first}/></div>
          <div className="text-xs space-y-1"><p>First seen: {text(first.first_seen_at)}</p><p>Source: {text(evidence.source)}</p><p>Profile: {text(record.profile_name)}</p><p>Original baseline: {text(record.baseline_status)}</p><p>Enhancement: {text(record.enhanced_status)}</p></div>
          <div className="text-xs space-y-1"><p>{latest ? 'Recorded snapshot · not live' : 'Pending snapshot'}</p><p>As of: {text(latest?.as_of)}</p><p>Confluence: Unknown</p><p>Observed option-mark range: {observedRange(latest)} · gapped observations, not continuous MFE/MAE or trade P&amp;L.</p><p>{events.length} original events / versions</p></div>
        </div>
        <details><summary className="cursor-pointer text-sm text-emerald-300">Original event history ({events.length})</summary>
          <div className="space-y-3 mt-3">{events.map(e => <section key={`${e.event_id}-${e.raw_hash}`} className="border-t border-slate-800 pt-3 text-xs space-y-2"><p>Provider event: <span>{e.event_id}</span></p><p>Execution: {text(e.executed_at)} · First seen: {text(e.first_seen_at)}</p><OriginalFields event={e}/><p>Source: {text(fields(fields(e.record).evidence).source)} · Profile: {text(fields(e.record).profile_name)}</p><p>Original baseline: {text(fields(e.record).baseline_status)} · Enhancement: {text(fields(e.record).enhanced_status)}</p><details><summary>Original record and provenance</summary><pre className="whitespace-pre-wrap break-all">{JSON.stringify({event_id:e.event_id,raw_hash:e.raw_hash,source_hash:e.source_hash},null,2)}</pre></details></section>)}</div>
        </details>
        <details><summary className="cursor-pointer text-sm text-emerald-300">Snapshot metadata ({snapshots.length})</summary>{!snapshots.length && <p className="text-xs">No snapshot recorded. Coverage and follow-up unknown.</p>}{snapshots.map((s,i) => <div key={text(s.id) + i} className="text-xs mt-3"><p>As of: {text(s.as_of)} · Received: {text(s.received_at)}</p><p>{text(s.post_first_seen_bars)} bars strictly after first-seen; {text(s.pre_first_seen_bars)} historical bars, not follow-up.</p><pre className="whitespace-pre-wrap break-all">{JSON.stringify({id:s.id,raw_hash:s.raw_hash,contract_identity:s.contract_identity},null,2)}</pre></div>)}</details>
      </article>;
    })}
  </section>;
}
export default function ResearchWatchlist() {
  const [data,setData] = useState<unknown>(null);
  const [error,setError] = useState('');
  const [loading,setLoading] = useState(true);
  useEffect(() => { let active = true; api.getResearchWatchlist().then(d => {if(active) {setData(d);setLoading(false);}}).catch(() => {if(active) {setError('Research watchlist unavailable — endpoint may await deployment.');setLoading(false);}}); return () => {active=false;}; }, []);
  if (error) return <p role="alert">{error}</p>;
  return loading ? <p role="status">Loading research watchlist…</p> : <WatchlistView data={data} />;
}
