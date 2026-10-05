import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.0-test.1.zip"
OUT=ROOT/"SGP_ClientPatch_1.8.0.zip"
WORK=ROOT/".work-180-stable"
BUILD=WORK/"build"

BASE_SHA="440fff574bb67eb91ed252ad38eb1811b29332499f70397dfea1c173502686e6"
ACCEPTED=["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.7.0","1.7.1"]
FORWARD_170=[f"1.7.0-test.{i}" for i in range(1,17)]
TEST180=["1.8.0-test.1"]

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
assert p["patchId"]=="sgp-client-1.8.0-test.1"
assert p["toVersion"]=="1.8.0-test.1"
assert p["fromVersions"]==ACCEPTED+FORWARD_170
assert "1.5.4" not in p["fromVersions"]

actions=json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))
before={f.relative_to(BUILD).as_posix():shaf(f) for f in BUILD.rglob("*") if f.is_file()}

p["patchId"]="sgp-client-1.8.0"
p["name"]="SGP Client 1.8.0"
p["toVersion"]="1.8.0"
p["fromVersions"]=ACCEPTED+FORWARD_170+TEST180
p["summary"]=[
  "Stable 1.8.0 promoted from owner-runtime-PASS 1.8.0-test.1.",
  "Create Mechanical Saw integration for Chipped 4.0.2 on Minecraft 1.21.1.",
  "Adds 6968 data-driven create:cutting recipes across 277 current Chipped workbench families.",
  "Payload/action set is identical to runtime-tested 1.8.0-test.1."
]
assert json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))==actions
mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
    "SGP Client 1.8.0\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Stable promotion of owner-runtime-PASS 1.8.0-test.1.\n"
    "Payload/action set is unchanged.\n"
    "Adds SGP Create x Chipped Cutting datapack: 6968 Mechanical Saw recipes across 277 Chipped 4.0.2 families.\n",
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

fixed=(2026,10,5,13,0,0)
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
    assert q["patchId"]=="sgp-client-1.8.0"
    assert q["toVersion"]=="1.8.0"
    assert q["fromVersions"]==ACCEPTED+FORWARD_170+TEST180
    assert json.dumps(q["actions"],ensure_ascii=False,separators=(",",":"))==actions
    for a in q["actions"]:
        if a["type"]=="copy":
            b=z.read(a["source"])
            assert len(b)==a["size"] and shab(b).lower()==a["sha256"].lower()

print("STABLE_180_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
