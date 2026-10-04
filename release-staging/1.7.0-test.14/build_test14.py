from __future__ import annotations
import hashlib, json, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.14'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.13.zip'
WORK=ROOT/'.work-170t14'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.14.zip'

BASE_SHA='ffb4028ff1a4ab22c92a3b9c3f6ef7312796ff69f5dd791210e8af77b6f181b7'
OLD_BRAND_SHA='259d67ec59db26e7d2bfe126da3aafd1bed6690e760ffd020b46622424d5cce4'
OLD_BRAND_SIZE=16816
CUBE_SHA='67c9973d3f5e277e318ef077f9d98b5ade0a6a83ae5fe751c9732534edbc1221'
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']
TESTS=['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5','1.7.0-test.6','1.7.0-test.7','1.7.0-test.8','1.7.0-test.9','1.7.0-test.10','1.7.0-test.11','1.7.0-test.12','1.7.0-test.13']

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str: return sha_bytes(p.read_bytes())
def run(*a:str):
    cp=subprocess.run(a,check=False,text=True,capture_output=True)
    if cp.returncode!=0:
        print("COMMAND FAILED:",a); print(cp.stdout); print(cp.stderr); cp.check_returncode()
    return cp

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest=BUILD/'patch.json'
p=json.loads(manifest.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.13'
assert p['toVersion']=='1.7.0-test.13'
assert p['fromVersions']==STABLE+TESTS[:-1]
base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.11.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==OLD_BRAND_SIZE
assert sha_file(old)==OLD_BRAND_SHA

with zipfile.ZipFile(old) as z:
    assert z.testzip() is None
    logo=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(logo)==CUBE_SHA
    assert int.from_bytes(logo[16:20],'big')==58
    assert int.from_bytes(logo[20:24],'big')==48
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.11"' in toml

classes=WORK/'classes'; classes.mkdir()
exports=['--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED','--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED']
run('javac',*exports,str(STAGE/'BrandingFixV1212.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.12.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV1212',str(old),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    logo=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(logo)==CUBE_SHA
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.12"' in toml and 'version="1.2.11"' not in toml
    cls=z.read('sgp/client/branding/SgpClientBranding.class')
    assert 'Версия SGP: '.encode('utf-8') in cls

javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]
assert render.count('sipush        175')==4
assert render.count('sipush        174')==1
assert 'sipush        169' not in render
assert 'sipush        168' not in render
# Preserve exact accepted test.13 cube/text geometry.
for token in ['bipush        8','bipush        12','bipush        29','bipush        24','bipush        58','bipush        48','bipush        41']:
    assert token in render, token
print('BRANDING 1.2.12 RIGHT-PADDING AUDIT: PASS')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

p['patchId']='sgp-client-1.7.0-test.14'
p['name']='SGP Client 1.7.0-test.14'
p['toVersion']='1.7.0-test.14'
p['fromVersions']=STABLE+TESTS
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.12: визуал cube/text test.13 сохранён, справа добавлено 6 GUI px свободного пространства.',
    'Ширина плашки пока фиксированная, не вычисляется автоматически по длине version text.',
    'Create Rope Pulley maxRopeLength=512 сохранён без изменений.'
]
idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
    {'actionId':'remove-sgp-client-branding-1-2-11','type':'delete','description':'Удалить SGP Client Branding 1.2.11 с тесной правой границей','target':'mods/SGP-Client-Branding-1.2.11.jar','optional':True},
    {'actionId':'install-sgp-client-branding-1-2-12','type':'copy','description':'Установить SGP Client Branding 1.2.12: test.13 cube + дополнительный right padding','source':'files/mods/SGP-Client-Branding-1.2.12.jar','target':'mods/SGP-Client-Branding-1.2.12.jar','sha256':new_sha,'size':new_size}
]
old.unlink()

ids=[a['actionId'] for a in p['actions']]
assert len(ids)==len(set(ids))
rope=[a for a in p['actions'] if a.get('actionId')=='increase-create-rope-pulley-max-length-512']
assert len(rope)==1 and rope[0]['edits'][0]['value']==512

for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/')) and target!='servers.dat' and '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']
        assert f.is_file() and f.stat().st_size==a['size'] and sha_file(f).lower()==a['sha256'].lower(),a['actionId']

now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={'patch.json','README.txt','files/mods/SGP-Client-Branding-1.2.11.jar','files/mods/SGP-Client-Branding-1.2.12.jar'}
for path,hsh in base_files.items():
    if path not in allowed: assert now.get(path)==hsh,path
for path,hsh in now.items():
    if path not in allowed: assert base_files.get(path)==hsh,path

manifest.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.14
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.13.

Changes relative to test.13:
- Branding 1.2.12 preserves the exact cube/text geometry from test.13.
- Only the plaque right edge changes: x=169 -> x=175, adding 6 GUI px of breathing room after the version string.
- Width is still fixed in this iteration; it is not auto-calculated from font.width(versionText).
- Raster SGP wordmark remains removed.
- Create maxRopeLength=512 remains unchanged.

Owner Minecraft runtime visual check is required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,20,0,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.14'
    assert q['toVersion']=='1.7.0-test.14'
    assert q['fromVersions']==STABLE+TESTS
    assert 'files/mods/SGP-Client-Branding-1.2.11.jar' not in z.namelist()
    brand=z.read('files/mods/SGP-Client-Branding-1.2.12.jar')
    assert sha_bytes(brand)==new_sha
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size'] and sha_bytes(data).lower()==a['sha256'].lower(),a['actionId']

print('FINAL TEST.14 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
Path('test14_brand_sha.txt').write_text(new_sha+'\n')
Path('test14_brand_size.txt').write_text(str(new_size)+'\n')
