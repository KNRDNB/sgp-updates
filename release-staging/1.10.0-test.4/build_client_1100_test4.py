import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.10.0-test.3.zip"
OUT=ROOT/"SGP_ClientPatch_1.10.0-test.4.zip"
WORK=ROOT/".work-1100-test4"
BUILD=WORK/"build"
RU_DIR=WORK/"sgp-ru"

BASE_SHA="19bc0769966fd8903b75b1d87e648fba97f719c55cfef9d014c2893a27983328"
RU_TARGET="config/paxi/resourcepacks/SGP_RU_Localization_MC1.21.1.zip"
OLD_RU_SHA="69cb222e2983abddb2a5dbd56c0e2d1a749529a2f332d3ae03376b3a7e3a7418"
OLD_RU_SIZE=360396

TRANSLATIONS={
  "block.permanentsponges.aqueous_sponge":"Водная губка",
  "block.permanentsponges.magmatic_sponge":"Магматическая губка",
  "item.permanentsponges.aqueous_sponge_on_a_stick":"Водная губка на палочке",
  "item.permanentsponges.magmatic_sponge_on_a_stick":"Магматическая губка на палочке",
  "itemGroup.permanentsponges.main":"Вечные губки",
}

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
assert p["patchId"]=="sgp-client-1.10.0-test.3"
assert p["toVersion"]=="1.10.0-test.3"
assert p["fromVersions"][-3:]==["1.9.1","1.10.0-test.1","1.10.0-test.2"]
assert "1.5.4" not in p["fromVersions"]

# Preserve all passed gameplay/config deltas exactly.
hud=next(a for a in p["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
assert [e["value"] for e in hud["edits"]]==[-111,-111,-111,-111]
assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in p["actions"])
assert any(a.get("target")=="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar" for a in p["actions"])
assert not any(a.get("target")=="mods/unbreakablecatalyst-1.0.2.jar" for a in p["actions"])

fix=next(a for a in p["actions"] if a.get("type")=="copy" and a.get("target")=="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip")
fix_path=BUILD/fix["source"]
fix_before=shaf(fix_path)

ru_actions=[a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==RU_TARGET]
assert len(ru_actions)==1,ru_actions
ru=ru_actions[0]
ru_path=BUILD/ru["source"]
assert ru_path.is_file()
assert shaf(ru_path)==OLD_RU_SHA,(shaf(ru_path),OLD_RU_SHA)
assert ru_path.stat().st_size==OLD_RU_SIZE,(ru_path.stat().st_size,OLD_RU_SIZE)

before_outer=hashes(BUILD)

RU_DIR.mkdir(parents=True)
with zipfile.ZipFile(ru_path) as z:
    assert z.testzip() is None
    z.extractall(RU_DIR)
before_ru=hashes(RU_DIR)

meta=RU_DIR/"pack.mcmeta"
m=json.loads(meta.read_text("utf-8"))
assert m["pack"]["description"]=="SGP RU Localization 1.9 — Curios slot names + Building Wands 3.0.5"
m["pack"]["description"]="SGP RU Localization 1.10 — Permanent Sponges + Curios + Building Wands"
meta.write_text(json.dumps(m,ensure_ascii=False,indent=2)+"\n","utf-8")

lang=RU_DIR/"assets/permanentsponges/lang/ru_ru.json"
assert not lang.exists()
lang.parent.mkdir(parents=True,exist_ok=True)
lang.write_text(json.dumps(TRANSLATIONS,ensure_ascii=False,indent=2)+"\n","utf-8")

after_ru=hashes(RU_DIR)
changed_ru={k for k in set(before_ru)|set(after_ru) if before_ru.get(k)!=after_ru.get(k)}
assert changed_ru=={"pack.mcmeta","assets/permanentsponges/lang/ru_ru.json"},changed_ru

ru_fixed=(2026,10,6,18,25,0)
new_ru=WORK/"SGP_RU_Localization_MC1.21.1.zip"
with zipfile.ZipFile(new_ru,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in RU_DIR.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(RU_DIR).as_posix(),ru_fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(new_ru) as z:
    assert z.testzip() is None
    mm=json.loads(z.read("pack.mcmeta"))
    assert mm["pack"]["description"].startswith("SGP RU Localization 1.10")
    rr=json.loads(z.read("assets/permanentsponges/lang/ru_ru.json"))
    assert rr==TRANSLATIONS

shutil.copyfile(new_ru,ru_path)
ru["sha256"]=shaf(new_ru)
ru["size"]=new_ru.stat().st_size
ru["description"]="Установить SGP RU Localization 1.10: полный русский перевод Permanent Sponges"

# The only payload change after test.3 PASS is the localization resource pack.
assert shaf(fix_path)==fix_before
p["patchId"]="sgp-client-1.10.0-test.4"
p["name"]="SGP Client 1.10.0-test.4"
p["toVersion"]="1.10.0-test.4"
p["fromVersions"]=list(p["fromVersions"])+["1.10.0-test.3"]
assert p["fromVersions"][-4:]==["1.9.1","1.10.0-test.1","1.10.0-test.2","1.10.0-test.3"]
assert "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "TEST.4 localization-only delta after owner runtime PASS of TEST.3.",
 "SGP RU Localization 1.10 adds all five Permanent Sponges 21.1.0 Russian language keys.",
 "ArmorHUD, Permanent Sponges/Puzzles Lib, SGP Fixes rev 1.15, portal behavior and all other TEST.3 payload/actions remain unchanged.",
 "No dedicated-server patch is built during client TEST."
]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.10.0-test.4\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Localization-only TEST after TEST.3 runtime PASS:\n"
 "- Permanent Sponges translated through existing SGP RU Localization 1.10.\n"
 "- Водная губка / Магматическая губка.\n"
 "- Водная губка на палочке / Магматическая губка на палочке.\n"
 "- Creative tab: Вечные губки.\n"
 "- All gameplay/config bytes from TEST.3 remain unchanged.\n"
 "- Dedicated server is not prepared during TEST.\n",
 "utf-8"
)

after_outer=hashes(BUILD)
ru_source=ru["source"]
changed_outer={k for k in set(before_outer)|set(after_outer) if before_outer.get(k)!=after_outer.get(k)}
assert changed_outer=={"patch.json","README.txt",ru_source},changed_outer

fixed=(2026,10,6,18,30,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.10.0-test.4"
    assert q["toVersion"]=="1.10.0-test.4"
    assert q["fromVersions"][-4:]==["1.9.1","1.10.0-test.1","1.10.0-test.2","1.10.0-test.3"]
    r=next(a for a in q["actions"] if a.get("type")=="copy" and a.get("target")==RU_TARGET)
    rb=z.read(r["source"])
    assert hashlib.sha256(rb).hexdigest()==r["sha256"]
    assert len(rb)==r["size"]
    import io
    with zipfile.ZipFile(io.BytesIO(rb)) as rz:
        assert json.loads(rz.read("assets/permanentsponges/lang/ru_ru.json"))==TRANSLATIONS
    assert not any(a.get("target")=="mods/unbreakablecatalyst-1.0.2.jar" for a in q["actions"])

Path("client1100test4_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client1100test4_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("ru110_sha.txt").write_text(shaf(new_ru)+"\n","utf-8")
Path("ru110_size.txt").write_text(str(new_ru.stat().st_size)+"\n","utf-8")
print("CLIENT_1100_TEST4_LOCALIZATION_AUDIT_PASS")
print("RU_SHA="+shaf(new_ru))
print("RU_SIZE="+str(new_ru.stat().st_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
