from __future__ import annotations
import hashlib, json, pathlib, shutil, urllib.request, zipfile

ROOT = pathlib.Path.cwd()
STAGE = ROOT / "release-staging/2.0.4-test.1"
OUT = ROOT / "SGP_ClientPatch_2.0.4-test.1.zip"
META = ROOT / "SGP_ClientPatch_2.0.4-test.1.meta.json"
WORK = ROOT / ".work-client-204-test1"

MOD_NAME = "ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar"
MOD_SHA = "c7df7bdd469237418ce4ef892497793addba84f9c92125b0fde05f8b6e353960"
MOD_SIZE = 50538
MOD_URLS = [
    "https://mediafilez.forgecdn.net/files/8986/734/" + MOD_NAME,
    "https://edge.forgecdn.net/files/8986/734/" + MOD_NAME,
]
FTB_SHA = "7464ff26796dd1144135513789b32e2bf778baeea39f7019d77fda3a05cd7d75"
FTB_SIZE = 9106
SPAWN_CFG_SHA = "4d82c90d99c8c14883c441c28ea36483a48d53fe1e42ab999bf02cb6052b10c3"
SPAWN_CFG_SIZE = 598

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())

if WORK.exists():
    shutil.rmtree(WORK)
WORK.mkdir()
mod = WORK / MOD_NAME
last = None
for url in MOD_URLS:
    try:
        urllib.request.urlretrieve(url, mod)
        if mod.stat().st_size == MOD_SIZE and sha_file(mod) == MOD_SHA:
            break
    except Exception as e:
        last = e
else:
    raise RuntimeError(f"Could not fetch exact Spawn Guard JAR: {last}")

assert mod.stat().st_size == MOD_SIZE and sha_file(mod) == MOD_SHA
with zipfile.ZipFile(mod) as z:
    assert z.testzip() is None
    toml = z.read("META-INF/neoforge.mods.toml").decode("utf-8")
for needle in [
    'modId = "ftb_chunks_mobs_spawn_control"',
    'version = "1.0.4"',
    'modId = "ftbchunks"',
    'versionRange = "[2101.1.22,)"',
    'modId = "architectury"',
    'versionRange = "[13.0.8,)"',
    'modId = "ftblibrary"',
    'versionRange = "[2101.1.34,)"',
    'modId = "ftbteams"',
    'versionRange = "[2101.1.9,)"',
]:
    assert needle in toml, needle

ftb = (STAGE / "ftbchunks-world-target.snbt").read_bytes()
spawn_cfg = (STAGE / "ftb_chunks_mobs_spawn_control-common.toml").read_bytes()
assert len(ftb) == FTB_SIZE and sha_bytes(ftb) == FTB_SHA
assert len(spawn_cfg) == SPAWN_CFG_SIZE and sha_bytes(spawn_cfg) == SPAWN_CFG_SHA

ftb_text = ftb.decode("utf-8")
for needle in [
    "disable_protection: true",
    "hard_team_claim_limit: 5000",
    "max_claimed_chunks: 1000",
    'party_limit_mode: "sum"',
    'force_load_mode: "always"',
    "hard_team_force_limit: 25",
    "max_force_loaded_chunks: 0",
]:
    assert needle in ftb_text, needle

cfg_text = spawn_cfg.decode("utf-8")
for needle in [
    'filterMode = "HOSTILE_ONLY"',
    'dimensionFilterMode = "ALL"',
    "blockNatural = true",
    "blockSpawner = false",
    "blockPatrol = false",
    "blockRaid = false",
    "blockStructure = false",
    "allowSpawnEgg = true",
    "allowCommand = true",
    "allowBreeding = true",
    "allowBucket = true",
    "allowDispenser = true",
    "allowNamedMobs = false",
    "allowPersistentMobs = false",
    "strictJoinFallback = false",
]:
    assert needle in cfg_text, needle

payloads = {
    "files/mods/" + MOD_NAME: mod.read_bytes(),
    "files/config/ftbchunks-world.snbt": ftb,
    "files/config/ftb_chunks_mobs_spawn_control-common.toml": spawn_cfg,
}

actions = []
for action_id, description, source, target in [
    (
        "install-ftb-chunks-mobs-spawn-control-1-0-4",
        "Установить FTB Chunks Mobs Spawn Control 1.0.4",
        "files/mods/" + MOD_NAME,
        "mods/" + MOD_NAME,
    ),
    (
        "configure-ftb-chunks-claims-for-spawn-guard",
        "Разрешить claims для разметки Mob Control без force-load",
        "files/config/ftbchunks-world.snbt",
        "config/ftbchunks-world.snbt",
    ),
    (
        "configure-ftb-spawn-guard-natural-hostiles-only",
        "Настроить Mob Control: блокировать только natural hostile spawn",
        "files/config/ftb_chunks_mobs_spawn_control-common.toml",
        "config/ftb_chunks_mobs_spawn_control-common.toml",
    ),
]:
    data = payloads[source]
    actions.append({
        "actionId": action_id,
        "type": "copy",
        "description": description,
        "source": source,
        "target": target,
        "sha256": sha_bytes(data),
        "size": len(data),
    })

PATCH = {
    "schemaVersion": 1,
    "patchId": "sgp-client-2.0.4-test.1",
    "name": "SGP Client 2.0.4-test.1",
    "targetPackId": "sgp-neoforge-1.21.1-client",
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "fromVersions": ["2.0.3"],
    "toVersion": "2.0.4-test.1",
    "restartRequired": True,
    "summary": [
        "Add FTB Chunks Mobs Spawn Control 1.0.4 for per-claimed-chunk spawn control.",
        "Enable up to 1000 claims per member, sum party limits, hard cap 5000; keep player force-loading disabled.",
        "Protected chunks block only natural hostile mob spawning; spawners, raids, patrols, structure spawns, eggs, commands, breeding, buckets and dispensers remain allowed."
    ],
    "actions": actions,
}

patch_bytes = (json.dumps(PATCH, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
readme = (
    "SGP Client 2.0.4-test.1\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "TEST candidate from accepted stable 2.0.3.\n\n"
    "Scope:\n"
    "- install FTB Chunks Mobs Spawn Control 1.0.4 (BOTH-side mod);\n"
    "- FTB Chunks claims: 1000/member, SUM party mode, 5000 hard team cap;\n"
    "- player force-load remains disabled (max_force_loaded_chunks=0);\n"
    "- claim protection remains disabled;\n"
    "- Mob Control blocks NATURAL HOSTILE_ONLY; all other configured spawn reasons remain allowed;\n"
    "- strictJoinFallback=false to avoid catching mod-controlled direct entity spawns.\n\n"
    "The protected_chunks.properties state file is intentionally NOT distributed.\n"
    "No other FTB configs, mods, datapacks, resource packs or options are changed.\n"
).encode("utf-8")

fixed = (2026, 10, 28, 9, 50, 0)
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
    assert p["fromVersions"] == ["2.0.3"] and p["toVersion"] == "2.0.4-test.1"
    for a in p["actions"]:
        data = z.read(a["source"])
        assert len(data) == a["size"] and sha_bytes(data) == a["sha256"]

meta = {
    "schemaVersion": 1,
    "channel": "test",
    "tag": "client-v2.0.4-test.1",
    "patchId": PATCH["patchId"],
    "targetPackId": PATCH["targetPackId"],
    "minecraft": "1.21.1",
    "neoforge": "21.1.249",
    "patchSchemaVersion": 1,
    "fromVersions": ["2.0.3"],
    "toVersion": "2.0.4-test.1",
    "assetName": OUT.name,
    "assetSize": OUT.stat().st_size,
    "sha256": sha_file(OUT),
    "minInstallerVersion": "2.0.0",
}
META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")

pathlib.Path("client204_test1_sha.txt").write_text(sha_file(OUT) + "\n")
pathlib.Path("client204_test1_size.txt").write_text(str(OUT.stat().st_size) + "\n")
pathlib.Path("client204_test1_meta_sha.txt").write_text(sha_file(META) + "\n")
pathlib.Path("client204_test1_meta_size.txt").write_text(str(META.stat().st_size) + "\n")

print("CLIENT_204_TEST1_STATIC_AUDIT_PASS")
print("CLIENT_SHA=" + sha_file(OUT))
print("CLIENT_SIZE=" + str(OUT.stat().st_size))
print("META_SHA=" + sha_file(META))
print("META_SIZE=" + str(META.stat().st_size))
print("MOD_SHA=" + MOD_SHA)
print("FTB_CONFIG_SHA=" + FTB_SHA)
print("SPAWN_CONFIG_SHA=" + SPAWN_CFG_SHA)
