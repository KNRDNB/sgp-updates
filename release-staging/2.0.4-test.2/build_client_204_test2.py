from __future__ import annotations
import hashlib, json, pathlib, urllib.request, zipfile

ROOT = pathlib.Path.cwd()
STAGE = ROOT / "release-staging/2.0.4-test.2"
TEST1 = ROOT / "release-staging/2.0.4-test.1"
OUT = ROOT / "SGP_ClientPatch_2.0.4-test.2.zip"
META = ROOT / "SGP_ClientPatch_2.0.4-test.2.meta.json"
ADDON = ROOT / "SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"

SPAWN_NAME = "ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
SPAWN_SHA = "c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
SPAWN_SIZE = 50538
SPAWN_URLS = [
    "https://mediafilez.forgecdn.net/files/8986/734/" + SPAWN_NAME,
    "https://edge.forgecdn.net/files/8986/734/" + SPAWN_NAME,
]
FTB_SHA = "7464ff26796dd1144135513789b32e2bf778baeea39f7019d77fda3a05cd7d75"
FTB_SIZE = 9106
SPAWN_CFG_SHA = "4d82c90d99c8c14883c441c28ea36483a48d53fe1e42ab999bf02cb6052b10c3"
SPAWN_CFG_SIZE = 598

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())

if not ADDON.is_file():
    raise FileNotFoundError(ADDON)

with zipfile.ZipFile(ADDON) as z:
    assert z.testzip() is None
    addon_toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    names = set(z.namelist())
assert 'modId="sgp_ftb_spawn_guard_auto_protect"' in addon_toml
assert 'version="1.0.0"' in addon_toml
assert 'modId="ftbchunks"' in addon_toml
assert 'versionRange="[2101.1.22,2101.2)"' in addon_toml
assert 'modId="ftb_chunks_mobs_spawn_control"' in addon_toml
assert 'versionRange="[1.0.4,1.1)"' in addon_toml
assert "sgp/ftbspawnguard/AutoProtectHook.class" in names
assert "sgp/ftbspawnguard/SgpFtbSpawnGuardAutoProtect.class" in names
assert not any(n.startswith("dev/ftb/") for n in names)
assert not any(n.startswith("org/ftb_chunks_mobs_spawn_control/") for n in names)

spawn = ROOT / SPAWN_NAME
last = None
for url in SPAWN_URLS:
    try:
        urllib.request.urlretrieve(url, spawn)
        if spawn.stat().st_size == SPAWN_SIZE and sha_file(spawn) == SPAWN_SHA:
            break
    except Exception as e:
        last = e
else:
    raise RuntimeError(f"Could not fetch exact Spawn Guard JAR: {last}")

assert spawn.stat().st_size == SPAWN_SIZE and sha_file(spawn) == SPAWN_SHA

ftb = (TEST1 / "ftbchunks-world-target.snbt").read_bytes()
spawn_cfg = (TEST1 / "ftb_chunks_mobs_spawn_control-common.toml").read_bytes()
assert len(ftb) == FTB_SIZE and sha_bytes(ftb) == FTB_SHA
assert len(spawn_cfg) == SPAWN_CFG_SIZE and sha_bytes(spawn_cfg) == SPAWN_CFG_SHA

payloads = {
    "files/mods/" + SPAWN_NAME: spawn.read_bytes(),
    "files/mods/" + ADDON.name: ADDON.read_bytes(),
    "files/config/ftbchunks-world.snbt": ftb,
    "files/config/ftb_chunks_mobs_spawn_control-common.toml": spawn_cfg,
}

def copy_action(action_id: str, description: str, source: str, target: str) -> dict:
    data = payloads[source]
    return {
        "actionId": action_id,
        "type": "copy",
        "description": description,
        "source": source,
        "target": target,
        "sha256": sha_bytes(data),
        "size": len(data),
    }

PATCH = {
    "schemaVersion": 1,
    "patchId": "sgp-client-2.0.4-test.2",
    "name": "SGP Client 2.0.4-test.2",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.3", "2.0.4-test.1"],
    "toVersion": "2.0.4-test.2",
    "restartRequired": True,
    "summary": [
        "FTB Chunks: новые claims автоматически получают защиту от естественного спауна враждебных мобов.",
        "Ручное переключение Mob Control средней кнопкой мыши сохраняется и не переопределяется до нового claim.",
        "Лимиты claims остаются 1000 на игрока / SUM / 5000 на команду; force-load обычным игрокам по-прежнему недоступен."
    ],
    "actions": [
        copy_action(
            "install-ftb-chunks-mobs-spawn-control-1-0-4",
            "Установить FTB Chunks Mobs Spawn Control 1.0.4",
            "files/mods/" + SPAWN_NAME,
            "mods/" + SPAWN_NAME,
        ),
        copy_action(
            "install-sgp-ftb-spawn-guard-auto-protect-1-0-0",
            "Установить SGP Auto Protect: автоматически включать Mob Control при создании claim",
            "files/mods/" + ADDON.name,
            "mods/" + ADDON.name,
        ),
        copy_action(
            "configure-ftb-chunks-claims-for-spawn-guard",
            "Настроить FTB Chunks: 1000 claims на игрока, SUM для команды, hard cap 5000, force-load 0",
            "files/config/ftbchunks-world.snbt",
            "config/ftbchunks-world.snbt",
        ),
        copy_action(
            "configure-ftb-spawn-guard-natural-hostiles-only",
            "Блокировать в Mob Control только естественный спаун враждебных мобов",
            "files/config/ftb_chunks_mobs_spawn_control-common.toml",
            "config/ftb_chunks_mobs_spawn_control-common.toml",
        ),
    ],
}

patch_bytes = (json.dumps(PATCH, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
readme = (
    "SGP Client 2.0.4-test.2\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "TEST-кандидат от принятой stable 2.0.3; также поддерживает обновление с 2.0.4-test.1.\n\n"
    "Изменения:\n"
    "- новый FTB Chunks claim автоматически включает Mob Control для этого чанка;\n"
    "- ручное переключение Mob Control средней кнопкой мыши сохраняется;\n"
    "- автоматическое повторное включение после ручного отключения не выполняется до нового claim;\n"
    "- миграции старых claims нет: по подтверждению владельца на live-сервере их сейчас нет;\n"
    "- natural hostile spawn блокируется, остальные согласованные способы спавна остаются разрешены;\n"
    "- claims: 1000 на игрока, SUM для команды, hard cap 5000;\n"
    "- force-load обычным игрокам остаётся 0;\n"
    "- protected_chunks.properties не распространяется.\n\n"
    "Новый SGP addon не модифицирует JAR Spawn Guard и использует его штатное ProtectionStore.\n"
    "Формальный server patch во время TEST не создаётся.\n"
).encode("utf-8")

fixed = (2026, 10, 28, 10, 0, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in [("patch.json", patch_bytes), ("README.txt", readme), *payloads.items()]:
        zi = zipfile.ZipInfo(name, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    expected = ["patch.json", "README.txt", *payloads.keys()]
    assert sorted(z.namelist()) == sorted(expected)
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    p = json.loads(z.read("patch.json"))
    assert p == PATCH
    assert p["fromVersions"] == ["2.0.3", "2.0.4-test.1"]
    assert p["toVersion"] == "2.0.4-test.2"
    for a in p["actions"]:
        data = z.read(a["source"])
        assert len(data) == a["size"]
        assert sha_bytes(data) == a["sha256"]

meta = {
    "schemaVersion": 1,
    "channel": "test",
    "tag": "client-v2.0.4-test.2",
    "patchId": PATCH["patchId"],
    "targetPackId": PATCH["targetPackId"],
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "patchSchemaVersion": 1,
    "fromVersions": PATCH["fromVersions"],
    "toVersion": PATCH["toVersion"],
    "assetName": OUT.name,
    "assetSize": OUT.stat().st_size,
    "sha256": sha_file(OUT),
    "minInstallerVersion": "2.0.0",
}
META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")

pathlib.Path("client204_test2_sha.txt").write_text(sha_file(OUT) + "\n")
pathlib.Path("client204_test2_size.txt").write_text(str(OUT.stat().st_size) + "\n")
pathlib.Path("client204_test2_meta_sha.txt").write_text(sha_file(META) + "\n")
pathlib.Path("client204_test2_meta_size.txt").write_text(str(META.stat().st_size) + "\n")
pathlib.Path("auto_protect_exact_sha.txt").write_text(sha_file(ADDON) + "\n")
pathlib.Path("auto_protect_exact_size.txt").write_text(str(ADDON.stat().st_size) + "\n")

print("CLIENT_204_TEST2_STATIC_AUDIT_PASS")
print("CLIENT_SHA=" + sha_file(OUT))
print("CLIENT_SIZE=" + str(OUT.stat().st_size))
print("META_SHA=" + sha_file(META))
print("META_SIZE=" + str(META.stat().st_size))
print("AUTO_PROTECT_SHA=" + sha_file(ADDON))
print("AUTO_PROTECT_SIZE=" + str(ADDON.stat().st_size))
print("SPAWN_GUARD_SHA=" + SPAWN_SHA)
print("FTB_CONFIG_SHA=" + FTB_SHA)
print("SPAWN_CONFIG_SHA=" + SPAWN_CFG_SHA)
