from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ClientPatch_2.0.5.zip"
META = ROOT / "SGP_ClientPatch_2.0.5.meta.json"
SRC_DIR = ROOT / ".stable-205-source"
BASE_ZIP = SRC_DIR / "SGP_ClientPatch_2.0.4.zip"
ADDON = ROOT / "SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"

BASE_TAG = "client-v2.0.4"
BASE_SHA = "e6f7e45dffd6ae61c517c19ca6bc16f83762b2f305958be5f395ed79bece97ce"
BASE_SIZE = 55218
OLD_ADDON = "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"
NEW_ADDON = "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

assert ADDON.is_file(), ADDON
addon_sha = sha_file(ADDON)
addon_size = ADDON.stat().st_size
expected_addon_sha = pathlib.Path("sgp205_addon_sha.txt").read_text("utf-8").strip()
expected_addon_size = int(pathlib.Path("sgp205_addon_size.txt").read_text("utf-8").strip())
assert addon_sha == expected_addon_sha
assert addon_size == expected_addon_size

with zipfile.ZipFile(ADDON) as az:
    assert az.testzip() is None
    names=set(az.namelist())
    toml=az.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert "sgp_ftb_spawn_guard_auto_protect.mixins.json" in names
    assert "sgp/ftbspawnguard/ManualTogglePayload.class" in names
    assert "sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class" in names
    assert 'version="1.0.1"' in toml
    assert 'versionRange="[1.0.4,1.0.5)"' in toml

SRC_DIR.mkdir(exist_ok=True)
subprocess.run([
    "gh", "release", "download", BASE_TAG,
    "--repo", "KNRDNB/sgp-updates",
    "--pattern", BASE_ZIP.name,
    "--dir", str(SRC_DIR),
], check=True)
assert BASE_ZIP.stat().st_size == BASE_SIZE
assert sha_file(BASE_ZIP) == BASE_SHA

with zipfile.ZipFile(BASE_ZIP) as bz:
    assert bz.testzip() is None
    base_patch=json.loads(bz.read("patch.json"))
    assert base_patch["toVersion"] == "2.0.4"
    assert any(a.get("target") == OLD_ADDON for a in base_patch["actions"])
    assert not any("SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar" in n for n in bz.namelist())

payload_name="files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
payload=ADDON.read_bytes()

PATCH = {
    "schemaVersion": 1,
    "patchId": "sgp-client-2.0.5",
    "name": "SGP Client 2.0.5",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.4"],
    "toVersion": "2.0.5",
    "restartRequired": True,
    "summary": [
        "Исправлен auto-protect: успешный FTB claim теперь строит Mob Control context прямо из уже созданного claim.",
        "Одиночные middle-click переключения Mob Control больше не идут через vanilla command-spam path.",
        "Сторонний FTB Chunks Mobs Spawn Control 1.0.4 остаётся неизменённым."
    ],
    "actions": [
        {
            "actionId": "remove-sgp-ftb-spawn-guard-auto-protect-1-0-0",
            "type": "delete",
            "description": "Удалить SGP Auto Protect 1.0.0 перед hotfix 1.0.1",
            "target": OLD_ADDON,
            "optional": False,
        },
        {
            "actionId": "install-sgp-ftb-spawn-guard-auto-protect-1-0-1",
            "type": "copy",
            "description": "Установить SGP Auto Protect 1.0.1: dedicated auto-protect + безопасный manual toggle transport",
            "source": payload_name,
            "target": NEW_ADDON,
            "sha256": addon_sha,
            "size": addon_size,
        },
    ],
}

patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=(
    "SGP Client 2.0.5\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Production hotfix для Mob Control / FTB Chunks.\n\n"
    "Исправления:\n"
    "- auto-protect больше не делает повторный lookup claim через FTB manager внутри AFTER_CLAIM;\n"
    "- context строится из уже подтверждённого claim event (dimension, chunk, teamData/team id);\n"
    "- одиночный middle-click Mob Control использует SGP custom payload вместо vanilla command packet;\n"
    "- server-side toggle выполняется через штатный Spawn Guard executeClaim(gui_toggle), сохраняя его permission checks и semantics;\n"
    "- Spawn Guard 1.0.4 не модифицируется и не перепаковывается;\n"
    "- protected_chunks.properties не распространяется и не перезаписывается.\n\n"
    "Владелец явно разрешил production release без отдельного тестового сервера; dedicated runtime verification выполняется на рабочем сервере после установки server 2.0.5.\n"
).encode("utf-8")

fixed=(2026,10,28,16,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),(payload_name,payload)]:
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == {"patch.json","README.txt",payload_name}
    p=json.loads(z.read("patch.json"))
    assert p==PATCH
    assert [a["type"] for a in p["actions"]] == ["delete","copy"]
    assert p["actions"][0]["target"] == OLD_ADDON and p["actions"][0]["optional"] is False
    assert p["actions"][1]["target"] == NEW_ADDON
    data=z.read(payload_name)
    assert sha_bytes(data)==addon_sha and len(data)==addon_size
    assert not any("protected_chunks.properties" in n for n in z.namelist())

meta={
    "schemaVersion":1,
    "channel":"stable",
    "tag":"client-v2.0.5",
    "patchId":PATCH["patchId"],
    "targetPackId":PATCH["targetPackId"],
    "minecraft":"1.21.1",
    "neoforge":"21.1.249",
    "patchSchemaVersion":1,
    "fromVersions":PATCH["fromVersions"],
    "toVersion":PATCH["toVersion"],
    "assetName":OUT.name,
    "assetSize":OUT.stat().st_size,
    "sha256":sha_file(OUT),
    "minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")

pathlib.Path("client205_sha.txt").write_text(sha_file(OUT)+"\n")
pathlib.Path("client205_size.txt").write_text(str(OUT.stat().st_size)+"\n")
pathlib.Path("client205_meta_sha.txt").write_text(sha_file(META)+"\n")
pathlib.Path("client205_meta_size.txt").write_text(str(META.stat().st_size)+"\n")

print("CLIENT_205_STATIC_AUDIT_PASS")
print("ADDON_SHA="+addon_sha)
print("ADDON_SIZE="+str(addon_size))
print("CLIENT_SHA="+sha_file(OUT))
print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META))
print("META_SIZE="+str(META.stat().st_size))
