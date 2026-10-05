import hashlib, io, json, re, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.1.zip"
MOD=ROOT/"SGP-Apotheosis-Soulbound-Compat-1.0.0.jar"
OUT=ROOT/"SGP_ClientPatch_1.8.2-test.4.zip"
WORK=ROOT/".work-182-test4"
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
EXPECTED_RU19_SHA="69cb222e2983abddb2a5dbd56c0e2d1a749529a2f332d3ae03376b3a7e3a7418"
EXPECTED_RU19_SIZE=360396

FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
RU_TARGET="config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip"
CURIOS_CONFIG_TARGET="config/curios-common.toml"
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
BASE_CURIOS_SLOTS=[
 "id=wings;size=1;order=-100;add_cosmetic=true",
 "id=quiver;size=1;order=-90;add_cosmetic=true",
 "id=glasses;size=1;order=-80;add_cosmetic=true",
]
NEW_CURIOS_SLOT="id=amulet_pocket;size=6;order=-70"

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
for v in ACCEPTED[:-1]:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

fix_actions=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET]
ru_actions=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==RU_TARGET]
assert len(fix_actions)==1,fix_actions
assert len(ru_actions)==1,ru_actions
fix=fix_actions[0]
ru=ru_actions[0]
fix_path=BUILD/fix["source"]
ru_path=BUILD/ru["source"]
assert shaf(fix_path)==OLD_FIXES_SHA and fix_path.stat().st_size==OLD_FIXES_SIZE
assert shaf(ru_path)==OLD_RU_SHA and ru_path.stat().st_size==OLD_RU_SIZE

before_outer=hashes(BUILD)

# --- SGP Fixes rev 1.14 ---
FIX_DIR.mkdir(parents=True)
with zipfile.ZipFile(fix_path) as z:
    assert z.testzip() is None
    z.extractall(FIX_DIR)
before_fix=hashes(FIX_DIR)

meta=FIX_DIR/"pack.mcmeta"
m=json.loads(meta.read_text("utf-8"))
assert m["pack"]["description"]=="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.10"
m["pack"]["description"]="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.14"
meta.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n","utf-8")

soul=FIX_DIR/"data/soulbound/tags/item/enchantable.json"
s=json.loads(soul.read_text("utf-8"))
assert s=={"replace":False,"values":OLD_SOUL}
s["values"].append("apotheosis:potion_charm")
soul.write_text(json.dumps(s,ensure_ascii=False,indent=2)+"\n","utf-8")

# Curios config creates the slot; datapack only declares which item is valid for that slot.
slot_tag=FIX_DIR/"data/curios/tags/item/amulet_pocket.json"
slot_tag.parent.mkdir(parents=True,exist_ok=True)
slot_tag.write_text(
    json.dumps({"replace":False,"values":["apotheosis:potion_charm"]},ensure_ascii=False,indent=2)+"\n",
    "utf-8"
)

# test.4 intentionally has NO datapack slot definition. Config is the single slot-registration mechanism.
bad_slot=FIX_DIR/"data/sgp_fixes/curios/slots/amulet_pocket.json"
assert not bad_slot.exists()

after_fix=hashes(FIX_DIR)
changed_fix={k for k in set(before_fix)|set(after_fix) if before_fix.get(k)!=after_fix.get(k)}
assert changed_fix=={
 "pack.mcmeta",
 "data/soulbound/tags/item/enchantable.json",
 "data/curios/tags/item/amulet_pocket.json"
},changed_fix

fixed=(2026,10,5,21,45,0)
new_fix=WORK/"SGP_Fixes_NeoForge_1.21.1.zip"
with zipfile.ZipFile(new_fix,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in FIX_DIR.rglob("*") if x.is_file()):
        arc=f.relative_to(FIX_DIR).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(new_fix) as z:
    assert z.testzip() is None
    assert json.loads(z.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.14")
    assert json.loads(z.read("data/soulbound/tags/item/enchantable.json"))["values"][-1]=="apotheosis:potion_charm"
    assert json.loads(z.read("data/curios/tags/item/amulet_pocket.json"))=={
        "replace":False,"values":["apotheosis:potion_charm"]
    }
    assert "data/sgp_fixes/curios/slots/amulet_pocket.json" not in z.namelist()
new_fix_sha=shaf(new_fix)
new_fix_size=new_fix.stat().st_size
shutil.copyfile(new_fix,fix_path)
fix["sha256"]=new_fix_sha
fix["size"]=new_fix_size
fix["description"]="Установить SGP fixes rev 1.14: Potion Charm Soulbound + Curios item tag"

# --- SGP RU Localization 1.9, byte-identical to test.3 ---
RU_DIR.mkdir(parents=True)
with zipfile.ZipFile(ru_path) as z:
    assert z.testzip() is None
    z.extractall(RU_DIR)
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
assert "Изменения 1.9:" not in rt
rt=rt.rstrip()+"\n\n\nИзменения 1.9:\n- Curios: добавлен перевод слота glasses → «Очки».\n- Curios: добавлено название нового слота amulet_pocket → «Кармашек для амулетов».\n"
readme.write_text(rt,"utf-8")

# Preserve exact test.3 archive bytes by using test.3's deterministic ZIP timestamp.
ru_fixed=(2026,10,5,21,15,0)
new_ru=WORK/"SGP_RU_Localization_MC1.21.1.zip"
with zipfile.ZipFile(new_ru,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in RU_DIR.rglob("*") if x.is_file()):
        arc=f.relative_to(RU_DIR).as_posix()
        zi=zipfile.ZipInfo(arc,ru_fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
new_ru_sha=shaf(new_ru)
new_ru_size=new_ru.stat().st_size
assert new_ru_sha==EXPECTED_RU19_SHA,(new_ru_sha,EXPECTED_RU19_SHA)
assert new_ru_size==EXPECTED_RU19_SIZE,(new_ru_size,EXPECTED_RU19_SIZE)
shutil.copyfile(new_ru,ru_path)
ru["sha256"]=new_ru_sha
ru["size"]=new_ru_size
ru["description"]="Установить SGP RU Localization 1.9: Очки + Кармашек для амулетов"

# --- Curios managed common config: use the already-proven SGP config mechanism ---
config_actions=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==CURIOS_CONFIG_TARGET]
if len(config_actions)>1:
    raise AssertionError(config_actions)

if config_actions:
    cfg_action=config_actions[0]
    cfg_path=BUILD/cfg_action["source"]
    assert cfg_path.is_file()
    raw=cfg_path.read_text("utf-8")
else:
    cfg_path=BUILD/"files/config/curios-common.toml"
    cfg_path.parent.mkdir(parents=True,exist_ok=True)
    raw=(
      "#List of slots to create or modify.\n"
      "#See documentation for syntax: https://docs.illusivesoulworks.com/curios/configuration#slot-configuration\n"
      "#\n"
      'slots = ["id=wings;size=1;order=-100;add_cosmetic=true", "id=quiver;size=1;order=-90;add_cosmetic=true", "id=glasses;size=1;order=-80;add_cosmetic=true"]\n'
    )
    cfg_path.write_text(raw,"utf-8")
    cfg_action={
      "actionId":"install-curios-common-amulet-pocket",
      "type":"copy",
      "description":"Обновить Curios common config: добавить 6 слотов Кармашек для амулетов",
      "source":"files/config/curios-common.toml",
      "target":CURIOS_CONFIG_TARGET,
      "sha256":"",
      "size":0
    }
    p["actions"].append(cfg_action)

slots_line=None
for line in raw.splitlines():
    if line.startswith("slots = "):
        slots_line=line
        break
assert slots_line is not None
for entry in BASE_CURIOS_SLOTS:
    assert entry in slots_line,entry
assert NEW_CURIOS_SLOT not in slots_line

new_entries=BASE_CURIOS_SLOTS+[NEW_CURIOS_SLOT]
new_slots_line="slots = ["+", ".join(json.dumps(x,ensure_ascii=False) for x in new_entries)+"]"
new_raw=raw.replace(slots_line,new_slots_line,1)
assert new_raw.count(NEW_CURIOS_SLOT)==1
cfg_path.write_text(new_raw,"utf-8")
cfg_action["sha256"]=shaf(cfg_path)
cfg_action["size"]=cfg_path.stat().st_size
cfg_action["description"]="Обновить Curios common config: 6 слотов «Кармашек для амулетов»"
cfg_sha=cfg_action["sha256"]
cfg_size=cfg_action["size"]

# Preserve already-working Soulbound compat bytes exactly.
mod_payload=BUILD/MOD_SOURCE
mod_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,mod_payload)

p["patchId"]="sgp-client-1.8.2-test.4"
p["name"]="SGP Client 1.8.2-test.4"
p["toVersion"]="1.8.2-test.4"
assert "1.8.1" not in p["fromVersions"]
p["fromVersions"]=list(p["fromVersions"])+[
    "1.8.1","1.8.2-test.1","1.8.2-test.2","1.8.2-test.3"
]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert p["fromVersions"][-3:]==["1.8.2-test.1","1.8.2-test.2","1.8.2-test.3"]
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "TEST.4: keep working Potion Charm Soulbound compat and RU translations byte-identical.",
 "Create the 6-slot Amulet Pocket through managed config/curios-common.toml, the same mechanism already used by SGP wings/quiver/glasses.",
 "SGP Fixes rev 1.14 now owns only Potion Charm Soulbound eligibility and the curios:amulet_pocket item tag; the failed datapack slot definition is removed.",
 "Cumulative from every accepted stable through 1.8.1 plus forward repair from 1.8.2-test.1/test.2/test.3."
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
 "SGP Client 1.8.2-test.4\n"
 "Potion Charm Soulbound + 6-slot Amulet Pocket via curios-common.toml.\n"
 "- Soulbound compat JAR unchanged from owner-PASS test.2/test.3.\n"
 "- RU Localization 1.9 unchanged from owner-PASS translation test.3.\n"
 "- Amulet Pocket is now created by the same Curios common-config mechanism as wings/quiver/glasses.\n"
 "- Exactly 6 equipment slots; only apotheosis:potion_charm is tagged valid.\n",
 "utf-8"
)

after_outer=hashes(BUILD)
allowed={"patch.json","README.txt",fix["source"],ru["source"],cfg_action["source"],MOD_SOURCE}
changed_outer={k for k in set(before_outer)|set(after_outer) if before_outer.get(k)!=after_outer.get(k)}
assert changed_outer==allowed,changed_outer

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
    assert q["patchId"]=="sgp-client-1.8.2-test.4"
    assert q["toVersion"]=="1.8.2-test.4"
    for v in ACCEPTED: assert v in q["fromVersions"],v
    assert q["fromVersions"][-3:]==["1.8.2-test.1","1.8.2-test.2","1.8.2-test.3"]
    assert hashlib.sha256(z.read(MOD_SOURCE)).hexdigest()==MOD_SHA
    ca=next(a for a in q["actions"] if a.get("target")==CURIOS_CONFIG_TARGET)
    cfg=z.read(ca["source"]).decode("utf-8")
    assert cfg.count(NEW_CURIOS_SLOT)==1

Path("fixes_rev114_sha.txt").write_text(new_fix_sha+"\n","utf-8")
Path("fixes_rev114_size.txt").write_text(str(new_fix_size)+"\n","utf-8")
Path("ru_19_sha.txt").write_text(new_ru_sha+"\n","utf-8")
Path("ru_19_size.txt").write_text(str(new_ru_size)+"\n","utf-8")
Path("curios_config_sha.txt").write_text(cfg_sha+"\n","utf-8")
Path("curios_config_size.txt").write_text(str(cfg_size)+"\n","utf-8")
print("CLIENT_182_TEST4_CUMULATIVE_AUDIT_PASS")
print("FIXES_SHA="+new_fix_sha)
print("FIXES_SIZE="+str(new_fix_size))
print("RU_SHA="+new_ru_sha)
print("RU_SIZE="+str(new_ru_size))
print("CONFIG_SHA="+cfg_sha)
print("CONFIG_SIZE="+str(cfg_size))
print("MOD_SHA="+MOD_SHA)
print("MOD_SIZE="+str(MOD_SIZE))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
