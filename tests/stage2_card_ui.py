#!/usr/bin/env python3
"""Mounted React contract replay of exact authenticated backend responses, not browser E2E."""
from pathlib import Path
import json, subprocess, tempfile, sys, shutil, os
R=Path(__file__).resolve().parents[1]

def main():
    evidence=Path(sys.argv[1])
    snapshots=json.loads((evidence/'operational-cards.json').read_text())
    snapshots['history']=json.loads((evidence/'malformed-history.json').read_text())
    snapshots['bounded']=json.loads((evidence/'bounded-history.json').read_text())
    snapshots['extra']=json.loads((evidence/'saturation.json').read_text())['body']
    snapshots['extra']['flows']=snapshots['extra']['flows'][:1]
    prelude=(R/'tests/step4_temporal_render.cjs').read_text().split('async function run(){',1)[0]
    prelude='\n'.join('const R = '+json.dumps(str(R))+';' if line.startswith('const R = ') else line for line in prelude.splitlines())
    # Mount the actual page with real transport and auth helpers.
    prelude='\n'.join(line for line in prelude.splitlines() if not line.startswith('const api='))+'\n'
    prelude=prelude.replace("if(name==='@/lib/api')return {api}; ", "if(name.startsWith('.') && name.endsWith('.js') && parent && fs.existsSync(path.resolve(path.dirname(parent.filename),name.slice(0,-3)+'.ts')))name=path.resolve(path.dirname(parent.filename),name.slice(0,-3)+'.ts'); ")
    prelude=prelude.replace("const Page=req(R+'/web/src/pages/NotableFlowPage.tsx').default;", "const {api,fetchJSON}=req(R+'/web/src/lib/api.ts'); const Page=req(R+'/web/src/pages/NotableFlowPage.tsx').default;")
    cases=r'''
const snapshots=SNAPSHOTS;
let posts=[], violations=[];
window.__HERMES_SESSION_TOKEN__='TEST-mounted-token';
global.fetch=async(url,init)=>{
 try {
 assert.equal(init.credentials,'include');assert.equal(init.headers.get('X-Hermes-Session-Token'),'TEST-mounted-token');
 const parsed=new URL(url,'http://fixture.invalid'); let response;
 if(parsed.pathname.endsWith('/notable-flow'))response=snapshots.history;
 else if(parsed.pathname.endsWith('/research-profiles')) {
  if(init.method==='POST'){const body=JSON.parse(init.body);assert.equal(body.base_version,snapshots.first.version_id);assert.equal(body.name,'Edited capped');posts.push(body);response=snapshots.edited;}
  else if(parsed.searchParams.has('version_id'))response=[snapshots.first,snapshots.edited,snapshots.clone].find(p=>p.version_id===parsed.searchParams.get('version_id'));
  else response={profiles:[snapshots.first,snapshots.edited,snapshots.clone]};
 } else if(parsed.pathname.endsWith('/portfolio'))response=base().portfolio;
 else if(parsed.pathname.endsWith('/strategies'))response=base().strategies;
 else if(parsed.pathname.endsWith('/live-quotes'))response={ok:true,quotes:{}};
 else throw Error('unexpected URL '+url);
 return new Response(JSON.stringify(response),{status:200,headers:{'Content-Type':'application/json'}});
 } catch(error){violations.push(String(error));throw error;}
};
async function input(label,value){await act(async()=>{const el=document.querySelector('[aria-label="'+label+'"]');Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set.call(el,value);el.dispatchEvent(new window.Event('input',{bubbles:true}));});}
async function choose(value){await act(async()=>{const el=document.querySelector('[aria-label="Research profile version"]');el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));});}
const history=()=>document.querySelector('[aria-label="Recorded research decisions"]');
async function run(){
 await fixture('actual_rejected_malformed_saved_API',base(),async()=>{const t=history().textContent;assert.match(t,/Profile: Unknown/);assert.match(t,/Reasons: Unknown/);assert.match(t,/size:rejected/);assert.match(t,/Original TEST/);});
 const good=snapshots.history.flows[0].research_candidates[0];
 snapshots.history.flows[0].research_candidates=[{...good,profile_name:{bad:1},baseline_reasons:7,enhancement_unknowns:[{}],max_otm_fraction:undefined}];
 await fixture('runtime_malformed_types',base(),async()=>{const t=history().textContent;assert.match(t,/Profile: Unknown/);assert.match(t,/Reasons: Unknown/);assert.match(t,/Unknowns: Unknown/);assert.match(t,/OTM cap: Unknown/);});
 snapshots.history=snapshots.bounded;
 await fixture('bounded_visible_source_history',base(),async()=>{const t=history().textContent;assert.match(t,/32 omitted/);assert.match(t,/visible source only/);assert.equal(history().querySelectorAll('article').length,10);});
 snapshots.history=snapshots.extra;
 await fixture('fresh_saved_objects_null_unknown',base(),async()=>{const t=history().textContent;assert.match(t,/Profile: Unknown/);assert.match(t,/Reasons: Unknown/);assert.match(t,/OTM cap: Unknown/);assert.match(t,/OTM cap: Unlimited/);assert.match(t,/6 shown of 15; 5 omitted by limits; 4 invalid/);assert.equal(history().querySelectorAll('article').length,6);});
 const extraGood=snapshots.history.flows[0].research_candidates[0];
 snapshots.history.flows[0].research_candidates=[{...extraGood,profile_name:{bad:1},decision_id:{bad:1},policy_version:[],policy_hash:{},origin:{},baseline_status:{},baseline_reasons:{bad:1},enhancement_unknowns:[{}],max_otm_fraction:undefined,filter_provenance:{bad:{}}}];
 await fixture('fresh_direct_reasons_objects',base(),async()=>{const t=history().textContent;for(const label of ['Profile','Decision','Policy','Reasons','Unknowns','OTM cap','Policy provenance','Filter provenance']) assert.ok(t.includes(label+': Unknown'),label);});
 assert.deepEqual(denials,[]);assert.deepEqual(violations,[]);console.log(JSON.stringify({positive_mounted:identities,audit_denials:denials}));
}
run().catch(e=>{console.error(e);process.exitCode=1;});
'''.replace('SNAPSHOTS',json.dumps(snapshots))
    with tempfile.TemporaryDirectory(prefix='astra-stage2-ui-') as name:
        t=Path(name).resolve(); node=Path(shutil.which('node') or sys.exit('Installed Node required')).resolve()
        policy=t/'guard.sb'
        policy.write_text('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (literal "/dev/null"))\n(deny file-read* (subpath '+json.dumps(str(Path.home()/'.hermes'))+') (regex #"/\\.env($|\\.)") (regex #"\\.(db|sqlite|sqlite3)$"))\n(deny process-exec)\n(allow process-exec (literal '+json.dumps(str(node))+'))\n')
        harness=t/'render.cjs';harness.write_text(prelude+cases)
        env=dict(HOME=str(t),HERMES_HOME=str(t/'profile'),TMPDIR=str(t),PATH='/usr/bin:/bin',TZ='UTC',LANG='C.UTF-8')
        result=subprocess.run(['/usr/bin/sandbox-exec','-f',str(policy),str(node),str(harness)],cwd=t,env=env,capture_output=True,text=True,timeout=60)
        Path(sys.argv[2]).write_text(result.stdout+result.stderr);print(result.stdout+result.stderr);return result.returncode
if __name__=='__main__':sys.exit(main())
