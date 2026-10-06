import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.10.0-test.2.zip"
OUT=ROOT/"SGP_ClientPatch_1.10.0-test.3.zip"
WORK=ROOT/".work-1100-test3"
BUILD=WORK/"build"

BASE_SHA="3b589a66ac22af5c53950a2dda6e5778911ea437ce6e4b33272d2fb2b1047fe8"
CAT_TARGET="mods/unbreakablecatalyst-1.0.2.jar"
CAT_ACTION="install-unbreakable-catalyst-1-0-2"
FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
SPONGE_ITEMS=[
 "permanentsponges:aqueous_sponge_on_a_stick",
 "permanentsponges:magmatic_sponge_on_a_stick",
]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.10.0-test.2"
assert p["toVersion"]=="1.10.0-test.2"
assert p["fromVersions"][-2:]==["1.9.1","1.10.0-test.1"]
assert "1.5.4" not in p["fromVersions"]

# test.2 mistakenly bundled a mod that already belongs to the SGP baseline.
cat=[a for a in p["actions"] if a.get("actionId")==CAT_ACTION]
assert len(cat)==1,cat
cat=cat[0]
assert cat.get("type")=="copy" and cat.get("target")==CAT_TARGET
cat_source=cat["source"]
cat_payload=BUILD/cat_source
assert cat_payload.is_file()

before=hashes(BUILD)

p["actions"]=[a for a in p["actions"] if a.get("actionId")!=CAT_ACTION]
cat_payload.unlink()

# No mutation/removal of the already-existing runtime mod.
assert not any(a.get("target")==CAT_TARGET for a in p["actions"])
assert not any(a.get("type")=="delete" and a.get("target")==CAT_TARGET for a in p["actions"])

# Preserve HUD + Permanent Sponges + Puzzles Lib + Soulbound candidate.
hud=next(a for a in p["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
assert hud["edits"]==[
  {"op":"set","path":"positions.legPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.bootPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.offPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.invPosX","value":-111,"createIfMissing":False},
]
assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in p["actions"])
assert any(a.get("target")=="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar" for a in p["actions"])

fix=next(a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET)
fix_path=BUILD/fix["source"]
assert fix_path.is_file()
with zipfile.ZipFile(fix_path) as fz:
    assert fz.testzip() is None
    assert json.loads(fz.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.15")
    tag=json.loads(fz.read("data/soulbound/tags/item/enchantable.json"))
    assert tag["values"][-2:]==SPONGE_ITEMS

p["patchId"]="sgp-client-1.10.0-test.3"
p["name"]="SGP Client 1.10.0-test.3"
p["toVersion"]="1.10.0-test.3"
p["fromVersions"]=list(p["fromVersions"])+["1.10.0-test.2"]
assert p["fromVersions"][-3:]==["1.9.1","1.10.0-test.1","1.10.0-test.2"]
assert "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "TEST.3: corrects TEST.2 packaging mistake: Unbreakable Catalyst 1.0.2 is already part of the SGP baseline and is no longer bundled or modified by this patch.",
 "Keeps ArmorHUD right-side -103 -> -111 spacing adjustment.",
 "Keeps Permanent Sponges 21.1.0 + required Puzzles Lib 21.1.62.",
 "Keeps SGP Fixes rev 1.15 with both sponge-on-a-stick items in soulbound:enchantable.",
 "Runtime check uses the already-installed SGP Unbreakable Catalyst for both sponge sticks.",
 "No dedicated-server patch is built during client TEST."
]

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.10.0-test.3\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "TEST.3 correction:\n"
 "- Unbreakable Catalyst 1.0.2 is ALREADY part of SGP and is NOT installed/replaced/deleted by this patch.\n"
 "- ArmorHUD right side remains -111; opposite side remains 136.\n"
 "- Permanent Sponges 21.1.0 + Puzzles Lib 21.1.62 remain.\n"
 "- SGP Fixes rev 1.15 adds both sponge-on-a-stick items to soulbound:enchantable.\n"
 "- Runtime: use the existing SGP Unbreakable Catalyst and Soulbound on BOTH sponge sticks, then verify sponge behavior.\n"
 "- Dedicated server is not prepared during TEST.\n",
 "utf-8"
)

after=hashes(BUILD)
allowed={"patch.json","README.txt",cat_source}
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed==allowed,changed

fixed=(2026,10,6,15,5,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.10.0-test.3"
    assert q["toVersion"]=="1.10.0-test.3"
    assert q["fromVersions"][-3:]==["1.9.1","1.10.0-test.1","1.10.0-test.2"]
    assert not any(a.get("actionId")==CAT_ACTION or a.get("target")==CAT_TARGET for a in q["actions"])
    assert cat_source not in z.namelist()
    fa=next(a for a in q["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET)
    import io
    with zipfile.ZipFile(io.BytesIO(z.read(fa["source"]))) as fz:
        tag=json.loads(fz.read("data/soulbound/tags/item/enchantable.json"))
        assert tag["values"][-2:]==SPONGE_ITEMS

Path("client1100test3_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client1100test3_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
print("CLIENT_1100_TEST3_CORRECTION_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
