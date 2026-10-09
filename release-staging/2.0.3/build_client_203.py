from __future__ import annotations
import base64, hashlib, json, tomllib, zipfile
from pathlib import Path

ROOT = Path.cwd()
STAGE = ROOT / "release-staging/2.0.3"
OUT = ROOT / "SGP_ClientPatch_2.0.3.zip"
META = ROOT / "SGP_ClientPatch_2.0.3.meta.json"

HUD_BASE_SHA = "86252c534fd19ba2750fe463ea92df2c53d8158bf41d9ff53c15037fe1e17828"
HUD_BASE_SIZE = 5993

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

raw = (STAGE / "inventoryhud-client-2.0.2-base.b64").read_text("ascii")
hud_base = base64.b64decode("".join(raw.split()))
assert len(hud_base) == HUD_BASE_SIZE and sha_bytes(hud_base) == HUD_BASE_SHA

hud_target = hud_base
for key in [b"helmPosX", b"chestPosX", b"mainPosX", b"arrPosX"]:
    old = b"\t" + key + b" = 111\r\n"
    new = b"\t" + key + b" = 136\r\n"
    assert hud_target.count(old) == 1, (key, hud_target.count(old))
    hud_target = hud_target.replace(old, new, 1)

for key in [b"legPosX", b"bootPosX", b"offPosX", b"invPosX"]:
    old = b"\t" + key + b" = -111\r\n"
    new = b"\t" + key + b" = -136\r\n"
    assert hud_target.count(old) == 1, (key, hud_target.count(old))
    hud_target = hud_target.replace(old, new, 1)

hb = flatten(tomllib.loads(hud_base.decode("utf-8")))
ht = flatten(tomllib.loads(hud_target.decode("utf-8")))
changed = {k: (hb.get(k), ht.get(k)) for k in set(hb) | set(ht) if hb.get(k) != ht.get(k)}
assert changed == {
    ("positions", "helmPosX"): (111, 136),
    ("positions", "chestPosX"): (111, 136),
    ("positions", "mainPosX"): (111, 136),
    ("positions", "arrPosX"): (111, 136),
    ("positions", "legPosX"): (-111, -136),
    ("positions", "bootPosX"): (-111, -136),
    ("positions", "offPosX"): (-111, -136),
    ("positions", "invPosX"): (-111, -136),
}, changed

PATCH = {
  "schemaVersion": 1,
  "patchId": "sgp-client-2.0.3",
  "name": "SGP Client 2.0.3",
  "targetPackId": "sgp-neoforge-1.21.1-client",
  "minecraft": "1.21.1",
  "neoforge": "21.1.249",
  "fromVersions": ["2.0.2"],
  "toVersion": "2.0.3",
  "restartRequired": True,
  "summary": [
    "ArmorHUD correction: restore the left-side positions to 136.",
    "ArmorHUD correction: move the right-side positions to -136 for symmetric spacing."
  ],
  "actions": [
    {
      "actionId": "inventoryhud-symmetric-136-spacing",
      "type": "tomlEdit",
      "description": "Вернуть левую группу ArmorHUD на 136 и сделать правую симметричной -136",
      "target": "config/inventoryhud-client.toml",
      "edits": [
        {"op": "set", "path": "positions.helmPosX", "value": 136, "createIfMissing": False},
        {"op": "set", "path": "positions.chestPosX", "value": 136, "createIfMissing": False},
        {"op": "set", "path": "positions.mainPosX", "value": 136, "createIfMissing": False},
        {"op": "set", "path": "positions.arrPosX", "value": 136, "createIfMissing": False},
        {"op": "set", "path": "positions.legPosX", "value": -136, "createIfMissing": False},
        {"op": "set", "path": "positions.bootPosX", "value": -136, "createIfMissing": False},
        {"op": "set", "path": "positions.offPosX", "value": -136, "createIfMissing": False},
        {"op": "set", "path": "positions.invPosX", "value": -136, "createIfMissing": False}
      ]
    }
  ]
}

patch_bytes = (json.dumps(PATCH, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
readme = (
    "SGP Client 2.0.3\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Owner-authorized direct stable client HUD correction.\n"
    "Exact sequential edge: 2.0.2 -> 2.0.3.\n\n"
    "ArmorHUD changes only:\n"
    "- left helmet/chest/main/arrows: 111 -> 136\n"
    "- right leggings/boots/offhand/inventory: -111 -> -136\n"
    "Create schematic settings from 2.0.2 are unchanged.\n"
    "No mods, datapacks, resource packs, options, server configs, or unrelated client config values are changed.\n"
).encode("utf-8")

fixed=(2026,10,9,21,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme)]:
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == ["README.txt","patch.json"]
    p=json.loads(z.read("patch.json"))
    assert p == PATCH
    assert p["fromVersions"] == ["2.0.2"] and p["toVersion"] == "2.0.3"
    assert len(p["actions"]) == 1 and p["actions"][0]["target"] == "config/inventoryhud-client.toml"

meta = {
  "schemaVersion":1,
  "channel":"stable",
  "tag":"client-v2.0.3",
  "patchId":"sgp-client-2.0.3",
  "targetPackId":"sgp-neoforge-1.21.1-client",
  "minecraft":"1.21.1",
  "neoforge":"21.1.249",
  "patchSchemaVersion":1,
  "fromVersions":["2.0.2"],
  "toVersion":"2.0.3",
  "assetName":"SGP_ClientPatch_2.0.3.zip",
  "assetSize":OUT.stat().st_size,
  "sha256":sha_file(OUT),
  "minInstallerVersion":"2.0.0"
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")

Path("client203_sha.txt").write_text(sha_file(OUT)+"\n","utf-8")
Path("client203_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("client203_meta_sha.txt").write_text(sha_file(META)+"\n","utf-8")
Path("client203_meta_size.txt").write_text(str(META.stat().st_size)+"\n","utf-8")
Path("hud203_sha.txt").write_text(sha_bytes(hud_target)+"\n","utf-8")
Path("hud203_size.txt").write_text(str(len(hud_target))+"\n","utf-8")

print("CLIENT_203_HUD_ONLY_STATIC_AUDIT_PASS")
print("CLIENT_SHA="+sha_file(OUT))
print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META))
print("META_SIZE="+str(META.stat().st_size))
print("HUD_SHA="+sha_bytes(hud_target))
print("HUD_SIZE="+str(len(hud_target)))
