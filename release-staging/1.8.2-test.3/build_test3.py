import hashlib, io, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.1.zip"
MOD=ROOT/"SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
OUT=ROOT/"SGP_ClientPatch_1.8.2-test.3.zip"
WORK=ROOT/".work-182-test3"
BUILD=WORK/"build"
FIX_DIR=WORK/"sgp-fixes"
RU_DIR=WORK/"sgp-ru"

BASE_SHA="9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
MOD_SHA="2e4857df16f2df04ef7b86674bd26cf737d671931646ccb4b707c4a7a6cf46d9"
MOD_SIZE=4256
OLD_FIXES_SHA="ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"
OLD_FIXES_SIZE=161325
OLD_RU_SHA="2dc1cb97a8f6be31bf3df326cc84355b49d82241b14498c922a87e80e8502a6d"
OLD_RU_SIZE=409577
FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
RU_TARGET="config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip"
MOD_TARGET="mods/SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
MOD_SOURCE="files/"+MOD_TARGET

ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1"
]
OLD_SOUL=[
 "#artifacts:artifacts","#icarus:wings","supplementaries:quiver",
 "sophisticatedbackpacks:backpack","sophisticatedbackpacks:copper_backpack",
 "sophisticatedbackpacks:iron_backpack","sophisticatedbackpacks:gold_backpack",
 "sophisticatedbackpacks:diamond_backpack","sophisticatedbackpacks:netherite_backpack"
]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file() and shaf(MOD)==MOD_SHA and MOD.stat().st_size==MOD_SIZE
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.1"
assert p["toVersion"]=="1.8.1"
for v in ACCEPTED[:-1]: assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

fix=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET]
ru=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==RU_TARGET]
assert len(fix)==1,fix
assert len(ru)==1,ru
fix=fix[0]; ru=ru[0]
fix_path=BUILD/fix["source"]; ru_path=BUILD/ru["source"]
assert shaf(fix_path)==OLD_FIXES_SHA and fix_path.stat().st_size==OLD_FIXES_SIZE
assert shaf(ru_path)==OLD_RU_SHA and ru_path.stat().st_size==OLD_RU_SIZE

before_outer=hashes(BUILD)

# SGP Fixes rev 1.13
FIX_DIR.mkdir(parents=True)
with zipfile.ZipFile(fix_path) as z:
    assert z.testzip() is None
    z.extractall(FIX_DIR)
before_fix=hashes(FIX_DIR)

meta=FIX_DIR/"pack.mcmeta"
m=json.loads(meta.read_text("utf-8"))
assert m["pack"]["description"]=="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.10"
m["pack"]["description"]="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.13"
meta.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n","utf-8")

soul=FIX_DIR/"data/soulbound/tags/item/enchantable.json"
s=json.loads(soul.read_text("utf-8"))
assert s=={"replace":False,"values":OLD_SOUL}
s["values"].append("apotheosis:potion_charm")
soul.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n","utf-8")

slot=FIX_DIR/"data/sgp_fixes/curios/slots/amulet_pocket.json"
slot.parent.mkdir(parents=True,exist_ok=True)
slot_data={
 "order":210,
 "size":6,
 "icon":"curios:slot/empty_charm_slot",
 "validators":["curios:tag"],
 "entities":["minecraft:player"]
}
slot.write_text(json.dumps(slot_data,ensure_ascii=False,indent=2)+"\n","utf-8")

slot_tag=FIX_DIR/"data/curios/tags/item/amulet_pocket.json"
slot_tag.parent.mkdir(parents=True,exist_ok=True)
slot_tag.write_text(json.dumps({"replace":False,"values":["apotheosis:potion_charm"]},ensure_ascii=False,indent=2)+"\n","utf-8")

after_fix=hashes(FIX_DIR)
changed_fix={k for k in set(before_fix)|set(after_fix) if before_fix.get(k)!=after_fix.get(k)}
assert changed_fix=={
 "pack.mcmeta",
 "data/soulbound/tags/item/enchantable.json",
 "data/sgp_fixes/curios/slots/amulet_pocket.json",
 "data/curios/tags/item/amulet_pocket.json"
},changed_fix

fixed=(2026,10,5,21,15,0)
new_fix=WORK/"SGP_Fixes_NeoForge_1.21.1.zip"
with zipfile.ZipFile(new_fix,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in FIX_DIR.rglob("*") if x.is_file()):
        arc=f.relative_to(FIX_DIR).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(new_fix) as z:
    assert z.testzip() is None
    assert json.loads(z.read("data/sgp_fixes/curios/slots/amulet_pocket.json"))==slot_data
    assert json.loads(z.read("data/curios/tags/item/amulet_pocket.json"))["values"]==["apotheosis:potion_charm"]
new_fix_sha=shaf(new_fix); new_fix_size=new_fix.stat().st_size
shutil.copyfile(new_fix,fix_path)
fix["sha256"]=new_fix_sha; fix["size"]=new_fix_size
fix["description"]="Установить SGP fixes rev 1.13: Potion Charm Soulbound + 6-player Amulet Pocket slots"

# SGP RU Localization 1.9
RU_DIR.mkdir(parents=True)
with zipfile.ZipFile(ru_path) as z:
    assert z.testzip() is None
    z.extractall(RU_DIR)
before_ru=hashes(RU_DIR)
ru_meta=RU_DIR/"pack.mcmeta"
rm=json.loads(ru_meta.read_text("utf-8"))
assert rm["pack"]["description"]=="SGP RU Localization 1.8 — Building Wands 3.0.5 full Russian localization"
rm["pack"]["description"]="SGP RU Localization 1.9 — Curios slot names + Building Wands 3.0.5"
ru_meta.write_text(json.dumps(rm,ensure_ascii=False,indent=2)+"\n","utf-8")

ru_lang=RU_DIR/"assets/curios/lang/ru_ru.json"
lang=json.loads(ru_lang.read_text("utf-8"))
assert lang["curios.identifier.wings"]=="Крылья"
assert lang["curios.identifier.quiver"]=="Колчан"
assert "curios.identifier.glasses" not in lang
lang["curios.identifier.glasses"]="Очки"
lang["curios.identifier.amulet_pocket"]="Кармашек для амулетов"
ru_lang.write_text(json.dumps(lang,ensure_ascii=False,indent=2)+"\n","utf-8")

readme=RU_DIR/"README_SGP_RU.txt"
rt=readme.read_text("utf-8")
if "Изменения 1.9:" not in rt:
    rt=rt.rstrip()+"\n\n\nИзменения 1.9:\n- Curios: добавлен перевод слота glasses → «Очки».\n- Curios: добавлено название нового слота amulet_pocket → «Кармашек для амулетов».\n"
readme.write_text(rt,"utf-8")

after_ru=hashes(RU_DIR)
changed_ru={k for k in set(before_ru)|set(after_ru) if before_ru.get(k)!=after_ru.get(k)}
assert changed_ru=={"pack.mcmeta","assets/curios/lang/ru_ru.json","README_SGP_RU.txt"},changed_ru

new_ru=WORK/"SGP_RU_Localization_MC1.21.1.zip"
with zipfile.ZipFile(new_ru,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in RU_DIR.rglob("*") if x.is_file()):
        arc=f.relative_to(RU_DIR).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(new_ru) as z:
    assert z.testzip() is None
    live=json.loads(z.read("assets/curios/lang/ru_ru.json"))
    assert live["curios.identifier.glasses"]=="Очки"
    assert live["curios.identifier.amulet_pocket"]=="Кармашек для амулетов"
new_ru_sha=shaf(new_ru); new_ru_size=new_ru.stat().st_size
shutil.copyfile(new_ru,ru_path)
ru["sha256"]=new_ru_sha; ru["size"]=new_ru_size
ru["description"]="Установить SGP RU Localization 1.9: Очки + Кармашек для амулетов"

mod_payload=BUILD/MOD_SOURCE
mod_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,mod_payload)

p["patchId"]="sgp-client-1.8.2-test.3"
p["name"]="SGP Client 1.8.2-test.3"
p["toVersion"]="1.8.2-test.3"
assert "1.8.1" not in p["fromVersions"]
p["fromVersions"]=list(p["fromVersions"])+["1.8.1","1.8.2-test.1","1.8.2-test.2"]
for v in ACCEPTED: assert v in p["fromVersions"],v
assert p["fromVersions"][-1]=="1.8.2-test.2"
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "TEST.3: preserve the working Potion Charm Soulbound compat from test.2 byte-for-byte.",
 "Fix Amulet Pocket registration by binding the 6-slot type to minecraft:player.",
 "Update SGP RU Localization to 1.9: Glasses -> Очки and amulet_pocket -> Кармашек для амулетов.",
 "Cumulative from every accepted stable through 1.8.1, plus forward repair from 1.8.2-test.1/test.2."
]
p["actions"].append({
 "actionId":"install-sgp-apotheosis-soulbound-compat-1-0-0",
 "type":"copy",
 "description":"Установить проверенный Potion Charm Soulbound compat 1.0.0",
 "source":MOD_SOURCE,
 "target":MOD_TARGET,
 "sha256":MOD_SHA,
 "size":MOD_SIZE
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
 "SGP Client 1.8.2-test.3\n"
 "Potion Charm Soulbound + fixed 6-slot Amulet Pocket + Curios RU names.\n"
 "- Soulbound compat JAR is byte-identical to test.2.\n"
 "- amulet_pocket is attached to minecraft:player and has size=6.\n"
 "- Glasses = Очки; amulet_pocket = Кармашек для амулетов.\n",
 "utf-8"
)
after_outer=hashes(BUILD)
allowed={"patch.json","README.txt",fix["source"],ru["source"],MOD_SOURCE}
changed_outer={k for k in set(before_outer)|set(after_outer) if before_outer.get(k)!=after_outer.get(k)}
assert changed_outer==allowed,changed_outer

with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.8.2-test.3"
    assert q["toVersion"]=="1.8.2-test.3"
    for v in ACCEPTED: assert v in q["fromVersions"],v
    assert q["fromVersions"][-1]=="1.8.2-test.2"
    assert hashlib.sha256(z.read(MOD_SOURCE)).hexdigest()==MOD_SHA

Path("fixes_rev113_sha.txt").write_text(new_fix_sha+"\n","utf-8")
Path("fixes_rev113_size.txt").write_text(str(new_fix_size)+"\n","utf-8")
Path("ru_19_sha.txt").write_text(new_ru_sha+"\n","utf-8")
Path("ru_19_size.txt").write_text(str(new_ru_size)+"\n","utf-8")
print("CLIENT_182_TEST3_CUMULATIVE_AUDIT_PASS")
print("FIXES_SHA="+new_fix_sha)
print("FIXES_SIZE="+str(new_fix_size))
print("RU_SHA="+new_ru_sha)
print("RU_SIZE="+str(new_ru_size))
print("MOD_SHA="+MOD_SHA)
print("MOD_SIZE="+str(MOD_SIZE))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
