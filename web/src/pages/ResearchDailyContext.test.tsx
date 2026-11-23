// @vitest-environment jsdom
import { readFileSync } from 'node:fs';
import { afterEach, expect, it, vi } from 'vitest';
import { cleanup, render, screen, within } from '@testing-library/react';
vi.mock('@/lib/api', () => ({ api: { getResearchWatchlist: vi.fn() } }));
import { api } from '@/lib/api';
import ResearchWatchlist from './ResearchWatchlist';
afterEach(cleanup);
it.skipIf(!process.env.RESEARCH_SAVED_PROJECTION)('replays saved authenticated REAL projection read-only, not a live qualification', async () => {
 const saved=JSON.parse(readFileSync(process.env.RESEARCH_SAVED_PROJECTION!, 'utf8'));
 const panel=await mount(saved);
 expect(saved.mode).toBe('REAL_DATA_RESEARCH');
 expect(within(panel).getByText('EMA8: 766.52')).toBeTruthy();
 expect(within(panel).getByText(/252 completed regular underlying bars/)).toBeTruthy();
 expect(screen.getByText(/1 covered contracts · 153 completed option-minute bars/)).toBeTruthy();
 expect(screen.getAllByTestId('tracking-contract')).toHaveLength(17);
});
it('selects latest aware receipt, keeps nulls unknown, rejects reversed chronology', async () => {
 const p=payload();
 p.underlying_technicals=[{...daily,received_at:'2026-09-29T21:00:00-07:00',ema:{...daily.ema,8:null} as never},daily];
 const panel=await mount(p);
 expect(within(within(panel).getByRole('article',{name:'SPY daily context'})).getByText('EMA8: Unknown')).toBeTruthy();
 expect(within(panel).queryByText('EMA8: 766.51')).toBeNull();
 cleanup();
 p.underlying_technicals=[{...daily,last_completed_at:'2026-10-01T20:00:00Z'}];
 const invalid=await mount(p);
 expect(within(invalid).getByText(/SPY · DAILY · Insufficient data/)).toBeTruthy();
 expect(within(invalid).queryByText('EMA8: 766.51')).toBeNull();
});
it('unavailable API never exposes the error body', async () => {
 vi.mocked(api.getResearchWatchlist).mockRejectedValueOnce(new Error('Bearer SECRET_RAW_BODY'));
 render(<ResearchWatchlist/>);
 expect(await screen.findByRole('alert')).toBeTruthy();
 expect(document.body.textContent).not.toContain('SECRET_RAW_BODY');
});
it('renders observed option ranges, not P&L, without dumping arbitrary API fields', async () => {
 const p={...payload(),snapshots:[{contract:'SPY260925P00760000',received_at:'2026-09-30T02:00:00Z',observed_mark_path:{observed_min_price:3.26,observed_max_price:4.5,trade_pnl:null},error_body:'SECRET_RAW_BODY'}]};
 await mount(p);
 expect(screen.getByText(/Observed option-mark range: 3.26–4.50/)).toBeTruthy();
 expect(document.body.textContent).not.toContain('SECRET_RAW_BODY');
});
it('unknown and invalid ranges stay unknown without coercing null to zero', async () => {
 await mount({...payload(),snapshots:[{contract:'SPY260925P00760000',received_at:'2026-09-30T02:00:00Z',observed_mark_path:{observed_min_price:5,observed_max_price:4}}]});
 expect(screen.getAllByText(/Observed option-mark range: Unknown/)).toHaveLength(2);
});
const daily = {ticker:'SPY',status:'AVAILABLE',research_timeframe:'DAILY',timeframe_approval:'PROVISIONAL_DESCRIPTIVE_ONLY',use:'RECEIPT_TIME_CONTEXT_NOT_DISCOVERY_TIME_SIGNAL',received_at:'2026-09-30T02:37:15Z',last_completed_at:'2026-09-29T20:00:00Z',underlying_completed_bars:252,ema:{8:766.51,21:765.57,50:761.10,100:748.73,200:723.16},variant:'TTM-style BB20x2 KC20x1.5 SMA-TR LR20',squeeze_on:false,squeeze_off:true,release:false,momentum:4.2,momentum_slope:0.12};
const event = (ticker:string) => ({event_id:`TEST-${ticker}`,raw_hash:'TEST',contract:`${ticker}260925P00760000`,record:{evidence:{ticker}}});
const payload = () => ({observations:[event('SPY'),event('QQQ')],snapshots:[],underlying_technicals:[daily],learning_summary:{covered_contract_count:1,completed_bars_latest_per_contract:153},source_availability:{discord:{context_status:'UNAVAILABLE',access_status:'HTTP_BLOCKED',http_status:403,live_verified:false},skylit:{context_status:'SAVED_CONTEXT_ONLY',access_status:'UNKNOWN',live_verified:false}}});
async function mount(value:unknown) {vi.mocked(api.getResearchWatchlist).mockResolvedValueOnce(value); render(<ResearchWatchlist/>); return await screen.findByRole('region',{name:'Daily underlying context'});}
it('mounts current API daily fields and separates underlying from option coverage', async () => {
 const panel = await mount(payload());
 expect(within(panel).getByText(/SPY · DAILY · Provisional/)).toBeTruthy();
 for (const [period,value] of Object.entries(daily.ema)) expect(within(panel).getByText(`EMA${period}: ${value.toFixed(2)}`)).toBeTruthy();
 expect(within(panel).getByText(/252 completed regular underlying bars/)).toBeTruthy();
 expect(within(panel).getByText(/TTM-style BB20x2 KC20x1.5 SMA-TR LR20/)).toBeTruthy();
 expect(within(panel).getByText(/Squeeze: off/)).toBeTruthy();
 expect(within(panel).getByText(/not a discovery-time signal/)).toBeTruthy();
 expect(within(panel).getByText(/QQQ · DAILY · Insufficient data/)).toBeTruthy();
 expect(screen.getByText(/1 covered contracts · 153 completed option-minute bars/)).toBeTruthy();
 expect(screen.getByText(/Discord: Unavailable · HTTP blocked \(403\)/)).toBeTruthy();
 expect(screen.getByText(/Numeric GEX: Unknown/)).toBeTruthy();
});
