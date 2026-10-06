import hashlib, io, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ServerPatch_1.3.2.zip"
CLIENT=ROOT/"SGP_ClientPatch_1.10.0-test.4.zip"
OUT=ROOT/"SGP_ServerPatch_2.0.0.zip"
WORK=ROOT/".work-server-200"
BUILD=WORK/"server-root"

BASE_SHA="7c9eb7d2f9ededa396f71d932f1a47c5c6c1492a960a6d0c8b811d66b20a7f31"
CLIENT_SHA="08cee43906d18ed02b588c826061d2ed535686606a87bcbbb3edd7349e4f8ef2"

FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
PERM_TARGET="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar"
PUZ_TARGET="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"
OLD_PUZ_TARGET="mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar"
CAT_TARGET="mods/unbreakablecatalyst-1.0.2.jar"

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert CLIENT.is_file() and shaf(CLIENT)==CLIENT_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

# Base 1.3.2 scope is a prepared-but-uninstalled overlay; use its parity files,
# but rewrite metadata to installed lineage 1.2.1 -> 2.0.0.
assert (BUILD/"config/curios-common.toml").is_file()
assert (BUILD/"mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar").is_file()
assert (BUILD/"mods/SGP-Shapeless-Nether-Portals-1.1.3.jar").is_file()
assert not (BUILD/CAT_TARGET).exists()

with zipfile.ZipFile(CLIENT) as cz:
    assert cz.testzip() is None
    cp=json.loads(cz.read("patch.json"))
    assert cp["patchId"]=="sgp-client-1.10.0-test.4"
    assert not any(a.get("target")==CAT_TARGET for a in cp["actions"])

    def payload_for(target):
        aa=[a for a in cp["actions"] if a.get("type")=="copy" and a.get("target")==target]
        assert len(aa)==1,(target,aa)
        a=aa[0]
        b=cz.read(a["source"])
        assert hashlib.sha256(b).hexdigest()==a["sha256"]
        assert len(b)==a["size"]
        return b,a

    fix_bytes,fix_action=payload_for(FIX_TARGET)
    perm_bytes,perm_action=payload_for(PERM_TARGET)
    puz_bytes,puz_action=payload_for(PUZ_TARGET)

# Exact tested SGP Fixes rev 1.15.
with zipfile.ZipFile(io.BytesIO(fix_bytes)) as fz:
    assert fz.testzip() is None
    assert json.loads(fz.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.15")
    soul=json.loads(fz.read("data/soulbound/tags/item/enchantable.json"))
    assert soul["values"][-2:]==[
      "permanentsponges:aqueous_sponge_on_a_stick",
      "permanentsponges:magmatic_sponge_on_a_stick"
    ]

# Exact mod identity/dependency checks.
with zipfile.ZipFile(io.BytesIO(perm_bytes)) as pz:
    assert pz.testzip() is None
    toml=pz.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'modId="permanentsponges"' in toml
    assert 'modId="puzzleslib"' in toml
with zipfile.ZipFile(io.BytesIO(puz_bytes)) as pz:
    assert pz.testzip() is None
    toml=pz.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'modId="puzzleslib"' in toml

for target,data in [(FIX_TARGET,fix_bytes),(PERM_TARGET,perm_bytes),(PUZ_TARGET,puz_bytes)]:
    p=BUILD/target
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data)

# Never carry client-only localization into dedicated server overlay.
assert not (BUILD/"config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip").exists()
# Never rebundle baseline Catalyst.
assert not (BUILD/CAT_TARGET).exists()
# The old Puzzles Lib lives in live baseline, not in this overlay; deletion is external exact step.
assert not (BUILD/OLD_PUZ_TARGET).exists()

# Rewrite .sgp to exact target identity and installed history.
if (BUILD/".sgp").exists(): shutil.rmtree(BUILD/".sgp")
sgp=BUILD/".sgp"; sgp.mkdir()
pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"2.0.0",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-2.0.0","type":"release","version":"2.0.0","releaseDate":"2026-10-06"}
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"2.0.0",
 "versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.2.1","type":"release","version":"1.2.1","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-2.0.0","type":"release","version":"2.0.0","releaseDate":"2026-10-06","installer":"manual"}
 ]
}
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

expected=sorted([
 ".sgp/history.json",
 ".sgp/pack.json",
 "config/curios-common.toml",
 FIX_TARGET,
 "mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar",
 "mods/SGP-Shapeless-Nether-Portals-1.1.3.jar",
 PERM_TARGET,
 PUZ_TARGET
])
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected

fixed=(2026,10,6,20,5,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==expected
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="2.0.0"
    h=json.loads(z.read(".sgp/history.json"))
    assert h["currentVersion"]=="2.0.0"
    assert [e["version"] for e in h["entries"]]==["1.0.0","1.2.0","1.2.1","2.0.0"]
    assert CAT_TARGET not in z.namelist()
    assert OLD_PUZ_TARGET not in z.namelist()
    assert "config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip" not in z.namelist()

Path("server200_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("server200_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("server200_pack_sha.txt").write_text(shaf(BUILD/".sgp/pack.json")+"\n","utf-8")
Path("server200_pack_size.txt").write_text(str((BUILD/".sgp/pack.json").stat().st_size)+"\n","utf-8")
Path("server200_history_sha.txt").write_text(shaf(BUILD/".sgp/history.json")+"\n","utf-8")
Path("server200_history_size.txt").write_text(str((BUILD/".sgp/history.json").stat().st_size)+"\n","utf-8")
Path("server200_delete.txt").write_text(OLD_PUZ_TARGET+"\n","utf-8")
print("SERVER_200_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+shaf(OUT))
print("SERVER_SIZE="+str(OUT.stat().st_size))
