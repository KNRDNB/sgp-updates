from __future__ import annotations
import hashlib, json, pathlib, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ClientPatch_2.0.11-test.1.zip"
META = ROOT / "SGP_ClientPatch_2.0.11-test.1.meta.json"
ADDON = ROOT / "SGP-Wands-Paxel-Compat-1.0.1.jar"

OLD = "mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
NEW = "mods/SGP-Wands-Paxel-Compat-1.0.1.jar"

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
assert 'version="1.0.1"' in toml
assert 'modId="wands"' in toml
assert 'modId="create_ironworks"' in toml
assert mixins["mixins"] == ["SgpWandsPaxelCompatMixin"]
assert "net/nicguzzo/wands/wand/SgpWandsPaxelCompatMixin.class" in names
assert "sgp/wandspaxel/PaxelIds.class" in names
assert "net/nicguzzo/wands/wand/Wand.class" not in names

payload_name = "files/mods/" + ADDON.name

patch = {
    "schemaVersion": 1,
    "patchId": "sgp-client-2.0.11-test.1",
    "name": "SGP Client 2.0.11-test.1",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.10"],
    "toVersion": "2.0.11-test.1",
    "restartRequired": True,
    "summary": [
        "Building Wands: SGP Paxel Compat 1.0.1 исправляет Replace стекла и добавляет полноценные axe/shovel Use-действия для всех 8 Create: Ironworks paxel.",
        "Paxel compat сохраняет tier/drop/durability семантику самого инструмента и не превращает paxel в hoe/shears.",
        "Sodium: Block Transparency Limits переводится SAFE -> UNLIMITED для TEST корректной сортировки всей семьи BetterNether Quartz Glass без изменения текстур, RGB или alpha."
    ],
    "actions": [
        {
            "actionId": "remove-sgp-wands-paxel-compat-1-0-0",
            "type": "delete",
            "description": "Удалить SGP Wands Paxel Compat 1.0.0",
            "target": OLD,
            "optional": True
        },
        {
            "actionId": "install-sgp-wands-paxel-compat-1-0-1",
            "type": "copy",
            "description": "Установить SGP Wands Paxel Compat 1.0.1",
            "source": payload_name,
            "target": NEW,
            "sha256": sha_bytes(addon_bytes),
            "size": len(addon_bytes)
        },
        {
            "actionId": "sodium-unlimited-block-transparency-test",
            "type": "jsonEdit",
            "description": "Sodium: снять SAFE-лимит разбиения прозрачной геометрии для проверки Quartz Glass + water",
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
readme = """SGP Client 2.0.11-test.1
Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21

TEST-кандидат от stable 2.0.10.

Изменения:
- SGP-Wands-Paxel-Compat 1.0.0 -> 1.0.1.
- Все 8 Create: Ironworks paxel распознаются одним точным registry-набором.
- Destroy/Replace не подменяет успешную логику Building Wands; compat дополняет только отсутствующие paxel-case.
- Исправлен Replace vanilla glass.
- Use-mode поддерживает axe/shovel-действия реального paxel: stripping, path, copper scrape/wax-off, если сам Ironworks их поддерживает.
- Paxel не получает hoe/shears capability.
- Сохраняется stop-at-5 durability и реальный Tool/drop/Silk Touch путь.
- Sodium quad_splitting_mode: SAFE -> UNLIMITED через точечный jsonEdit.
- BetterNether texture/RGB/alpha не изменяются и не входят в patch.

Runtime acceptance:
1) paxel: glass + stone/ore + wood + dirt/path + log strip + copper scrape/wax-off;
2) negative: farmland/tilling и shear-only действия paxel делать не должен;
3) durability <=5 должна блокировать действие;
4) Quartz Glass: clear + black + framed/pane variant with water behind, shaders OFF and Complementary ON;
5) отдельно оценить FPS/chunk rebuild stability из-за Sodium UNLIMITED.

Для multiplayer paxel-fix должен быть установлен и на dedicated server; formal server release во время TEST не публикуется.
""".encode("utf-8")

payloads = {payload_name: addon_bytes}
fixed = (2026, 11, 8, 12, 0, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in [("patch.json", patch_bytes), ("README.txt", readme), *payloads.items()]:
        info = zipfile.ZipInfo(name, fixed)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted(["patch.json", "README.txt", payload_name])
    p = json.loads(z.read("patch.json"))
    assert p == patch
    assert p["fromVersions"] == ["2.0.10"]
    assert p["toVersion"] == "2.0.11-test.1"
    assert [a["type"] for a in p["actions"]] == ["delete", "copy", "jsonEdit"]
    assert p["actions"][0]["target"] == OLD
    assert p["actions"][1]["target"] == NEW
    assert p["actions"][2]["target"] == "config/sodium-options.json"
    assert p["actions"][2]["edits"] == [{
        "op": "set",
        "path": "/performance/quad_splitting_mode",
        "value": "UNLIMITED",
        "createIfMissing": False,
    }]
    assert not any("betternether" in n.lower() for n in z.namelist())
    assert not any(n.startswith("files/config/") for n in z.namelist())

meta = {
    "schemaVersion": 1,
    "channel": "test",
    "tag": "client-v2.0.11-test.1",
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
    "addon_sha256": sha_file(ADDON),
    "addon_size": ADDON.stat().st_size,
    "zip_sha256": sha_file(OUT),
    "zip_size": OUT.stat().st_size,
    "meta_sha256": sha_file(META),
    "meta_size": META.stat().st_size,
    "actions": patch["actions"],
    "betternether_texture_payloads": 0,
    "sodium_quad_splitting_target": "UNLIMITED",
    "runtime": "PENDING_OWNER"
}
pathlib.Path("client2011_test1_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", "utf-8")
print(json.dumps(audit, ensure_ascii=False, indent=2))
print("CLIENT_2011_TEST1_STATIC_PACKAGE_PASS")
