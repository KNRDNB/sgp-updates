import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
CLIENT=ROOT/"SGP_ClientPatch_1.8.0.zip"
OUT=ROOT/"SGP_ServerPatch_1.2.0.zip"
WORK=ROOT/".work-server-120"
BUILD=WORK/"server-root"
STAGE_110=ROOT/"release-staging/server-1.1.0"

CLIENT_SHA="34c6f2b223892b92a1c6f1da0074802de474cfe4116fcd5c90e3d869081ef9bb"
WANDS_SHA="565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
COMPAT_SHA="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
FIXES_SHA="ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"
FARM_SHA="a148e4d1778d52819d2a4574ba9ccc3f39b7eefb0ace86fbe4121057ee7d1eca"
CUTTING_SHA="5ccabcd443793b581adfe14ecd6c7514becfaf866e74581e30305389d3e63ee8"

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return shab(Path(p).read_bytes())

assert shaf(CLIENT)==CLIENT_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(CLIENT) as z:
    assert z.testzip() is None
    pm=json.loads(z.read("patch.json"))
    assert pm["patchId"]=="sgp-client-1.8.0"
    assert pm["toVersion"]=="1.8.0"

    payloads={
      "mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar":
        "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "mods/SGP-Wands-Paxel-Compat-1.0.0.jar":
        "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip":
        "files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
      "mods/letsdo-farm_and_charm-neoforge-1.1.26.jar":
        "files/mods/letsdo-farm_and_charm-neoforge-1.1.26.jar",
      "config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip":
        "files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip",
    }
    for dst,src in payloads.items():
        p=BUILD/dst
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(z.read(src))

assert shaf(BUILD/"mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar")==WANDS_SHA
assert shaf(BUILD/"mods/SGP-Wands-Paxel-Compat-1.0.0.jar")==COMPAT_SHA
assert shaf(BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip")==FIXES_SHA
assert shaf(BUILD/"mods/letsdo-farm_and_charm-neoforge-1.1.26.jar")==FARM_SHA
assert shaf(BUILD/"config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip")==CUTTING_SHA

with zipfile.ZipFile(BUILD/"mods/letsdo-farm_and_charm-neoforge-1.1.26.jar") as z:
    assert z.testzip() is None
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'modId = "farm_and_charm"' in toml
    assert 'version = "1.1.26"' in toml
    assert 'side = "BOTH"' in toml

with zipfile.ZipFile(BUILD/"config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip") as z:
    assert z.testzip() is None
    assert json.loads(z.read("pack.mcmeta"))["pack"]["pack_format"]==48
    recipes=[n for n in z.namelist() if n.startswith("data/sgp_create_chipped_cutting/recipe/") and n.endswith(".json")]
    assert len(recipes)==6968
    families=set()
    for n in recipes:
        r=json.loads(z.read(n))
        assert r["type"]=="create:cutting"
        assert r["processing_time"]==50
        assert r["results"][0]["id"].startswith("chipped:")
        families.add(r["ingredients"][0]["tag"])
    assert len(families)==277

wbase=json.loads((STAGE_110/"wands-base.json").read_text("utf-8"))
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

cbase=(STAGE_110/"create-server-base.toml").read_bytes()
old=b"maxRopeLength = 384"
new=b"maxRopeLength = 512"
assert cbase.count(old)==1
ctarget=cbase.replace(old,new,1)
assert len(ctarget)==len(cbase)
cp=BUILD/"world/serverconfig/create-server.toml"
cp.parent.mkdir(parents=True,exist_ok=True)
cp.write_bytes(ctarget)
assert cp.read_bytes().count(new)==1 and cp.read_bytes().count(old)==0

pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"1.2.0",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05"}
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"1.2.0",
 "versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05","installer":"manual"}
 ]
}
sgp=BUILD/".sgp"; sgp.mkdir()
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

expected=sorted([
 ".sgp/history.json",
 ".sgp/pack.json",
 "world/serverconfig/create-server.toml",
 "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
 "config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip",
 "config/wands.json",
 "mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
 "mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
 "mods/letsdo-farm_and_charm-neoforge-1.1.26.jar",
])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,5,13,30,0)
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
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.2.0"
    h=json.loads(z.read(".sgp/history.json"))
    assert h["currentVersion"]=="1.2.0"
    assert [e["version"] for e in h["entries"]]==["1.0.0","1.2.0"]
    assert b"maxRopeLength = 512" in z.read("world/serverconfig/create-server.toml")

print("SERVER_120_STATIC_AUDIT_PASS")
print("DELETE_IF_PRESENT=mods/BuildingWands-neoforge-MC1.21-2.14.jar")
print("DELETE_IF_PRESENT=mods/letsdo-farm_and_charm-neoforge-1.1.24.jar")
print("SERVER_ZIP_SHA="+shaf(OUT))
print("SERVER_ZIP_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+shaf(BUILD/".sgp/pack.json"))
print("PACK_SIZE="+str((BUILD/".sgp/pack.json").stat().st_size))
print("HISTORY_SHA="+shaf(BUILD/".sgp/history.json"))
print("HISTORY_SIZE="+str((BUILD/".sgp/history.json").stat().st_size))
print("CREATE_SERVER_SHA="+shaf(cp))
print("WANDS_CONFIG_SHA="+shaf(wp))
