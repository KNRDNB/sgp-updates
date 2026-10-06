import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.10.0-test.1.zip"
CAT=ROOT/"unbreakablecatalyst-1.0.2.jar"
OUT=ROOT/"SGP_ClientPatch_1.10.0-test.2.zip"
WORK=ROOT/".work-1100-test2"
BUILD=WORK/"build"
FIX_DIR=WORK/"sgp-fixes"

BASE_SHA="586473090d69f29b65bfdcb787a4b52f6a8349b086b9d10266e7dbcd90aa69c6"
FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
CAT_TARGET="mods/unbreakablecatalyst-1.0.2.jar"
CAT_SOURCE="files/"+CAT_TARGET
SPONGE_ITEMS=[
 "permanentsponges:aqueous_sponge_on_a_stick",
 "permanentsponges:magmatic_sponge_on_a_stick",
]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert CAT.is_file()

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.10.0-test.1"
assert p["toVersion"]=="1.10.0-test.1"
assert p["fromVersions"][-1]=="1.9.1"
assert "1.5.4" not in p["fromVersions"]

# test.1 invariants that must remain intact.
hud=next(a for a in p["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
assert hud["edits"]==[
  {"op":"set","path":"positions.legPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.bootPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.offPosX","value":-111,"createIfMissing":False},
  {"op":"set","path":"positions.invPosX","value":-111,"createIfMissing":False},
]
assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in p["actions"])
assert any(a.get("target")=="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar" for a in p["actions"])

before=hashes(BUILD)

# SGP Fixes rev 1.15: make both sponge-on-a-stick items explicitly Soulbound-compatible.
fix_actions=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET]
assert len(fix_actions)==1,fix_actions
fix=fix_actions[0]
fix_path=BUILD/fix["source"]
assert fix_path.is_file()

FIX_DIR.mkdir(parents=True)
with zipfile.ZipFile(fix_path) as z:
    assert z.testzip() is None
    z.extractall(FIX_DIR)
before_fix=hashes(FIX_DIR)

meta=FIX_DIR/"pack.mcmeta"
m=json.loads(meta.read_text("utf-8"))
desc=m["pack"]["description"]
assert desc.endswith("internal rev 1.14"),desc
m["pack"]["description"]=desc[:-len("1.14")]+"1.15"
meta.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n","utf-8")

soul=FIX_DIR/"data/soulbound/tags/item/enchantable.json"
s=json.loads(soul.read_text("utf-8"))
assert s["replace"] is False
vals=s["values"]
assert "apotheosis:potion_charm" in vals
for item in SPONGE_ITEMS:
    assert item not in vals,item
    vals.append(item)
soul.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n","utf-8")

after_fix=hashes(FIX_DIR)
changed_fix={k for k in set(before_fix)|set(after_fix) if before_fix.get(k)!=after_fix.get(k)}
assert changed_fix=={"pack.mcmeta","data/soulbound/tags/item/enchantable.json"},changed_fix

fixed_fix=(2026,10,6,11,20,0)
new_fix=WORK/"SGP_Fixes_NeoForge_1.21.1.zip"
with zipfile.ZipFile(new_fix,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in FIX_DIR.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(FIX_DIR).as_posix(),fixed_fix)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(new_fix) as z:
    assert z.testzip() is None
    assert json.loads(z.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.15")
    t=json.loads(z.read("data/soulbound/tags/item/enchantable.json"))
    assert t["values"][-2:]==SPONGE_ITEMS

shutil.copyfile(new_fix,fix_path)
fix["sha256"]=shaf(new_fix)
fix["size"]=new_fix.stat().st_size
fix["description"]="Установить SGP fixes rev 1.15: Soulbound для Potion Charm и обеих губок на палочке"

# NeoForge replacement for BCG/Things Hardening Catalyst.
cat_payload=BUILD/CAT_SOURCE
cat_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(CAT,cat_payload)
p["actions"].append({
  "actionId":"install-unbreakable-catalyst-1-0-2",
  "type":"copy",
  "description":"Установить Unbreakable Catalyst 1.0.2 — NeoForge-аналог Hardening Catalyst из Things",
  "source":CAT_SOURCE,
  "target":CAT_TARGET,
  "sha256":shaf(CAT),
  "size":CAT.stat().st_size
})

p["patchId"]="sgp-client-1.10.0-test.2"
p["name"]="SGP Client 1.10.0-test.2"
p["toVersion"]="1.10.0-test.2"
p["fromVersions"]=list(p["fromVersions"])+["1.10.0-test.1"]
assert p["fromVersions"][-2:]==["1.9.1","1.10.0-test.1"]
assert "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "TEST.2: keeps TEST.1 ArmorHUD -111 right-side spacing and Permanent Sponges/Puzzles Lib payload unchanged.",
 "Adds Unbreakable Catalyst 1.0.2, the NeoForge 1.21.1 analogue of Things' Hardening Catalyst.",
 "SGP Fixes rev 1.15 explicitly adds both Permanent Sponges stick items to soulbound:enchantable.",
 "Both sponge sticks are damageable items (65/129 durability) and therefore are candidates for Unbreakable Catalyst's damageable-item anvil path.",
 "Dedicated-server parity remains deferred until explicit owner release instruction."
]

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
assert sum(a.get("actionId")=="install-unbreakable-catalyst-1-0-2" for a in p["actions"])==1

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.10.0-test.2\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "TEST.2:\n"
 "- ArmorHUD: TEST.1 right-side nudge stays -103 -> -111; opposite side 136 unchanged.\n"
 "- Permanent Sponges 21.1.0 + Puzzles Lib 21.1.62 unchanged from TEST.1.\n"
 "- Added Unbreakable Catalyst 1.0.2: NeoForge analogue of BCG/Things Hardening Catalyst.\n"
 "- SGP Fixes rev 1.15: aqueous_sponge_on_a_stick and magmatic_sponge_on_a_stick added to soulbound:enchantable.\n"
 "- Runtime check: apply Unbreakable Catalyst and Soulbound to BOTH sponge sticks, then verify sponge use still works.\n"
 "- BOTH-side additions are tested in singleplayer/integrated server; dedicated-server patch is not prepared during TEST.\n",
 "utf-8"
)

after=hashes(BUILD)
allowed={"patch.json","README.txt",fix["source"],CAT_SOURCE}
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed==allowed,changed

fixed=(2026,10,6,11,25,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.10.0-test.2"
    assert q["toVersion"]=="1.10.0-test.2"
    assert q["fromVersions"][-2:]==["1.9.1","1.10.0-test.1"]
    ca=next(a for a in q["actions"] if a.get("actionId")=="install-unbreakable-catalyst-1-0-2")
    b=z.read(ca["source"])
    assert hashlib.sha256(b).hexdigest()==ca["sha256"]
    fa=next(a for a in q["actions"] if a.get("target")==FIX_TARGET and a.get("type")=="copy")
    fb=z.read(fa["source"])
    assert hashlib.sha256(fb).hexdigest()==fa["sha256"]
    import io
    with zipfile.ZipFile(io.BytesIO(fb)) as fz:
        tag=json.loads(fz.read("data/soulbound/tags/item/enchantable.json"))
        assert tag["values"][-2:]==SPONGE_ITEMS

Path("client1100test2_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client1100test2_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("catalyst_sha.txt").write_text(shaf(CAT)+"\n","utf-8")
Path("catalyst_size.txt").write_text(str(CAT.stat().st_size)+"\n","utf-8")
Path("fixes115_sha.txt").write_text(shaf(new_fix)+"\n","utf-8")
Path("fixes115_size.txt").write_text(str(new_fix.stat().st_size)+"\n","utf-8")
print("CLIENT_1100_TEST2_CUMULATIVE_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
