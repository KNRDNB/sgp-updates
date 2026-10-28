from __future__ import annotations
import hashlib, io, json, pathlib, subprocess, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ServerPatch_2.0.4.zip"
BASE_DIR = ROOT / ".server-204-base"
CLIENT_DIR = ROOT / ".server-204-client"
BASE_OUTER = BASE_DIR / "sgp-2.0.2-release-evidence.zip"
BASE_SERVER = BASE_DIR / "SGP_ServerPatch_2.0.2.zip"
CLIENT_ZIP = CLIENT_DIR / "SGP_ClientPatch_2.0.4.zip"

BASE_RUN = "37987188158"
BASE_ARTIFACT = "sgp-2.0.2-release-evidence"
BASE_SERVER_SHA = "fc98c058a9bc0f13859e1b81c0d08029af1f77a1bd1a22dcac98f9e1adca7786"
BASE_SERVER_SIZE = 11266

CLIENT_TAG = "client-v2.0.4"
CLIENT_SHA = "e6f7e45dffd6ae61c517c19ca6bc16f83762b2f305958be5f395ed79bece97ce"
CLIENT_SIZE = 55218

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
TARGET_MAP = {
    "files/mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar":
        "mods/ftb_chunks_mobs_spawn_control-1.0.4-neoforge-1.21.1.jar",
    "files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar":
        "mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar",
    "files/config/ftbchunks-world.snbt":
        "config/ftbchunks-world.snbt",
    "files/config/ftb_chunks_mobs_spawn_control-common.toml":
        "config/ftb_chunks_mobs_spawn_control-common.toml",
}

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

BASE_DIR.mkdir(exist_ok=True)
CLIENT_DIR.mkdir(exist_ok=True)

subprocess.run([
    "gh", "run", "download", BASE_RUN,
    "--repo", "KNRDNB/sgp-updates",
    "--name", BASE_ARTIFACT,
    "--dir", str(BASE_DIR),
], check=True)

# gh run download extracts artifact contents directly.
if not BASE_SERVER.is_file():
    candidates = list(BASE_DIR.rglob("SGP_ServerPatch_2.0.2.zip"))
    assert len(candidates) == 1, candidates
    BASE_SERVER = candidates[0]

assert BASE_SERVER.stat().st_size == BASE_SERVER_SIZE
assert sha_file(BASE_SERVER) == BASE_SERVER_SHA

with zipfile.ZipFile(BASE_SERVER) as bz:
    assert bz.testzip() is None
    base_names = set(bz.namelist())
    assert ".sgp/pack.json" in base_names and ".sgp/history.json" in base_names
    base_pack = json.loads(bz.read(".sgp/pack.json"))
    base_history = json.loads(bz.read(".sgp/history.json"))
    assert base_pack["version"] == "2.0.2"
    assert base_history["currentVersion"] == "2.0.2"
    assert [e["version"] for e in base_history["entries"]] == ["1.0.0", "1.2.0", "1.2.1", "2.0.0", "2.0.1", "2.0.2"]
    # Canonical installed-base audit: these 2.0.4 components are not part of the handed-off 2.0.2 overlay.
    for target in TARGET_MAP.values():
        assert target not in base_names

subprocess.run([
    "gh", "release", "download", CLIENT_TAG,
    "--repo", "KNRDNB/sgp-updates",
    "--pattern", CLIENT_ZIP.name,
    "--dir", str(CLIENT_DIR),
], check=True)

assert CLIENT_ZIP.stat().st_size == CLIENT_SIZE
assert sha_file(CLIENT_ZIP) == CLIENT_SHA

with zipfile.ZipFile(CLIENT_ZIP) as cz:
    assert cz.testzip() is None
    cp = json.loads(cz.read("patch.json"))
    assert cp["toVersion"] == "2.0.4"
    assert cp["fromVersions"] == ["2.0.3", "2.0.4-test.1", "2.0.4-test.2"]
    payloads = {name: cz.read(name) for name in PAYLOAD_EXPECTED}

for name, data in payloads.items():
    digest, size = PAYLOAD_EXPECTED[name]
    assert len(data) == size
    assert sha_bytes(data) == digest

pack = dict(base_pack)
pack["version"] = "2.0.4"
pack["baseline"] = False
pack["lastUpdate"] = {
    "id": "sgp-server-2.0.4",
    "type": "release",
    "version": "2.0.4",
    "releaseDate": "2026-10-28",
}

history = dict(base_history)
history["currentVersion"] = "2.0.4"
history["entries"] = list(base_history["entries"]) + [{
    "id": "sgp-server-2.0.4",
    "type": "release",
    "version": "2.0.4",
    "releaseDate": "2026-10-28",
    "installer": "manual",
}]

pack_bytes = (json.dumps(pack, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
history_bytes = (json.dumps(history, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

files = {
    ".sgp/pack.json": pack_bytes,
    ".sgp/history.json": history_bytes,
}
for source, target in TARGET_MAP.items():
    files[target] = payloads[source]

fixed = (2026, 10, 28, 11, 15, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in files.items():
        zi = zipfile.ZipInfo(name, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist()) == set(files)
    assert not any(n.startswith("world/serverconfig/") for n in z.namelist())
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    assert not any(n.startswith("world/") for n in z.namelist())
    rp = json.loads(z.read(".sgp/pack.json"))
    rh = json.loads(z.read(".sgp/history.json"))
    assert rp["version"] == "2.0.4"
    assert rh["currentVersion"] == "2.0.4"
    assert [e["version"] for e in rh["entries"]] == ["1.0.0", "1.2.0", "1.2.1", "2.0.0", "2.0.1", "2.0.2", "2.0.4"]
    for source, target in TARGET_MAP.items():
        assert z.read(target) == payloads[source]

pathlib.Path("server204_sha.txt").write_text(sha_file(OUT) + "\n")
pathlib.Path("server204_size.txt").write_text(str(OUT.stat().st_size) + "\n")
pathlib.Path("server204_pack_sha.txt").write_text(sha_bytes(pack_bytes) + "\n")
pathlib.Path("server204_pack_size.txt").write_text(str(len(pack_bytes)) + "\n")
pathlib.Path("server204_history_sha.txt").write_text(sha_bytes(history_bytes) + "\n")
pathlib.Path("server204_history_size.txt").write_text(str(len(history_bytes)) + "\n")

print("SERVER_204_EXISTING_COMPONENT_CANONICAL_BASE_AUDIT_PASS")
print("SERVER_204_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA=" + sha_file(OUT))
print("SERVER_SIZE=" + str(OUT.stat().st_size))
print("PACK_SHA=" + sha_bytes(pack_bytes))
print("PACK_SIZE=" + str(len(pack_bytes)))
print("HISTORY_SHA=" + sha_bytes(history_bytes))
print("HISTORY_SIZE=" + str(len(history_bytes)))
print("DELETION_LIST=NONE")
