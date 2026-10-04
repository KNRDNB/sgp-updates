#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN missing}"
: "${REPO:?REPO missing}"

ROOT="$PWD"
WORK="$ROOT/.work-170t2"
OUT="$ROOT/out-170t2"
rm -rf "$WORK" "$OUT"
mkdir -p "$WORK" "$OUT"
cd "$WORK"

V161="SGP_ClientPatch_1.6.1.zip"
V162="SGP_ClientPatch_1.6.2.zip"
VT1="SGP_ClientPatch_1.7.0-test.1.zip"
FINAL="SGP_ClientPatch_1.7.0-test.2.zip"

gh release download v1.6.1 --repo "$REPO" -p "$V161"
gh release download v1.6.2 --repo "$REPO" -p "$V162"
gh release download v1.7.0-test.1 --repo "$REPO" -p "$VT1"

echo "83d7849366efe854f055edf5a148d2ca0494b2ed60f19c4ae064a8028c8aa63f  $V161" | sha256sum -c -
echo "1a864e6187875304319418b09f1b48082b782b77130530686060f7eb442c8896  $V162" | sha256sum -c -
echo "ae66f323b358b6b965573e1405a7a0c7f103c4ca39b1a61cfcff1401dfbed421  $VT1" | sha256sum -c -

python3 - <<'PY'
from pathlib import Path
import zipfile, json, hashlib, shutil, copy, os

wd=Path(".")
v161=wd/"SGP_ClientPatch_1.6.1.zip"
v162=wd/"SGP_ClientPatch_1.6.2.zip"
vt1=wd/"SGP_ClientPatch_1.7.0-test.1.zip"
build=wd/"build"
if build.exists(): shutil.rmtree(build)
build.mkdir()

def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

with zipfile.ZipFile(v161) as z:
    assert z.testzip() is None
    z.extractall(build)
    p161=json.loads(z.read("patch.json"))

with zipfile.ZipFile(v162) as z:
    assert z.testzip() is None
    p162=json.loads(z.read("patch.json"))

with zipfile.ZipFile(vt1) as z:
    assert z.testzip() is None
    pt1=json.loads(z.read("patch.json"))
    for arc in [
        "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
    ]:
        dst=build/arc
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(z.read(arc))

stable=[
    "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
    "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1",
    "1.5.2","1.5.3","1.6.0","1.6.1","1.6.2"
]
legacy_base=stable[:-2]  # through 1.6.0
assert p161["fromVersions"] == legacy_base
assert p161["toVersion"] == "1.6.1"
assert p162["fromVersions"] == ["1.6.1"]
assert p162["toVersion"] == "1.6.2"
assert pt1["fromVersions"] == ["1.6.2"]
assert pt1["toVersion"] == "1.7.0-test.1"

# Replay/idempotence audit for accepted cumulative 1.6.1 base.
assert len(p161["actions"]) == 60
for a in p161["actions"]:
    t=a["type"]
    if t in {"delete","deleteGlob"}:
        assert a.get("optional") is True, (a["actionId"], "delete must be optional")
    elif t=="copy":
        assert "precondition" not in a, (a["actionId"], "copy precondition would block replay")
    elif t=="textReplaceExact":
        assert a.get("expectedOccurrences")==1
        assert a.get("alreadyAppliedText"), (a["actionId"], "text replace not idempotent")
    elif t=="optionsEdit":
        for e in a["edits"]:
            assert e["key"]=="forceUnicodeFont" and e["value"]=="false" and e.get("createIfMissing") is False
    elif t=="tomlEdit":
        for e in a["edits"]:
            assert e["op"] in {"set","arrayAddUnique"}, (a["actionId"],e)
            assert e.get("createIfMissing") is False
    else:
        raise AssertionError(("unexpected base action type",t,a["actionId"]))

# Accepted 1.6.2 localization actions are explicitly idempotent.
assert len(p162["actions"]) == 23
for a in p162["actions"]:
    assert a["type"]=="textReplaceExact"
    assert a["target"]=="config/apotheosis/name_generation.cfg"
    assert a["expectedOccurrences"]==1
    assert a.get("alreadyAppliedText")

# 1.6.1 cumulative payload does not mutate Wands or Apotheosis name generation;
# these deltas are layered explicitly below.
assert not any("BuildingWands" in (a.get("target") or "") for a in p161["actions"])
assert not any(a.get("target")=="config/wands.json" for a in p161["actions"])
assert not any(a.get("target")=="config/apotheosis/name_generation.cfg" for a in p161["actions"])

# Build SGP Fixes rev 1.10 from exact accepted rev 1.9 embedded in 1.6.1 payload.
fixes=build/"files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
assert fixes.exists()
assert fixes.stat().st_size==162427
assert sha_file(fixes)=="20c32d4e527fce247f216a4f868a6d53c61d543c3f981a158512e8f7c7718b57"
new_fixes=fixes.with_suffix(".new.zip")
recipe_path="data/sgp_fixes/recipe/compat/ends_delight/chorus_succulent.json"
recipe={
  "type":"minecraft:crafting_shapeless",
  "category":"misc",
  "ingredients":[
    {"item":"minecraft:chorus_fruit"},
    {"item":"minecraft:chorus_fruit"},
    {"item":"minecraft:chorus_fruit"},
    {"item":"minecraft:chorus_fruit"},
    {"item":"minecraft:bone_meal"}
  ],
  "result":{"id":"ends_delight:chorus_succulent","count":1},
  "neoforge:conditions":[
    {"type":"neoforge:mod_loaded","modid":"ends_delight"},
    {"type":"neoforge:mod_loaded","modid":"betterend"}
  ]
}
with zipfile.ZipFile(fixes,"r") as zin:
    infos=zin.infolist()
    original={i.filename:zin.read(i.filename) for i in infos}
    assert recipe_path not in original
    pm=json.loads(original["pack.mcmeta"])
    assert pm["pack"]["pack_format"]==48
    assert pm["pack"]["description"]=="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.9"
    pm["pack"]["description"]="SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.10"
    pm_bytes=(json.dumps(pm,ensure_ascii=False,indent=2)+"\n").encode()
    rec_bytes=(json.dumps(recipe,ensure_ascii=False,indent=2)+"\n").encode()
    with zipfile.ZipFile(new_fixes,"w") as zout:
        for old in infos:
            zi=zipfile.ZipInfo(old.filename,old.date_time)
            zi.compress_type=old.compress_type
            zi.comment=old.comment
            zi.extra=old.extra
            zi.internal_attr=old.internal_attr
            zi.external_attr=old.external_attr
            zi.create_system=old.create_system
            zi.flag_bits=old.flag_bits
            data=pm_bytes if old.filename=="pack.mcmeta" else original[old.filename]
            zout.writestr(zi,data)
        zi=zipfile.ZipInfo(recipe_path,(2026,10,4,0,0,0))
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644 << 16
        zout.writestr(zi,rec_bytes,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(new_fixes) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))
    assert set(names)==set(original)|{recipe_path}
    for n,b in original.items():
        if n!="pack.mcmeta":
            assert z.read(n)==b, ("unexpected SGP Fixes byte change",n)
    pm=json.loads(z.read("pack.mcmeta"))
    assert pm["pack"]["description"].endswith("internal rev 1.10")
    assert json.loads(z.read(recipe_path))==recipe
    for n in names:
        if n.endswith(".json"):
            json.loads(z.read(n))
    # Recipe-only compatibility addition: no new worldgen path.
    assert not recipe_path.startswith("data/minecraft/worldgen/")
new_fixes.replace(fixes)
fixes_sha=sha_file(fixes)
fixes_size=fixes.stat().st_size

# Replace the existing cumulative SGP Fixes action rather than adding a parallel datapack.
actions=copy.deepcopy(p161["actions"])
fix_action=[a for a in actions if a["actionId"]=="update-sgp-fixes-curios-equipment-slots"]
assert len(fix_action)==1
fix_action=fix_action[0]
fix_action["description"]="Обновить SGP Fixes до internal rev 1.10: существующие fixes + End's Delight × BetterEnd Chorus Succulent compat"
fix_action["sha256"]=fixes_sha
fix_action["size"]=fixes_size

# Fold accepted 1.6.2 localization into the cumulative target.
actions.extend(copy.deepcopy(p162["actions"]))

# Add 1.7.0 line.
wands_rel="files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar"
compat_rel="files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
wands=build/wands_rel
compat=build/compat_rel
assert sha_file(wands)=="565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
assert wands.stat().st_size==465238
assert sha_file(compat)=="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
assert compat.stat().st_size==3472

actions.extend([
  {
    "actionId":"remove-building-wands-2-14",
    "type":"delete",
    "description":"Удалить Building Wands 2.14, если он присутствует",
    "target":"mods/BuildingWands-neoforge-MC1.21-2.14.jar",
    "optional":True
  },
  {
    "actionId":"install-building-wands-3-0-5",
    "type":"copy",
    "description":"Установить Building Wands 3.0.5",
    "source":wands_rel,
    "target":"mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
    "sha256":sha_file(wands),
    "size":wands.stat().st_size
  },
  {
    "actionId":"install-wands-paxel-compat",
    "type":"copy",
    "description":"Установить SGP compat для Create: Ironworks paxel",
    "source":compat_rel,
    "target":"mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
    "sha256":sha_file(compat),
    "size":compat.stat().st_size
  },
  {
    "actionId":"remove-standalone-end-compat-test1",
    "type":"delete",
    "description":"Удалить standalone SGP End compat из superseded test.1; функция перенесена в SGP Fixes",
    "target":"config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip",
    "optional":True
  },
  {
    "actionId":"configure-wand-limits",
    "type":"jsonEdit",
    "description":"Настроить лимиты Building Wands",
    "target":"config/wands.json",
    "precondition":{"state":"exists"},
    "edits":[
      {"op":"set","path":"/max_limit___increment_this_if_your_machine_can_handle_it","value":8192,"createIfMissing":False},
      {"op":"set","path":"/stone_wand_limit","value":128,"createIfMissing":False},
      {"op":"set","path":"/copper_wand_limit","value":256,"createIfMissing":False},
      {"op":"set","path":"/iron_wand_limit","value":512,"createIfMissing":False},
      {"op":"set","path":"/diamond_wand_limit","value":1024,"createIfMissing":False},
      {"op":"set","path":"/netherite_wand_limit","value":4096,"createIfMissing":False},
      {"op":"set","path":"/creative_wand_limit","value":8192,"createIfMissing":False}
    ]
  }
])

from_versions=stable+["1.7.0-test.1"]
manifest={
  "schemaVersion":1,
  "patchId":"sgp-client-1.7.0-test.2",
  "name":"SGP Client 1.7.0-test.2",
  "targetPackId":"sgp-neoforge-1.21.1-client",
  "minecraft":"1.21.1",
  "neoforge":"21.1.249",
  "fromVersions":from_versions,
  "toVersion":"1.7.0-test.2",
  "restartRequired":True,
  "summary":[
    "Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.",
    "Все изменения accepted 1.6.1 cumulative + Apotheosis RU name generation из 1.6.2.",
    "Building Wands 2.14 → 3.0.5; лимиты 128 / 256 / 512 / 1024 / 4096 / 8192.",
    "SGP Wands Paxel Compat 1.0.0 для Create: Ironworks 4.0.3.",
    "End's Delight × BetterEnd Chorus Succulent compat встроен в SGP_Fixes_NeoForge_1.21.1.zip rev 1.10; worldgen не меняется."
  ],
  "actions":actions
}

# Unique action IDs and exact mandatory cumulative source set.
ids=[a["actionId"] for a in actions]
assert len(ids)==len(set(ids))
assert manifest["fromVersions"]==[
    "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
    "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1",
    "1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.7.0-test.1"
]
assert "1.5.4" not in manifest["fromVersions"]

# No protected or personal-state targets.
for a in actions:
    target=(a.get("target") or "").replace("\\","/")
    assert not target.startswith(".sgp/")
    assert not target.startswith("saves/")
    assert not target.startswith("journeymap/")
    assert target not in {"servers.dat"}
    assert ".." not in target.split("/")

(build/"patch.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(build/"README.txt").write_text("""SGP Client 1.7.0-test.2
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install is supported from every accepted stable SGP Client version 1.0.0 through 1.6.2.
Unofficial 1.5.4 is intentionally excluded.
1.7.0-test.1 is additionally supported as a forward-repair source.

Changes:
- Includes the full accepted 1.6.1 cumulative target state.
- Includes the accepted 1.6.2 Apotheosis RU name-generation fix.
- Building Wands 2.14 -> 3.0.5.
- Wands limits: Stone 128, Copper 256, Iron 512, Diamond 1024, Netherite 4096, Creative 8192, Global 8192.
- SGP Wands Paxel Compat 1.0.0 for Create: Ironworks 4.0.3.
- Chorus Succulent compatibility moved into existing SGP_Fixes_NeoForge_1.21.1.zip, internal rev 1.10.
- 4x Chorus Fruit + 1x Bone Meal -> 1x End's Delight Chorus Succulent when End's Delight and BetterEnd are loaded.
- End worldgen is not changed.

Runtime owner test is mandatory before stable 1.7.0.
""",encoding="utf-8")

# Final payload consistency before packaging.
for a in actions:
    if a["type"]=="copy":
        f=build/a["source"]
        assert f.is_file(), ("missing payload",a["source"])
        assert f.stat().st_size==a["size"], ("size",a["actionId"])
        assert sha_file(f).lower()==a["sha256"].lower(), ("sha",a["actionId"])

# No obsolete standalone End compat payload in the new ZIP.
assert not (build/"files/config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip").exists()

# Build deterministic archive from all build files.
out=wd/"SGP_ClientPatch_1.7.0-test.2.zip"
fixed=(2026,10,4,0,0,0)
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(p for p in build.rglob("*") if p.is_file()):
        arc=f.relative_to(build).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

# Archive safety/integrity.
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert len(names)==len(set(names))
    for n in names:
        assert not n.startswith("/")
        assert ".." not in Path(n).parts
        assert not n.startswith(".sgp/")
        assert not n.startswith("saves/")
        assert not n.startswith("journeymap/")
        assert n!="servers.dat"
    pm=json.loads(z.read("patch.json"))
    assert pm==manifest
    for a in pm["actions"]:
        if a["type"]=="copy":
            b=z.read(a["source"])
            assert len(b)==a["size"]
            assert sha_bytes(b).lower()==a["sha256"].lower()
    with zipfile.ZipFile(__import__("io").BytesIO(z.read("files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"))) as fz:
        assert fz.testzip() is None
        assert recipe_path in fz.namelist()
        assert json.loads(fz.read(recipe_path))==recipe

report={
  "candidate":"SGP_ClientPatch_1.7.0-test.2.zip",
  "sha256":sha_file(out),
  "size":out.stat().st_size,
  "actions":len(actions),
  "fromVersions":from_versions,
  "base161Actions":len(p161["actions"]),
  "localization162Actions":len(p162["actions"]),
  "fixesSha256":fixes_sha,
  "fixesSize":fixes_size,
  "checks":[
    "released 1.6.1/1.6.2/test.1 source SHA verified before build",
    "mandatory cumulative source set 1.0.0–1.6.2 present; 1.5.4 excluded",
    "1.7.0-test.1 forward repair included",
    "1.6.1 cumulative action replay/idempotence shape audited",
    "1.6.2 textReplaceExact actions all carry alreadyAppliedText",
    "SGP Fixes rev1.9 -> rev1.10 modifies only pack.mcmeta and adds one conditioned recipe",
    "all copy payload SHA/size match manifest",
    "archive paths unique/safe and protected personal/.sgp paths absent",
    "standalone SGP_EndCompat payload absent"
  ]
}
(wd/"audit-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
PY

# Exact final Mixin/target preflight.
WANDS="$WORK/build/files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar"
COMPAT="$WORK/build/files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar"

javap -classpath "$COMPAT" -p -v sgp.wands.paxelcompat.mixin.WandPaxelMixin > "$WORK/mixin.txt"
grep -Fq "major version: 65" "$WORK/mixin.txt"
grep -Fq "RuntimeInvisibleAnnotations" "$WORK/mixin.txt"
grep -Fq "org.spongepowered.asm.mixin.Mixin(" "$WORK/mixin.txt"
grep -Fq 'targets=["net.nicguzzo.wands.wand.Wand"]' "$WORK/mixin.txt"
grep -Fq "RuntimeVisibleAnnotations" "$WORK/mixin.txt"
grep -Fq "org.spongepowered.asm.mixin.injection.Inject(" "$WORK/mixin.txt"
grep -Fq "can_dig(Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z" "$WORK/mixin.txt"
grep -Fq "require=1" "$WORK/mixin.txt"
grep -Fq "cancellable=true" "$WORK/mixin.txt"

javap -classpath "$WANDS" -p -s net.nicguzzo.wands.wand.Wand > "$WORK/wands.txt"
grep -Fq "boolean can_dig(net.minecraft.world.level.block.state.BlockState, boolean, net.minecraft.world.item.ItemStack);" "$WORK/wands.txt"
grep -Fq "descriptor: (Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z" "$WORK/wands.txt"

python3 - <<'PY'
from pathlib import Path
import zipfile, re, json
compat=Path(".work-170t2/build/files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar")
with zipfile.ZipFile(compat) as z:
    assert z.testzip() is None
    names=z.namelist()
    assert "sgp/wands/paxelcompat/mixin/WandPaxelMixin.class" in names
    assert "sgp_wands_paxel_compat.mixins.json" in names
    assert not any(n.startswith("net/minecraft/") for n in names)
    assert not any(n.startswith("org/spongepowered/") for n in names)
    assert not any(n.startswith("net/neoforged/") for n in names)
    mx=json.loads(z.read("sgp_wands_paxel_compat.mixins.json"))
    assert "WandPaxelMixin" in mx.get("mixins",[])
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    for needle in ["modId=\"sgp_wands_paxel_compat\"","version=\"1.0.0\"","modId=\"wands\"","versionRange=\"[3.0.5]\"","modId=\"create_ironworks\"","versionRange=\"[4.0.3]\""]:
        assert needle in toml, needle
print("MIXIN PREFLIGHT: PASS")
PY

cp "$WORK/$FINAL" "$OUT/$FINAL"
cp "$WORK/audit-report.json" "$OUT/audit-report.json"
echo "$(sha256sum "$OUT/$FINAL" | awk '{print $1}')" > "$OUT/sha256.txt"
echo "BUILD_AUDIT_PASS"
