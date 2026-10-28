from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ClientPatch_2.0.4.zip"
META = ROOT / "SGP_ClientPatch_2.0.4.meta.json"
SRC_DIR = ROOT / ".stable-204-source"
TEST_ZIP = SRC_DIR / "SGP_ClientPatch_2.0.4-test.2.zip"

TEST_TAG = "client-v2.0.4-test.2"
TEST_SHA = "0a75730768746efa34b7b63294122b8975a603a96bbbc024fe26cfaef0afcb95"
TEST_SIZE = 55372

PAYLOAD_EXPECTED = {
    "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar":
        ("c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960", 50538),
    "files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar":
        ("abf4a0418a8d991d460d389264792d1c92c65baf01c009da4a46ef5f95fc5674", 5622),
    "files/config/ftbchunks-world.snbt":
        ("7464ff26796dd1144135513789b32e2bf778baeea39f7019d77fda3a05cd7d75", 9106),
    "files/config/ftb_chunks_mobs_spawn_control-common.toml":
        ("4d82c90d99c8c14883c441c28ea36483a48d53fe1e42ab999bf02cb6052b10c3", 598),
}

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

SRC_DIR.mkdir(exist_ok=True)
subprocess.run([
    "gh", "release", "download", TEST_TAG,
    "--repo", "KNRDNB/sgp-updates",
    "--pattern", TEST_ZIP.name,
    "--dir", str(SRC_DIR),
], check=True)

assert TEST_ZIP.stat().st_size == TEST_SIZE
assert sha_file(TEST_ZIP) == TEST_SHA

with zipfile.ZipFile(TEST_ZIP) as tz:
    assert tz.testzip() is None
    test_patch = json.loads(tz.read("patch.json"))
    assert test_patch["patchId"] == "sgp-client-2.0.4-test.2"
    assert test_patch["fromVersions"] == ["2.0.3", "2.0.4-test.1"]
    assert test_patch["toVersion"] == "2.0.4-test.2"
    assert [a["type"] for a in test_patch["actions"]] == ["copy", "copy", "copy", "copy"]
    assert not any("protected_chunks.properties" in n for n in tz.namelist())
    payloads = {name: tz.read(name) for name in PAYLOAD_EXPECTED}

for name, data in payloads.items():
    expected_sha, expected_size = PAYLOAD_EXPECTED[name]
    assert len(data) == expected_size, name
    assert sha_bytes(data) == expected_sha, name

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
    "patchId": "sgp-client-2.0.4",
    "name": "SGP Client 2.0.4",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.3", "2.0.4-test.1", "2.0.4-test.2"],
    "toVersion": "2.0.4",
    "restartRequired": True,
    "summary": [
        "FTB Chunks: новые claims автоматически получают Mob Control.",
        "Mob Control блокирует только естественный спаун враждебных мобов; ручное переключение средней кнопкой сохраняется.",
        "Claims: 1000 на игрока / SUM / hard cap 5000; force-load обычным игрокам остаётся отключён."
    ],
    "actions": [
        copy_action(
            "install-ftb-chunks-mobs-spawn-control-1-0-4",
            "Установить FTB Chunks Mobs Spawn Control 1.0.4",
            "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
            "mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
        ),
        copy_action(
            "install-sgp-ftb-spawn-guard-auto-protect-1-0-0",
            "Установить SGP Auto Protect: автоматически включать Mob Control при создании claim",
            "files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar",
            "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar",
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
    "SGP Client 2.0.4\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Стабильное обновление механики Mob Control для FTB Chunks.\n\n"
    "Изменения:\n"
    "- новый FTB Chunks claim автоматически включает Mob Control для этого чанка;\n"
    "- ручное переключение Mob Control средней кнопкой мыши сохраняется;\n"
    "- после ручного отключения Mob Control не включается обратно автоматически до нового claim/re-claim;\n"
    "- natural hostile spawn блокируется, остальные согласованные способы спавна остаются разрешены настройками;\n"
    "- claims: 1000 на игрока, SUM для команды, hard cap 5000;\n"
    "- force-load обычным игрокам остаётся 0;\n"
    "- protected_chunks.properties не распространяется.\n\n"
    "Сторонний FTB Chunks Mobs Spawn Control 1.0.4 используется без модификации JAR.\n"
    "SGP Auto Protect 1.0.0 включает защиту только по событию успешного нового claim.\n"
).encode("utf-8")

fixed = (2026, 10, 28, 11, 0, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in [("patch.json", patch_bytes), ("README.txt", readme), *payloads.items()]:
        zi = zipfile.ZipInfo(name, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == sorted(["patch.json", "README.txt", *payloads.keys()])
    p = json.loads(z.read("patch.json"))
    assert p == PATCH
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    for action in p["actions"]:
        data = z.read(action["source"])
        assert len(data) == action["size"]
        assert sha_bytes(data) == action["sha256"]

meta = {
    "schemaVersion": 1,
    "channel": "stable",
    "tag": "client-v2.0.4",
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

pathlib.Path("client204_sha.txt").write_text(sha_file(OUT) + "\n")
pathlib.Path("client204_size.txt").write_text(str(OUT.stat().st_size) + "\n")
pathlib.Path("client204_meta_sha.txt").write_text(sha_file(META) + "\n")
pathlib.Path("client204_meta_size.txt").write_text(str(META.stat().st_size) + "\n")

print("CLIENT_204_STABLE_STATIC_AUDIT_PASS")
print("SOURCE_TEST_SHA=" + TEST_SHA)
print("CLIENT_SHA=" + sha_file(OUT))
print("CLIENT_SIZE=" + str(OUT.stat().st_size))
print("META_SHA=" + sha_file(META))
print("META_SIZE=" + str(META.stat().st_size))
