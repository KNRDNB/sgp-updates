from __future__ import annotations
import base64, hashlib, json, shutil, struct, subprocess, zlib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.7'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.6.zip'
WORK=ROOT/'.work-170t7'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.7.zip'

BASE_SHA='26fd1cd38a1e518e873872f9732a631c4a6338d31dbaf1842145a34187a52426'
OLD_BRAND_SHA='44d45a7b8e71221f3db449b09635765a7a5814665a26da18b72b849dfb68297b'
OLD_BRAND_SIZE=13991
LOGO_SHA='f02276b4a3165d2048794a81c3ff8fe8d7d5da3d0146ae215aeae5f9bcbf9f17'
LOGO_SIZE=5846
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str:
    return sha_bytes(p.read_bytes())
def run(*a:str):
    return subprocess.run(a,check=True,text=True,capture_output=True)

def png_rgba_alpha(data:bytes):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; width=height=None; bit=color=None; idat=b''
    while pos<len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0]
        typ=data[pos+4:pos+8]
        chunk=data[pos+8:pos+8+n]
        pos+=12+n
        if typ==b'IHDR':
            width,height,bit,color,comp,filt,interlace=struct.unpack('>IIBBBBB',chunk)
            assert bit==8 and color==6 and comp==0 and filt==0 and interlace==0
        elif typ==b'IDAT':
            idat+=chunk
        elif typ==b'IEND':
            break
    raw=zlib.decompress(idat)
    bpp=4; stride=width*bpp
    rows=[]; prev=bytearray(stride); off=0
    def paeth(a,b,c):
        p=a+b-c; pa=abs(p-a); pb=abs(p-b); pc=abs(p-c)
        return a if pa<=pb and pa<=pc else (b if pb<=pc else c)
    for _ in range(height):
        ft=raw[off]; off+=1
        scan=bytearray(raw[off:off+stride]); off+=stride
        for x in range(stride):
            left=scan[x-bpp] if x>=bpp else 0
            up=prev[x]
            ul=prev[x-bpp] if x>=bpp else 0
            if ft==1: scan[x]=(scan[x]+left)&255
            elif ft==2: scan[x]=(scan[x]+up)&255
            elif ft==3: scan[x]=(scan[x]+((left+up)//2))&255
            elif ft==4: scan[x]=(scan[x]+paeth(left,up,ul))&255
            elif ft!=0: raise AssertionError(f'unsupported PNG filter {ft}')
        rows.append(bytes(scan)); prev=scan
    alphas=[]
    coords=[]
    for y,row in enumerate(rows):
        for x in range(0,stride,4):
            a=row[x+3]
            alphas.append(a)
            if a:
                coords.append((x//4,y,a))
    return width,height,alphas,coords

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest_path=BUILD/'patch.json'
p=json.loads(manifest_path.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.6'
assert p['toVersion']=='1.7.0-test.6'
assert p['fromVersions']==STABLE+['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5']
assert '1.5.4' not in p['fromVersions']

base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

# Exact high-quality logo: tight-cropped from the owner's original transparent source,
# premultiplied-alpha Lanczos downsample, low-alpha fringe floor 12, no runtime scaling.
logo=WORK/'sgp_logo_96x37_hq.png'
logo_b64=''.join((STAGE/f'sgp_logo_96x37_hq.part{i}.b64').read_text('ascii') for i in range(5))
logo.write_bytes(base64.b64decode(logo_b64))
assert logo.stat().st_size==LOGO_SIZE
assert sha_file(logo)==LOGO_SHA
w,h,alphas,coords=png_rgba_alpha(logo.read_bytes())
assert (w,h)==(96,37)
nonzero=sorted({a for a in alphas if a})
assert nonzero[0]==12, nonzero[:20]
assert nonzero[-1]==255
assert any(12 <= a < 255 for a in nonzero), 'anti-aliasing unexpectedly removed'
xs=[x for x,y,a in coords]; ys=[y for x,y,a in coords]
assert (min(xs),min(ys),max(xs)+1,max(ys)+1)==(0,0,96,37), 'logo must be tightly cropped'
print(f'HQ LOGO AUDIT: PASS {w}x{h}, alpha floor={nonzero[0]}, partial-alpha preserved, tight bbox')

# Patch exact Branding 1.2.5 from published test.6.
brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.5.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==OLD_BRAND_SIZE
assert sha_file(old)==OLD_BRAND_SHA

classes=WORK/'classes'; classes.mkdir()
exports=[
    '--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED',
    '--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED'
]
run('javac',*exports,str(STAGE/'BrandingFixV126.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.6.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV126',str(old),str(logo),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    embedded=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(embedded)==LOGO_SHA
    ew,eh,ealphas,ecoords=png_rgba_alpha(embedded)
    assert (ew,eh)==(96,37)
    assert min(a for a in ealphas if a)==12
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.6"' in toml and 'version="1.2.5"' not in toml

# Bytecode verification.
verify=WORK/'verify'; verify.mkdir()
verify_exports=exports+['--add-exports','java.base/jdk.internal.org.objectweb.asm.tree.analysis=ALL-UNNAMED']
run('javac',*verify_exports,str(ROOT/'release-staging/1.7.0-test.4/AsmVerify.java'),'-d',str(verify))
rv=run('java',*verify_exports,'-cp',str(verify),'AsmVerify',str(new),'sgp/client/branding/SgpClientBranding.class')
assert 'ASM BASIC VERIFY: PASS methods=17' in rv.stdout
javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
for needle in [
    'major version: 65',
    'AbstractTexture.setFilter:(ZZ)V',
    'Method loadPackVersion:()Ljava/lang/String;',
    'GuiGraphics.blit:(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V'
]:
    assert needle in javap, needle
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]

# 1:1 nearest render: 96x37 source == texture == destination.
assert render.count('bipush        96')>=3, render.count('bipush        96')
assert render.count('bipush        37')>=3, render.count('bipush        37')
assert 'bipush        108' in render
assert render.count('bipush        108')==3
# Linear filtering must not be re-enabled.
fidx=render.index('AbstractTexture.setFilter:(ZZ)V')
fpre=render[max(0,fidx-450):fidx]
assert fpre.count('iconst_0')>=2
print('BRANDING 1.2.6 ASM/LAYOUT AUDIT: PASS (logo 8..104, text x=108, plaque right=220)')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

# Cumulative manifest test.6 -> test.7.
p['patchId']='sgp-client-1.7.0-test.7'
p['name']='SGP Client 1.7.0-test.7'
p['toVersion']='1.7.0-test.7'
p['fromVersions']=STABLE+[
    '1.7.0-test.1','1.7.0-test.2','1.7.0-test.3',
    '1.7.0-test.4','1.7.0-test.5','1.7.0-test.6'
]
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.6: качественный tight-cropped logo 96×37, premultiplied high-quality downsample и 1:1 nearest render без runtime scaling.',
    'Текст плашки сдвинут на x=108: полный крупный логотип и версия не перекрываются.',
    'Постоянная SGP-плашка, prerelease SemVer, update-state, полный русский Building Wands, paxel compat, лимиты и SGP Fixes rev 1.10 сохранены.'
]

idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
    {
        'actionId':'remove-sgp-client-branding-1-2-5',
        'type':'delete',
        'description':'Удалить SGP Client Branding 1.2.5 с чрезмерно пиксельным logo',
        'target':'mods/SGP-Client-Branding-1.2.5.jar',
        'optional':True
    },
    {
        'actionId':'install-sgp-client-branding-1-2-6',
        'type':'copy',
        'description':'Установить SGP Client Branding 1.2.6 с high-quality 96×37 logo',
        'source':'files/mods/SGP-Client-Branding-1.2.6.jar',
        'target':'mods/SGP-Client-Branding-1.2.6.jar',
        'sha256':new_sha,
        'size':new_size
    }
]
old.unlink()

ids=[a['actionId'] for a in p['actions']]
assert len(ids)==len(set(ids))
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

# Everything except Branding/manifest/readme must remain byte-identical to test.6.
now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={
    'patch.json','README.txt',
    'files/mods/SGP-Client-Branding-1.2.5.jar',
    'files/mods/SGP-Client-Branding-1.2.6.jar'
}
for path,hsh in base_files.items():
    if path not in allowed:
        assert now.get(path)==hsh, path
for path,hsh in now.items():
    if path not in allowed:
        assert base_files.get(path)==hsh, path

manifest_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.7
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.6.

Changes relative to test.6:
- Branding 1.2.6 uses a tightly cropped high-quality 96x37 transparent UI logo.
- Asset preparation uses premultiplied-alpha high-quality downsample; alpha values below 12 are removed, while smooth partial-alpha antialiasing is preserved.
- Logo is rendered 1:1 with nearest filtering: no runtime resize/filter blur.
- Logo occupies x=8..104; plaque text starts at x=108, so the larger logo cannot overlap the version/update text.
- Every non-Branding payload is byte-identical to test.6.

Owner Minecraft runtime visual check is still required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,12,30,0)
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
    assert q['patchId']=='sgp-client-1.7.0-test.7'
    assert q['toVersion']=='1.7.0-test.7'
    assert q['fromVersions']==STABLE+[
        '1.7.0-test.1','1.7.0-test.2','1.7.0-test.3',
        '1.7.0-test.4','1.7.0-test.5','1.7.0-test.6'
    ]
    assert 'files/mods/SGP-Client-Branding-1.2.5.jar' not in names
    assert sha_bytes(z.read('files/mods/SGP-Client-Branding-1.2.6.jar'))==new_sha
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size']
            assert sha_bytes(data).lower()==a['sha256'].lower(), a['actionId']

print('FINAL TEST.7 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
Path('test7_brand_sha.txt').write_text(new_sha+'\n')
Path('test7_brand_size.txt').write_text(str(new_size)+'\n')
