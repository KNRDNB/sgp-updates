import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
MOD=ROOT/"SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
FIXES=ROOT/".work-182-test3/SGP_Fixes_NeoForge_1.21.1.zip"
OUT=ROOT/"SGP_ServerPatch_1.2.2.zip"
WORK=ROOT/".work-server-122-test3"
BUILD=WORK/"server-root"

MOD_SHA="2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9"

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert MOD.is_file() and shaf(MOD)==MOD_SHA
assert FIXES.is_file()

if WORK.exists(): shutil.rmtree(WORK)
(BUILD/"mods").mkdir(parents=True)
(BUILD/"config/paxi/datapacks").mkdir(parents=True)
shutil.copyfile(MOD,BUILD/"mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar")
shutil.copyfile(FIXES,BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip")

pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"1.2.2",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-1.2.2","type":"release","version":"1.2.2","releaseDate":"2026-10-05"}
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"1.2.2",
 "versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.2.1","type":"release","version":"1.2.1","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.2.2","type":"release","version":"1.2.2","releaseDate":"2026-10-05","installer":"manual"}
 ]
}
sgp=BUILD/".sgp"; sgp.mkdir()
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

expected=sorted([
 ".sgp/history.json",
 ".sgp/pack.json",
 "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
 "mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,5,21,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==expected
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.2.2"
    h=json.loads(z.read(".sgp/history.json"))
    assert h["currentVersion"]=="1.2.2"
    assert [e["version"] for e in h["entries"]]==["1.0.0","1.2.0","1.2.1","1.2.2"]
    with zipfile.ZipFile(__import__("io").BytesIO(z.read("config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"))) as dz:
        slot=json.loads(dz.read("data/sgp_fixes/curios/slots/amulet_pocket.json"))
        assert slot["size"]==6
        assert slot["entities"]==["minecraft:player"]

Path("server122_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("server122_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("server122_pack_sha.txt").write_text(shaf(BUILD/".sgp/pack.json")+"\n","utf-8")
Path("server122_pack_size.txt").write_text(str((BUILD/".sgp/pack.json").stat().st_size)+"\n","utf-8")
Path("server122_history_sha.txt").write_text(shaf(BUILD/".sgp/history.json")+"\n","utf-8")
Path("server122_history_size.txt").write_text(str((BUILD/".sgp/history.json").stat().st_size)+"\n","utf-8")
print("SERVER_122_TEST3_STATIC_AUDIT_PASS")
print("SERVER_SHA="+shaf(OUT))
print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+shaf(BUILD/".sgp/pack.json"))
print("HISTORY_SHA="+shaf(BUILD/".sgp/history.json"))
