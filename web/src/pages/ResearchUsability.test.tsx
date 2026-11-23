// @vitest-environment jsdom
import { it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
vi.mock('@/lib/api', () => ({api:{getResearchWatchlist:vi.fn()}}));
import ResearchWatchlist from './ResearchWatchlist';
import { api } from '@/lib/api';
it('renders TEST lifecycle, descriptive outcomes and heuristic priority through existing API', async () => {
  vi.mocked(api.getResearchWatchlist).mockResolvedValueOnce({mode:'TEST',observations:[],snapshots:[],research_requests:[{ticket_id:'TEST-ticket',setup_id:'TEST-setup',ticker:'AAOI',state:'analyzed',timeframe:'swing'}],outcome_research:{adaptive_ranking:{status:'INSUFFICIENT_SAMPLE'},candidates:[{event_id:'TEST-event',contract:'AAOI260925C00100000',status:'COMPLETED',priority:{score:0,kind:'EVIDENCE_COVERAGE_HEURISTIC_NOT_LEARNED_EDGE'},outcomes:[{minutes:1,status:'COMPLETED',mark_return_pct:50}]}]}});
  render(<ResearchWatchlist/>);
  expect(await screen.findByText(/TEST-ticket/)).toBeTruthy();
  expect(screen.getByText(/analyzed/)).toBeTruthy();
  expect(screen.getByText(/INSUFFICIENT_SAMPLE/)).toBeTruthy();
  expect(screen.getByText(/Priority: 0/)).toBeTruthy();
  expect(screen.getByText(/50%/)).toBeTruthy();
});
