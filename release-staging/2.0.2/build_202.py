from __future__ import annotations
import base64, hashlib, json, shutil, tomllib, zipfile
from pathlib import Path

ROOT = Path.cwd()
STAGE = ROOT / "release-staging/2.0.2"
CLIENT_ZIP = ROOT / "SGP_ClientPatch_2.0.2.zip"
CLIENT_META = ROOT / "SGP_ClientPatch_2.0.2.meta.json"
SERVER_ZIP = ROOT / "SGP_ServerPatch_2.0.2.zip"
WORK = ROOT / ".work-202"

CREATE_BASE_SHA = "ae72f1cef1b1bc5565092c9afdd48cf6d83cda4f0197d3116a66e779e85da6bc"
CREATE_BASE_SIZE = 16286
HUD_BASE_SHA = "00e40e6c14965cdfb2074899b935d59792d69c9f69133cabce9ac30bd144bccd"
HUD_BASE_SIZE = 5993
SERVER_201_PACK_SHA = "d322fe9116f25a7463f3e48c99478d00096285ac265f801935593661f8fc19b5"
SERVER_201_HISTORY_SHA = "5368c19fa1ab8ac31b74453ac190ac2fb509e06f3a4aad5447d5626c159d3c48"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())

def flatten(obj, prefix=()):
    out = {}
    for k, v in obj.items():
        if isinstance(v, dict):
            out.update(flatten(v, prefix + (k,)))
        else:
            out[prefix + (k,)] = v
    return out

def decode_base(name: str) -> bytes:
    raw = (STAGE / name).read_text("ascii")
    return base64.b64decode("".join(raw.split()))

create_base = decode_base("create-server-2.0.1-base.b64")
hud_base = decode_base("inventoryhud-client-2.0.1-base.b64")
assert len(create_base) == CREATE_BASE_SIZE and sha_bytes(create_base) == CREATE_BASE_SHA
assert len(hud_base) == HUD_BASE_SIZE and sha_bytes(hud_base) == HUD_BASE_SHA

# Exact target bytes: only intended scalar replacements.
create_target = create_base
for old, new in [
    (b"\tmaxTotalSchematicSize = 2048\n", b"\tmaxTotalSchematicSize = 20480\n"),
    (b"\tmaxSchematicPacketSize = 1024\n", b"\tmaxSchematicPacketSize = 32767\n"),
]:
    assert create_target.count(old) == 1, (old, create_target.count(old))
    create_target = create_target.replace(old, new, 1)

hud_target = hud_base
for key in [b"helmPosX", b"chestPosX", b"mainPosX", b"arrPosX"]:
    old = b"\t" + key + b" = 136\r\n"
    new = b"\t" + key + b" = 111\r\n"
    assert hud_target.count(old) == 1, (key, hud_target.count(old))
    hud_target = hud_target.replace(old, new, 1)

# Semantic diff audit.
cb = flatten(tomllib.loads(create_base.decode("utf-8")))
ct = flatten(tomllib.loads(create_target.decode("utf-8")))
create_changed = {k: (cb.get(k), ct.get(k)) for k in set(cb) | set(ct) if cb.get(k) != ct.get(k)}
assert create_changed == {
    ("schematics", "maxTotalSchematicSize"): (2048, 20480),
    ("schematics", "maxSchematicPacketSize"): (1024, 32767),
}, create_changed

hb = flatten(tomllib.loads(hud_base.decode("utf-8")))
ht = flatten(tomllib.loads(hud_target.decode("utf-8")))
hud_changed = {k: (hb.get(k), ht.get(k)) for k in set(hb) | set(ht) if hb.get(k) != ht.get(k)}
assert hud_changed == {
    ("positions", "helmPosX"): (136, 111),
    ("positions", "chestPosX"): (136, 111),
    ("positions", "mainPosX"): (136, 111),
    ("positions", "arrPosX"): (136, 111),
}, hud_changed
for key in ["legPosX", "bootPosX", "offPosX", "invPosX"]:
    assert ht[("positions", key)] == -111

PATCH = {
  "schemaVersion": 1,
  "patchId": "sgp-client-2.0.2",
  "name": "SGP Client 2.0.2",
  "targetPackId": "sgp-neoforge-1.21.1-client",
  "minecraft": "1.21.1",
  "neoforge": "21.1.249",
  "fromVersions": ["2.0.1"],
  "toVersion": "2.0.2",
  "restartRequired": True,
  "summary": [
    "ArmorHUD: move the left-side group inward to match the accepted right-side spacing.",
    "Create: increase schematic upload file limit from 2 MiB to 20 MiB.",
    "Create: raise schematic upload chunk size from 1024 to 32767 bytes to reduce upload time."
  ],
  "actions": [
    {
      "actionId": "inventoryhud-left-side-symmetry",
      "type": "tomlEdit",
      "description": "Симметрично сместить левую группу ArmorHUD",
      "target": "config/inventoryhud-client.toml",
      "edits": [
        {"op": "set", "path": "positions.helmPosX", "value": 111, "createIfMissing": False},
        {"op": "set", "path": "positions.chestPosX", "value": 111, "createIfMissing": False},
        {"op": "set", "path": "positions.mainPosX", "value": 111, "createIfMissing": False},
        {"op": "set", "path": "positions.arrPosX", "value": 111, "createIfMissing": False}
      ]
    },
    {
      "actionId": "create-schematic-upload-limits",
      "type": "tomlEdit",
      "description": "Увеличить лимит и скорость загрузки Create schematics",
      "target": "config/create-server.toml",
      "edits": [
        {"op": "set", "path": "schematics.maxTotalSchematicSize", "value": 20480, "createIfMissing": False},
        {"op": "set", "path": "schematics.maxSchematicPacketSize", "value": 32767, "createIfMissing": False}
      ]
    }
  ]
}

patch_bytes = (json.dumps(PATCH, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
readme = (
    "SGP Client 2.0.2\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Owner-authorized direct stable config-only maintenance release.\n"
    "Exact sequential edge: 2.0.1 -> 2.0.2.\n\n"
    "Changes:\n"
    "- ArmorHUD left-side X values: helm/chest/main/arrows 136 -> 111; right-side -111 values unchanged.\n"
    "- Create schematics.maxTotalSchematicSize: 2048 -> 20480 KiB.\n"
    "- Create schematics.maxSchematicPacketSize: 1024 -> 32767 bytes.\n"
    "No mods, datapacks, resource packs, options, or unrelated config values are changed.\n"
).encode("utf-8")

fixed_client = (2026, 10, 9, 20, 0, 0)
with zipfile.ZipFile(CLIENT_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for name, data in [("patch.json", patch_bytes), ("README.txt", readme)]:
        zi = zipfile.ZipInfo(name, fixed_client)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(CLIENT_ZIP) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == ["README.txt", "patch.json"]
    p = json.loads(z.read("patch.json"))
    assert p == PATCH
    assert p["fromVersions"] == ["2.0.1"] and p["toVersion"] == "2.0.2"
    assert [a["type"] for a in p["actions"]] == ["tomlEdit", "tomlEdit"]

meta = {
  "schemaVersion": 1,
  "channel": "stable",
  "tag": "client-v2.0.2",
  "patchId": "sgp-client-2.0.2",
  "targetPackId": "sgp-neoforge-1.21.1-client",
  "minecraft": "1.21.1",
  "neoforge": "21.1.249",
  "patchSchemaVersion": 1,
  "fromVersions": ["2.0.1"],
  "toVersion": "2.0.2",
  "assetName": "SGP_ClientPatch_2.0.2.zip",
  "assetSize": CLIENT_ZIP.stat().st_size,
  "sha256": sha_file(CLIENT_ZIP),
  "minInstallerVersion": "2.0.0"
}
CLIENT_META.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", "utf-8")

# Reconstruct exact installed server 2.0.1 metadata bytes and prove hashes before advancing.
pack201 = {
 "schemaVersion": 1,
 "packId": "sgp-neoforge-1.21.1-server",
 "familyId": "sgp-neoforge-1.21.1",
 "displayName": "SGP Minecraft 1.21.1 (Server)",
 "side": "server",
 "version": "2.0.1",
 "versionFormat": "semver",
 "minecraft": "1.21.1",
 "loader": "neoforge",
 "neoforge": "21.1.249",
 "javaMajor": 21,
 "releaseChannel": "stable",
 "baseline": False,
 "stateSchemaVersion": 1,
 "lastUpdate": {"id": "sgp-server-2.0.1", "type": "release", "version": "2.0.1", "releaseDate": "2026-10-08"}
}
history201 = {
 "schemaVersion": 1,
 "packId": "sgp-neoforge-1.21.1-server",
 "currentVersion": "2.0.1",
 "versionFormat": "semver",
 "entries": [
  {"id": "sgp-baseline-1.0.0", "type": "baseline", "version": "1.0.0", "releaseDate": "2026-09-22", "installer": "manual"},
  {"id": "sgp-server-1.2.0", "type": "release", "version": "1.2.0", "releaseDate": "2026-10-05", "installer": "manual"},
  {"id": "sgp-server-1.2.1", "type": "release", "version": "1.2.1", "releaseDate": "2026-10-05", "installer": "manual"},
  {"id": "sgp-server-2.0.0", "type": "release", "version": "2.0.0", "releaseDate": "2026-10-06", "installer": "manual"},
  {"id": "sgp-server-2.0.1", "type": "release", "version": "2.0.1", "releaseDate": "2026-10-08", "installer": "manual"}
 ]
}
pack201_bytes = (json.dumps(pack201, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
history201_bytes = (json.dumps(history201, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
assert sha_bytes(pack201_bytes) == SERVER_201_PACK_SHA
assert sha_bytes(history201_bytes) == SERVER_201_HISTORY_SHA

pack202 = dict(pack201)
pack202["version"] = "2.0.2"
pack202["lastUpdate"] = {"id": "sgp-server-2.0.2", "type": "release", "version": "2.0.2", "releaseDate": "2026-10-09"}
history202 = json.loads(json.dumps(history201))
history202["currentVersion"] = "2.0.2"
history202["entries"].append(
  {"id": "sgp-server-2.0.2", "type": "release", "version": "2.0.2", "releaseDate": "2026-10-09", "installer": "manual"}
)

if WORK.exists():
    shutil.rmtree(WORK)
build = WORK / "server-root"
sgp = build / ".sgp"
sgp.mkdir(parents=True)
(sgp / "pack.json").write_text(json.dumps(pack202, ensure_ascii=False, indent=2) + "\n", "utf-8")
(sgp / "history.json").write_text(json.dumps(history202, ensure_ascii=False, indent=2) + "\n", "utf-8")
for rel in ["config/create-server.toml", "world/serverconfig/create-server.toml"]:
    p = build / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(create_target)

expected_server_files = [
    ".sgp/history.json",
    ".sgp/pack.json",
    "config/create-server.toml",
    "world/serverconfig/create-server.toml",
]
files = sorted(p for p in build.rglob("*") if p.is_file())
assert [p.relative_to(build).as_posix() for p in files] == expected_server_files

fixed_server = (2026, 10, 9, 20, 5, 0)
with zipfile.ZipFile(SERVER_ZIP, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for f in files:
        zi = zipfile.ZipInfo(f.relative_to(build).as_posix(), fixed_server)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(SERVER_ZIP) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == expected_server_files
    a = z.read("config/create-server.toml")
    b = z.read("world/serverconfig/create-server.toml")
    assert a == b == create_target
    conf = tomllib.loads(a.decode("utf-8"))
    assert conf["schematics"]["maxTotalSchematicSize"] == 20480
    assert conf["schematics"]["maxSchematicPacketSize"] == 32767
    pk = json.loads(z.read(".sgp/pack.json"))
    hs = json.loads(z.read(".sgp/history.json"))
    assert pk["version"] == "2.0.2"
    assert hs["currentVersion"] == "2.0.2"
    assert [e["version"] for e in hs["entries"]] == ["1.0.0","1.2.0","1.2.1","2.0.0","2.0.1","2.0.2"]

outputs = {
  "CLIENT_SHA": sha_file(CLIENT_ZIP),
  "CLIENT_SIZE": str(CLIENT_ZIP.stat().st_size),
  "META_SHA": sha_file(CLIENT_META),
  "META_SIZE": str(CLIENT_META.stat().st_size),
  "TARGET_CREATE_SHA": sha_bytes(create_target),
  "TARGET_CREATE_SIZE": str(len(create_target)),
  "TARGET_HUD_SHA": sha_bytes(hud_target),
  "TARGET_HUD_SIZE": str(len(hud_target)),
  "SERVER_SHA": sha_file(SERVER_ZIP),
  "SERVER_SIZE": str(SERVER_ZIP.stat().st_size),
  "SERVER_PACK_SHA": sha_file(sgp / "pack.json"),
  "SERVER_PACK_SIZE": str((sgp / "pack.json").stat().st_size),
  "SERVER_HISTORY_SHA": sha_file(sgp / "history.json"),
  "SERVER_HISTORY_SIZE": str((sgp / "history.json").stat().st_size),
}
for k,v in outputs.items():
    Path(k.lower()+".txt").write_text(v+"\n","utf-8")

print("CLIENT_202_CONFIG_ONLY_STATIC_AUDIT_PASS")
print("SERVER_202_CONFIG_ONLY_STATIC_AUDIT_PASS")
for k,v in outputs.items():
    print(f"{k}={v}")
