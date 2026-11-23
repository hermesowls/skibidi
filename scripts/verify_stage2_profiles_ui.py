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
    prelude=prelude.replace("const Page=req(R+'/web/src/pages/NotableFlowPage.tsx').default;", "const {api,fetchJSON}=req(R+'/web/src/lib/api.ts'); const Page=req(R+'/web/src/pages/ResearchProfiles.tsx').default;")
    cases=r'''
const snapshots=SNAPSHOTS;
let index=0, posts=[], transportViolations=[];
global.fetch=async(url,init)=>{
 try {
 const row=snapshots.recordings[index++];assert.ok(row,'unexpected external fetch');
 assert.equal(url,row.url);assert.equal(init.method??'GET',row.method);
 assert.equal(init.credentials,'include');
 assert.equal(init.headers.get('X-Hermes-Session-Token'),index===1?null:'TEST-mounted-token');
 const body=init.body===undefined?null:JSON.parse(init.body);assert.deepEqual(body,row.body);
 if(row.method==='POST'){assert.equal(init.headers.get('Content-Type'),'application/json');posts.push(body);}
 return new Response(JSON.stringify(row.response),{status:row.status,headers:{'Content-Type':'application/json'}});
 } catch(error){transportViolations.push(String(error));throw error;}
};
async function input(label,value){const el=document.querySelector('[aria-label="'+label+'"]');assert.ok(el,label);await act(async()=>{const setter=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;setter.call(el,value);el.dispatchEvent(new window.Event('input',{bubbles:true}));});}
async function choose(value){await act(async()=>{const el=document.querySelector('[aria-label="Research profile version"]');el.value=value;el.dispatchEvent(new window.Event('change',{bubbles:true}));});}
async function run(){
 await assert.rejects(fetchJSON('/api/analyst-trader/research-profiles',undefined,{allowUnauthorized:true}),/401/);
 window.__HERMES_SESSION_TOKEN__='TEST-mounted-token';
 await fixture('persisted_profile_contract_replay',base(),async()=>{
  assert.match(text(),/TEST research profiles/);
  await input('Profile name','Default TEST');await click('Create profile');
  assert.equal(posts[0].name,'Default TEST');assert.equal(posts[0].changes.max_otm_fraction,null);
  assert.match(text(),/Uncapped/);assert.match(text(),/no delivery or execution permission/);
  await choose(snapshots.first.version_id);
  await click('Preview TEST evidence');assert.match(text(),/QUALIFIED/);
  assert.match(document.querySelector('[aria-label="TEST preview results"]').textContent,new RegExp(snapshots.first.version_id));
  await input('Profile name','Renamed capped');await input('Maximum OTM fraction','0.1');await click('Save new version');
  assert.equal(posts[2].base_version,snapshots.first.version_id);assert.equal(posts[2].changes.max_otm_fraction,.1);
  assert.match(document.querySelector('[aria-label="TEST preview results"]').textContent,new RegExp(snapshots.first.version_id));
  assert.match(document.querySelector('[aria-label="TEST preview results"]').textContent,/TEST preview: Default TEST/);
  assert.doesNotMatch(document.querySelector('[aria-label="TEST preview results"]').textContent,/Renamed capped/);
  await click('Preview TEST evidence');assert.match(text(),/REJECTED/);assert.match(text(),/otm:rejected/);
  assert.match(document.querySelector('[aria-label="TEST preview results"]').textContent,/TEST preview: Renamed capped/);
  await choose(snapshots.first.version_id);assert.match(text(),/Uncapped/);
  await input('Profile name','Clone');await click('Clone profile');
  assert.equal(posts[4].base_version,snapshots.first.version_id);assert.deepEqual(posts[4].changes,{});
  await input('Profile name','Bad');await input('Maximum OTM fraction','0');await click('Save new version');
  assert.match(text(),/Profile save failed — prior immutable version unchanged/);
  assert.match(text(),new RegExp(snapshots.clone.version_id));
  await choose(snapshots.first.version_id);assert.match(text(),/Uncapped/);
  assert.equal(index,snapshots.recordings.length);assert.deepEqual(transportViolations,[]);
 });
 assert.deepEqual(denials,[]);console.log(JSON.stringify({rendered_tests:identities.length,identities,audit_denials:denials}));
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
