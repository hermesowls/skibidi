// @vitest-environment jsdom
import {it, expect, vi} from 'vitest';
import {render,screen,fireEvent,cleanup} from '@testing-library/react';
import {MemoryRouter} from 'react-router';
vi.mock('@/lib/api',() => ({api:new Proxy({}, {get:() => vi.fn().mockResolvedValue({flows:[],profiles:[],holdings:[],strategies:[]})})}));
vi.mock('./ResearchProfiles',() => ({default:() => <section>Profile editor fixture</section>}));
vi.mock('./ResearchWatchlist',() => ({default:() => <section>Captured cohort fixture</section>}));
import NotableFlowPage from './NotableFlowPage';
it('opens Tracking independently while preserving the original tabs',async () => {
  render(<MemoryRouter><NotableFlowPage/></MemoryRouter>);
  expect(screen.queryByText('Captured cohort fixture')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Tracking'}));
  expect(screen.getByText('Captured cohort fixture')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Strategy Validator (Paper Portfolio)'})).toBeTruthy();
  expect(screen.getByRole('button',{name:'Strategy Alpha & Learnings'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Whale Flow Tape'}));
  expect(screen.queryByText('Captured cohort fixture')).toBeNull();
  cleanup();
});
