import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.7.0-test.16.zip"
OUT=ROOT/"SGP_ClientPatch_1.7.0.zip"
WORK=ROOT/".work-170-stable"
BUILD=WORK/"build"
BASE_SHA="80535ebbf29aa9167e8ef8408dcb907069561d95a9e0d5fe95a9764395b93419"
STABLE=["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2"]
TESTS=[f"1.7.0-test.{i}" for i in range(1,17)]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()

assert sha(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

mp=BUILD/"patch.json"
p=json.loads(mp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.7.0-test.16"
assert p["toVersion"]=="1.7.0-test.16"
assert p["fromVersions"]==STABLE+TESTS[:-1]
actions=json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))
before={f.relative_to(BUILD).as_posix():sha(f) for f in BUILD.rglob("*") if f.is_file()}

p["patchId"]="sgp-client-1.7.0"
p["name"]="SGP Client 1.7.0"
p["toVersion"]="1.7.0"
p["fromVersions"]=STABLE+TESTS
p["summary"]=[
  "Stable 1.7.0 promoted from owner-runtime-PASS 1.7.0-test.16.",
  "Cumulative direct update from accepted stable 1.0.0-1.6.2.",
  "Payload/action set is identical to test.16."
]
assert json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))==actions
mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text("""SGP Client 1.7.0
Minecraft 1.21.1 / NeoForge 21.1.249
Stable promotion of owner-runtime-PASS 1.7.0-test.16.
Payload/action set is unchanged.
""","utf-8")

after={f.relative_to(BUILD).as_posix():sha(f) for f in BUILD.rglob("*") if f.is_file()}
for k,v in before.items():
    if k not in {"patch.json","README.txt"}: assert after[k]==v
for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.stat().st_size==a["size"] and sha(f).lower()==a["sha256"].lower()

fixed=(2026,10,4,18,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.7.0"
    assert q["toVersion"]=="1.7.0"
    assert q["fromVersions"]==STABLE+TESTS
    assert json.dumps(q["actions"],ensure_ascii=False,separators=(",",":"))==actions
    for a in q["actions"]:
        if a["type"]=="copy":
            b=z.read(a["source"])
            assert len(b)==a["size"] and shab(b).lower()==a["sha256"].lower()

print("STABLE_170_AUDIT_PASS")
print("FINAL_SHA="+sha(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
