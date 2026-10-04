from __future__ import annotations
import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.9.zip'
WORK=ROOT/'.work-170t10'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.10.zip'

BASE_SHA='315a9f26527e48b99f675bec3c8f18a6de03de0b001f659f37289863be8809e9'
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']
TESTS=['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5','1.7.0-test.6','1.7.0-test.7','1.7.0-test.8','1.7.0-test.9']

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p:Path)->str:
    return sha_bytes(p.read_bytes())

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest_path=BUILD/'patch.json'
p=json.loads(manifest_path.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.9'
assert p['toVersion']=='1.7.0-test.9'
assert p['fromVersions']==STABLE+TESTS[:-1]
assert '1.5.4' not in p['fromVersions']

base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

# test.10 only adds one owner-requested Create integrated-server config change.
# Use TOML path editing rather than replacing create-server.toml, so the action is
# cumulative and independent of whether a historical source had 256/384/etc.
action={
    'actionId':'increase-create-rope-pulley-max-length-512',
    'type':'tomlEdit',
    'description':'Create Rope Pulley: увеличить максимальную длину троса/лебёдки до 512 блоков',
    'target':'config/create-server.toml',
    'edits':[
        {
            'op':'set',
            'path':'kinetics.contraptions.maxRopeLength',
            'value':512,
            'createIfMissing':False
        }
    ]
}

ids=[a['actionId'] for a in p['actions']]
assert action['actionId'] not in ids
assert not any(
    a.get('type')=='tomlEdit'
    and a.get('target')=='config/create-server.toml'
    and any(e.get('path')=='kinetics.contraptions.maxRopeLength' for e in a.get('edits',[]))
    for a in p['actions']
)

# Keep action near other Create config edits.
insert_at=len(p['actions'])
for i,a in enumerate(p['actions']):
    if a.get('actionId')=='decouple-create-stockkeeper-jei-search':
        insert_at=i+1
        break
p['actions'].insert(insert_at,action)

p['patchId']='sgp-client-1.7.0-test.10'
p['name']='SGP Client 1.7.0-test.10'
p['toVersion']='1.7.0-test.10'
p['fromVersions']=STABLE+TESTS
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.8 сохранён: только cube icon + Minecraft-текст «Версия SGP: <version>».',
    'Create Rope Pulley: maxRopeLength установлен в 512 блоков через точечный tomlEdit config/create-server.toml.',
    'Все payload-файлы относительно test.9 byte-identical; меняются только manifest/README и новая config action.'
]

# General action safety/static checks.
ids=[a['actionId'] for a in p['actions']]
assert len(ids)==len(set(ids))
rope=[a for a in p['actions'] if a['actionId']=='increase-create-rope-pulley-max-length-512']
assert len(rope)==1
ra=rope[0]
assert ra==action
assert ra['target']=='config/create-server.toml'
assert ra['edits'][0]['path']=='kinetics.contraptions.maxRopeLength'
assert ra['edits'][0]['value']==512
assert ra['edits'][0]['createIfMissing'] is False

for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/'))
    assert target!='servers.dat'
    assert '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']
        assert f.is_file()
        assert f.stat().st_size==a['size']
        assert sha_file(f).lower()==a['sha256'].lower(), a['actionId']

# No payload bytes change in test.10.
now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
for path,hsh in base_files.items():
    if path not in {'patch.json','README.txt'}:
        assert now.get(path)==hsh, path
for path,hsh in now.items():
    if path not in {'patch.json','README.txt'}:
        assert base_files.get(path)==hsh, path

manifest_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.10
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.9.

Changes relative to test.9:
- Branding 1.2.8 stays unchanged: cube-only icon + Minecraft text "Версия SGP: <version>".
- Create integrated-server config: kinetics.contraptions.maxRopeLength = 512.
- The Create setting is applied through a targeted tomlEdit; create-server.toml is not replaced wholesale.
- Every payload file is byte-identical to test.9.

The same Create server-side setting must be carried into the matching dedicated-server patch before multiplayer rollout.
Owner Minecraft runtime check is required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,17,0,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.10'
    assert q['toVersion']=='1.7.0-test.10'
    assert q['fromVersions']==STABLE+TESTS
    qr=[a for a in q['actions'] if a['actionId']=='increase-create-rope-pulley-max-length-512']
    assert len(qr)==1
    assert qr[0]['type']=='tomlEdit'
    assert qr[0]['target']=='config/create-server.toml'
    assert qr[0]['edits']==[{
        'op':'set',
        'path':'kinetics.contraptions.maxRopeLength',
        'value':512,
        'createIfMissing':False
    }]
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size']
            assert sha_bytes(data).lower()==a['sha256'].lower(), a['actionId']

print('FINAL TEST.10 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
print('CREATE_MAX_ROPE_LENGTH=512')
