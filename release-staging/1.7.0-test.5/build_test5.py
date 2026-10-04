from __future__ import annotations
import hashlib, json, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.5'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.4.zip'
WORK=ROOT/'.work-170t5'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.5.zip'
BASE_SHA='4a2ca6d37cce136558db7fdf1baa92c3dcb38084780d2b455af2e0fd83d5fe2e'
OLD_BRAND_SHA='506742cad60c67a00d512c06397dbe7e5a3a9d8e478cc1950a8068f94e674893'
LOGO_SHA='993d39e756438788a85536a8324a5b20fe71281ae25f4d4192854e5cc111f53e'
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:return sha_bytes(p.read_bytes())
def run(*a:str):return subprocess.run(a,check=True,text=True,capture_output=True)

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)
p=json.loads((BUILD/'patch.json').read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.4'
assert p['toVersion']=='1.7.0-test.4'
assert p['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3']
base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.3.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==20887 and sha_file(old)==OLD_BRAND_SHA

classes=WORK/'classes'; classes.mkdir()
exports=['--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED','--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED']
run('javac',*exports,str(STAGE/'BrandingFixV124.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.4.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV124',str(old),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    logo=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(logo)==LOGO_SHA
    assert int.from_bytes(logo[16:20],'big')==144 and int.from_bytes(logo[20:24],'big')==48
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.4"' in toml and 'version="1.2.3"' not in toml

verify=WORK/'verify'; verify.mkdir()
verify_exports=exports+['--add-exports','java.base/jdk.internal.org.objectweb.asm.tree.analysis=ALL-UNNAMED']
run('javac',*verify_exports,str(ROOT/'release-staging/1.7.0-test.4/AsmVerify.java'),'-d',str(verify))
rv=run('java',*verify_exports,'-cp',str(verify),'AsmVerify',str(new),'sgp/client/branding/SgpClientBranding.class')
assert 'ASM BASIC VERIFY: PASS methods=17' in rv.stdout
javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
scaled='GuiGraphics.blit:(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V'
old_sig='GuiGraphics.blit:(Lnet/minecraft/resources/ResourceLocation;IIIFFIIII)V'
assert scaled in javap and old_sig not in javap
for needle in ['AbstractTexture.setFilter:(ZZ)V','Method loadPackVersion:()Ljava/lang/String;','major version: 65']:
    assert needle in javap,needle
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]
for needle in ['bipush        72','bipush        24','sipush        144','bipush        48']:
    assert needle in render,needle
print('Branding 1.2.4 scaled-full-texture ASM audit: PASS')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

# Update cumulative manifest: test4 -> test5, only Branding payload changes.
p['patchId']='sgp-client-1.7.0-test.5'
p['name']='SGP Client 1.7.0-test.5'
p['toVersion']='1.7.0-test.5'
p['fromVersions']=STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4']
p['summary']=[
  'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
  'SGP Client Branding 1.2.4: исправлена обрезка логотипа — вся 144×48 texture масштабируется в 72×24 вместо выборки только левой половины.',
  'Постоянная SGP-плашка, prerelease SemVer, update-state, полный русский Building Wands, paxel compat, лимиты и SGP Fixes rev 1.10 сохранены.'
]
idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
 {'actionId':'remove-sgp-client-branding-1-2-3','type':'delete','description':'Удалить SGP Client Branding 1.2.3 с обрезанным logo render','target':'mods/SGP-Client-Branding-1.2.3.jar','optional':True},
 {'actionId':'install-sgp-client-branding-1-2-4','type':'copy','description':'Установить SGP Client Branding 1.2.4 с полным масштабированным logo','source':'files/mods/SGP-Client-Branding-1.2.4.jar','target':'mods/SGP-Client-Branding-1.2.4.jar','sha256':new_sha,'size':new_size}
]
old.unlink()
ids=[a['actionId'] for a in p['actions']]; assert len(ids)==len(set(ids))
for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/')) and target!='servers.dat' and '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']; assert f.is_file() and f.stat().st_size==a['size'] and sha_file(f).lower()==a['sha256'].lower()

# All non-Branding payloads must remain byte-identical to test4.
now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={'patch.json','README.txt','files/mods/SGP-Client-Branding-1.2.3.jar','files/mods/SGP-Client-Branding-1.2.4.jar'}
for path,h in base_files.items():
    if path not in allowed: assert now.get(path)==h,path
for path,h in now.items():
    if path not in allowed: assert base_files.get(path)==h,path

(BUILD/'patch.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.5
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.4.

Changes relative to test.4:
- Branding 1.2.4 fixes the cropped logo. The previous GuiGraphics overload used width/height as both draw size and source-region size, so test.4 sampled only 72x24 from the left side of the 144x48 texture.
- Branding 1.2.4 uses the scaling overload: full source region 144x48 -> destination 72x24.
- Transparent logo bytes and linear filtering are unchanged.
- Every non-Branding payload is byte-identical to test.4.

Owner Minecraft runtime test is mandatory before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,10,30,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix(); zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.5'
    assert q['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4']
    assert 'files/mods/SGP-Client-Branding-1.2.3.jar' not in z.namelist()
    assert sha_bytes(z.read('files/mods/SGP-Client-Branding-1.2.4.jar'))==new_sha
print('FINAL TEST.5 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
