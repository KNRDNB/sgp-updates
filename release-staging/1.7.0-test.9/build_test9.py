from __future__ import annotations
import binascii, hashlib, json, shutil, struct, subprocess, zlib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.9'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.8.zip'
WORK=ROOT/'.work-170t9'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.9.zip'

BASE_SHA='e40d39d1ab657c4a31870bc6ac229526bc8207687dabc7457d405271b67c75a9'
OLD_BRAND_SHA='899a898cd512438011ef367d24437f9aea2440919a0626f01047957d9bc967ba'
OLD_BRAND_SIZE=18128
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']
TESTS=['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5','1.7.0-test.6','1.7.0-test.7','1.7.0-test.8']

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p:Path)->str:
    return sha_bytes(p.read_bytes())

def run(*a:str):
    cp=subprocess.run(a,check=False,text=True,capture_output=True)
    if cp.returncode!=0:
        print("COMMAND FAILED:",a)
        print("STDOUT:\n"+cp.stdout)
        print("STDERR:\n"+cp.stderr)
        cp.check_returncode()
    return cp

def parse_rgba_png(data:bytes):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; width=height=None; idat=b''
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
    pixels=[]
    for y,row in enumerate(rows):
        for x in range(0,stride,4):
            pixels.append((x//4,y,row[x],row[x+1],row[x+2],row[x+3]))
    return width,height,pixels

def encode_rgba_png(width:int,height:int,pixels:list[tuple[int,int,int,int,int,int]])->bytes:
    bypos={(x,y):(r,g,b,a) for x,y,r,g,b,a in pixels}
    raw=bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(bypos[(x,y)])
    def chunk(kind:bytes,payload:bytes)->bytes:
        return struct.pack('>I',len(payload))+kind+payload+struct.pack('>I',binascii.crc32(kind+payload)&0xffffffff)
    ihdr=struct.pack('>IIBBBBB',width,height,8,6,0,0,0)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')

def crop_cube_only(data:bytes)->tuple[bytes,int,int]:
    width,height,pixels=parse_rgba_png(data)
    assert (width,height)==(96,37)
    alpha={(x,y):a for x,y,r,g,b,a in pixels}
    col_has=[any(alpha[(x,y)]>0 for y in range(height)) for x in range(width)]
    assert col_has[0], 'test.8 logo should be tight on the left'
    cut=None
    for x in range(24,55):
        if not col_has[x] and any(col_has[x+1:]):
            cut=x
            break
    assert cut is not None, 'could not detect transparent gap after cube'
    assert 24<=cut<=44, cut
    assert any(col_has[cut+1:]), 'SGP letters expected after cube gap'
    cropped=[(x,y,r,g,b,a) for x,y,r,g,b,a in pixels if x<cut]
    assert any(a>0 for x,y,r,g,b,a in cropped)
    bbox=[(x,y) for x,y,r,g,b,a in cropped if a>0]
    assert min(x for x,y in bbox)==0
    assert max(x for x,y in bbox)==cut-1
    out=encode_rgba_png(cut,height,cropped)
    return out,cut,height

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest_path=BUILD/'patch.json'
p=json.loads(manifest_path.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.8'
assert p['toVersion']=='1.7.0-test.8'
assert p['fromVersions']==STABLE+TESTS[:-1]
assert '1.5.4' not in p['fromVersions']

base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.7.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==OLD_BRAND_SIZE
assert sha_file(old)==OLD_BRAND_SHA

class_entry='sgp/client/branding/SgpClientBranding.class'
logo_entry='assets/sgp_client_branding/textures/gui/sgp_logo.png'
toml_entry='META-INF/neoforge.mods.toml'
with zipfile.ZipFile(old) as zin:
    assert zin.testzip() is None
    old_logo=zin.read(logo_entry)
    ow,oh,opixels=parse_rgba_png(old_logo)
    assert (ow,oh)==(96,37)

cube_bytes,cube_w,cube_h=crop_cube_only(old_logo)
cube=WORK/'sgp_cube_only.png'
cube.write_bytes(cube_bytes)
cube_sha=sha_file(cube)
cube_size=cube.stat().st_size
text_x=8+cube_w+4

cw,ch,cpixels=parse_rgba_png(cube_bytes)
assert (cw,ch)==(cube_w,37)
alphas=[a for x,y,r,g,b,a in cpixels if a>0]
assert alphas and min(alphas)>=48
cyan=[px for px in cpixels if px[5]>0 and px[4]>px[2]+30 and px[3]>px[2]+20]
assert not cyan, cyan[:10]
print(f'CUBE-ONLY LOGO AUDIT: PASS {cube_w}x37, exact left cube retained from test.8, alpha floor={min(alphas)}, cyan/teal outliers=0')
print('CUBE_SHA='+cube_sha)
print('CUBE_SIZE='+str(cube_size))
print('TEXT_X='+str(text_x))

classes=WORK/'classes'; classes.mkdir()
exports=[
    '--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED',
    '--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED'
]
run('javac',*exports,str(STAGE/'BrandingFixV128.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.8.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV128',str(old),str(cube),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    embedded=z.read(logo_entry)
    assert sha_bytes(embedded)==cube_sha
    ew,eh,epixels=parse_rgba_png(embedded)
    assert (ew,eh)==(cube_w,37)
    toml=z.read(toml_entry).decode('utf-8')
    assert 'version="1.2.8"' in toml and 'version="1.2.7"' not in toml
    cls=z.read(class_entry)
    assert 'Версия SGP: '.encode('utf-8') in cls
    assert 'Версия: '.encode('utf-8') not in cls

verify=WORK/'verify'; verify.mkdir()
verify_exports=exports+['--add-exports','java.base/jdk.internal.org.objectweb.asm.tree.analysis=ALL-UNNAMED']
run('javac',*verify_exports,str(ROOT/'release-staging/1.7.0-test.4/AsmVerify.java'),'-d',str(verify))
rv=run('java',*verify_exports,'-cp',str(verify),'AsmVerify',str(new),class_entry)
assert 'ASM BASIC VERIFY: PASS methods=17' in rv.stdout
javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
for needle in [
    'major version: 65',
    'AbstractTexture.setFilter:(ZZ)V',
    'Method loadPackVersion:()Ljava/lang/String;',
    'GuiGraphics.blit:(Lnet/minecraft/resources/ResourceLocation;IIIIFFIIII)V',
    'Версия SGP: '
]:
    assert needle in javap, needle
assert 'Версия: ' not in javap
print(f'BRANDING 1.2.8 ASM/LAYOUT AUDIT: PASS (cube 8..{8+cube_w}, text x={text_x}, plaque right unchanged)')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

p['patchId']='sgp-client-1.7.0-test.9'
p['name']='SGP Client 1.7.0-test.9'
p['toVersion']='1.7.0-test.9'
p['fromVersions']=STABLE+TESTS
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.8: raster теперь содержит только жёлтый куб; крупная raster-надпись SGP удалена.',
    'Версия выводится обычным Minecraft-текстом как «Версия SGP: <version>»; текст сдвинут к кубу.',
    'Куб взят byte/pixel-exact из очищенного test.8 logo; все non-Branding payload сохранены без изменений.'
]

idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
    {
        'actionId':'remove-sgp-client-branding-1-2-7',
        'type':'delete',
        'description':'Удалить SGP Client Branding 1.2.7 с raster-надписью SGP',
        'target':'mods/SGP-Client-Branding-1.2.7.jar',
        'optional':True
    },
    {
        'actionId':'install-sgp-client-branding-1-2-8',
        'type':'copy',
        'description':'Установить SGP Client Branding 1.2.8: cube-only icon + текст «Версия SGP»',
        'source':'files/mods/SGP-Client-Branding-1.2.8.jar',
        'target':'mods/SGP-Client-Branding-1.2.8.jar',
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

now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={
    'patch.json','README.txt',
    'files/mods/SGP-Client-Branding-1.2.7.jar',
    'files/mods/SGP-Client-Branding-1.2.8.jar'
}
for path,hsh in base_files.items():
    if path not in allowed:
        assert now.get(path)==hsh, path
for path,hsh in now.items():
    if path not in allowed:
        assert base_files.get(path)==hsh, path

manifest_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text(f'''SGP Client 1.7.0-test.9
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.8.

Changes relative to test.8:
- Branding 1.2.8 removes the raster SGP wordmark entirely.
- The texture now contains only the existing cleaned yellow cube cropped directly from the exact test.8 logo.
- The normal version label is rendered as Minecraft text: "Версия SGP: <version>".
- Cube is rendered 1:1 at x=8; text starts at x={text_x}; plaque geometry/right edge stay unchanged.
- Every non-Branding payload is byte-identical to test.8.

Owner Minecraft runtime visual check is required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,16,0,0)
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
    assert q['patchId']=='sgp-client-1.7.0-test.9'
    assert q['toVersion']=='1.7.0-test.9'
    assert q['fromVersions']==STABLE+TESTS
    assert 'files/mods/SGP-Client-Branding-1.2.7.jar' not in names
    brand=z.read('files/mods/SGP-Client-Branding-1.2.8.jar')
    assert sha_bytes(brand)==new_sha
    with zipfile.ZipFile(__import__('io').BytesIO(brand)) as bz:
        emb=bz.read(logo_entry)
        assert sha_bytes(emb)==cube_sha
        assert int.from_bytes(emb[16:20],'big')==cube_w
        assert int.from_bytes(emb[20:24],'big')==37
        cls=bz.read(class_entry)
        assert 'Версия SGP: '.encode('utf-8') in cls
        assert 'Версия: '.encode('utf-8') not in cls
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size']
            assert sha_bytes(data).lower()==a['sha256'].lower(), a['actionId']

print('FINAL TEST.9 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
Path('test9_brand_sha.txt').write_text(new_sha+'\n')
Path('test9_brand_size.txt').write_text(str(new_size)+'\n')
Path('test9_cube_sha.txt').write_text(cube_sha+'\n')
Path('test9_cube_size.txt').write_text(str(cube_size)+'\n')
Path('test9_cube_width.txt').write_text(str(cube_w)+'\n')
Path('test9_text_x.txt').write_text(str(text_x)+'\n')
