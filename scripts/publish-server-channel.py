#!/usr/bin/env python3
"""Release tooling only. Activate the static pointer only after verified exact public assets."""
import base64, hashlib, importlib.util, json, os, pathlib, subprocess, urllib.request

root=pathlib.Path.cwd(); version=os.environ['VERSION']; tag='server-v'+version; repo='KNRDNB/sgp-updates'
spec=importlib.util.spec_from_file_location('guard',root/'scripts/server-release-guard.py'); guard=importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
guard.version(version)
zip_path=root/'handoff'/('SGP_ServerPatch_'+version+'.zip'); meta_path=root/'channel'/('SGP_ServerPatch_'+version+'.meta.json')
meta=guard.parse(meta_path.read_bytes()); guard.validate_metadata(meta); guard.validate_zip(zip_path,meta)
state={}; public=False; pointer_active=False; previous=None; activation=None
def gh(*args): return subprocess.check_output(['gh',*args])
def save(): (root/'publication-state.json').write_bytes(guard.json_bytes(state))
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
try:
    # A Draft need not have a tag object yet. Retain its ID; never address it via /tags/.
    snapshots=json.loads(gh('api',f'repos/{repo}/releases?per_page=100'))
    matches=[r for r in snapshots if r['tag_name']==tag]
    guard.require(len(matches)<=1,'Ambiguous server release')
    if matches:
        release=matches[0]
        guard.require(release['draft'] and not release['prerelease'],'Accepted/public server release is immutable')
    else:
        request={'tag_name':tag,'name':'SGP Сервер '+version,'body':(root/'changelog.txt').read_text(encoding='utf-8').strip(),'draft':True,'prerelease':False,'make_latest':'false'}
        (root/'release-request.json').write_text(json.dumps(request),encoding='utf-8')
        release=json.loads(gh('api','--method','POST',f'repos/{repo}/releases','--input',str(root/'release-request.json')))
    state['draftId']=release['id'];save()
    guard.require(all(a['name'] in (zip_path.name,meta_path.name) for a in release['assets']),'Unexpected Draft asset')
    assets=list(release['assets'])
    for source in (zip_path,meta_path):
        present=[a for a in assets if a['name']==source.name]
        guard.require(len(present)<=1,'Duplicate Draft asset')
        if present:
            guard.require(present[0]['size']==source.stat().st_size and present[0]['digest']=='sha256:'+digest(source),'Existing Draft asset differs; refuse overwrite')
        else:
            assets.append(json.loads(gh('api','--method','POST',f'https://uploads.github.com/repos/{repo}/releases/{release["id"]}/assets?name={source.name}','-H','Content-Type: application/octet-stream','--input',str(source))))
    verify=root/'draft-verified'; verify.mkdir(exist_ok=True)
    for source in (zip_path,meta_path):
        asset=next(a for a in assets if a['name']==source.name); retained=verify/source.name
        if not retained.exists():retained.write_bytes(gh('api',f'repos/{repo}/releases/assets/{asset["id"]}','-H','Accept: application/octet-stream'))
        guard.require(digest(retained)==digest(source) and retained.stat().st_size==source.stat().st_size,'Draft asset byte mismatch')
    state['draftAssets']='PASS';save()
    (root/'promotion.json').write_text(json.dumps({'draft':False,'prerelease':False,'make_latest':'false'}),encoding='utf-8')
    gh('api','--method','PATCH',f'repos/{repo}/releases/{state["draftId"]}','--input',str(root/'promotion.json'));public=True
    release=json.loads(gh('api',f'repos/{repo}/releases/{state["draftId"]}'))
    guard.require(not release['draft'] and not release['prerelease'] and release['tag_name']==tag and len(release['assets'])==2,'Public identity mismatch')
    for source in (zip_path,meta_path):
        asset=[a for a in release['assets'] if a['name']==source.name]
        guard.require(len(asset)==1 and asset[0]['size']==source.stat().st_size and asset[0]['digest']=='sha256:'+digest(source),'Public asset binding mismatch')
        url=f'https://github.com/{repo}/releases/download/{tag}/{source.name}'
        with urllib.request.urlopen(url,timeout=90) as response:
            data=response.read(source.stat().st_size+1)
        guard.require(len(data)==source.stat().st_size and hashlib.sha256(data).hexdigest()==digest(source),'Public download mismatch')
    state['publicAssets']='PASS';state['releaseId']=release['id'];state['assets']=[{k:a[k] for k in ('id','name','size','digest')} for a in release['assets']];save()
    old=subprocess.run(['gh','api',f'repos/{repo}/contents/server/latest.json'],capture_output=True)
    request={'message':'Activate exact official server '+version,'content':base64.b64encode((root/'channel/latest.json').read_bytes()).decode(),'branch':'main'}
    if old.returncode==0:
        previous=json.loads(old.stdout); request['sha']=previous['sha']; before=guard.parse(base64.b64decode(previous['content']))
        guard.require(guard.version(before['version'])<guard.version(version),'Pointer must move forward only')
    (root/'pointer-request.json').write_text(json.dumps(request),encoding='utf-8')
    activation=json.loads(gh('api','--method','PUT',f'repos/{repo}/contents/server/latest.json','--input',str(root/'pointer-request.json')))
    pointer_active=True; state['activationCommit']=activation['commit']['sha'];save()
    url=f'https://raw.githubusercontent.com/{repo}/main/server/latest.json'
    with urllib.request.urlopen(url,timeout=30) as response:data=response.read(4097)
    guard.require(data==(root/'channel/latest.json').read_bytes(),'Static pointer binding mismatch')
    state['result']='PASS';save()
except Exception:
    state['result']='FAIL';state['pointerActive']=pointer_active;save()
    if pointer_active:
        rollback={'message':'Restore server pointer after failed activation verification','sha':activation['content']['sha'],'branch':'main'}
        if previous:
            rollback['content']=previous['content'].replace('\n','');method='PUT'
        else:method='DELETE'
        (root/'pointer-rollback.json').write_text(json.dumps(rollback),encoding='utf-8')
        gh('api','--method',method,f'repos/{repo}/contents/server/latest.json','--input',str(root/'pointer-rollback.json'))
        pointer_active=False;state['pointerRestored']=True;save()
    if public:subprocess.run(['gh','api','--method','PATCH',f'repos/{repo}/releases/{state["draftId"]}','-F','draft=true'],check=True)
    raise
