#!/usr/bin/env python3
"""Finalize client 2.1.0 from exact owner-RUNTIME-PASS 2.1.0-test.1 bytes.
Only release identity/fromVersions/readme may differ; action payload and
preconditions MUST be strictly identical to the runtime-tested TEST.
"""
from __future__ import annotations
import hashlib
import io
import json
import pathlib
import zipfile

ROOT = pathlib.Path.cwd()
SRC_ZIP = ROOT / "test-proof" / "SGP_ClientPatch_2.1.0-test.1.zip"
SRC_META = ROOT / "test-proof" / "SGP_ClientPatch_2.1.0-test.1.meta.json"
VERSION = "2.1.0"
OUT_ZIP = ROOT / ("SGP_ClientPatch_" + VERSION + ".zip")
OUT_META = ROOT / ("SGP_ClientPatch_" + VERSION + ".meta.json")
SRC_VERSION = "2.1.0-test.1"
SRC_SHA = "08215fd8d3716e0c744a36f9fe4467d0f50bda87b7d49a8f8b93283359491a98"
SRC_META_SHA = "0727019f32c15e1ab924c9649bd7ab6a948c2e654a85562fd6f3d6cb0681be77"
PAXEL_NAME = "SGP-Wands-Paxel-Compat-1.0.3.jar"
PAXEL_SHA = "52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
GLASS_NAME = "SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"
GLASS_SHA = "60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"
SOURCES = ["2.0.10", "2.0.11-test.1", "2.0.11-test.2", "2.0.11-test.3", SRC_VERSION]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


assert sha(SRC_ZIP.read_bytes()) == SRC_SHA, "Test ZIP byte identity mismatch"
assert sha(SRC_META.read_bytes()) == SRC_META_SHA, "Test metadata byte identity mismatch"
source_metadata = json.loads(SRC_META.read_bytes())
assert source_metadata["toVersion"] == SRC_VERSION
assert source_metadata["channel"] == "test"
assert source_metadata["tag"] == "client-v" + SRC_VERSION
assert source_metadata["fromVersions"] == SOURCES[:-1]
assert source_metadata["sha256"] == SRC_SHA
assert source_metadata["assetSize"] == SRC_ZIP.stat().st_size

with zipfile.ZipFile(SRC_ZIP) as old:
    assert old.testzip() is None
    names = old.namelist()
    required = {
        "patch.json",
        "README.txt",
        "files/mods/" + PAXEL_NAME,
        "files/mods/" + GLASS_NAME,
    }
    assert set(names) == required and len(names) == len(required), "Unknown TEST ZIP payload"
    test_patch = json.loads(old.read("patch.json"))
    paxel = old.read("files/mods/" + PAXEL_NAME)
    glass = old.read("files/mods/" + GLASS_NAME)

assert test_patch["fromVersions"] == SOURCES[:-1]
assert test_patch["toVersion"] == SRC_VERSION
assert test_patch["patchId"] == "sgp-client-" + SRC_VERSION
assert sha(paxel) == PAXEL_SHA and len(paxel) == 7673
assert sha(glass) == GLASS_SHA and len(glass) == 4811
assert [a["type"] for a in test_patch["actions"]] == ["delete","delete","delete","copy","copy","jsonEdit"]

for blob, name in [(paxel,PAXEL_NAME),(glass,GLASS_NAME)]:
    with zipfile.ZipFile(io.BytesIO(blob)) as jar:
        assert jar.testzip() is None
        assert "META-INF/neoforge.mods.toml" in jar.namelist()
        assert not any(n.startswith("net/nicguzzo/wands/") for n in jar.namelist())

patch = json.loads(json.dumps(test_patch))
patch["patchId"] = "sgp-client-" + VERSION
patch["name"] = "SGP Client " + VERSION
patch["toVersion"] = VERSION
patch["fromVersions"] = SOURCES

# Contract: full action set, including all preconditions and bytes, unchanged.
assert patch["actions"] == test_patch["actions"], "Payload/action/precondition drift"
assert patch["summary"] == test_patch["summary"], "Changed behavior summary"
for field in ("schemaVersion","targetPackId","minecraft","neoforge","restartRequired"):
    assert patch[field] == test_patch[field]
assert set(patch) == set(test_patch)
assert patch["fromVersions"] == test_patch["fromVersions"] + [SRC_VERSION]
assert patch["actions"][-1]["edits"] == [{
    "op":"set",
    "path":"/performance/quad_splitting_mode",
    "value":"SAFE",
    "createIfMissing":False,
}]

readme = (
    "SGP Client 2.1.0 — stable release\n\n"
    "Promoted from owner-runtime-PASS client 2.1.0-test.1.\n"
    "Owner confirmed all 9 grouped runtime checks PASS on 2026-11-08:\n"
    "Destroy/Replace; Use log stripping; Use paths; Use copper transformations;\n"
    "durability; tool selection; mining/drop/tier restrictions;\n"
    "other paxels and vanilla tools; BetterNether Quartz Glass.\n"
    "The exact TEST action set/preconditions and SGP mod JAR bytes are unchanged.\n"
    "Wands Paxel Compat 1.0.3 and BetterNether Quartz Glass Compat 1.0.0.\n"
    "Sodium quad_splitting_mode remains SAFE.\n"
    "No server release is part of this client patch.\n"
    "Previous TEST source 2.1.0-test.1 is eligible for identity-only promotion.\n"
).encode("utf-8")
new_manifest_bytes = (json.dumps(patch,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
entries = [
    ("patch.json",new_manifest_bytes),
    ("README.txt",readme),
    ("files/mods/" + PAXEL_NAME,paxel),
    ("files/mods/" + GLASS_NAME,glass),
]
fixed = (2026,11,8,19,0,0)
with zipfile.ZipFile(OUT_ZIP,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
    for name,data in entries:
        info = zipfile.ZipInfo(name,fixed)
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT_ZIP) as final:
    assert final.testzip() is None
    assert set(final.namelist()) == required
    assert len(final.namelist()) == 4
    assert json.loads(final.read("patch.json")) == patch
    assert final.read("files/mods/" + PAXEL_NAME) == paxel
    assert final.read("files/mods/" + GLASS_NAME) == glass

metadata = json.loads(json.dumps(source_metadata))
metadata["channel"] = "stable"
metadata["tag"] = "client-v" + VERSION
metadata["toVersion"] = VERSION
metadata["patchId"] = patch["patchId"]
metadata["fromVersions"] = SOURCES
metadata["assetName"] = OUT_ZIP.name
metadata["assetSize"] = OUT_ZIP.stat().st_size
metadata["sha256"] = sha(OUT_ZIP.read_bytes())
assert set(metadata) == set(source_metadata)
OUT_META.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

test_action_sha = sha(json.dumps(test_patch["actions"],ensure_ascii=False,sort_keys=True).encode())
stable_action_sha = sha(json.dumps(patch["actions"],ensure_ascii=False,sort_keys=True).encode())
assert test_action_sha == stable_action_sha

report={
    "release":VERSION,
    "test_source":SRC_VERSION,
    "test_zip_sha256":SRC_SHA,
    "test_meta_sha256":SRC_META_SHA,
    "test_action_sha256":test_action_sha,
    "stable_action_sha256":stable_action_sha,
    "fromVersions":SOURCES,
    "paxel_sha256":sha(paxel),
    "paxel_size":len(paxel),
    "glass_sha256":sha(glass),
    "glass_size":len(glass),
    "stable_zip_sha256":sha(OUT_ZIP.read_bytes()),
    "stable_zip_size":OUT_ZIP.stat().st_size,
    "stable_meta_sha256":sha(OUT_META.read_bytes()),
    "stable_meta_size":OUT_META.stat().st_size,
    "owner_runtime":"PASS_9_OF_9_GROUPS_REPORTED_2026_11_08",
    "server_release":"NOT_INCLUDED",
}
(ROOT / "client210_stable_audit.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,ensure_ascii=False,indent=2))
print("SGP_CLIENT_210_STABLE_IDENTICAL_TEST_ACTIONS_PASS")
