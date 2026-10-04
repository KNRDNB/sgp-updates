from __future__ import annotations
import base64, hashlib, json, shutil, struct, zlib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/'release-staging/1.7.0-test.8'
BASE=ROOT/'SGP_ClientPatch_1.7.0-test.7.zip'
WORK=ROOT/'.work-170t8'
BUILD=WORK/'build'
OUT=ROOT/'SGP_ClientPatch_1.7.0-test.8.zip'

BASE_SHA='3bafd98c071813bf1cf0b5062b560ff2c36059f9eeb8dd3a3af7efdd37fed1fa'
OLD_BRAND_SHA='1da89ef5a67b79869b9beed5d9670e87dd877f96e686c10545ce624e6e99e9fb'
OLD_BRAND_SIZE=18690
LOGO_SHA='2aede6f23278b786d9bdaaabf1593ad701362b83c8ffe51b026e8fc8e25dc76e'
LOGO_SIZE=5876
STABLE=['1.0.0','1.0.1','1.0.2','1.0.3','1.1.0','1.2.0','1.2.1','1.3.0','1.3.1','1.3.2','1.3.3','1.4.0','1.5.0','1.5.1','1.5.2','1.5.3','1.6.0','1.6.1','1.6.2']

def sha_bytes(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p:Path)->str:
    return sha_bytes(p.read_bytes())

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

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

manifest_path=BUILD/'patch.json'
p=json.loads(manifest_path.read_text('utf-8'))
assert p['patchId']=='sgp-client-1.7.0-test.7'
assert p['toVersion']=='1.7.0-test.7'
assert p['fromVersions']==STABLE+[
    '1.7.0-test.1','1.7.0-test.2','1.7.0-test.3',
    '1.7.0-test.4','1.7.0-test.5','1.7.0-test.6'
]
assert '1.5.4' not in p['fromVersions']

base_files={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}

# Exact owner-approved-quality geometry from test.7, with edge RGB decontamination:
# alpha <48 removed; alpha 48..191 keeps smooth coverage but RGB is inherited from the
# nearest solid edge color, eliminating isolated cyan/teal fringe pixels.
logo=WORK/'sgp_logo_96x37_decontaminated.png'
logo.write_bytes(base64.b64decode((STAGE/'sgp_logo_96x37_decontaminated.b64').read_text('ascii')))
assert logo.stat().st_size==LOGO_SIZE
assert sha_file(logo)==LOGO_SHA
w,h,pixels=parse_rgba_png(logo.read_bytes())
assert (w,h)==(96,37)
alphas=[a for _,_,_,_,_,a in pixels if a>0]
assert min(alphas)==48
assert any(48<=a<255 for a in alphas)
# No cyan/teal chromatic outliers remain at any visible pixel.
cyan=[px for px in pixels if px[5]>0 and px[4]>px[2]+30 and px[3]>px[2]+20]
assert not cyan, cyan[:10]
print('TEST.8 LOGO AUDIT: PASS 96x37, alpha floor=48, smooth partial alpha preserved, cyan/teal outliers=0')

brand_actions=[a for a in p['actions'] if a['type']=='copy' and a.get('target')=='mods/SGP-Client-Branding-1.2.6.jar']
assert len(brand_actions)==1
ba=brand_actions[0]
old=BUILD/ba['source']
assert old.stat().st_size==OLD_BRAND_SIZE
assert sha_file(old)==OLD_BRAND_SHA

# Build Branding 1.2.7 by changing only mod version metadata + logo resource.
new=BUILD/'files/mods/SGP-Client-Branding-1.2.7.jar'
class_entry='sgp/client/branding/SgpClientBranding.class'
logo_entry='assets/sgp_client_branding/textures/gui/sgp_logo.png'
toml_entry='META-INF/neoforge.mods.toml'
with zipfile.ZipFile(old) as zin:
    assert zin.testzip() is None
    old_class=zin.read(class_entry)
    old_logo=zin.read(logo_entry)
    old_toml=zin.read(toml_entry).decode('utf-8')
    assert 'version="1.2.6"' in old_toml and old_toml.count('version="1.2.6"')==1
    new_toml=old_toml.replace('version="1.2.6"','version="1.2.7"')
    entries=[(zi, zin.read(zi.filename)) for zi in zin.infolist() if not zi.is_dir()]

with zipfile.ZipFile(new,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as zout:
    for zi,data in entries:
        if zi.filename==toml_entry:
            data=new_toml.encode('utf-8')
        elif zi.filename==logo_entry:
            data=logo.read_bytes()
        ni=zipfile.ZipInfo(zi.filename,zi.date_time)
        ni.compress_type=zipfile.ZIP_DEFLATED
        ni.external_attr=zi.external_attr
        ni.comment=zi.comment
        ni.extra=zi.extra
        zout.writestr(ni,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

new_sha=sha_file(new); new_size=new.stat().st_size
with zipfile.ZipFile(new) as z:
    assert z.testzip() is None
    assert sha_bytes(z.read(class_entry))==sha_bytes(old_class), 'Branding class bytecode changed unexpectedly'
    assert sha_bytes(z.read(logo_entry))==LOGO_SHA
    nt=z.read(toml_entry).decode('utf-8')
    assert 'version="1.2.7"' in nt and 'version="1.2.6"' not in nt
print('BRANDING 1.2.7 AUDIT: PASS; class byte-identical to 1.2.6')
print('BRAND_SHA='+new_sha)
print('BRAND_SIZE='+str(new_size))

p['patchId']='sgp-client-1.7.0-test.8'
p['name']='SGP Client 1.7.0-test.8'
p['toVersion']='1.7.0-test.8'
p['fromVersions']=STABLE+[
    '1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4',
    '1.7.0-test.5','1.7.0-test.6','1.7.0-test.7'
]
p['summary']=[
    'Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.',
    'SGP Client Branding 1.2.7: качество/геометрия test.7 сохранены, но edge RGB очищен от cyan/teal fringe; очень слабый alpha <48 удалён.',
    'Branding bytecode/layout не менялись относительно 1.2.6: logo 96×37, 1:1 render, text x=108.',
    'Building Wands, перевод, paxel compat, лимиты и SGP Fixes rev 1.10 сохранены без изменений.'
]

idx=p['actions'].index(ba)
p['actions'][idx:idx+1]=[
    {
        'actionId':'remove-sgp-client-branding-1-2-6',
        'type':'delete',
        'description':'Удалить SGP Client Branding 1.2.6 с цветным fringe на logo',
        'target':'mods/SGP-Client-Branding-1.2.6.jar',
        'optional':True
    },
    {
        'actionId':'install-sgp-client-branding-1-2-7',
        'type':'copy',
        'description':'Установить SGP Client Branding 1.2.7 с decontaminated HQ logo',
        'source':'files/mods/SGP-Client-Branding-1.2.7.jar',
        'target':'mods/SGP-Client-Branding-1.2.7.jar',
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

# Everything except Branding/manifest/readme stays byte-identical to test.7.
now={f.relative_to(BUILD).as_posix():sha_file(f) for f in BUILD.rglob('*') if f.is_file()}
allowed={
    'patch.json','README.txt',
    'files/mods/SGP-Client-Branding-1.2.6.jar',
    'files/mods/SGP-Client-Branding-1.2.7.jar'
}
for path,hsh in base_files.items():
    if path not in allowed:
        assert now.get(path)==hsh, path
for path,hsh in now.items():
    if path not in allowed:
        assert base_files.get(path)==hsh, path

manifest_path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n','utf-8')
(BUILD/'README.txt').write_text('''SGP Client 1.7.0-test.8
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install: all accepted stable SGP Client 1.0.0–1.6.2.
Forward repair: 1.7.0-test.1 through 1.7.0-test.7.

Changes relative to test.7:
- Branding 1.2.7 keeps the same 96x37 geometry and byte-identical Java class/layout.
- The logo raster is edge-decontaminated: isolated cyan/teal fringe RGB is removed.
- Very weak edge coverage below alpha 48 is removed; normal partial-alpha antialiasing remains.
- No runtime resize/filter/layout change: logo remains 1:1, text x=108.
- Every non-Branding payload is byte-identical to test.7.

Owner Minecraft runtime visual check is required before stable 1.7.0.
''','utf-8')

fixed=(2026,10,4,13,30,0)
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
    assert q['patchId']=='sgp-client-1.7.0-test.8'
    assert q['toVersion']=='1.7.0-test.8'
    assert q['fromVersions']==STABLE+[
        '1.7.0-test.1','1.7.0-test.2','1.7.0-test.3','1.7.0-test.4',
        '1.7.0-test.5','1.7.0-test.6','1.7.0-test.7'
    ]
    assert 'files/mods/SGP-Client-Branding-1.2.6.jar' not in names
    assert sha_bytes(z.read('files/mods/SGP-Client-Branding-1.2.7.jar'))==new_sha
    for a in q['actions']:
        if a['type']=='copy':
            data=z.read(a['source'])
            assert len(data)==a['size']
            assert sha_bytes(data).lower()==a['sha256'].lower(), a['actionId']

print('FINAL TEST.8 STATIC VALIDATION: PASS')
print('CANDIDATE_SHA='+sha_file(OUT))
print('CANDIDATE_SIZE='+str(OUT.stat().st_size))
Path('test8_brand_sha.txt').write_text(new_sha+'\n')
Path('test8_brand_size.txt').write_text(str(new_size)+'\n')
