import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.7.0.zip"
FARM=ROOT/"letsdo-farm_and_charm-neoforge-1.1.26.jar"
OUT=ROOT/"SGP_ClientPatch_1.7.1.zip"
WORK=ROOT/".work-171"
BUILD=WORK/"build"

BASE_SHA="95e649ccb3ad53ac5e21584e31a010907d245a4c6d1572eaf281fc8ef8234377"
FARM_SHA="a148e4d1778d52819d2a4574ba9ccc3f39b7eefb0ace86fbe4121057ee7d1eca"
FARM_SIZE=2664623
STABLE=["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.7.0"]
TESTS=[f"1.7.0-test.{i}" for i in range(1,17)]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shab(b): return hashlib.sha256(b).hexdigest()

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert FARM.is_file() and FARM.stat().st_size==FARM_SIZE and shaf(FARM)==FARM_SHA

with zipfile.ZipFile(FARM) as z:
    assert z.testzip() is None
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'modId = "farm_and_charm"' in toml
    assert 'version = "1.1.26"' in toml
    assert 'side = "BOTH"' in toml
    # 1.1.26 must no longer carry the conflicting crop->bone-meal silo recipes.
    bad=[]
    for n in z.namelist():
        if not (n.startswith("data/") and n.endswith(".json")):
            continue
        b=z.read(n)
        if b"minecraft:bone_meal" in b and any(x in b for x in [b"minecraft:wheat",b"farm_and_charm:barley",b"farm_and_charm:corn",b"farm_and_charm:oat"]):
            bad.append(n)
    assert not bad,bad

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

mp=BUILD/"patch.json"
p=json.loads(mp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.7.0"
assert p["toVersion"]=="1.7.0"
assert p["fromVersions"]==[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2"
]+TESTS

before={f.relative_to(BUILD).as_posix():shaf(f) for f in BUILD.rglob("*") if f.is_file()}
base_actions=list(p["actions"])

farm_target="mods/letsdo-farm_and_charm-neoforge-1.1.26.jar"
farm_source="files/"+farm_target
farm_dst=BUILD/farm_source
farm_dst.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(FARM,farm_dst)

# Exact optional deletions keep the patch cumulative across the accepted lineage
# without wildcard deletion and without ever touching unrelated mods.
deletes=[]
for minor in range(0,26):
    ver=f"1.1.{minor}"
    deletes.append({
      "actionId":f"remove-farm-and-charm-{ver.replace('.','-')}",
      "type":"delete",
      "description":f"Удалить старую Farm & Charm {ver}, если она присутствует",
      "target":f"mods/letsdo-farm_and_charm-neoforge-{ver}.jar",
      "optional":True
    })

copy={
  "actionId":"install-farm-and-charm-1-1-26",
  "type":"copy",
  "description":"Установить [Let's Do] Farm & Charm 1.1.26 NeoForge 1.21.1",
  "source":farm_source,
  "target":farm_target,
  "sha256":FARM_SHA,
  "size":FARM_SIZE
}

p["patchId"]="sgp-client-1.7.1"
p["name"]="SGP Client 1.7.1"
p["toVersion"]="1.7.1"
p["fromVersions"]=STABLE+TESTS
p["summary"]=[
  "Stable 1.7.1 direct maintenance release by explicit owner exception; no TEST prerelease for this release.",
  "Cumulative direct update from every accepted stable 1.0.0-1.7.0 plus forward repair from retained 1.7.0-test.1..test.16.",
  "[Let's Do] Farm & Charm updated to 1.1.26 NeoForge 1.21.1.",
  "Upstream 1.1.26 removes conflicting Wheat/Barley/Corn/Oat Silo -> Bone Meal recipes that could win over Brewery drying recipes.",
  "No Brewery update and no other payload/config changes relative to 1.7.0."
]
p["actions"]=base_actions+deletes+[copy]

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
assert p["fromVersions"][-17:] == ["1.7.0"]+TESTS
assert "1.5.4" not in p["fromVersions"]

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text("""SGP Client 1.7.1
Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21

Direct stable maintenance release by explicit owner exception; no TEST prerelease.

Change:
- [Let's Do] Farm & Charm -> 1.1.26 NeoForge 1.21.1.
- Fixes the Silo recipe conflict where Wheat/Barley/Corn/Oat could be selected for Bone Meal instead of Brewery drying outputs.
- Brewery itself is unchanged.
- Server archive intentionally not produced for this exception; owner will update the same mod manually on the dedicated server.

All 1.7.0 payload/actions are retained, so this remains cumulative-to-latest.
""","utf-8")

after={f.relative_to(BUILD).as_posix():shaf(f) for f in BUILD.rglob("*") if f.is_file()}
allowed={"patch.json","README.txt",farm_source}
for path,h in before.items():
    if path not in allowed:
        assert after.get(path)==h,path
for path,h in after.items():
    if path not in allowed:
        assert before.get(path)==h,path

fixed=(2026,10,5,10,45,0)
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
    assert q["patchId"]=="sgp-client-1.7.1"
    assert q["toVersion"]=="1.7.1"
    assert q["fromVersions"]==STABLE+TESTS
    assert z.read(farm_source)==FARM.read_bytes()
    assert sum(1 for a in q["actions"] if a.get("actionId")=="install-farm-and-charm-1-1-26")==1

print("STABLE_171_STATIC_AUDIT_PASS")
print("FARM_SHA="+FARM_SHA)
print("FARM_SIZE="+str(FARM_SIZE))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
