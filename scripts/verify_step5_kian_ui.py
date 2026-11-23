#!/usr/bin/env python3
"""Mount unchanged React page with exact connected authenticated API responses.

Installed tools only. Uses inspected Step4 DOM guard plus macOS deny-network,
deny-write, deny-private-read sandbox. No listener, install or served output.
"""
from pathlib import Path
import json,subprocess,tempfile,sys
R=Path(__file__).resolve().parents[1]

def main():
    source=Path(sys.argv[1]); output=Path(sys.argv[2])
    snapshots={key:json.loads((source/f'TEST-api-{key}.json').read_text()) for key in ('0.75','0.25')}
    prelude=(R/'tests/step4_temporal_render.cjs').read_text().split('async function run(){',1)[0]
    cases='''
async function run(){
 for(const [name,data] of Object.entries(snapshots)){
  await fixture('connected_exact_api_'+name,data,async()=>{
   await click('Validat');
   const net=data.strategies.statistics.total.net_realized_pnl;
   assert.equal(data.portfolio.portfolios.autonomous_ai.net_realized_pnl,net);
   assert.ok(text().includes('net $'+net.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})),text());
   assert.match(text(),/not live execution/);
   responses.error=true;await click('Refresh Positions');
   assert.match(text(),/Portfolio refresh failed/);
  });
 }
 assert.equal(new Set(identities).size,identities.length);assert.deepEqual(denials,[]);
 console.log(JSON.stringify({rendered_tests:identities.length,identities,audit_denials:denials}));
}
run().catch(e=>{console.error(e);console.error(JSON.stringify({completed:identities,audit_denials:denials}));process.exitCode=1;});
'''
    with tempfile.TemporaryDirectory(prefix='astra-step5-ui-') as name:
        t=Path(name).resolve();node=Path('/Users/admin/.local/bin/node').resolve()
        policy=t/'guard.sb'
        policy.write_text('''(version 1)
(allow default)
(deny network*)
(deny file-write*)
(allow file-write* (literal "/dev/null"))
(deny file-read* (subpath "/Users/admin/.hermes") (regex #"/\\.env($|\\.)") (regex #"\\.(db|sqlite|sqlite3)$"))
(deny process-exec)
(allow process-exec (literal %s))
''' % json.dumps(str(node)))
        harness=t/'render.cjs';harness.write_text(prelude+'\nconst snapshots='+json.dumps(snapshots)+';\n'+cases)
        env=dict(HOME=str(t),HERMES_HOME=str(t/'profile'),TMPDIR=str(t),PATH='/usr/bin:/bin',TZ='UTC',LANG='C.UTF-8')
        result=subprocess.run(['/usr/bin/sandbox-exec','-f',str(policy),str(node),str(harness)],cwd=t,env=env,capture_output=True,text=True,timeout=120)
        output.write_text(result.stdout+result.stderr)
        print(result.stdout+result.stderr);return result.returncode

if __name__=='__main__':sys.exit(main())
