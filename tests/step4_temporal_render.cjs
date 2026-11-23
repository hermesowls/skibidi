// Installed-only React DOM fixture runner; no application transport is imported.
const fs = require('node:fs');
const Module = require('node:module');
const path = require('node:path');
const R = '/Users/admin/repos/hermes-agent';
const req = Module.createRequire(R + '/package.json');
const denials = [];
const deny = name => () => { denials.push(name); throw Error('OFFLINE GUARD: ' + name); };
for (const [name, methods] of Object.entries({'node:net':['connect','createConnection','createServer'],'node:http':['request','get','createServer'],'node:https':['request','get','createServer'],'node:dns':['lookup','resolve'],'node:child_process':['spawn','exec','execFile','fork','spawnSync','execSync','execFileSync']})) {
 const mod = require(name); for (const method of methods) mod[method] = deny(name+'.'+method);
}
global.fetch = deny('fetch');
for (const method of ['writeFileSync','writeFile','mkdirSync','mkdir','renameSync','rename','unlinkSync','unlink','createWriteStream']) fs[method] = deny('fs.'+method);
const originalRead = fs.readFileSync;
fs.readFileSync = function(file,...rest) {
 const name=String(file);
 if (name.includes('/.hermes/') || /(^|\/)\.env($|\.)|\.(db|sqlite|sqlite3)$/.test(name)) return deny('private read')();
 return originalRead.call(this,file,...rest);
};
const {JSDOM} = req('jsdom');
const dom = new JSDOM('<!doctype html><html><body><div id="root"></div></body></html>', {url:'http://fixture.invalid/'});
global.window=dom.window; global.document=dom.window.document; global.navigator=dom.window.navigator;
global.HTMLElement=dom.window.HTMLElement; global.IS_REACT_ACT_ENVIRONMENT=true;
global.setInterval=()=>1; global.clearInterval=()=>{};
const realNow = Date.now;
let clock = realNow(), nextTimer = 0;
const timers = new Map();
Date.now = () => clock;
global.setTimeout = (fn, delay=0) => { const id=++nextTimer; timers.set(id,{fn,at:clock+delay}); return id; };
global.clearTimeout = id => timers.delete(id);
async function advance(ms) {
 clock += ms;
 await act(async()=>{ for (const [id,t] of [...timers]) if(t.at<=clock){timers.delete(id);t.fn();} });
}
const ts=req('typescript');
const oldLoad=Module._load;
let responses={};
const api={getPortfolioSummary:async()=>{if(responses.wait)return new Promise(()=>{});if(responses.error)throw Error('fixture failed refresh');return responses.portfolio;},getRecordedStrategies:async()=>{if(responses.strategyError)throw Error('strategies failed');return responses.strategies;},getNotableFlows:async()=>{if(responses.flowError)throw Error('flow failed');return {ok:true,flows:responses.flows??[]};},getLiveQuotes:async()=>{if(responses.quoteWait)return new Promise(()=>{});if(responses.quoteError)throw Error('quotes failed');return {ok:true,quotes:responses.quotes??{}};}};
Module._load=function(name,parent,isMain){if(name==='@/lib/api')return {api}; if(name.startsWith('@/'))name=R+'/web/src/'+name.slice(2);return oldLoad.call(this,name,parent,isMain);};
Module._extensions['.tsx']=Module._extensions['.ts']=function(mod,filename){const code=originalRead(process.argv[2] && filename===R+'/web/src/pages/NotableFlowPage.tsx' ? process.argv[2] : filename,'utf8');const result=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022}});mod._compile(result.outputText,filename);};
const React=req('react'); const {act}=React; const {createRoot}=req('react-dom/client'); const {MemoryRouter}=req('react-router');
const Page=req(R+'/web/src/pages/NotableFlowPage.tsx').default;
const assert=require('node:assert/strict');
async function click(text){const b=[...document.querySelectorAll('button')].find(b=>b.textContent.includes(text));assert.ok(b,'button '+text);await act(async()=>{b.dispatchEvent(new window.MouseEvent('click',{bubbles:true}));});}
const identities=[];
const base=()=>({portfolio:{ok:true,portfolios:{autonomous_ai:{cash_balance:null,total_value:null,realized_pnl:null,active_positions_count:null,win_rate_pct:null,closed_positions_count:0,open_positions:[],as_of:'2026-09-01T00:00:00Z'}}},strategies:{ok:true,strategies:[],statistics:{as_of:'2026-09-01T00:00:00Z',by_archetype:{DREAM:{closed_count:0,open_count:0,excluded_count:0,unknown_cost_count:0,gross_win_rate_pct:null}}}}});
const flow={flow_id:'fixture',source:'notable_flow',ticker:'TEST',asset_type:'equity',strike:100,call_put:'CALL',expiration:'2099-12-31',dte:90,premium_usd:200000,premium_raw:'200K',trade_timestamp:'2026-09-01T00:00:00Z'};
const text=()=>document.body.textContent;
async function fixture(name, data, check){responses=data;const root=createRoot(document.getElementById('root'));await act(async()=>root.render(React.createElement(MemoryRouter,null,React.createElement(Page))));try{await check();identities.push(name);}finally{await act(async()=>root.unmount());assert.equal(timers.size,0,'expiry timer cleaned up');clock=realNow();}}
async function run(){
 await fixture('null_portfolio_unknown',base(),async()=>{await click('Validat');assert.match(text(),/Unknown/);assert.doesNotMatch(text(),/\$0\.00/);});
 let data=base();Object.assign(data.portfolio.portfolios.autonomous_ai,{cash_balance:0,total_value:0,realized_pnl:0,active_positions_count:0});
 await fixture('observed_zero_not_unknown',data,async()=>{await click('Validat');assert.match(text(),/\$0\.00/);assert.match(text(),/0 Open/);});
 data=base();data.wait=true;
 await fixture('loading_not_zero',data,async()=>{await click('Validat');assert.match(text(),/Loading portfolio/);assert.doesNotMatch(text(),/\$0\.00/);});
 data=base();data.portfolio.portfolios.autonomous_ai.total_value=12345;
 await fixture('failed_refresh_clears_prior_success',data,async()=>{await click('Validat');assert.match(text(),/12,345\.00/);responses.error=true;await click('Refresh Positions');assert.match(text(),/Portfolio refresh failed/);assert.doesNotMatch(text(),/12,345\.00/);});
 await fixture('empty_strategy_insufficient',base(),async()=>{await click('Strategy Alpha');assert.match(text(),/Insufficient data/);assert.match(text(),/0 closed holdings/);assert.doesNotMatch(text(),/100\.0% Gross Win Rate/);});
 data=base();data.strategies.strategies=[{trace_id:'TEST-trim',strategy_name:'DREAM',realized_pnl:100,outcome_label:'WIN'}];data.strategies.statistics.by_archetype.DREAM.open_count=1;
 await fixture('profitable_trim_not_closed_uses_backend',data,async()=>{await click('Strategy Alpha');assert.match(text(),/0 closed holdings; 1 open/);assert.match(text(),/Insufficient data/);});
 data=base();Object.assign(data.strategies.statistics.by_archetype.DREAM,{closed_count:2,gross_win_rate_pct:50});
 await fixture('backend_complete_history_not_visible_events',data,async()=>{await click('Strategy Alpha');assert.match(text(),/50\.0% Gross Win Rate/);assert.match(text(),/2 closed holdings/);});
 data=base();data.strategyError=true;data.portfolio.portfolios.autonomous_ai.cash_balance=42;
 await fixture('independent_sibling_error',data,async()=>{await click('Validat');assert.match(text(),/\$42\.00/);assert.match(text(),/Strategy refresh failed/);});
 for(const [name,q,pattern] of [
 ['fresh_quote',{price:100,change_pct:null,source:'fixture_observed',as_of:new Date(clock).toISOString()},/Observed \$100\.00/],
 ['stale_quote',{price:100,change_pct:0,source:'fixture_observed',as_of:'2000-01-01T00:00:00Z'},/Stale quotes/],
 ['missing_quote',{},/Quotes unknown/],
 ['observed_zero_quote',{price:0,change_pct:0,source:'fixture_observed',as_of:new Date(clock).toISOString()},/Observed \$0\.00/],
 ]){data=base();data.flows=[flow];data.quotes={TEST:q};await fixture(name,data,async()=>{assert.match(text(),pattern);assert.match(text(),/side unknown/);assert.match(text(),/Estimated mark:/);assert.match(text(),/nonexecutable/);assert.doesNotMatch(text(),/BIG ASK|Live Mark/);if(name==='stale_quote'||name==='missing_quote')assert.match(text(),/Estimated mark: Unknown/);});}
 data=base();data.flows=[flow];data.quoteError=true;
 await fixture('quote_error_unknown',data,async()=>{assert.match(text(),/Quote refresh failed/);assert.match(text(),/Estimated mark: Unknown/);});
 data=base();data.flows=[flow];data.quotes={TEST:{price:101,change_pct:0,source:'TEST-observed',as_of:new Date(clock).toISOString()}};
 await fixture('failed_quote_refresh_removes_previous_quote',data,async()=>{assert.match(text(),/Observed \$101\.00/);responses.quoteError=true;await act(async()=>document.querySelector('button[title="Refresh Notable Flow"]').dispatchEvent(new window.MouseEvent('click',{bubbles:true})));assert.match(text(),/Quote refresh failed/);assert.doesNotMatch(text(),/Observed \$101\.00/);});
 data=base();data.portfolio.portfolios.autonomous_ai.open_positions=[{holding_id:'TEST-share',ticker:'TEST',asset_type:'stock',quantity:2,average_cost:10,current_price:11,last_price_updated_at:'2000-01-01T00:00:00Z'}];
 await fixture('underlying_mode_and_stale_nonexecutable_mark',data,async()=>{await click('Validat');assert.match(text(),/UNDERLYING/);assert.match(text(),/Paper shares/);assert.match(text(),/2 shares/);assert.match(text(),/stale · nonexecutable/);assert.match(text(),/stale snapshot/);});
 data=base();data.portfolio.portfolios.autonomous_ai.recent_closed_positions=[{holding_id:'TEST-closed',ticker:'TEST',realized_pnl:0}];
 await fixture('closed_unknown_evidence_not_win',data,async()=>{await click('Validat');assert.match(text(),/Unknown \/ excluded/);assert.doesNotMatch(text(),/GROSS WIN/);});
 data=base();data.strategies.statistics.by_cohort={paper_test:{holding_count:2,excluded_count:1}};
 await fixture('cohorts_explicit_not_live_qualification',data,async()=>{await click('Strategy Alpha');assert.match(text(),/paper_test: 2 holdings, 1 excluded/);assert.match(text(),/not live qualification/);});
 data=base();data.flowError=true;
 await fixture('flow_error_visible',data,async()=>assert.match(text(),/Flow refresh failed/));
 data=base();data.flows=[flow];data.quotes={TEST:{price:101,source:'TEST',as_of:new Date(clock).toISOString()}};
 await fixture('hung_refresh_no_current_estimate',data,async()=>{
  assert.match(text(),/Observed \$101/);responses.quoteWait=true;
  await act(async()=>document.querySelector('button[title="Refresh Notable Flow"]').dispatchEvent(new window.MouseEvent('click',{bubbles:true})));
  await advance(120000);assert.match(text(),/Estimated mark: Unknown/);assert.doesNotMatch(text(),/Observed \$101/);assert.match(text(),/nonexecutable/);
 });
 for (const mode of ['expiry_timer_without_response','forced_rerender_after_120s','zero_quote_expires']) {
  data=base();data.flows=[flow];const price=mode==='zero_quote_expires'?0:101;
  data.quotes={TEST:{price,change_pct:0,source:'TEST-observed',as_of:new Date(clock).toISOString()}};
  await fixture(mode,data,async()=>{
   assert.match(text(),new RegExp('Observed \\$'+price+'\\.00'));
   if(mode==='forced_rerender_after_120s'){clock+=120000;await click('Strategy Alpha');await click('Tape');}
   else {await advance(60000);assert.match(text(),/Observed/);await advance(60000);}
   assert.match(text(),/Estimated mark: Unknown/);assert.match(text(),/Stale quotes/);
   assert.doesNotMatch(text(),/Observed \$(101|0)\.00/);assert.match(text(),/nonexecutable/);
  });
 }
 for(const [name,stamp] of [['missing',undefined],['naive','2026-09-01T00:00:00'],['malformed','not-a-date'],['future','2099-01-01T00:00:00Z'],['calendar','2026-02-30T00:00:00Z']]) {
  data=base();data.flows=[flow];data.quotes={TEST:{price:101,source:'TEST',as_of:stamp}};
  await fixture('quote_timestamp_'+name,data,async()=>{assert.match(text(),/Estimated mark: Unknown/);assert.doesNotMatch(text(),/Observed \$101/);});
  data=base();data.portfolio.portfolios.autonomous_ai.total_value=100123;
  data.portfolio.portfolios.autonomous_ai.open_positions=[{holding_id:'invalid',ticker:'TEST',current_price:2,last_price_updated_at:stamp}];
  await fixture('defensive_mark_timestamp_'+name,data,async()=>{await click('Validat');assert.match(text(),/Estimated Unknown/);assert.doesNotMatch(text(),/\$100,123\.00|not-a-date/);});
 }
 data=base();data.portfolio=JSON.parse(originalRead(R+'/tests/fixtures/step4-invalid-mark-response.json','utf8'));
 await fixture('actual_api_invalid_mark_response',data,async()=>{await click('Validat');assert.match(text(),/Total Portfolio ValueUnknown/);assert.match(text(),/Estimated Unknown/);assert.match(text(),/nonexecutable/);});
 assert.equal(new Set(identities).size,identities.length);
 assert.deepEqual(denials,[]);
 console.log(JSON.stringify({rendered_tests:identities.length,identities,audit_denials:denials}));
}
run().catch(e=>{console.error(e);console.error(JSON.stringify({completed:identities,audit_denials:denials}));process.exitCode=1;});
