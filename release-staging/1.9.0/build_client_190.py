import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.2.zip"
MOD=ROOT/"SGP-Shapeless-Nether-Portals-1.0.0.jar"
OUT=ROOT/"SGP_ClientPatch_1.9.0.zip"
WORK=ROOT/".work-190-stable"
BUILD=WORK/"build"

BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"
MOD_TARGET="mods/SGP-Shapeless-Nether-Portals-1.0.0.jar"
MOD_SOURCE="files/"+MOD_TARGET

ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0",
 "1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"
]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root):
    return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file()
mod_sha=shaf(MOD)
mod_size=MOD.stat().st_size

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.2"
assert p["toVersion"]=="1.8.2"
for v in ACCEPTED[:-1]:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

before=hashes(BUILD)

p["patchId"]="sgp-client-1.9.0"
p["name"]="SGP Client 1.9.0"
p["toVersion"]="1.9.0"
assert "1.8.2" not in p["fromVersions"]
p["fromVersions"]=list(p["fromVersions"])+["1.8.2"]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "Direct stable release explicitly requested by the owner; separate TEST runtime gate waived for this release.",
 "Adds SGP Shapeless Nether Portals 1.0.0 for enclosed vertical obsidian Nether portal frames of arbitrary shape.",
 "Vanilla Nether portal blocks, teleportation and portal linking remain in use; only frame-shape validation/fill is extended.",
 "Implementation is dependency-free beyond Minecraft/NeoForge and includes required MIT attribution for adapted Nicer Portals portal-shape logic."
]

payload=BUILD/MOD_SOURCE
payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,payload)

p["actions"].append({
 "actionId":"install-sgp-shapeless-nether-portals-1-0-0",
 "type":"copy",
 "description":"Установить SGP Shapeless Nether Portals 1.0.0",
 "source":MOD_SOURCE,
 "target":MOD_TARGET,
 "sha256":mod_sha,
 "size":mod_size
})

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.9.0\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Direct stable owner-requested release. Runtime TEST gate explicitly waived by owner.\n"
 "Adds SGP Shapeless Nether Portals 1.0.0.\n"
 "Build enclosed vertical obsidian Nether portal frames in arbitrary shapes (for example circles), then ignite normally.\n"
 "Maximum scanned interior: 2304 portal blocks. Vanilla portal travel/linking remains unchanged.\n",
 "utf-8"
)

after=hashes(BUILD)
allowed={"patch.json","README.txt",MOD_SOURCE}
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed==allowed,changed

fixed=(2026,10,6,1,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.9.0"
    assert q["toVersion"]=="1.9.0"
    assert q["fromVersions"][-1]=="1.8.2"
    for v in ACCEPTED: assert v in q["fromVersions"],v
    assert "1.5.4" not in q["fromVersions"]
    a=[x for x in q["actions"] if x.get("target")==MOD_TARGET]
    assert len(a)==1
    b=z.read(a[0]["source"])
    assert hashlib.sha256(b).hexdigest()==mod_sha
    assert len(b)==mod_size

Path("portal_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("portal_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")
print("CLIENT_190_CUMULATIVE_AUDIT_PASS")
print("MOD_SHA="+mod_sha)
print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
