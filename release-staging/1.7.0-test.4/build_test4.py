from __future__ import annotations
import base64, hashlib, json, re, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.4'
BASE_ZIP=ROOT/'SGP_ClientPatch_1.7.0-test.3.zip'
WORK=ROOT/'.work-170t4'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.4.zip'
BASE_SHA='c6d98a99d0c36c228ebd69b6a097936d2ddbe35399b1167854900165cdb5123f'
OLD_BRAND_SHA='4d4a754f6b1f17ef035e2282f96aabe79a5b9c4a1dd320b7a58b2fae6307d832'
NEW_BRAND_SHA='506742cad60c67a00d512c06397dbe7e5a3a9d8e478cc1950a8068f94e674893'
NEW_BRAND_SIZE=20887
LOGO_SHA='993d39e756438788a85536a8324a5b20fe71281ae25f4d4192854e5cc111f53e'
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:return sha_bytes(p.read_bytes())
def run(*a:str):return subprocess.run(a,check=True,text=True,capture_output=True)

def copy_action(p:dict,suffix:str)->dict:
    a=[x for x in p['actions'] if x['type']=='copy' and (x.get('target') or '').endswith(suffix)]
    assert len(a)==1,(suffix,a);return a[0]

assert BASE_ZIP.is_file() and sha_file(BASE_ZIP)==BASE_SHA
with zipfile.ZipFile(BASE_ZIP) as z: assert z.testzip() is None
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE_ZIP) as z:z.extractall(BUILD)
manifest_path=BUILD/'patch.json'
p=json.loads(manifest_path.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.3'
assert p['toVersion']=='1.7.0-test.3'
assert p['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2']
assert '1.5.4' not in p['fromVersions']
base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

# Decode exact transparent logo prepared from owner's original transparent source.
logo=WORK/'sgp_logo_144x48_clean.png'
logo.write_bytes(base64.b64decode((STAGE/'sgp_logo_144x48_clean.b64').read_text('ascii')))
assert sha_file(logo)==LOGO_SHA
b=logo.read_bytes(); assert b[:8]==b'\x89PNG\r\n\x1a\n'
assert int.from_bytes(b[16:20],'big')==144 and int.from_bytes(b[20:24],'big')==48
assert b[25]==6  # RGBA PNG

ba=copy_action(p,'SGP-Client-Branding-1.2.2.jar')
old_brand=BUILD/ba['source']
assert old_brand.stat().st_size==16841 and sha_file(old_brand)==OLD_BRAND_SHA
classes=WORK/'classes'; classes.mkdir()
exports=['--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED','--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED']
run('javac',*exports,str(STAGE/'BrandingFixV123.java'),'-d',str(classes))
new_brand=BUILD/'files/mods/SGP-Client-Branding-1.2.3.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV123',str(old_brand),str(logo),str(new_brand))
assert new_brand.stat().st_size==NEW_BRAND_SIZE and sha_file(new_brand)==NEW_BRAND_SHA
with zipfile.ZipFile(new_brand) as z:
    assert z.testzip() is None
    assert sha_bytes(z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png'))==LOGO_SHA
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.3"' in toml and 'version="1.2.2"' not in toml

# Final class verification, including exact render/filter and state refresh changes.
verify=WORK/'verify'; verify.mkdir()
verify_exports=exports+['--add-exports','java.base/jdk.internal.org.objectweb.asm.tree.analysis=ALL-UNNAMED']
run('javac',*verify_exports,str(STAGE/'AsmVerify.java'),'-d',str(verify))
r=run('java',*verify_exports,'-cp',str(verify),'AsmVerify',str(new_brand),'sgp/client/branding/SgpClientBranding.class')
assert 'ASM BASIC VERIFY: PASS methods=17' in r.stdout
javap=run('javap','-classpath',str(new_brand),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
for needle in ['major version: 65','AbstractTexture.setFilter:(ZZ)V','TextureManager.getTexture:',
               'Method loadPackVersion:()Ljava/lang/String;','Field packVersion:Ljava/lang/String;']:
    assert needle in javap,needle
with zipfile.ZipFile(new_brand) as bz:
    cls=bz.read('sgp/client/branding/SgpClientBranding.class')
    for label in ['Версия: ','Доступно обновление','Новая версия: ','Обновить']:
        assert label.encode('utf-8') in cls,label
init=javap[javap.index('private static void onScreenInitPost'):javap.index('private static void onScreenRenderPost')]
assert init.count('Method loadPackVersion:()Ljava/lang/String;')==1
assert 'putstatic' in init and 'Field packVersion:Ljava/lang/String;' in init
assert init.index('Method loadPackVersion:()Ljava/lang/String;') < init.index('Method startUpdateCheck:()V')
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]
assert 'bipush        12' in render and 'bipush        72' in render and 'bipush        24' in render and 'sipush        144' in render and 'bipush        48' in render

# Independent SemVer regression proof for the screenshot issue.
rx=re.compile(r'^v(\d+)\.(\d+)\.(\d+)(?:-test\.(\d+))?$')
def sem(v:str):
    m=rx.fullmatch('v'+v.removeprefix('v')); assert m
    return tuple(map(int,m.groups()[:3]))+(int(m.group(4)) if m.group(4) else 2**31-1,)
assert sem('1.6.2') < sem('1.7.0-test.3') < sem('1.7.0-test.4') < sem('1.7.0')
assert sem('1.7.0') > sem('1.7.0-test.999')
print('Branding 1.2.3 static/ASM/SemVer checks: PASS')

# Transform cumulative manifest while preserving every non-branding payload byte.
p['patchId']='sgp-client-1.7.0-test.4'
p['name']='SGP Client 1.7.0-test.4'
p['toVersion']='1.7.0-test.4'
p['fromVersions']=STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3']
p['summary']=[
  'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
  'SGP Client Branding 1.2.3: чистый прозрачный логотип без точечного halo, линейная фильтрация и повторное чтение .sgp версии при открытии главного меню.',
  'Плашка SGP постоянно видна: без обновления показывает текущую версию; при новой stable-версии — мигающее уведомление и кнопку «Обновить».',
  'Building Wands 3.0.5, полный русский перевод 348/348, paxel compat, лимиты и SGP Fixes rev 1.10 сохранены без gameplay-изменений.'
]
idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
  {'actionId':'remove-sgp-client-branding-1-2-2','type':'delete','description':'Удалить SGP Client Branding 1.2.2 перед исправлением логотипа','target':'mods/SGP-Client-Branding-1.2.2.jar','optional':True},
  {'actionId':'install-sgp-client-branding-1-2-3','type':'copy','description':'Установить SGP Client Branding 1.2.3 с чистым прозрачным логотипом','source':'files/mods/SGP-Client-Branding-1.2.3.jar','target':'mods/SGP-Client-Branding-1.2.3.jar','sha256':NEW_BRAND_SHA,'size':NEW_BRAND_SIZE}
]
old_brand.unlink()
ids=[a['actionId'] for a in p['actions']]; assert len(ids)==len(set(ids))
for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/')) and target!='servers.dat' and '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']; assert f.is_file() and f.stat().st_size==a['size'] and sha_file(f).lower()==a['sha256'].lower()
assert not old_brand.exists()

# Prove only intended payload file changed between test.3 and test.4 build tree.
now_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={'patch.json','README.txt','files/mods/SGP-Client-Branding-1.2.2.jar','files/mods/SGP-Client-Branding-1.2.3.jar'}
for path,h in base_files.items():
    if path not in allowed: assert now_files.get(path)==h,path
for path in now_files:
    if path not in allowed: assert base_files.get(path)==now_files[path],path

manifest_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.4
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1, test.2 and test.3.
Unofficial 1.5.4 remains intentionally excluded.

Changes relative to test.3:
- SGP Client Branding 1.2.3 uses a clean 144x48 transparent logo source with linear filtering and correct 3:1 display geometry, removing the dotted/checker halo seen in test.3.
- Main-menu SGP plaque remains persistent: normal state shows current version and no button; update state shows blinking red notice, target stable version and «Обновить».
- Branding refreshes authoritative .sgp/pack.json version when TitleScreen opens, hardening against stale constructor-time state.
- Installer application of this patch writes local pack version to 1.7.0-test.4.
- All gameplay/resource payload except Branding is byte-identical to test.3.

Owner Minecraft runtime test is mandatory before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,9,30,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix(); zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names=z.namelist(); assert len(names)==len(set(names))
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.4' and q['toVersion']=='1.7.0-test.4'
    assert q['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3']
    assert 'files/mods/SGP-Client-Branding-1.2.2.jar' not in names
    assert sha_bytes(z.read('files/mods/SGP-Client-Branding-1.2.3.jar'))==NEW_BRAND_SHA
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source']); assert len(data)==a['size'] and sha_bytes(data).lower()==a['sha256'].lower(),a['actionId']
print('FINAL STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
