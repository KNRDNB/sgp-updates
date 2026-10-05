import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT = Path.cwd()
BASE = ROOT / "SGP_ClientPatch_1.8.1.zip"
OUT = ROOT / "SGP_ClientPatch_1.8.2-test.1.zip"
WORK = ROOT / ".work-182-test1"
BUILD = WORK / "build"
DP_WORK = WORK / "sgp-fixes"

BASE_SHA = "9f367afb0f4a50d389f671a35767099c5793c2b255e5f385b73b541cf87c2ce8"
OLD_FIXES_SHA = "ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"
OLD_FIXES_SIZE = 161325
FIXES_TARGET = "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
ENCHANTABLE = "data/soulbound/tags/item/enchantable.json"
PACK_META = "pack.mcmeta"

ACCEPTED_OLD = [
    "1.0.0","1.0.1","1.0.2","1.0.3",
    "1.1.0","1.2.0","1.2.1",
    "1.3.0","1.3.1","1.3.2","1.3.3",
    "1.4.0",
    "1.5.0","1.5.1","1.5.2","1.5.3",
    "1.6.0","1.6.1","1.6.2",
    "1.7.0","1.7.1","1.8.0"
]
ACCEPTED_TARGET_SOURCES = ACCEPTED_OLD + ["1.8.1"]

OLD_VALUES = [
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
NEW_ITEM = "apotheosis:potion_charm"

def shaf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tree_hashes(root: Path):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file()
    }

assert BASE.is_file() and shaf(BASE) == BASE_SHA
if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

patch_path = BUILD / "patch.json"
patch = json.loads(patch_path.read_text("utf-8"))
assert patch["patchId"] == "sgp-client-1.8.1"
assert patch["toVersion"] == "1.8.1"
for version in ACCEPTED_OLD:
    assert version in patch["fromVersions"], version
assert "1.5.4" not in patch["fromVersions"]

matching = [
    a for a in patch["actions"]
    if a.get("type") == "copy" and a.get("target") == FIXES_TARGET
]
assert len(matching) == 1, matching
fix_action = matching[0]
fix_source = BUILD / fix_action["source"]
assert fix_source.is_file()
assert fix_source.stat().st_size == OLD_FIXES_SIZE
assert shaf(fix_source) == OLD_FIXES_SHA
assert fix_action["size"] == OLD_FIXES_SIZE
assert fix_action["sha256"].lower() == OLD_FIXES_SHA

base_payload_hashes = tree_hashes(BUILD)

DP_WORK.mkdir(parents=True)
with zipfile.ZipFile(fix_source) as z:
    assert z.testzip() is None
    z.extractall(DP_WORK)

before_dp = tree_hashes(DP_WORK)
assert ENCHANTABLE in before_dp
assert PACK_META in before_dp

meta_path = DP_WORK / PACK_META
meta = json.loads(meta_path.read_text("utf-8"))
assert meta["pack"]["pack_format"] == 48
assert meta["pack"]["description"] == "SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.10"
meta["pack"]["description"] = "SGP compatibility fixes • NeoForge 1.21.1 • internal rev 1.11"
meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")

tag_path = DP_WORK / ENCHANTABLE
tag = json.loads(tag_path.read_text("utf-8"))
assert tag == {"replace": False, "values": OLD_VALUES}
tag["values"].append(NEW_ITEM)
tag_path.write_text(json.dumps(tag, ensure_ascii=False, indent=2) + "\n", "utf-8")

after_dp = tree_hashes(DP_WORK)
assert set(before_dp) == set(after_dp)
changed = sorted(k for k in before_dp if before_dp[k] != after_dp[k])
assert changed == [ENCHANTABLE, PACK_META], changed

tag2 = json.loads(tag_path.read_text("utf-8"))
assert tag2["replace"] is False
assert tag2["values"][:-1] == OLD_VALUES
assert tag2["values"][-1] == NEW_ITEM
assert tag2["values"].count(NEW_ITEM) == 1

fixed = (2026, 10, 5, 19, 30, 0)
new_dp = WORK / "SGP_Fixes_NeoForge_1.21.1.zip"
with zipfile.ZipFile(new_dp, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in sorted(p for p in DP_WORK.rglob("*") if p.is_file()):
        arc = f.relative_to(DP_WORK).as_posix()
        zi = zipfile.ZipInfo(arc, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(new_dp) as z:
    assert z.testzip() is None
    meta_live = json.loads(z.read(PACK_META))
    tag_live = json.loads(z.read(ENCHANTABLE))
    assert meta_live["pack"]["description"].endswith("internal rev 1.11")
    assert tag_live["values"] == OLD_VALUES + [NEW_ITEM]

new_dp_sha = shaf(new_dp)
new_dp_size = new_dp.stat().st_size
assert new_dp_sha != OLD_FIXES_SHA
shutil.copyfile(new_dp, fix_source)

fix_action["sha256"] = new_dp_sha
fix_action["size"] = new_dp_size
if "description" in fix_action:
    fix_action["description"] = fix_action["description"].replace("1.10", "1.11")

patch["patchId"] = "sgp-client-1.8.2-test.1"
patch["name"] = "SGP Client 1.8.2-test.1"
patch["toVersion"] = "1.8.2-test.1"
assert "1.8.1" not in patch["fromVersions"]
patch["fromVersions"] = list(patch["fromVersions"]) + ["1.8.1"]
for version in ACCEPTED_TARGET_SOURCES:
    assert version in patch["fromVersions"], version
assert patch["fromVersions"][-1] == "1.8.1"
assert "1.5.4" not in patch["fromVersions"]
patch["summary"] = [
    "TEST: allow Soulbound to be applied to every Apotheosis Potion Charm variant.",
    "SGP Fixes internal rev 1.11 adds apotheosis:potion_charm to soulbound:enchantable.",
    "All potion effects use the same registry item, so Flight, Resistance and every other Potion Charm variant are covered.",
    "No Soulbound config, Apotheosis config, JEI, Create, MineColonies or JVM changes."
]
patch_path.write_text(json.dumps(patch, ensure_ascii=False, indent=2) + "\n", "utf-8")
(BUILD / "README.txt").write_text(
    "SGP Client 1.8.2-test.1\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Soulbound eligibility maintenance TEST.\n"
    "- SGP Fixes internal rev 1.11.\n"
    "- Adds apotheosis:potion_charm to soulbound:enchantable.\n"
    "- Covers every Apotheosis Potion Charm effect variant.\n"
    "- This enables applying Soulbound; it does not auto-enchant existing charms.\n",
    "utf-8"
)

for a in patch["actions"]:
    if a["type"] == "copy":
        f = BUILD / a["source"]
        assert f.is_file(), a["source"]
        assert f.stat().st_size == a["size"], a["actionId"]
        assert shaf(f).lower() == a["sha256"].lower(), a["actionId"]

after_payload_hashes = tree_hashes(BUILD)
allowed_outer_changes = {"patch.json", "README.txt", fix_action["source"]}
outer_changed = sorted(
    k for k in set(base_payload_hashes) | set(after_payload_hashes)
    if base_payload_hashes.get(k) != after_payload_hashes.get(k)
)
assert set(outer_changed) == allowed_outer_changes, outer_changed

with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in sorted(p for p in BUILD.rglob("*") if p.is_file()):
        arc = f.relative_to(BUILD).as_posix()
        zi = zipfile.ZipInfo(arc, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q = json.loads(z.read("patch.json"))
    assert q["patchId"] == "sgp-client-1.8.2-test.1"
    assert q["toVersion"] == "1.8.2-test.1"
    assert q["fromVersions"][-1] == "1.8.1"
    for version in ACCEPTED_TARGET_SOURCES:
        assert version in q["fromVersions"], version
    assert "1.5.4" not in q["fromVersions"]
    qa = [a for a in q["actions"] if a.get("type") == "copy" and a.get("target") == FIXES_TARGET]
    assert len(qa) == 1
    nested = z.read(qa[0]["source"])
    assert hashlib.sha256(nested).hexdigest() == new_dp_sha
    assert len(nested) == new_dp_size
    with zipfile.ZipFile(__import__("io").BytesIO(nested)) as dz:
        assert dz.testzip() is None
        assert json.loads(dz.read(PACK_META))["pack"]["description"].endswith("internal rev 1.11")
        assert json.loads(dz.read(ENCHANTABLE))["values"] == OLD_VALUES + [NEW_ITEM]

Path("sgp_fixes_rev111_sha.txt").write_text(new_dp_sha + "\n", "utf-8")
Path("sgp_fixes_rev111_size.txt").write_text(str(new_dp_size) + "\n", "utf-8")

print("CLIENT_182_TEST1_CUMULATIVE_AUDIT_PASS")
print("FIXES_REV=1.11")
print("FIXES_SHA=" + new_dp_sha)
print("FIXES_SIZE=" + str(new_dp_size))
print("FINAL_SHA=" + shaf(OUT))
print("FINAL_SIZE=" + str(OUT.stat().st_size))
