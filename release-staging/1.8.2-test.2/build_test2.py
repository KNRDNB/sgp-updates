import hashlib, io, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.1.zip"
MOD=ROOT/"SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
OUT=ROOT/"SGP_ClientPatch_1.8.2-test.2.zip"
WORK=ROOT/".work-182-test2"
BUILD=WORK/"build"
DP_WORK=WORK/"sgp-fixes"

BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
OLD_FIXES_SHA="ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"
OLD_FIXES_SIZE=161325
FIXES_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
SOUL_TAG="data/soulbound/tags/item/enchantable.json"
SLOT_JSON="data/sgp_fixes/curios/slots/amulet_pocket.json"
SLOT_TAG="data/curios/tags/item/amulet_pocket.json"
MOD_TARGET="mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
MOD_SOURCE="files/"+MOD_TARGET

ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3",
 "1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3",
 "1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1"
]

OLD_SOUL_VALUES=[
 "#artifacts:artifacts",
 "#icarus:wings",
 "supplementaries:quiver",
 "sophisticatedbackpacks:backpack",
 "sophisticatedbackpacks:copper_backpack",
 "sophisticatedbackpacks:iron_backpack",
 "sophisticatedbackpacks:gold_backpack",
 "sophisticatedbackpacks:diamond_backpack",
 "sophisticatedbackpacks:netherite_backpack"
]

def shaf(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def shab(b):
    return hashlib.sha256(b).hexdigest()

def hashes(root):
    return {p.relative_to(root).as_posix(): shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file()
mod_sha=shaf(MOD)
mod_size=MOD.stat().st_size

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.1"
assert p["toVersion"]=="1.8.1"
for v in ACCEPTED[:-1]:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

fix=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIXES_TARGET]
assert len(fix)==1
fix=fix[0]
fix_path=BUILD/fix["source"]
assert fix_path.is_file()
assert fix_path.stat().st_size==OLD_FIXES_SIZE
assert shaf(fix_path)==OLD_FIXES_SHA
assert fix["sha256"].lower()==OLD_FIXES_SHA

before_outer=hashes(BUILD)

DP_WORK.mkdir(parents=True)
with zipfile.ZipFile(fix_path) as z:
    assert z.testzip() is None
    z.extractall(DP_WORK)

before_dp=hashes(DP_WORK)
meta_path=DP_WORK/"pack.mcmeta"
tag_path=DP_WORK/SOUL_TAG
meta=json.loads(meta_path.read_text("utf-8"))
assert meta["pack"]["pack_format"]==48
assert meta["pack"]["description"]=="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.10"
meta["pack"]["description"]="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.12"
meta_path.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")

tag=json.loads(tag_path.read_text("utf-8"))
assert tag=={"replace":False,"values":OLD_SOUL_VALUES}
tag["values"].append("apotheosis:potion_charm")
tag_path.write_text(json.dumps(tag,ensure_ascii=False,indent=2)+"\n","utf-8")

slot_path=DP_WORK/SLOT_JSON
slot_path.parent.mkdir(parents=True,exist_ok=True)
slot_path.write_text(json.dumps({
 "order":210,
 "size":6,
 "icon":"curios:slot/empty_charm_slot",
 "validators":["curios:tag"]
},ensure_ascii=False,indent=2)+"\n","utf-8")

slot_tag_path=DP_WORK/SLOT_TAG
slot_tag_path.parent.mkdir(parents=True,exist_ok=True)
slot_tag_path.write_text(json.dumps({
 "replace":False,
 "values":["apotheosis:potion_charm"]
},ensure_ascii=False,indent=2)+"\n","utf-8")

after_dp=hashes(DP_WORK)
changed=[k for k in set(before_dp)|set(after_dp) if before_dp.get(k)!=after_dp.get(k)]
assert set(changed)=={"pack.mcmeta",SOUL_TAG,SLOT_JSON,SLOT_TAG},changed
assert json.loads(tag_path.read_text("utf-8"))=={"replace":False,"values":OLD_SOUL_VALUES+["apotheosis:potion_charm"]}
assert json.loads(slot_path.read_text("utf-8"))=={
 "order":210,"size":6,"icon":"curios:slot/empty_charm_slot","validators":["curios:tag"]
}
assert json.loads(slot_tag_path.read_text("utf-8"))=={
 "replace":False,"values":["apotheosis:potion_charm"]
}

fixed=(2026,10,5,20,30,0)
new_dp=WORK/"SGP_Fixes_NeoForge_1.21.1.zip"
with zipfile.ZipFile(new_dp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in DP_WORK.rglob("*") if x.is_file()):
        arc=f.relative_to(DP_WORK).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(new_dp) as z:
    assert z.testzip() is None
    assert json.loads(z.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.12")
    assert json.loads(z.read(SOUL_TAG))["values"]==OLD_SOUL_VALUES+["apotheosis:potion_charm"]
    assert json.loads(z.read(SLOT_JSON))["size"]==6
    assert json.loads(z.read(SLOT_TAG))["values"]==["apotheosis:potion_charm"]

new_dp_sha=shaf(new_dp)
new_dp_size=new_dp.stat().st_size
shutil.copyfile(new_dp,fix_path)
fix["sha256"]=new_dp_sha
fix["size"]=new_dp_size
if "description" in fix:
    fix["description"]="Установить SGP fixes rev 1.12: Potion Charm Soulbound + 6-slot Amulet Pocket"

mod_payload=BUILD/MOD_SOURCE
mod_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,mod_payload)

p["patchId"]="sgp-client-1.8.2-test.2"
p["name"]="SGP Client 1.8.2-test.2"
p["toVersion"]="1.8.2-test.2"
assert "1.8.1" not in p["fromVersions"]
p["fromVersions"]=list(p["fromVersions"])+["1.8.1","1.8.2-test.1"]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert p["fromVersions"][-1]=="1.8.2-test.1"
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "TEST.2: properly allow Soulbound on Apotheosis Potion Charms via a narrow runtime compatibility mixin.",
 "Adds a 6-slot Curios type amulet_pocket for Potion Charms only; Russian display name: Кармашек для амулетов.",
 "SGP Fixes internal rev 1.12 keeps apotheosis:potion_charm in soulbound:enchantable and adds the Curios slot/tag.",
 "No unrelated enchantments are enabled for Potion Charms; no other server/gameplay configs are changed."
]

p["actions"].append({
 "actionId":"install-sgp-apotheosis-soulbound-compat-1-0-0",
 "type":"copy",
 "description":"Установить точечный compat: Soulbound разрешён на Apotheosis Potion Charm",
 "source":MOD_SOURCE,
 "target":MOD_TARGET,
 "sha256":mod_sha,
 "size":mod_size
})

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.8.2-test.2\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Potion Charm Soulbound + Amulet Pocket TEST.\n"
 "- Exact Apotheosis 8.8.0 blocks all normal enchantments in PotionCharmItem.supportsEnchantment().\n"
 "- SGP compat allows only soulbound:soulbound.\n"
 "- SGP Fixes rev 1.12 adds a 6-slot amulet_pocket Curios slot for apotheosis:potion_charm only.\n"
 "- Russian slot name: Кармашек для амулетов.\n"
 "- Cumulative from all accepted stable versions through 1.8.1 and forward-repair from 1.8.2-test.1.\n",
 "utf-8"
)

after_outer=hashes(BUILD)
allowed={"patch.json","README.txt",fix["source"],MOD_SOURCE}
outer_changed={k for k in set(before_outer)|set(after_outer) if before_outer.get(k)!=after_outer.get(k)}
assert outer_changed==allowed,outer_changed

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
    assert q["patchId"]=="sgp-client-1.8.2-test.2"
    assert q["toVersion"]=="1.8.2-test.2"
    for v in ACCEPTED: assert v in q["fromVersions"],v
    assert q["fromVersions"][-1]=="1.8.2-test.1"
    nested=z.read(fix["source"])
    assert hashlib.sha256(nested).hexdigest()==new_dp_sha
    mod=z.read(MOD_SOURCE)
    assert hashlib.sha256(mod).hexdigest()==mod_sha
    with zipfile.ZipFile(io.BytesIO(nested)) as dz:
        assert dz.testzip() is None
        assert json.loads(dz.read(SLOT_JSON))["size"]==6
        assert json.loads(dz.read(SLOT_TAG))["values"]==["apotheosis:potion_charm"]

Path("fixes_rev112_sha.txt").write_text(new_dp_sha+"\n","utf-8")
Path("fixes_rev112_size.txt").write_text(str(new_dp_size)+"\n","utf-8")
Path("compat_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("compat_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")

print("CLIENT_182_TEST2_CUMULATIVE_AUDIT_PASS")
print("FIXES_SHA="+new_dp_sha)
print("FIXES_SIZE="+str(new_dp_size))
print("MOD_SHA="+mod_sha)
print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
