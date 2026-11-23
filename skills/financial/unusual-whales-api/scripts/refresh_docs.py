#!/usr/bin/env python3
"""Public documentation only. No authentication, market-data calls or installs."""
import argparse, collections, datetime, hashlib, json, pathlib, re, urllib.request
import yaml
ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = 'https://api.unusualwhales.com/docs/openapi.yaml'
DOCS = 'https://api.unusualwhales.com/docs/'
METHODS = {'get','put','post','delete','patch','head','options','trace'}
def dump(x):
    return json.dumps(x, indent=2, ensure_ascii=False, default=str)+'\n'
def generate(raw, retrieved_at, docs_status):
    spec = yaml.safe_load(raw)
    refs, cycles = set(), set()
    def resolve(x, stack=()):
        if isinstance(x,list): return [resolve(v,stack) for v in x]
        if not isinstance(x,dict): return x
        if '$ref' in x:
            ref=x['$ref']; refs.add(ref)
            if not ref.startswith('#/'): raise ValueError('External reference requires explicit retrieval: '+ref)
            target=spec
            for part in ref[2:].split('/'): target=target[part.replace('~1','/').replace('~0','~')]
            if ref in stack:
                cycles.add(ref); return dict(x)
            out=resolve(target,stack+(ref,))
            if isinstance(out,dict): out={**out,**{k:resolve(v,stack) for k,v in x.items() if k!='$ref'}}
            return out
        return {k:resolve(v,stack) for k,v in x.items()}
    operations=[]; source_keys=[]
    for path,item in spec['paths'].items():
        item=resolve(item)
        for method,op in item.items():
            if method.lower() not in METHODS: continue
            key=method.upper()+' '+path; source_keys.append(key)
            params={}
            for p in item.get('parameters',[])+op.get('parameters',[]): params[(p['in'],p['name'])]=p
            operation=dict(op); operation['parameters']=list(params.values())
            operation['security']=op.get('security',spec.get('security',[]))
            operation['servers']=op.get('servers',item.get('servers',spec.get('servers',[])))
            operations.append({'key':key,'method':method.upper(),'path':path,'transport':'websocket-documentation' if 'websocket' in op.get('tags',[]) else 'http-rest','operation':operation})
    # Validate every reference in the entire source, even unreferenced components.
    resolve(spec)
    assert len(source_keys)==len(set(source_keys))
    assert set(source_keys)=={o['key'] for o in operations}
    groups=collections.defaultdict(list)
    for op in operations: groups[(op['operation'].get('tags') or ['untagged'])[0]].append(op)
    files={'references/openapi.yaml':raw.decode('utf-8')}
    manifest={'source_url':SOURCE,'starting_docs_url':DOCS+'#/', 'retrieved_at_utc':retrieved_at,'starting_docs_http_status':docs_status,'source_sha256':hashlib.sha256(raw).hexdigest(),'source_bytes':len(raw),'openapi_version':spec.get('openapi'),'info_version':spec.get('info',{}).get('version'),'path_count':len(spec['paths']),'http_operation_count':len(operations),'http_rest_operation_count':sum(o['transport']=='http-rest' for o in operations),'websocket_documentation_operation_count':sum(o['transport']=='websocket-documentation' for o in operations),'unique_operation_keys':len(set(source_keys)),'schema_count':len(spec.get('components',{}).get('schemas',{})),'resolved_unique_ref_count':len(refs),'recursive_refs_preserved':sorted(cycles),'category_count':len(groups),'category_counts':{k:len(v) for k,v in sorted(groups.items())},'live_read_tested_operations':0,'mcp_wrapper_count_in_build_session':128,'limitations':['Documentation validation only; no live endpoint calls.','Websocket-tagged HTTP documentation entries are counted separately, not presented as REST data routes.','Undocumented cursor boundary inclusivity, tie ordering and stable snapshot guarantees remain unknown.','Spec examples are documentation examples, not observed market data.','Response schemas and entitlement/rate behavior may be incomplete; preserve original source and do not invent missing semantics.']}
    inv={'manifest':manifest,'security_schemes':resolve(spec.get('components',{}).get('securitySchemes',{})),'operations':operations}
    files['references/inventory.json']=dump(inv)
    files['references/manifest.json']=dump(manifest)
    files['references/source-context.md']='# Official source context\n\n'+spec.get('info',{}).get('description','')+'\n\n## Servers and security schemes\n```json\n'+dump({'servers':spec.get('servers'),'security':spec.get('security'),'schemes':inv['security_schemes']})+'```\n'
    catalog=['# Complete operation catalog','',f"{len(operations)} HTTP operations under {len(spec['paths'])} paths; {manifest['http_rest_operation_count']} REST and {manifest['websocket_documentation_operation_count']} websocket documentation entries. MCP wrappers are separate.",'','Every operation appears exactly once below, grouped by its first tag. All tags remain in inventory. Category references retain full resolved operations including response schemas; examples originate in the spec and are NOT live results.','']
    for tag,ops in sorted(groups.items()):
        slug=re.sub('[^a-z0-9]+','-',tag.lower()).strip('-'); name='references/categories/'+slug+'.md'
        catalog+=['## '+tag, '',f'Full definitions: [categories/{slug}.md](categories/{slug}.md)','']
        text=['# '+tag,'','Source: '+SOURCE+'; retrieved '+retrieved_at,'','Full descriptions, inherited security, effective parameters, responses and schemas. No live calls.','']
        for op in sorted(ops,key=lambda x:x['key']):
            catalog.append('- `'+op['key']+'` — '+op['operation'].get('summary','')+(' [deprecated]' if op['operation'].get('deprecated') else ''))
            text+=['## '+op['key'],'',op['operation'].get('summary',''),'',op['operation'].get('description',''),'', '### Fully resolved operation', '```json',dump(op),'```','']
        files[name]='\n'.join(text)
    files['references/catalog.md']='\n'.join(catalog)+'\n'
    # Exhaustive endpoint-local time/filter/pagination descriptions, no guessed semantics.
    semantics=['# Exhaustive date/filter/cursor constraints','', 'Read these with each full category schema. Missing semantics are not inferred. Pagination boundaries/ties require separately authorized live tests.','']
    for op in operations:
        selected=[p for p in op['operation']['parameters'] if re.search(r'date|time|cursor|since|until|older|newer|limit|offset|page|dte|intraday|agg|premium|volume|greater_oi',p['name'])]
        semantics+=['## '+op['key'],'',op['operation'].get('description',''),'', '```json',dump(selected),'```','']
    files['references/time-filter-pagination.md']='\n'.join(semantics)
    # Manager has a 1 MiB per-file ceiling. Lossless UTF-8 shards plus index.
    packed={}
    for path,content in files.items():
        if len(content.encode('utf-8'))<=80000:
            packed[path]=content
        else:
            parts=[]
            for i,start in enumerate(range(0,len(content),80000)):
                part=path+'.part%03d'%i
                packed[part]=content[start:start+80000]; parts.append(part)
            packed[path+'.index.json']=dump({'logical_path':path,'parts':parts,'sha256':hashlib.sha256(content.encode('utf-8')).hexdigest(),'bytes':len(content.encode('utf-8')),'reconstruction':'Concatenate UTF-8 part bytes in listed order; no separators.'})
    return packed

def load_logical(path):
    if (ROOT/path).exists(): return (ROOT/path).read_text()
    index=json.loads((ROOT/(path+'.index.json')).read_text())
    content=''.join((ROOT/p).read_text() for p in index['parts'])
    assert hashlib.sha256(content.encode('utf-8')).hexdigest()==index['sha256']
    return content

def validate():
    raw=load_logical('references/openapi.yaml').encode('utf-8')
    manifest=json.loads((ROOT/'references/manifest.json').read_text())
    files=generate(raw,manifest['retrieved_at_utc'],manifest['starting_docs_http_status'])
    for path,content in files.items():
        assert (ROOT/path).read_text()==content, 'Generated artifact drift: '+path
    examples=json.loads((ROOT/'references/request-examples.json').read_text())
    # Hand-authored templates are intentionally outside the source-only generator.
    # Public documentation refreshes must not redefine the approved local cohort.
    baselines=[e for e in examples if e.get('baseline') is True]
    assert len(baselines)==1, 'Exactly one approved baseline required'
    baseline=baselines[0]
    assert baseline['operation']=='GET /api/option-trades'
    assert baseline['query']=={'min_premium':'50000','min_size':500,'volume_greater_oi':True,'min_dte':1,'max_dte':14,'is_otm':True,'include_agg_trades':False,'limit':20}, 'Approved baseline drift'
    assert baseline['local_policy']=={'max_otm_fraction':None,'dte_basis':'current_analysis_date_America/New_York'}, 'Local policy drift'
    for example in examples:
        assert 'max_otm_fraction' not in example.get('query',{}), 'Local policy is not an API parameter'
        if example.get('query',{}).get('include_agg_trades') is True or example['operation']=='GET /api/option-trades/flow-alerts':
            assert example.get('baseline') is False
            assert 'separately authorized different cohort' in example['label']
    inv=json.loads(load_logical('references/inventory.json')); lookup={o['key']:o for o in inv['operations']}
    source=yaml.safe_load(raw)
    source_keys={method.upper()+' '+path for path,item in source['paths'].items() for method in item if method.lower() in METHODS}
    assert source_keys==set(lookup), 'Source/inventory coverage mismatch'
    catalog=load_logical('references/catalog.md')
    catalog_keys=re.findall(r'^- `([^`]+)`',catalog,re.M)
    assert len(catalog_keys)==len(set(catalog_keys))==len(source_keys)
    assert set(catalog_keys)==source_keys, 'Catalog coverage mismatch'
    assert hashlib.sha256(raw).hexdigest()==manifest['source_sha256']
    checked=0
    for example in examples:
        op=lookup[example['operation']]['operation']; defs={(p['in'],p['name']):p for p in op['parameters']}
        for location in ['path','query']:
            values=example.get(location,{})
            for name,value in values.items():
                assert (location,name) in defs,(example['operation'],name)
                schema=defs[(location,name)].get('schema',{})
                kind=schema.get('type')
                assert kind!='integer' or (isinstance(value,int) and not isinstance(value,bool))
                assert kind!='boolean' or isinstance(value,bool)
                assert kind!='string' or isinstance(value,str)
                assert kind!='array' or isinstance(value,list)
                if 'enum' in schema: assert value in schema['enum']
                if 'minimum' in schema: assert value>=schema['minimum']
                if 'maximum' in schema: assert value<=schema['maximum']
            for (loc,name),p in defs.items():
                if loc==location and p.get('required'): assert name in values
        checked+=1
    result={'verified':True,'generated_files_verified':len(files),'examples_schema_checked':checked,'approved_baseline_and_local_policy_verified':True,'source_inventory_catalog_coverage_verified':len(source_keys),**manifest}
    print(dump(result))
    return result

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--validate',action='store_true'); parser.add_argument('--refresh-payload'); parser.add_argument('--apply-public-refresh',action='store_true',help='Apply generated artifacts atomically through installed Hermes skill_manage; default-profile only.')
    parser.add_argument('--show-operation',help='Print one exact METHOD /api/path operation offline')
    args=parser.parse_args()
    if args.show_operation:
        inv=json.loads(load_logical('references/inventory.json'))
        matches=[o for o in inv['operations'] if o['key']==args.show_operation]
        if not matches: parser.error('Unknown exact operation key; see references/catalog.md')
        print(dump(matches[0])); return
    if args.validate: validate(); return
    if not (args.refresh_payload or args.apply_public_refresh): parser.error('Choose --validate or --refresh-payload or --apply-public-refresh')
    import os
    home=pathlib.Path(os.environ.get('HERMES_HOME',pathlib.Path.home()/'.hermes')).resolve()
    assert home==(pathlib.Path.home()/'.hermes').resolve(),'Only default profile authorized'
    raw=urllib.request.urlopen(SOURCE,timeout=60).read()
    status=urllib.request.urlopen(DOCS,timeout=60).status
    files=generate(raw,datetime.datetime.now(datetime.timezone.utc).isoformat(),status)
    payload={'operations':[{'name':'unusual-whales-api','action':'write_file','file_path':p,'file_content':c} for p,c in files.items()]}
    if args.refresh_payload: pathlib.Path(args.refresh_payload).write_text(dump(payload))
    if args.apply_public_refresh:
        from tools.skill_manager_tool import skill_manage
        # Each batch is atomic; manager caps calls at 20 operations.
        for start in range(0,len(payload['operations']),20):
            result=json.loads(skill_manage(action='batch',name='unusual-whales-api',operations=payload['operations'][start:start+20]))
            print(dump(result)); assert result.get('success'),result
    print(files['references/manifest.json'])
if __name__=='__main__': main()
