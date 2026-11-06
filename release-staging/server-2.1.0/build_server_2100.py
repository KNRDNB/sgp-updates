from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import time
import urllib.request
import zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ServerPatch_2.1.0.zip"
BASE = ROOT / ".sgp-server-210-base" / "SGP_ServerPatch_2.0.10.zip"

BASE_SHA = "6c2835347f8b724fbd50aa38c293a2c32797a7ce75d3d996d9f562a825cb4da7"
BASE_SIZE = 7_957_178
PACK_BASE_SHA = "bb72e1138d2054954017048ef7a1dfd9a400d02ff8937da990966d3999bec712"
HISTORY_BASE_SHA = "d6d495cf8bd31e839fd77228b7af8661bbccd193553db43a1f174a965c1a41be"

JM_VERSION_ID = "F1lEUGxf"  # Official Modrinth JourneyMap 1.21.1-6.0.8+neoforge
JM_PROJECT_ID = "lfHFW1mp"
JM_FILE = "journeymap-neoforge-1.21.1-6.0.8.jar"
JM_SIZE = 4_303_084  # Owner's client mods/ file scan 2026-11-02.
JM_TARGET = "mods/" + JM_FILE
RELEASE_DATE = "2026-11-07"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def get(url: str) -> bytes:
    assert url.startswith("https://")
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SGP-ServerPatch-Audit/2.1.0", "Accept": "application/json, application/octet-stream"})
            with urllib.request.urlopen(req, timeout=90) as response:
                return response.read()
        except Exception:
            if attempt == 2:
                raise
            time.sleep((attempt + 1) * 3)
    raise AssertionError("download unavailable")

BASE.parent.mkdir(parents=True, exist_ok=True)
subprocess.run([
    "gh", "release", "download", "server-v2.0.10", "--repo", "KNRDNB/sgp-updates",
    "--pattern", BASE.name, "--dir", str(BASE.parent)
], check=True)
assert BASE.is_file() and BASE.stat().st_size == BASE_SIZE
assert sha256(BASE.read_bytes()) == BASE_SHA
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    pack_raw, history_raw = z.read(".sgp/pack.json"), z.read(".sgp/history.json")
    assert len(pack_raw) == 532 and sha256(pack_raw) == PACK_BASE_SHA
    assert len(history_raw) == 2217 and sha256(history_raw) == HISTORY_BASE_SHA
    pack = json.loads(pack_raw)
    history = json.loads(history_raw)
    assert pack["version"] == history["currentVersion"] == "2.0.10"
    assert pack["packId"] == history["packId"] == "sgp-neoforge-1.21.1-server"
    assert history["entries"][-1]["version"] == "2.0.10"

metadata = json.loads(get("https://api.modrinth.com/v2/version/" + JM_VERSION_ID))
assert metadata["project_id"] == JM_PROJECT_ID
assert metadata["version_number"] == "1.21.1-6.0.8+neoforge"
assert "neoforge" in metadata["loaders"] and "1.21.1" in metadata["game_versions"]
matching = [f for f in metadata["files"] if f["filename"] == JM_FILE]
assert len(matching) == 1, "Unexpected official JourneyMap artifact filename"
official_file = matching[0]
assert official_file["size"] == JM_SIZE, "Official artifact differs from owner's exact client filename/size"
url = official_file["url"]
assert url.startswith("https://cdn.modrinth.com/")
jm_bytes = get(url)
assert len(jm_bytes) == JM_SIZE
assert hashlib.sha512(jm_bytes).hexdigest() == official_file["hashes"]["sha512"]
audit_jar = ROOT / ".sgp-server-210-journeymap-audit.jar"
audit_jar.write_bytes(jm_bytes)
with zipfile.ZipFile(audit_jar) as z:
    assert z.testzip() is None
    assert any(n.endswith("neoforge.mods.toml") for n in z.namelist())
audit_jar.unlink()

pack = dict(pack)
pack["version"] = "2.1.0"
pack["baseline"] = False
pack["lastUpdate"] = {
    "id": "sgp-server-2.1.0",
    "type": "release",
    "version": "2.1.0",
    "releaseDate": RELEASE_DATE,
}
history = dict(history)
history["currentVersion"] = "2.1.0"
history["entries"] = list(history["entries"]) + [{
    "id": "sgp-server-2.1.0",
    "type": "release",
    "version": "2.1.0",
    "releaseDate": RELEASE_DATE,
    "installer": "manual",
}]

pack_bytes = (json.dumps(pack, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
history_bytes = (json.dumps(history, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
content = {
    ".sgp/pack.json": pack_bytes,
    ".sgp/history.json": history_bytes,
    JM_TARGET: jm_bytes,
}
fixed = (2026, 11, 7, 12, 0, 0)
with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in content.items():
        info = zipfile.ZipInfo(name, fixed)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None and set(z.namelist()) == set(content)
    assert all(z.read(name) == data for name, data in content.items())
    assert not any(name.startswith(("world/", "config/", "serverconfig/", "journeymap/")) for name in z.namelist())
    target_pack = json.loads(z.read(".sgp/pack.json"))
    target_history = json.loads(z.read(".sgp/history.json"))
    assert target_pack["version"] == target_history["currentVersion"] == "2.1.0"
    assert [e["version"] for e in target_history["entries"]][-2:] == ["2.0.10", "2.1.0"]
    assert len(target_history["entries"]) == len(json.loads(history_raw)["entries"]) + 1

checks = {
    "source_release": "server-v2.0.10",
    "source_sha256": BASE_SHA,
    "target_version": "2.1.0",
    "journeymap_version_id": JM_VERSION_ID,
    "journeymap_sha256": sha256(jm_bytes),
    "journeymap_sha512": hashlib.sha512(jm_bytes).hexdigest(),
    "journeymap_size": len(jm_bytes),
    "pack_sha256": sha256(pack_bytes),
    "pack_size": len(pack_bytes),
    "history_sha256": sha256(history_bytes),
    "history_size": len(history_bytes),
    "zip_sha256": sha256(OUT.read_bytes()),
    "zip_size": OUT.stat().st_size,
    "zip_paths": sorted(content),
    "deletions": [],
    "runtime": "NOT_TESTED_BY_OWNER",
}
(ROOT / "server2100_audit.json").write_text(json.dumps(checks, indent=2) + "\n")
print(json.dumps(checks, indent=2))
print("SERVER_2100_OFFICIAL_MODRINTH_SHA512_PASS")
print("SERVER_2100_EXACT_BASE_210_PASS")
print("SERVER_2100_ROOT_OVERLAY_AUDIT_PASS")
