import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.1-test.2.zip"
OUT=ROOT/"SGP_ClientPatch_1.8.1.zip"
WORK=ROOT/".work-181-stable"
BUILD=WORK/"build"
BASE_SHA="810111faa329becbdd87b666af6fc9e955167095f25b3d3d69d0ba37d3a78af3"

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()

assert BASE.is_file() and shaf(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

mp=BUILD/"patch.json"
p=json.loads(mp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.1-test.2"
assert p["toVersion"]=="1.8.1-test.2"
assert p["fromVersions"][-1]=="1.8.1-test.1"
actions=json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))
before={f.relative_to(BUILD).as_posix():shaf(f) for f in BUILD.rglob("*") if f.is_file()}

p["patchId"]="sgp-client-1.8.1"
p["name"]="SGP Client 1.8.1"
p["toVersion"]="1.8.1"
p["fromVersions"]=list(p["fromVersions"])+["1.8.1-test.2"]
p["summary"]=[
  "Stable 1.8.1 promoted from owner-runtime-PASS 1.8.1-test.2.",
  "Create x Chipped Mechanical Saw performance hotfix: zero registered recipe JSONs on runtime path.",
  "Restores JEI visibility with client-only synthetic create:sawing entries for all 6968 routes.",
  "Payload/action set is identical to runtime-tested 1.8.1-test.2."
]
assert json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))==actions
mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
    "SGP Client 1.8.1\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Stable promotion of owner-runtime-PASS 1.8.1-test.2.\n"
    "Payload/action set is unchanged.\n"
    "Create x Chipped runtime bridge keeps zero recipe JSONs and client-only JEI visibility.\n",
    "utf-8"
)

after={f.relative_to(BUILD).as_posix():shaf(f) for f in BUILD.rglob("*") if f.is_file()}
for k,v in before.items():
    if k not in {"patch.json","README.txt"}:
        assert after[k]==v,k

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

fixed=(2026,10,5,15,45,0)
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
    assert q["patchId"]=="sgp-client-1.8.1"
    assert q["toVersion"]=="1.8.1"
    assert q["fromVersions"][-1]=="1.8.1-test.2"
    assert json.dumps(q["actions"],ensure_ascii=False,separators=(",",":"))==actions
    assert "files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip" not in z.namelist()
    assert "files/mods/SGP-Create-Chipped-Cutting-1.0.0.jar" not in z.namelist()
    m=z.read("files/mods/SGP-Create-Chipped-Cutting-1.0.1.jar")
    assert hashlib.sha256(m).hexdigest()=="433d99ad5172119a0f12613162dec28c9d50097dde397564d3a2c4b714c6dc31"

print("STABLE_181_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
