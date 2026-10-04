import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
CLIENT=ROOT/"SGP_ClientPatch_1.7.0.zip"
OUT=ROOT/"SGP_ServerPatch_1.1.0.zip"
WORK=ROOT/".work-server-110"
BUILD=WORK/"server-root"
STAGE=ROOT/"release-staging/server-1.1.0"

CLIENT_SHA="95e649ccb3ad53ac5e21584e31a010907d245a4c6d1572eaf281fc8ef8234377"
WANDS_SHA="565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
COMPAT_SHA="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
FIXES_SHA="ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return shab(Path(p).read_bytes())

assert shaf(CLIENT)==CLIENT_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(CLIENT) as z:
    assert z.testzip() is None
    pm=json.loads(z.read("patch.json"))
    assert pm["patchId"]=="sgp-client-1.7.0"
    assert pm["toVersion"]=="1.7.0"

    payloads={
      "mods/BuildingWands-neoforge-MC1.21-2.14.jar":
        "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "mods/SGP-Wands-Paxel-Compat-1.0.0.jar":
        "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip":
        "files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
    }
    for dst,src in payloads.items():
        p=BUILD/dst
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(z.read(src))

assert shaf(BUILD/"mods/BuildingWands-neoforge-MC1.21-2.14.jar")==WANDS_SHA
assert shaf(BUILD/"mods/SGP-Wands-Paxel-Compat-1.0.0.jar")==COMPAT_SHA
assert shaf(BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip")==FIXES_SHA

# Pure root-overlay policy: replace existing server files directly.
# Building Wands 3.0.5 bytes intentionally use the existing 2.14 filename,
# so drag/drop "replace files" removes the old mod bytes without a delete step.
with zipfile.ZipFile(BUILD/"mods/BuildingWands-neoforge-MC1.21-2.14.jar") as z:
    assert z.testzip() is None

# Full replacement target for Wands config, derived from exact staged current server config.
wbase=json.loads((STAGE/"wands-base.json").read_text("utf-8"))
wtarget=dict(wbase)
wtarget.update({
  "max_limit___increment_this_if_your_machine_can_handle_it":8192,
  "stone_wand_limit":128,
  "copper_wand_limit":256,
  "iron_wand_limit":512,
  "diamond_wand_limit":1024,
  "netherite_wand_limit":4096,
  "creative_wand_limit":8192,
})
allowed={
  "max_limit___increment_this_if_your_machine_can_handle_it",
  "stone_wand_limit","copper_wand_limit","iron_wand_limit",
  "diamond_wand_limit","netherite_wand_limit","creative_wand_limit"
}
changed={k for k in wtarget if wtarget[k]!=wbase[k]}
assert changed <= allowed
assert {"stone_wand_limit","copper_wand_limit","iron_wand_limit","diamond_wand_limit","netherite_wand_limit","creative_wand_limit"} <= changed
wp=BUILD/"config/wands.json"
wp.parent.mkdir(parents=True,exist_ok=True)
wp.write_text(json.dumps(wtarget,ensure_ascii=False,indent=2)+"\n","utf-8")

# Full replacement target for Create server config, preserving all owner/current bytes except Rope Pulley 384 -> 512.
cbase=(STAGE/"create-server-base.toml").read_bytes()
old=b"maxRopeLength = 384"
new=b"maxRopeLength = 512"
assert cbase.count(old)==1
ctarget=cbase.replace(old,new,1)
assert len(ctarget)==len(cbase)
cp=BUILD/"config/create-server.toml"
cp.write_bytes(ctarget)
assert cp.read_bytes().count(new)==1 and cp.read_bytes().count(old)==0

# Final target .sgp metadata is part of the same overlay.
pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"1.1.0",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-1.1.0","type":"release","version":"1.1.0","releaseDate":"2026-10-04"}
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"1.1.0",
 "versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.1.0","type":"release","version":"1.1.0","releaseDate":"2026-10-04","installer":"manual"}
 ]
}
sgp=BUILD/".sgp";sgp.mkdir()
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

expected=sorted([
 ".sgp/history.json",
 ".sgp/pack.json",
 "config/create-server.toml",
 "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
 "config/wands.json",
 "mods/BuildingWands-neoforge-MC1.21-2.14.jar",
 "mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,4,18,30,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==expected
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.1.0"
    assert json.loads(z.read(".sgp/history.json"))["currentVersion"]=="1.1.0"

print("SERVER_110_PURE_OVERLAY_AUDIT_PASS")
print("SERVER_ZIP_SHA="+shaf(OUT))
print("SERVER_ZIP_SIZE="+str(OUT.stat().st_size))
print("CREATE_SERVER_SHA="+shaf(cp))
print("WANDS_CONFIG_SHA="+shaf(wp))
print("WANDS_JAR_SHA="+shaf(BUILD/"mods/BuildingWands-neoforge-MC1.21-2.14.jar"))
