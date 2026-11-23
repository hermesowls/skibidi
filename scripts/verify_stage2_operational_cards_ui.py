#!/usr/bin/env python3
"""Mounted React contract replay of exact authenticated backend responses, not browser E2E."""
from pathlib import Path
import json, subprocess, tempfile, sys
R=Path(__file__).resolve().parents[1]

def main():
    snapshots=json.loads(Path(sys.argv[1]).read_text())
    prelude=(R/'tests/step4_temporal_render.cjs').read_text().split('async function run(){',1)[0]
    # Mount only the profile component; import real transport and its auth helpers.
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
 await fixture('operational_history_after_profile_edit',base(),async()=>{
  assert.ok(history(),'operational history missing');const before=history().textContent;
  assert.match(before,/Original TEST/);assert.ok(before.includes(snapshots.first.version_id));
  assert.match(before,/OTM cap: Unlimited/);assert.match(before,/110%/);assert.match(before,/user_chosen_research/);
  await choose(snapshots.first.version_id);await input('Profile name','Edited capped');await input('Maximum OTM fraction','0.1');await click('Save new version');
  assert.equal(posts.length,1);assert.equal(history().textContent,before);
  await choose(snapshots.clone.version_id);assert.equal(history().textContent,before);
 });
 // Legacy/malformed missing observations are deliberately not backfilled.
 const original=snapshots.history.flows[0].research_candidates;
 snapshots.history.flows[0].research_candidates=[{decision_id:'legacy',baseline_status:'REJECTED',baseline_reasons:['size:rejected']}];
 await fixture('legacy_rejected_unknown_history',base(),async()=>{const t=history().textContent;assert.match(t,/REJECTED/);assert.match(t,/size:rejected/);assert.match(t,/Profile: Unknown/);assert.match(t,/OTM cap: Unknown/);assert.doesNotMatch(t,/Unlimited|Original TEST/);});
 snapshots.history.flows[0].research_candidates=original;
 assert.deepEqual(violations,[]);assert.deepEqual(denials,[]);console.log(JSON.stringify({rendered_tests:identities.length,identities,audit_denials:denials}));
}
run().catch(e=>{console.error(e);process.exitCode=1;});
'''.replace('SNAPSHOTS',json.dumps(snapshots))
    with tempfile.TemporaryDirectory(prefix='astra-stage2-ui-') as name:
        t=Path(name).resolve(); node=Path('/Users/admin/.local/bin/node').resolve()
        policy=t/'guard.sb'
        policy.write_text('(version 1)\n(allow default)\n(deny network*)\n(deny file-write*)\n(allow file-write* (literal "/dev/null"))\n(deny file-read* (subpath "/Users/admin/.hermes") (regex #"/\\.env($|\\.)") (regex #"\\.(db|sqlite|sqlite3)$"))\n(deny process-exec)\n(allow process-exec (literal '+json.dumps(str(node))+'))\n')
        harness=t/'render.cjs';harness.write_text(prelude+cases)
        env=dict(HOME=str(t),HERMES_HOME=str(t/'profile'),TMPDIR=str(t),PATH='/usr/bin:/bin',TZ='UTC',LANG='C.UTF-8')
        result=subprocess.run(['/usr/bin/sandbox-exec','-f',str(policy),str(node),str(harness)],cwd=t,env=env,capture_output=True,text=True,timeout=60)
        Path(sys.argv[2]).write_text(result.stdout+result.stderr);print(result.stdout+result.stderr);return result.returncode
if __name__=='__main__':sys.exit(main())
