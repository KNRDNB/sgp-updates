import hashlib, io, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
CLIENT=ROOT/"SGP_ClientPatch_1.8.2-test.4.zip"
OUT=ROOT/"SGP_ServerPatch_1.2.2.zip"
WORK=ROOT/".work-server-122-test4"
BUILD=WORK/"server-root"

FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
CFG_TARGET="config/curios-common.toml"
MOD_TARGET="mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
MOD_SHA="2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9"

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert CLIENT.is_file()
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(CLIENT) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    assert p["toVersion"]=="1.8.2-test.4"
    def payload(target):
        a=[x for x in p["actions"] if x.get("type")=="copy" and x.get("target")==target]
        assert len(a)==1,(target,a)
        b=z.read(a[0]["source"])
        assert len(b)==a[0]["size"]
        assert shab(b)==a[0]["sha256"]
        return b
    fixes=payload(FIX_TARGET)
    mod=payload(MOD_TARGET)

cfg=(
    "#List of slots to create or modify.\n"
    "#See documentation for syntax: https://docs.illusivesoulworks.com/curios/configuration#slot-configuration\n"
    "#\n"
    'slots = ["id=wings;size=1;order=-100;add_cosmetic=true", "id=quiver;size=1;order=-90;add_cosmetic=true", "id=glasses;size=1;order=-80;add_cosmetic=true", "id=amulet_pocket;size=6;order=-70"]\n'
).encode("utf-8")

assert shab(mod)==MOD_SHA
with zipfile.ZipFile(io.BytesIO(fixes)) as dz:
    assert dz.testzip() is None
    assert json.loads(dz.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.14")
    assert "data/sgp_fixes/curios/slots/amulet_pocket.json" not in dz.namelist()
    assert json.loads(dz.read("data/curios/tags/item/amulet_pocket.json"))["values"]==["apotheosis:potion_charm"]

cfg_text=cfg.decode("utf-8")
assert cfg_text.count("id=amulet_pocket;size=6;order=-70")==1

for target,b in [(FIX_TARGET,fixes),(CFG_TARGET,cfg),(MOD_TARGET,mod)]:
    f=BUILD/target
    f.parent.mkdir(parents=True,exist_ok=True)
    f.write_bytes(b)

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
 ".sgp/history.json",".sgp/pack.json",
 FIX_TARGET,CFG_TARGET,MOD_TARGET
])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,5,21,45,0)
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
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.2.2"
    assert "id=amulet_pocket;size=6;order=-70" in z.read(CFG_TARGET).decode("utf-8")

Path("server122_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("server122_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("server122_pack_sha.txt").write_text(shaf(BUILD/".sgp/pack.json")+"\n","utf-8")
Path("server122_history_sha.txt").write_text(shaf(BUILD/".sgp/history.json")+"\n","utf-8")
Path("server122_curios_config_sha.txt").write_text(shab(cfg)+"\n","utf-8")
Path("server122_curios_config_size.txt").write_text(str(len(cfg))+"\n","utf-8")
print("SERVER_122_TEST4_STATIC_AUDIT_PASS")
print("SERVER_SHA="+shaf(OUT))
print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+shaf(BUILD/".sgp/pack.json"))
print("HISTORY_SHA="+shaf(BUILD/".sgp/history.json"))
print("CONFIG_SHA="+shab(cfg))
print("CONFIG_SIZE="+str(len(cfg)))
