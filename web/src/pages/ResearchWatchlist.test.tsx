// @vitest-environment jsdom
import { describe, expect, it, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
vi.mock('@/lib/api', () => ({api:{getResearchWatchlist:vi.fn()}}));
import ResearchWatchlist, { WatchlistView } from './ResearchWatchlist';
import { api } from '@/lib/api';
afterEach(cleanup);
const event = (id: string, contract = 'TEST260925C00100000') => ({event_id:id,raw_hash:id,contract,executed_at:'2026-09-24T13:30:00Z',first_seen_at:'2026-09-24T16:35:00Z',record:{baseline_status:'INCOMPLETE',profile_name:'TEST baseline',evidence:{source:'TEST'},raw:{premium:'50001',size:501,volume:700,open_interest:600}}});
const data = {observation_count:2,contract_count:1,pending_contracts:['TEST260925C00100000'],snapshots:[],observations:[event('TEST-a'),event('TEST-b')]};
describe('Tracking TEST fixtures', () => {
  it('sorts first-seen chronologically across explicit timezone offsets', () => {
    render(<WatchlistView data={{observations:[{...event('early','EARLY260925C00100000'),first_seen_at:'2026-09-24T16:00:00Z'},{...event('later','LATER260925C00100000'),first_seen_at:'2026-09-24T10:00:00-07:00'}],snapshots:[]}}/>);
    expect(screen.getAllByTestId('tracking-contract')[0].textContent).toContain('EARLY');
  });
  it('retains the full 20-observation / 17-contract TEST cohort', () => {
    const observations = Array.from({length:20}, (_,i) => event(`TEST-event-${i}`,`T${i % 17}260925C00100000`));
    render(<WatchlistView data={{observations,snapshots:[{contract:observations[0].contract,as_of:'2026-09-24T16:36:00Z',post_first_seen_bars:1,pre_first_seen_bars:0,contract_identity:'REQUEST_PATH_ONLY_NO_RESPONSE_ECHO'}]}}/>);
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(17);
    for (const observation of observations) expect(screen.getByText(observation.event_id)).toBeTruthy();
    expect(screen.getByText(/20 original observations · 17 contracts · 17 shown/)).toBeTruthy();
    expect(screen.getByText(/1 bars strictly after first-seen; 0 historical bars/)).toBeTruthy();
    expect(screen.getByText(/REQUEST_PATH_ONLY_NO_RESPONSE_ECHO/)).toBeTruthy();
  });
  it('filters only on explicit search/coverage and restores every contract', () => {
    render(<WatchlistView data={{...data, observations:[...data.observations,event('TEST-c','OTHER260925P00005000')],snapshots:[{contract:'OTHER260925P00005000',as_of:'old',received_at:'old'}]}}/>);
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(2);
    fireEvent.change(screen.getByLabelText('Coverage'),{target:{value:'pending'}});
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Coverage'),{target:{value:'all'}});
    fireEvent.change(screen.getByLabelText('Search ticker or contract'),{target:{value:'other'}});
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(1);
    fireEvent.change(screen.getByLabelText('Search ticker or contract'),{target:{value:'missing'}});
    expect(screen.getByText(/No matching contracts/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText('Search ticker or contract'),{target:{value:''}});
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(2);
  });
  it('guards invalid and empty payloads without inventing zero values', () => {
    const view = render(<WatchlistView data={null}/>);
    expect(screen.getByRole('alert')).toBeTruthy();
    view.rerender(<WatchlistView data={{observations:[],snapshots:[]}}/>);
    expect(screen.getByText(/No captured research observations/)).toBeTruthy();
    view.rerender(<WatchlistView data={{observations:[{...event('missing'),record:{}}],snapshots:[]}}/>);
    expect(screen.getAllByText('Unknown').length).toBeGreaterThan(0);
  });
  it('handles loading, rejected API, and malformed successful API response', async () => {
    vi.mocked(api.getResearchWatchlist).mockRejectedValueOnce(new Error('TEST offline'));
    const view = render(<ResearchWatchlist/>);
    expect(screen.getByRole('status')).toBeTruthy();
    expect(await screen.findByRole('alert')).toBeTruthy();
    view.unmount();
    vi.mocked(api.getResearchWatchlist).mockResolvedValueOnce(null);
    render(<ResearchWatchlist/>);
    expect(await screen.findByRole('alert')).toBeTruthy();
  });
  it('groups contracts without discarding old incomplete event history', () => {
    render(<WatchlistView data={data}/>);
    expect(screen.getAllByTestId('tracking-contract')).toHaveLength(1);
    expect(screen.getByText('TEST · 2026-09-25 · $100 · Call')).toBeTruthy();
    expect(screen.getByText('TEST-a')).toBeTruthy();
    expect(screen.getByText('TEST-b')).toBeTruthy();
    expect(screen.getByText(/Prioritization not yet validated/)).toBeTruthy();
    expect(screen.getAllByText('50001').length).toBeGreaterThan(0);
  });
});
