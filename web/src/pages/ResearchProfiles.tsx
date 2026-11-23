import { useEffect, useState } from 'react';
import { api } from '@/lib/api';


const TEST_EVIDENCE = {ticker:'TEST',strike:105,call_put:'C',expiration:'2026-09-30',
  contract_symbol:'TEST260930C00105000',observed_at:'2026-09-23T15:00:00+00:00',
  spot_observed_at:'2026-09-23T15:00:00+00:00',spot_price:50,premium_usd:1000000,
  size:500,volume:1000,open_interest:0,complex_trade:false,reported_side:'ask',
  premium_definition:'single_print_usd',size_definition:'single_print_contracts',volume_definition:'aggregate_contract_session'};

// Local exact-version selection only. Never changes the tape, delivery or execution.
export default function ResearchProfiles() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [name, setName] = useState('Default TEST');
  const [fields, setFields] = useState<Record<string, any>>({min_premium:50000,min_size:500,dte_min:1,dte_max:14,otm_required:true,max_otm_fraction:null});
  const [results, setResults] = useState<any[]>([]);
  const preview = async () => {
    if (!selected) return;
    setBusy(true); setError('');
    try {
      const result = await api.previewResearchProfile(selected.version_id, TEST_EVIDENCE);
      // Store response snapshots, never resolve historical labels from selection.
      setResults(previous => [result, ...previous].slice(0, 10));
    } catch { setError('TEST preview failed — prior results unchanged'); }
    finally { setBusy(false); }
  };
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const load = async () => {
    setBusy(true); setError('');
    try { const data = await api.getResearchProfiles(); setProfiles(data.profiles); }
    catch { setProfiles([]); setSelected(null); setError('Profiles unavailable — selection cleared'); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, []);
  const choose = async (version: string) => {
    setSelected(null); setError('');
    if (!version) return;
    setBusy(true);
    try {
      const snapshot = await api.getResearchProfiles(version);
      setSelected(snapshot); setName(snapshot.profile.research_profile_name);
      const p = snapshot.profile.kian_research;
      setFields(Object.fromEntries(Object.keys(fields).map(k => [k,p[k]])));
    } catch { setError('Profile version unavailable — selection cleared'); }
    finally { setBusy(false); }
  };
  const save = async (mode: 'create'|'edit'|'clone') => {
    setBusy(true); setError('');
    try {
      const changes = mode === 'clone' ? {} : fields;
      const saved = await api.saveResearchProfile({name,changes,...(mode !== 'create' ? {base_version:selected.version_id} : {})});
      // Read back persisted exact version; no optimistic claim that a write succeeded.
      const confirmed = await api.getResearchProfiles(saved.version_id);
      const data = await api.getResearchProfiles();
      setProfiles(data.profiles); setSelected(confirmed);
    } catch { setError('Profile save failed — prior immutable version unchanged'); }
    finally { setBusy(false); }
  };
  const inputClass = 'bg-slate-900 border border-slate-600 rounded px-2 py-1';
  return <><section className="border border-slate-700 rounded-xl p-4 space-y-3" aria-label="TEST research profiles">
    <h2 className="font-semibold">TEST research profiles</h2>
    <p className="text-sm text-slate-400">Offline research configuration only; no delivery or execution permission. Selection does not start a scan or change live tape filters.</p>
    {error && <p role="alert">{error}</p>}
    <select className={inputClass} aria-label="Research profile version" disabled={busy} value={selected?.version_id ?? ''} onChange={e => void choose(e.target.value)}>
      <option value="">No selected profile</option>
      {profiles.map(p => <option key={p.version_id} value={p.version_id}>{p.profile.research_profile_name} · {p.version_id}</option>)}
    </select>
    <button disabled={busy} onClick={() => void load()}>Refresh profiles</button>
    <div className="flex flex-wrap gap-3">
      <label>Name <input className={inputClass} aria-label="Profile name" maxLength={100} value={name} onChange={e => setName(e.target.value)} /></label>
      {Object.entries({min_premium:'Minimum single-print USD',min_size:'Minimum single-print contracts',dte_min:'Minimum DTE',dte_max:'Maximum DTE',max_otm_fraction:'Maximum OTM fraction'}).map(([key,label]) => <label key={key}>{label} <input className={inputClass} aria-label={label} type="number" step={key === 'max_otm_fraction' ? 'any' : '1'} value={fields[key] ?? ''} onChange={e => setFields({...fields,[key]:e.target.value === '' && key === 'max_otm_fraction' ? null : Number(e.target.value)})} /></label>)}
      <label><input type="checkbox" checked={fields.otm_required} onChange={e => setFields({...fields,otm_required:e.target.checked})} /> OTM required</label>
    </div>
    <p>OTM cap: {fields.max_otm_fraction === null ? 'Uncapped (blank)' : fields.max_otm_fraction}. Volume &gt; known OI fixed; complex trades rejected; ask report only, not verified buying.</p>
    <div className="flex gap-4"><button disabled={busy || !name.trim()} onClick={() => void save('create')}>Create profile</button><button disabled={busy || !selected} onClick={() => void save('edit')}>Save new version</button><button disabled={busy || !selected} onClick={() => void save('clone')}>Clone profile</button></div>
    {selected && <div><p>Selected: {selected.profile.research_profile_name} · {selected.version_id}</p><p>Provenance: {JSON.stringify(selected.profile.filter_provenance)}</p><p>Explicit offline context: profile_version={selected.version_id}; policy_hash={selected.profile.kian_policy_hash}</p></div>}
    <div><p>Fixed hypothetical TEST fixture: TEST call, strike $105, spot $50, $1M single print, 500 contracts, volume 1000, known OI 0; simple trade, reported ask only. As of September 23, 2026 15:00 UTC, expires September 30. Not market data or a live scan. Unsaved edits are not previewed.</p>
      <details><summary>Supplied TEST evidence</summary><pre>{JSON.stringify(TEST_EVIDENCE,null,2)}</pre></details>
      <button disabled={busy || !selected} onClick={() => void preview()}>Preview TEST evidence</button>
    </div>
    <div aria-label="TEST preview results">{results.map((r,i) => <article key={`${r.decision_id}-${i}`} className="border border-slate-700 p-3">
      <h3>TEST preview: {r.profile_name} · {r.policy_version}</h3>
      <p>{r.notice}</p><p>Baseline: {r.baseline_status}; enhancements: {r.enhanced_status}</p>
      <p>OTM fraction: {r.otm_fraction ?? 'Unknown'}; cap: {r.max_otm_fraction === null ? 'Uncapped' : r.max_otm_fraction}; DTE: {r.dte}</p>
      <p>Reasons: {r.baseline_reasons.length ? r.baseline_reasons.join(', ') : 'Declared TEST baseline passed only'}</p>
      <p>Unknowns: {r.enhancement_unknowns.join(', ')}</p>
      <p>Policy hash: {r.policy_hash}</p><p>TEST source hash: {r.source_hash}</p><p>TEST decision hash: {r.decision_hash}</p>
      <p>Provenance: {JSON.stringify(r.filter_provenance)}</p>
      <p>No verified buying, confirmed setup, probability or execution permission. Hedges and multileg activity remain possible; complex prints are excluded by this screen.</p>
    </article>)}</div>
  </section></>;
}
