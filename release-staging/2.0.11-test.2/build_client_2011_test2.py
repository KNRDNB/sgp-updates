from __future__ import annotations
import hashlib, json, pathlib, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ClientPatch_2.0.11-test.2.zip"
META = ROOT / "SGP_ClientPatch_2.0.11-test.2.meta.json"
ADDON = ROOT / "SGP-Wands-Paxel-Compat-1.0.2.jar"

OLD0 = "mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
OLD1 = "mods/SGP-Wands-Paxel-Compat-1.0.1.jar"
NEW = "mods/SGP-Wands-Paxel-Compat-1.0.2.jar"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())

if not ADDON.is_file():
    raise FileNotFoundError(ADDON)

addon_bytes = ADDON.read_bytes()
with zipfile.ZipFile(ADDON) as z:
    assert z.testzip() is None
    names = set(z.namelist())
    toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    mixins = json.loads(z.read("sgp_wands_paxel_compat.mixins.json"))
assert 'modId="sgp_wands_paxel_compat"' in toml
assert 'version="1.0.2"' in toml
assert 'modId="wands"' in toml
assert 'modId="create_ironworks"' in toml
assert mixins["package"] == "sgp.wandspaxel.mixin"
assert mixins["mixins"] == ["SgpWandsPaxelCompatMixin"]
assert "sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class" in names
assert not any(n.startswith("net/nicguzzo/wands/") for n in names)

payload_name = "files/mods/" + ADDON.name

patch = {
    "schemaVersion": 1,
    "patchId": "sgp-client-2.0.11-test.2",
    "name": "SGP Client 2.0.11-test.2",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.10", "2.0.11-test.1"],
    "toVersion": "2.0.11-test.2",
    "restartRequired": True,
    "summary": [
        "Исправлен startup FAIL 2.0.11-test.1: SGP Wands Paxel Compat 1.0.2 больше не создаёт split-package с Building Wands.",
        "Сохраняется полный multi-tool scope для всех 8 Create: Ironworks paxel: Replace/Destroy + axe/shovel Use без hoe/shears расширения.",
        "Sodium Block Transparency Limits остаётся UNLIMITED для TEST BetterNether Quartz Glass без изменения текстур/RGB/alpha."
    ],
    "actions": [
        {
            "actionId": "remove-sgp-wands-paxel-compat-1-0-0",
            "type": "delete",
            "description": "Удалить SGP Wands Paxel Compat 1.0.0",
            "target": OLD0,
            "optional": True
        },
        {
            "actionId": "remove-failed-sgp-wands-paxel-compat-1-0-1",
            "type": "delete",
            "description": "Удалить failed SGP Wands Paxel Compat 1.0.1",
            "target": OLD1,
            "optional": True
        },
        {
            "actionId": "install-sgp-wands-paxel-compat-1-0-2",
            "type": "copy",
            "description": "Установить SGP Wands Paxel Compat 1.0.2",
            "source": payload_name,
            "target": NEW,
            "sha256": sha_bytes(addon_bytes),
            "size": len(addon_bytes)
        },
        {
            "actionId": "sodium-unlimited-block-transparency-test",
            "type": "jsonEdit",
            "description": "Sodium: оставить UNLIMITED-разбиение прозрачной геометрии для проверки Quartz Glass + water",
            "target": "config/sodium-options.json",
            "precondition": {"state": "exists"},
            "edits": [
                {
                    "op": "set",
                    "path": "/performance/quad_splitting_mode",
                    "value": "UNLIMITED",
                    "createIfMissing": False
                }
            ]
        }
    ]
}

patch_bytes = (json.dumps(patch, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
readme = """SGP Client 2.0.11-test.2
Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21

Corrective TEST after owner startup FAIL of 2.0.11-test.1.

Root cause fixed:
- 1.0.1 placed its mixin class in net.nicguzzo.wands.wand, creating a Java module split-package with Building Wands.
- 1.0.2 uses only sgp.wandspaxel.* packages.
- The mixin accesses selected tool slots through public player/player_data state and @Shadow fields; no class from net.nicguzzo.wands.* is bundled.

Functional scope remains:
- all 8 Create: Ironworks paxels;
- glass/special Destroy/Replace;
- axe/shovel Use actions;
- no hoe/shears expansion;
- real paxel tier/drop/Silk Touch semantics;
- stop at <=5 remaining durability.

Quartz Glass TEST remains:
- Sodium quad_splitting_mode = UNLIMITED;
- no BetterNether texture/RGB/alpha payload.

Runtime acceptance:
1) startup to main menu + open singleplayer world;
2) paxel Replace: vanilla glass, stone/ore, wood, shovel-domain block;
3) paxel Use: path, log strip, copper scrape/wax-off;
4) negative: hoe/tilling and shear-only actions unavailable;
5) durability <=5 blocked;
6) BetterNether Quartz Glass: clear + black + framed/pane with water, shaders OFF and Complementary ON;
7) FPS/chunk rebuild stability.

No dedicated-server TEST is built or handed off. After owner PASS + explicit release instruction, the normal matching server patch is built separately.
""".encode("utf-8")

fixed = (2026, 11, 8, 18, 30, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in [("patch.json", patch_bytes), ("README.txt", readme), (payload_name, addon_bytes)]:
        info = zipfile.ZipInfo(name, fixed)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted(["patch.json", "README.txt", payload_name])
    p = json.loads(z.read("patch.json"))
    assert p == patch
    assert p["fromVersions"] == ["2.0.10", "2.0.11-test.1"]
    assert p["toVersion"] == "2.0.11-test.2"
    assert [a["type"] for a in p["actions"]] == ["delete", "delete", "copy", "jsonEdit"]
    assert p["actions"][0]["target"] == OLD0
    assert p["actions"][1]["target"] == OLD1
    assert p["actions"][2]["target"] == NEW
    assert p["actions"][3]["target"] == "config/sodium-options.json"
    assert p["actions"][3]["edits"] == [{
        "op": "set",
        "path": "/performance/quad_splitting_mode",
        "value": "UNLIMITED",
        "createIfMissing": False,
    }]
    assert not any("betternether" in n.lower() for n in z.namelist())

meta = {
    "schemaVersion": 1,
    "channel": "test",
    "tag": "client-v2.0.11-test.2",
    "patchId": patch["patchId"],
    "targetPackId": patch["targetPackId"],
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "patchSchemaVersion": 1,
    "fromVersions": patch["fromVersions"],
    "toVersion": patch["toVersion"],
    "assetName": OUT.name,
    "assetSize": OUT.stat().st_size,
    "sha256": sha_file(OUT),
    "minInstallerVersion": "2.0.0"
}
META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")

audit = {
    "target": patch["toVersion"],
    "sources": patch["fromVersions"],
    "addon_sha256": sha_file(ADDON),
    "addon_size": ADDON.stat().st_size,
    "zip_sha256": sha_file(OUT),
    "zip_size": OUT.stat().st_size,
    "meta_sha256": sha_file(META),
    "meta_size": META.stat().st_size,
    "actions": patch["actions"],
    "split_package_guard": "PASS_EXPECTED_FROM_BUILD",
    "betternether_texture_payloads": 0,
    "sodium_quad_splitting_target": "UNLIMITED",
    "server_test_artifacts": 0,
    "runtime": "PENDING_OWNER"
}
pathlib.Path("client2011_test2_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps(audit, ensure_ascii=False, indent=2))
print("CLIENT_2011_TEST2_STATIC_PACKAGE_PASS")
