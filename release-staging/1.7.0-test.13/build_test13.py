from __future__ import annotations
import base64, binascii, hashlib, json, shutil, struct, subprocess, zlib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.13'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.12.zip'
WORK=ROOT/'.work-170t13'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.13.zip'

BASE_SHA='3320ec383dd04fc30cde105639f1738911256a939e7a2aae8708f1468e4e5563'
OLD_BRAND_SHA='85ba0e384355c71dcb1822e584e4159736b8c99ee2c3fe2ba13138bb76cf29ec'
OLD_BRAND_SIZE=16218
TEST5_FULL_LOGO_SHA='993d39e756438788a85536a8324a5b20fe71281ae25f4d4192854e5cc111f53e'
TEST5_FULL_LOGO_B64='''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'''
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']
TESTS=['1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4','1.7.0-test.5','1.7.0-test.6','1.7.0-test.7','1.7.0-test.8','1.7.0-test.9','1.7.0-test.10','1.7.0-test.11','1.7.0-test.12']

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def sha_file(p:Path)->str: return sha_bytes(p.read_bytes())
def run(*a:str):
    cp=subprocess.run(a,check=False,text=True,capture_output=True)
    if cp.returncode!=0:
        print("COMMAND FAILED:",a); print(cp.stdout); print(cp.stderr); cp.check_returncode()
    return cp

def parse_rgba_png(data:bytes):
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    pos=8; width=height=None; idat=b''
    while pos<len(data):
        n=struct.unpack('>I',data[pos:pos+4])[0]
        typ=data[pos+4:pos+8]; chunk=data[pos+8:pos+8+n]; pos+=12+n
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
            left=scan[x-bpp] if x>=bpp else 0; up=prev[x]; ul=prev[x-bpp] if x>=bpp else 0
            if ft==1: scan[x]=(scan[x]+left)&255
            elif ft==2: scan[x]=(scan[x]+up)&255
            elif ft==3: scan[x]=(scan[x]+((left+up)//2))&255
            elif ft==4: scan[x]=(scan[x]+paeth(left,up,ul))&255
            elif ft!=0: raise AssertionError(ft)
        rows.append(bytes(scan)); prev=scan
    pixels=[]
    for y,row in enumerate(rows):
        for x in range(0,stride,4):
            pixels.append((x//4,y,row[x],row[x+1],row[x+2],row[x+3]))
    return width,height,pixels

def encode_rgba_png(width:int,height:int,pixels):
    by={(x,y):(r,g,b,a) for x,y,r,g,b,a in pixels}
    raw=bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width): raw.extend(by[(x,y)])
    def chunk(t,p):
        return struct.pack('>I',len(p))+t+p+struct.pack('>I',binascii.crc32(t+p)&0xffffffff)
    ihdr=struct.pack('>IIBBBBB',width,height,8,6,0,0,0)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',ihdr)+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')

def extract_complete_test5_cube(full:bytes):
    w,h,pixels=parse_rgba_png(full)
    assert (w,h)==(144,48)
    alpha={(x,y):a for x,y,r,g,b,a in pixels}
    col_has=[any(alpha[(x,y)]>0 for y in range(h)) for x in range(w)]
    # Find the first real transparent separator after the cube. Require >=2 empty
    # columns and visible wordmark pixels after it. Keep 2 transparent separator
    # columns in the cube texture so linear filtering cannot clip the right edge.
    gap_start=None; gap_len=0
    x=32
    while x<80:
        if not col_has[x]:
            j=x
            while j<80 and not col_has[j]: j+=1
            if j-x>=2 and any(col_has[j:]):
                gap_start=x; gap_len=j-x; break
            x=j
        else:
            x+=1
    assert gap_start is not None, 'could not detect transparent cube/wordmark separator'
    crop_w=gap_start+min(2,gap_len)
    assert 49<=crop_w<=64, (gap_start,gap_len,crop_w)
    crop=[(x,y,r,g,b,a) for x,y,r,g,b,a in pixels if x<crop_w]
    occupied=[(x,y) for x,y,r,g,b,a in crop if a>0]
    assert occupied
    # Critical regression proof: the old 48px crop was incomplete.
    assert max(x for x,y in occupied)>=48, max(x for x,y in occupied)
    assert all(not col_has[x] for x in range(gap_start,crop_w))
    return encode_rgba_png(crop_w,48,crop), crop_w, gap_start, gap_len

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest=BUILD/'patch.json'
p=json.loads(manifest.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.12'
assert p['toVersion']=='1.7.0-test.12'
assert p['fromVersions']==STABLE+TESTS[:-1]
base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.10.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==OLD_BRAND_SIZE
assert sha_file(old)==OLD_BRAND_SHA

full=base64.b64decode(TEST5_FULL_LOGO_B64)
assert sha_bytes(full)==TEST5_FULL_LOGO_SHA
cube,cube_w,gap_start,gap_len=extract_complete_test5_cube(full)
cube_path=WORK/'sgp_test5_cube_complete.png'
cube_path.write_bytes(cube)
cube_sha=sha_bytes(cube)
dest_w=(cube_w+1)//2
text_x=8+dest_w+4
delta=text_x-36
right=164+delta
print(f'COMPLETE TEST5 CUBE: PASS crop={cube_w}x48 gap_start={gap_start} gap_len={gap_len} dest={dest_w}x24 textX={text_x} right={right}')
print('CUBE_SHA='+cube_sha)
print('CUBE_SIZE='+str(len(cube)))

classes=WORK/'classes'; classes.mkdir()
exports=['--add-exports','java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED','--add-exports','java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED']
run('javac',*exports,str(STAGE/'BrandingFixV1211.java'),'-d',str(classes))
new=BUILD/'files/mods/SGP-Client-Branding-1.2.11.jar'
run('java',*exports,'-cp',str(classes),'BrandingFixV1211',str(old),str(cube_path),str(new))
new_sha=sha_file(new); new_size=new.stat().st_size

with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    logo=z.read('assets/sgp_client_branding/textures/gui/sgp_logo.png')
    assert sha_bytes(logo)==cube_sha
    assert int.from_bytes(logo[16:20],'big')==cube_w
    assert int.from_bytes(logo[20:24],'big')==48
    toml=z.read('META-INF/neoforge.mods.toml').decode('utf-8')
    assert 'version="1.2.11"' in toml and 'version="1.2.10"' not in toml
    cls=z.read('sgp/client/branding/SgpClientBranding.class')
    assert 'Версия SGP: '.encode('utf-8') in cls

javap=run('javap','-classpath',str(new),'-p','-c','-v','sgp.client.branding.SgpClientBranding').stdout
render=javap[javap.index('private static void onScreenRenderPost'):javap.index('private static void startUpdateCheck')]
for value,count in [(right,4),(right-1,1)]:
    token=('bipush        '+str(value)) if value<=127 else ('sipush        '+str(value))
    assert render.count(token)==count,(token,render.count(token))
for value in [8,12,dest_w,24,cube_w,48,text_x]:
    token=('bipush        '+str(value)) if value<=127 else ('sipush        '+str(value))
    assert token in render,(value,token)
print('BRANDING 1.2.11 FULL-CUBE/LAYOUT AUDIT: PASS')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

p['patchId']='sgp-client-1.7.0-test.13'
p['name']='SGP Client 1.7.0-test.13'
p['toVersion']='1.7.0-test.13'
p['fromVersions']=STABLE+TESTS
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.11: исправлен реально обрезанный cube source — граница теперь определяется по прозрачному separator исходного test.5 raster, с сохранением прозрачного padding.',
    'Компактная плашка test.12 и текст «Версия SGP: <version>» сохранены с минимальной компенсацией ширины под полный cube.',
    'Create Rope Pulley maxRopeLength=512 сохранён без изменений.'
]
idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
    {'actionId':'remove-sgp-client-branding-1-2-10','type':'delete','description':'Удалить SGP Client Branding 1.2.10 с обрезанным 48px cube source','target':'mods/SGP-Client-Branding-1.2.10.jar','optional':True},
    {'actionId':'install-sgp-client-branding-1-2-11','type':'copy','description':'Установить SGP Client Branding 1.2.11 с полным test.5 cube и компактной плашкой','source':'files/mods/SGP-Client-Branding-1.2.11.jar','target':'mods/SGP-Client-Branding-1.2.11.jar','sha256':new_sha,'size':new_size}
]
old.unlink()

ids=[a['actionId'] for a in p['actions']]
assert len(ids)==len(set(ids))
rope=[a for a in p['actions'] if a.get('actionId')=='increase-create-rope-pulley-max-length-512']
assert len(rope)==1 and rope[0]['edits']==[{'op':'set','path':'kinetics.contraptions.maxRopeLength','value':512,'createIfMissing':False}]

for a in p['actions']:
    target=(a.get('target') or '').replace('\\','/')
    assert not target.startswith(('.sgp/','saves/','journeymap/')) and target!='servers.dat' and '..' not in target.split('/')
    if a['type']=='copy':
        f=BUILD/a['source']
        assert f.is_file() and f.stat().st_size==a['size'] and sha_file(f).lower()==a['sha256'].lower(),a['actionId']

now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={'patch.json','README.txt','files/mods/SGP-Client-Branding-1.2.10.jar','files/mods/SGP-Client-Branding-1.2.11.jar'}
for path,hsh in base_files.items():
    if path not in allowed: assert now.get(path)==hsh,path
for path,hsh in now.items():
    if path not in allowed: assert base_files.get(path)==hsh,path

manifest.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text(f'''SGP Client 1.7.0-test.13
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.12.

Changes relative to test.12:
- Branding 1.2.11 fixes the actual cube-source clipping.
- Instead of hard-cropping the test.5 source at 48px, the builder detects the transparent separator before the old SGP wordmark and keeps 2 transparent padding columns.
- Exact resulting cube source: {cube_w}x48; render destination: {dest_w}x24 at x=8/y=12.
- Text starts at x={text_x}; compact plaque right edge is adjusted only by the same delta to preserve the test.12 right padding.
- Raster SGP wordmark remains removed; normal text remains "Версия SGP: <version>".
- Create maxRopeLength=512 remains unchanged.

Owner Minecraft runtime visual check is required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,19,30,0)
with zipfile.ZipFile(OUT,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob('*') if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read('patch.json'))
    assert q['patchId']=='sgp-client-1.7.0-test.13'
    assert q['toVersion']=='1.7.0-test.13'
    assert q['fromVersions']==STABLE+TESTS
    assert 'files/mods/SGP-Client-Branding-1.2.10.jar' not in z.namelist()
    brand=z.read('files/mods/SGP-Client-Branding-1.2.11.jar')
    assert sha_bytes(brand)==new_sha
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size'] and sha_bytes(data).lower()==a['sha256'].lower(),a['actionId']

print('FINAL TEST.13 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
Path('test13_brand_sha.txt').write_text(new_sha+'\n')
Path('test13_brand_size.txt').write_text(str(new_size)+'\n')
Path('test13_cube_sha.txt').write_text(cube_sha+'\n')
Path('test13_cube_width.txt').write_text(str(cube_w)+'\n')
Path('test13_dest_width.txt').write_text(str(dest_w)+'\n')
Path('test13_text_x.txt').write_text(str(text_x)+'\n')
Path('test13_right.txt').write_text(str(right)+'\n')
