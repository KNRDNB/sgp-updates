from __future__ import annotations
import base64, hashlib, json, shutil, struct, subprocess, zlib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.6'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.5.zip'
WORK=ROOT/'.work-170t6'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.6.zip'
BASE_SHA='13caca7b10d6efdcec8eadf57a873a9ddc3a3ce4b6eb7dc51e7943b6941ff8f2'
OLD_BRAND_SHA='33f9e2a2c9da3eedd3abec04bd19dedf88d1b44941646a221349668245f1be8c'
LOGO_SHA='538106dec269985505ec73ea64220a5469b5401242d2efa48caae11a5068c0c5'
LOGO_SIZE=1161
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']

def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:return sha_bytes(p.read_bytes())
def run(*a:str):return subprocess.run(a,check=True,text=True,capture_output=True)

def png_rgba_alpha_values(data:bytes):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; width=height=None; bit=None; color=None; idat=b''
    while pos<len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0]; typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+n]; pos+=12+n
        if typ==b'IHDR':
            width,height,bit,color,comp,filt,interlace=struct.unpack('>IIBBBBB',chunk)
            assert bit==8 and color==6 and comp==0 and filt==0 and interlace==0
        elif typ==b'IDAT': idat+=chunk
        elif typ==b'IEND': break
    raw=zlib.decompress(idat); bpp=4; stride=width*bpp
    rows=[]; prev=bytearray(stride); off=0
    def paeth(a,b,c):
        p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        ft=raw[off]; off+=1; scan=bytearray(raw[off:off+stride]); off+=stride
        for x in range(stride):
            left=scan[x-bpp] if x>=bpp else 0
            up=prev[x]
            ul=prev[x-bpp] if x>=bpp else 0
            if ft==1: scan[x]=(scan[x]+left)&255
            elif ft==2: scan[x]=(scan[x]+up)&255
            elif ft==3: scan[x]=(scan[x]+((left+up)//2))&255
            elif ft==4: scan[x]=(scan[x]+paeth(left,up,ul))&255
            elif ft!=0: raise AssertionError(f'unsupported filter {ft}')
        rows.append(bytes(scan)); prev=scan
    alphas={row[x+3] for row in rows for x in range(0,stride,4)}
    return width,height,alphas

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)
p=json.loads((BUILD/'patch.json').read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.5'
assert p['toVersion']=='1.7.0-test.5'
assert p['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4']
base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

logo=WORK/'sgp_logo_72x24_pixelclean.png'
logo.write_bytes(base64.b64decode((STAGE/'sgp_logo_72x24_pixelclean.b64').read_text('ascii')))
assert logo.stat().st_size==LOGO_SIZE and sha_file(logo)==LOGO_SHA
w,h,alphas=png_rgba_alpha_values(logo.read_bytes())
assert (w,h)==(72,24)
assert alphas=={0,255}, alphas
print('PIXEL-CLEAN LOGO: PASS 72x24 RGBA alpha={0,255}')

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.4.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==20883 and sha_file(old)==OLD_BRAND_SHA

classes=WORK/'classes'; classes.mkdir()
exports=['--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED','--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED']
run('javac',*exports,str(STAGE/'BrandingFixV125.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.5.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV125',str(old),str(logo),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    embedded=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(embedded)==LOGO_SHA
    assert png_rgba_alpha_values(embedded)==(72,24,{0,255})
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.5"' in toml and 'version="1.2.4"' not in toml

verify=WORK/'verify'; verify.mkdir()
verify_exports=exports+['--add-exports','java.base/jdk.internal.org.objectweb.asm.tree.analysis=ALL-UNNAMED']
run('javac',*verify_exports,str(ROOT/'release-staging/1.7.0-test.4/AsmVerify.java'),'-d',str(verify))
rv=run('java',*verify_exports,'-cp',str(verify),'AsmVerify',str(new),'sgp/client/branding/SgpClientBranding.class')
assert 'ASM BASIC VERIFY: PASS methods=17' in rv.stdout
javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
for needle in ['major version: 65','AbstractTexture.setFilter:(ZZ)V',
               'Method loadPackVersion:()Ljava/lang/String;',
               'GuiGraphics.blit:(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V']:
    assert needle in javap,needle
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]
# We intentionally require nearest filtering (false,false) and 1:1 source/texture/destination dimensions.
filter_idx=render.index('AbstractTexture.setFilter:(ZZ)V')
before=render[max(0,filter_idx-400):filter_idx]
assert before.count('iconst_0')>=2, before
for needle in ['bipush        72','bipush        24']:
    assert render.count(needle)>=3, (needle,render.count(needle))
assert 'sipush        144' not in render
print('Branding 1.2.5 nearest/pixel-clean ASM audit: PASS')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

p['patchId']='sgp-client-1.7.0-test.6'
p['name']='SGP Client 1.7.0-test.6'
p['toVersion']='1.7.0-test.6'
p['fromVersions']=STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5']
p['summary']=[
  'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
  'SGP Client Branding 1.2.5: pixel-clean logo 72×24 с только binary alpha 0/255 и nearest filtering — без полупрозрачного dotted halo.',
  'Постоянная SGP-плашка, prerelease SemVer, update-state, полный русский Building Wands, paxel compat, лимиты и SGP Fixes rev 1.10 сохранены.'
]
idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
 {'actionId':'remove-sgp-client-branding-1-2-4','type':'delete','description':'Удалить SGP Client Branding 1.2.4 с antialias fringe на logo','target':'mods/SGP-Client-Branding-1.2.4.jar','optional':True},
 {'actionId':'install-sgp-client-branding-1-2-5','type':'copy','description':'Установить SGP Client Branding 1.2.5 с pixel-clean logo','source':'files/mods/SGP-Client-Branding-1.2.5.jar','target':'mods/SGP-Client-Branding-1.2.5.jar','sha256':new_sha,'size':new_size}
]
old.unlink()
ids=[a['actionId'] for a in p['actions']]; assert len(ids)==len(set(ids))
for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/')) and target!='servers.dat' and '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']; assert f.is_file() and f.stat().st_size==a['size'] and sha_file(f).lower()==a['sha256'].lower()

now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={'patch.json','README.txt','files/mods/SGP-Client-Branding-1.2.4.jar','files/mods/SGP-Client-Branding-1.2.5.jar'}
for path,hsh in base_files.items():
    if path not in allowed: assert now.get(path)==hsh,path
for path,hsh in now.items():
    if path not in allowed: assert base_files.get(path)==hsh,path

(BUILD/'patch.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.6
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.5.

Changes relative to test.5:
- Branding 1.2.5 replaces the antialiased 144x48 logo path with an exact UI-size 72x24 pixel-clean transparent asset.
- Alpha is binary only: every pixel is fully transparent or fully opaque. There are no semi-transparent edge pixels that can appear as dotted halo.
- Texture filtering is nearest (false,false), and source/texture/destination are all 72x24.
- Every non-Branding payload is byte-identical to test.5.

Owner Minecraft runtime test is mandatory before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,11,30,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix(); zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.6'
    assert q['toVersion']=='1.7.0-test.6'
    assert q['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5']
    assert 'files/mods/SGP-Client-Branding-1.2.4.jar' not in z.namelist()
    assert sha_bytes(z.read('files/mods/SGP-Client-Branding-1.2.5.jar'))==new_sha
print('FINAL TEST.6 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
(Path('test6_brand_sha.txt')).write_text(new_sha+'\n')
(Path('test6_brand_size.txt')).write_text(str(new_size)+'\n')
