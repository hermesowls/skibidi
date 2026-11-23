// Appended to the unchanged mounted harness prelude by the evidence assembler.
// `snapshots` is unmodified JSON emitted by test_step4_mark_contract.
async function run(){
 const make=name=>({...base(),portfolio:structuredClone(snapshots[name])});
 const portfolio=data=>data.portfolio.portfolios.autonomous_ai;
 const unknown=()=>{assert.match(text(),/Estimated Unknown/);assert.doesNotMatch(text(),/Estimated \$[\d,]+\.\d\d/);};
 await fixture('actual_api_hour24_rejected',make('hour24'),async()=>{
  await click('Validat');assert.match(text(),/Total Portfolio ValueUnknown/);unknown();
 });
 let data=make('microsecond_future');
 clock=Date.parse(portfolio(data).as_of)+120000;
 await fixture('actual_api_microsecond_future_later_render_stays_unknown',data,async()=>{
  await click('Validat');unknown();
  await advance(120000);await click('Strategy Alpha');await click('Validat');unknown();
  responses.portfolio=structuredClone(snapshots.recovery);
  await click('Refresh Positions');assert.match(text(),/Estimated \$0\.00/);
  responses.portfolio=structuredClone(snapshots.microsecond_future);
  await click('Refresh Positions');unknown();
 });
 for(const name of ['valid_zero','valid_stale']){
  data=make(name);clock=Date.parse(portfolio(data).as_of)+1000;
  await fixture('actual_api_'+name,data,async()=>{
   await click('Validat');assert.match(text(),/Estimated \$0\.00/);
   assert.match(text(),/nonexecutable/);
   if(name==='valid_stale')assert.match(text(),/stale · nonexecutable/);
  });
 }
 // Negative transport-corruption probes derived from a real accepted response;
 // no hand-authored positive business economics or accepted outcomes.
 const corruptions={
  raw_nonnull_validated_unknown:p=>{p.statistics.holdings[0].mark_freshness='unknown';p.statistics.holdings[0].estimated_market_value=null;},
  missing_statistics:p=>{delete p.statistics;},
  missing_holding_identity:p=>{delete p.open_positions[0].holding_id;},
  missing_validated_identity:p=>{delete p.statistics.holdings[0].holding_id;},
  wrong_holding_identity:p=>{p.statistics.holdings[0].holding_id+='-wrong';},
  duplicate_validated_identity:p=>{p.statistics.holdings.push(structuredClone(p.statistics.holdings[0]));},
  duplicate_raw_identity:p=>{p.open_positions.push(structuredClone(p.open_positions[0]));},
  old_validated_new_snapshot:p=>{p.as_of=snapshots.recovery.portfolios.autonomous_ai.as_of;},
  old_validated_new_raw_timestamp:p=>{p.open_positions[0].last_price_updated_at=snapshots.recovery.portfolios.autonomous_ai.open_positions[0].last_price_updated_at;},
  old_validated_new_raw_value:p=>{p.open_positions[0].market_value=400;},
  old_validated_new_raw_quantity:p=>{p.open_positions[0].quantity+=1;},
  wrong_portfolio:p=>{p.statistics.holdings[0].portfolio_id='wrong';},
  wrong_mode:p=>{p.open_positions[0].asset_type='stock';},
  wrong_status:p=>{p.statistics.holdings[0].holding_status='CLOSED';},
 };
 for(const [name,mutate] of Object.entries(corruptions)){
  data=make('valid_zero');mutate(portfolio(data));
  // A separate successful strategies response must never supply the row mark.
  data.strategies.statistics=structuredClone(snapshots.valid_zero.portfolios.autonomous_ai.statistics);
  await fixture(name,data,async()=>{await click('Validat');unknown();assert.match(text(),/Total Portfolio ValueUnknown/);});
 }
 for(const [name,stamp] of [['hour24','2026-09-01T24:00:00Z'],['hour25','2026-09-01T25:00:00Z'],['minute60','2026-09-02T00:60:00Z'],['second60','2026-09-02T00:00:60Z'],['offset_hour24','2026-09-02T00:00:00+24:00'],['offset_minute60','2026-09-02T00:00:00+00:60']]){
  data=base();data.flows=[flow];data.quotes={TEST:{price:101,source:'TEST',as_of:stamp}};
  clock=Date.parse('2026-09-02T00:00:01Z');
  await fixture('quote_range_'+name,data,async()=>{assert.match(text(),/Estimated mark: Unknown/);assert.doesNotMatch(text(),/Observed \$101/);});
 }
 assert.equal(new Set(identities).size,identities.length);
 assert.deepEqual(denials,[]);
 console.log(JSON.stringify({rendered_tests:identities.length,identities,audit_denials:denials}));
}
run().catch(e=>{console.error(e);console.error(JSON.stringify({completed:identities,audit_denials:denials}));process.exitCode=1;});
