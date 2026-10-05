import hashlib
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path.cwd()
BASE = ROOT / "SGP_ClientPatch_1.7.1.zip"
CHIPPED = ROOT / "chipped-neoforge-1.21.1-4.0.2.jar"
CHIPPED_META = ROOT / "chipped-version.json"
DATAPACK = ROOT / "SGP_Create_Chipped_Cutting_MC1.21.1.zip"
OUT = ROOT / "SGP_ClientPatch_1.8.0-test.1.zip"
WORK = ROOT / ".work-180-test1"
BUILD = WORK / "build"
DP_BUILD = WORK / "datapack"

BASE_SHA = "999397411a293407057507d83039b070212574dfcb87fd370489cbecd54f3325"
CHIPPED_VERSION_ID = "eqVowbGc"
CHIPPED_VERSION = "4.0.2"
CHIPPED_FILENAME = "chipped-neoforge-1.21.1-4.0.2.jar"
TARGET_DP = "config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip"
SOURCE_DP = "files/" + TARGET_DP
RECIPE_NAMESPACE = "sgp_create_chipped_cutting"
PACK_FORMAT = 48
PROCESSING_TIME = 50

ACCEPTED_STABLES = [
    "1.0.0", "1.0.1", "1.0.2", "1.0.3", "1.1.0", "1.2.0", "1.2.1",
    "1.3.0", "1.3.1", "1.3.2", "1.3.3", "1.4.0", "1.5.0", "1.5.1",
    "1.5.2", "1.5.3", "1.6.0", "1.6.1", "1.6.2", "1.7.0", "1.7.1",
]
FORWARD_TESTS = [f"1.7.0-test.{i}" for i in range(1, 17)]
FROM_VERSIONS = ACCEPTED_STABLES + FORWARD_TESTS


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_resource_id(raw: str) -> str:
    if raw.startswith("#"):
        raise AssertionError(f"Nested tag is not expected in a Chipped family item tag: {raw}")
    return raw if ":" in raw else f"minecraft:{raw}"


def tag_entry_id(value) -> str:
    if isinstance(value, str):
        return normalize_resource_id(value)
    if isinstance(value, dict) and isinstance(value.get("id"), str):
        return normalize_resource_id(value["id"])
    raise AssertionError(f"Unsupported tag entry: {value!r}")


def safe_resource_path(resource_id: str) -> Path:
    ns, path = resource_id.split(":", 1)
    assert ns == "chipped"
    assert path and not path.startswith("/") and ".." not in path.split("/")
    return Path(*path.split("/"))


def recipe_filename(family: str, output_id: str) -> Path:
    # Chipped 4.0.2 intentionally has a few overlapping exposed workbench tags
    # (for example lantern + special_lantern). Keep every family->variant route
    # and make the recipe id unique by nesting under the family path.
    return safe_resource_path(family) / safe_resource_path(output_id).with_suffix(".json")


def verify_modrinth_metadata_and_jar() -> None:
    assert CHIPPED_META.is_file(), CHIPPED_META
    meta = json.loads(CHIPPED_META.read_text("utf-8"))
    assert meta["id"] == CHIPPED_VERSION_ID
    assert meta["version_number"] == CHIPPED_VERSION
    assert "1.21.1" in meta.get("game_versions", [])
    assert "neoforge" in meta.get("loaders", [])

    files = [f for f in meta.get("files", []) if f.get("filename") == CHIPPED_FILENAME]
    assert len(files) == 1, files
    mf = files[0]
    assert CHIPPED.is_file()
    assert CHIPPED.stat().st_size == mf["size"]
    data = CHIPPED.read_bytes()
    hashes = mf.get("hashes", {})
    if "sha512" in hashes:
        assert hashlib.sha512(data).hexdigest() == hashes["sha512"]
    if "sha1" in hashes:
        assert hashlib.sha1(data).hexdigest() == hashes["sha1"]

    with zipfile.ZipFile(CHIPPED) as z:
        assert z.testzip() is None
        names = set(z.namelist())
        assert "META-INF/neoforge.mods.toml" in names
        toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
        assert re.search(r'(?m)^\s*modId\s*=\s*["\']chipped["\']\s*$', toml), "Chipped mod id missing"
        assert CHIPPED_VERSION in toml, "Chipped version missing from NeoForge metadata"
        assert any(n.startswith("data/chipped/tags/item/") and n.endswith(".json") for n in names)
        assert any(n.startswith("data/chipped/recipe/") and n.endswith(".json") for n in names)


def discover_workbench_family_tags(z: zipfile.ZipFile) -> list[str]:
    family_tags: set[str] = set()
    workbench_recipe_count = 0
    for name in sorted(z.namelist()):
        if not (name.startswith("data/chipped/recipe/") and name.endswith(".json")):
            continue
        try:
            obj = json.loads(z.read(name))
        except Exception:
            continue
        if obj.get("type") != "chipped:workbench":
            continue
        workbench_recipe_count += 1
        ingredients = obj.get("ingredients")
        assert isinstance(ingredients, list) and ingredients, name
        for ing in ingredients:
            assert isinstance(ing, dict) and set(ing) == {"tag"}, (name, ing)
            tag = ing["tag"]
            assert isinstance(tag, str) and tag.startswith("chipped:"), (name, tag)
            family_tags.add(tag)
    assert workbench_recipe_count >= 5, workbench_recipe_count
    assert len(family_tags) >= 200, len(family_tags)
    return sorted(family_tags)


def build_datapack() -> tuple[int, int, str, int]:
    if DP_BUILD.exists():
        shutil.rmtree(DP_BUILD)
    recipe_root = DP_BUILD / "data" / RECIPE_NAMESPACE / "recipe"
    recipe_root.mkdir(parents=True)

    pack = {
        "pack": {
            "pack_format": PACK_FORMAT,
            "description": "SGP: Create Mechanical Saw recipes for Chipped 4.0.2 (MC 1.21.1)"
        }
    }
    (DP_BUILD / "pack.mcmeta").write_text(json.dumps(pack, ensure_ascii=False, indent=2) + "\n", "utf-8")

    family_to_outputs: dict[str, list[str]] = {}
    route_count = 0

    with zipfile.ZipFile(CHIPPED) as z:
        family_tags = discover_workbench_family_tags(z)
        names = set(z.namelist())
        for family in family_tags:
            tag_path = family.split(":", 1)[1]
            entry_name = f"data/chipped/tags/item/{tag_path}.json"
            assert entry_name in names, f"Missing current Chipped item tag: {family}"
            tag_obj = json.loads(z.read(entry_name))
            values = tag_obj.get("values")
            assert isinstance(values, list) and values, family

            chipped_outputs: list[str] = []
            for raw in values:
                rid = tag_entry_id(raw)
                if rid.startswith("chipped:"):
                    chipped_outputs.append(rid)
            chipped_outputs = sorted(set(chipped_outputs))
            assert chipped_outputs, family
            family_to_outputs[family] = chipped_outputs

            for out_id in chipped_outputs:
                recipe = {
                    "neoforge:conditions": [
                        {"type": "neoforge:mod_loaded", "modid": "create"},
                        {"type": "neoforge:mod_loaded", "modid": "chipped"},
                    ],
                    "type": "create:cutting",
                    "ingredients": [{"tag": family}],
                    "processing_time": PROCESSING_TIME,
                    "results": [{"count": 1, "id": out_id}],
                }
                dst = recipe_root / recipe_filename(family, out_id)
                dst.parent.mkdir(parents=True, exist_ok=True)
                assert not dst.exists(), dst
                dst.write_text(json.dumps(recipe, ensure_ascii=False, indent=2) + "\n", "utf-8")
                route_count += 1

    recipe_files = sorted(recipe_root.rglob("*.json"))
    assert len(recipe_files) == route_count
    assert len(recipe_files) >= 6000, len(recipe_files)

    fixed = (2026, 10, 5, 12, 0, 0)
    if DATAPACK.exists():
        DATAPACK.unlink()
    with zipfile.ZipFile(DATAPACK, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(x for x in DP_BUILD.rglob("*") if x.is_file()):
            arc = f.relative_to(DP_BUILD).as_posix()
            zi = zipfile.ZipInfo(arc, fixed)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(DATAPACK) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert "pack.mcmeta" in names
        mcmeta = json.loads(z.read("pack.mcmeta"))
        assert mcmeta["pack"]["pack_format"] == PACK_FORMAT
        recipes = [n for n in names if n.startswith(f"data/{RECIPE_NAMESPACE}/recipe/") and n.endswith(".json")]
        assert len(recipes) == len(recipe_files)
        assert not any("/recipes/" in n for n in names)
        for n in recipes:
            obj = json.loads(z.read(n))
            assert obj["type"] == "create:cutting"
            assert obj["processing_time"] == PROCESSING_TIME
            assert "processingTime" not in obj
            assert len(obj["ingredients"]) == 1 and "tag" in obj["ingredients"][0]
            assert obj["ingredients"][0]["tag"] in family_to_outputs
            assert len(obj["results"]) == 1
            result = obj["results"][0]
            assert result["count"] == 1
            assert result["id"].startswith("chipped:")
            assert "item" not in result
            assert obj["neoforge:conditions"] == [
                {"type": "neoforge:mod_loaded", "modid": "create"},
                {"type": "neoforge:mod_loaded", "modid": "chipped"},
            ]

    return len(family_to_outputs), len(recipe_files), sha256_file(DATAPACK), DATAPACK.stat().st_size


def build_patch(dp_sha: str, dp_size: int, family_count: int, recipe_count: int) -> tuple[str, int]:
    assert BASE.is_file() and sha256_file(BASE) == BASE_SHA
    if WORK.exists():
        shutil.rmtree(WORK)
    BUILD.mkdir(parents=True)
    with zipfile.ZipFile(BASE) as z:
        assert z.testzip() is None
        z.extractall(BUILD)

    mp = BUILD / "patch.json"
    p = json.loads(mp.read_text("utf-8"))
    assert p["patchId"] == "sgp-client-1.7.1"
    assert p["toVersion"] == "1.7.1"
    expected_base_from = ACCEPTED_STABLES[:-1] + FORWARD_TESTS
    assert p["fromVersions"] == expected_base_from, p["fromVersions"]
    assert "1.5.4" not in p["fromVersions"]

    old_actions = list(p["actions"])
    old_ids = [a["actionId"] for a in old_actions]
    assert len(old_ids) == len(set(old_ids))
    assert "install-sgp-create-chipped-cutting" not in old_ids

    payload_dst = BUILD / SOURCE_DP
    payload_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DATAPACK, payload_dst)

    p["patchId"] = "sgp-client-1.8.0-test.1"
    p["name"] = "SGP Client 1.8.0-test.1"
    p["fromVersions"] = FROM_VERSIONS
    p["toVersion"] = "1.8.0-test.1"
    p["summary"] = [
        "TEST: Create Mechanical Saw integration for Chipped 4.0.2 on Minecraft 1.21.1.",
        f"Adds {recipe_count} data-driven create:cutting recipes across {family_count} current Chipped workbench families.",
        "Each recipe converts any block in a Chipped family tag into one exact Chipped variant, so a Mechanical Saw filter can automate the desired variant.",
        "Generated from exact Chipped 4.0.2 NeoForge workbench recipes + item tags; legacy Chipped 3.1.2 recipe lists are not reused.",
        "No ticking logic/worldgen; only datapack recipe reload/startup and JEI indexing overhead.",
    ]
    p["actions"] = old_actions + [{
        "actionId": "install-sgp-create-chipped-cutting",
        "type": "copy",
        "description": "Добавить SGP Create × Chipped Cutting datapack для Mechanical Saw",
        "source": SOURCE_DP,
        "target": TARGET_DP,
        "sha256": dp_sha,
        "size": dp_size,
    }]

    ids = [a["actionId"] for a in p["actions"]]
    assert len(ids) == len(set(ids))
    assert p["fromVersions"] == FROM_VERSIONS
    assert "1.5.4" not in p["fromVersions"]
    assert p["actions"][:-1] == old_actions

    for a in p["actions"]:
        if a["type"] == "copy":
            f = BUILD / a["source"]
            assert f.is_file(), a["source"]
            assert f.stat().st_size == a["size"], a["actionId"]
            assert sha256_file(f).lower() == a["sha256"].lower(), a["actionId"]

    mp.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", "utf-8")
    (BUILD / "README.txt").write_text(
        "SGP Client 1.8.0-test.1\n"
        "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
        "TEST change:\n"
        f"- Adds SGP_Create_Chipped_Cutting_MC1.21.1.zip with {recipe_count} Create Mechanical Saw cutting recipes.\n"
        f"- Recipes cover {family_count} current Chipped 4.0.2 workbench families.\n"
        "- Generated from exact Chipped 4.0.2 NeoForge data, not mechanically ported from the old 3.1.2 pack.\n"
        "- All recipes are data-driven; no worldgen or ticking code.\n\n"
        "All 1.7.1 payload/actions are retained, so this TEST remains cumulative-to-latest.\n",
        "utf-8",
    )

    fixed = (2026, 10, 5, 12, 30, 0)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
            arc = f.relative_to(BUILD).as_posix()
            zi = zipfile.ZipInfo(arc, fixed)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    with zipfile.ZipFile(OUT) as z:
        assert z.testzip() is None
        q = json.loads(z.read("patch.json"))
        assert q["patchId"] == "sgp-client-1.8.0-test.1"
        assert q["toVersion"] == "1.8.0-test.1"
        assert q["fromVersions"] == FROM_VERSIONS
        assert q["actions"][:-1] == old_actions
        assert q["actions"][-1]["actionId"] == "install-sgp-create-chipped-cutting"
        b = z.read(SOURCE_DP)
        assert len(b) == dp_size and sha256_bytes(b) == dp_sha

    return sha256_file(OUT), OUT.stat().st_size


def main() -> None:
    verify_modrinth_metadata_and_jar()
    family_count, recipe_count, dp_sha, dp_size = build_datapack()
    final_sha, final_size = build_patch(dp_sha, dp_size, family_count, recipe_count)

    (ROOT / "test1_datapack_sha.txt").write_text(dp_sha + "\n", "utf-8")
    (ROOT / "test1_datapack_size.txt").write_text(str(dp_size) + "\n", "utf-8")
    (ROOT / "test1_family_count.txt").write_text(str(family_count) + "\n", "utf-8")
    (ROOT / "test1_recipe_count.txt").write_text(str(recipe_count) + "\n", "utf-8")
    (ROOT / "test1_chipped_sha.txt").write_text(sha256_file(CHIPPED) + "\n", "utf-8")

    print("SGP_CREATE_CHIPPED_DATAPACK_AUDIT_PASS")
    print(f"CHIPPED_SHA={sha256_file(CHIPPED)}")
    print(f"FAMILY_COUNT={family_count}")
    print(f"RECIPE_COUNT={recipe_count}")
    print(f"DATAPACK_SHA={dp_sha}")
    print(f"DATAPACK_SIZE={dp_size}")
    print("CLIENT_180_TEST1_STATIC_AUDIT_PASS")
    print(f"FINAL_SHA={final_sha}")
    print(f"FINAL_SIZE={final_size}")


if __name__ == "__main__":
    main()
