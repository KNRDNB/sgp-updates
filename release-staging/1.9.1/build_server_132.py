import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ServerPatch_1.2.2.zip"
MOD=ROOT/"SGP-Shapeless-Nether-Portals-1.1.3.jar"
OUT=ROOT/"SGP_ServerPatch_1.3.2.zip"
WORK=ROOT/".work-server-132-stable191"
BUILD=WORK/"server-root"
BASE_SHA="2dc63bc7122fc9d0fe033bc063d6cd5d7a8fb5f64e2ed2ea236fe083cc99b571"
MOD_TARGET="mods/SGP-Shapeless-Nether-Portals-1.1.3.jar"

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert BASE.is_file() and shaf(BASE)==BASE_SHA and MOD.is_file()
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

assert (BUILD/"config/curios-common.toml").is_file()
assert (BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip").is_file()
assert (BUILD/"mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar").is_file()
for old in ["1.0.0","1.1.0","1.1.1","1.1.2"]:
    assert not (BUILD/f"mods/SGP-Shapeless-Nether-Portals-{old}.jar").exists(),old

shutil.rmtree(BUILD/".sgp")
sgp=BUILD/".sgp"; sgp.mkdir()
pack={
 "schemaVersion":1,"packId":"sgp-neoforge-1.21.1-server","familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)","side":"server","version":"1.3.2","versionFormat":"semver",
 "minecraft":"1.21.1","loader":"neoforge","neoforge":"21.1.249","javaMajor":21,"releaseChannel":"stable",
 "baseline":False,"stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-1.3.2","type":"release","version":"1.3.2","releaseDate":"2026-10-06"}
}
history={
 "schemaVersion":1,"packId":"sgp-neoforge-1.21.1-server","currentVersion":"1.3.2","versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.2.1","type":"release","version":"1.2.1","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.3.2","type":"release","version":"1.3.2","releaseDate":"2026-10-06","installer":"manual"}
 ]}
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")
target=BUILD/MOD_TARGET; target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(MOD,target)

expected=sorted([".sgp/history.json",".sgp/pack.json","config/curios-common.toml",
 "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip","mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar",MOD_TARGET])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,6,4,20,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None and sorted(z.namelist())==expected
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.3.2"
    h=json.loads(z.read(".sgp/history.json")); assert h["currentVersion"]=="1.3.2"
    assert [e["version"] for e in h["entries"]]==["1.0.0","1.2.0","1.2.1","1.3.2"]

for name,path in [
 ("server132_sha.txt",OUT),("server132_pack_sha.txt",BUILD/".sgp/pack.json"),
 ("server132_history_sha.txt",BUILD/".sgp/history.json")]:
    Path(name).write_text(shaf(path)+"\n","utf-8")
for name,path in [
 ("server132_size.txt",OUT),("server132_pack_size.txt",BUILD/".sgp/pack.json"),
 ("server132_history_size.txt",BUILD/".sgp/history.json")]:
    Path(name).write_text(str(path.stat().st_size)+"\n","utf-8")
print("SERVER_132_STABLE191_STATIC_AUDIT_PASS")
print("SERVER_SHA="+shaf(OUT)); print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+shaf(BUILD/".sgp/pack.json")); print("PACK_SIZE="+str((BUILD/".sgp/pack.json").stat().st_size))
print("HISTORY_SHA="+shaf(BUILD/".sgp/history.json")); print("HISTORY_SIZE="+str((BUILD/".sgp/history.json").stat().st_size))
