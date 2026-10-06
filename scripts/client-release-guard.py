"""Prepublication binding guard. Does not replace package/runtime/owner gates.
Read-only by default; --publish explicitly creates a NEW Draft, verifies both
downloaded assets, then publishes. Existing tags/releases are immutable.
"""
import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import tempfile
import zipfile

REPO = "KNRDNB/sgp-updates"
ROOT = pathlib.Path(__file__).resolve().parents[1]
FIELDS = set("schemaVersion channel tag patchId targetPackId minecraft neoforge patchSchemaVersion fromVersions toVersion assetName assetSize sha256 minInstallerVersion".split())

def require(ok, message):
    if not ok:
        raise ValueError(message)

def pairs(items):
    obj = {}
    for k, v in items:
        require(k not in obj, "Duplicate JSON property: " + k)
        obj[k] = v
    return obj

def strict_json(raw, limit):
    require(0 < len(raw) <= limit, "JSON byte limit")
    require(not raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM forbidden")
    return json.loads(raw.decode("utf-8", errors="strict"), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))

def version(text):
    require(isinstance(text, str) and len(text) <= 128, "Version type/length")
    m = re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?", text)
    require(m is not None, "Noncanonical SemVer: " + text)
    core = tuple(int(m[i]) for i in (1, 2, 3))
    require(all(n <= 2147483647 for n in core), "Version component overflow")
    ids = m[4].split(".") if m[4] else []
    require(all(not i.isdecimal() or len(i) == 1 or i[0] != "0" for i in ids), "Prerelease leading zero")
    return core, ids

def compare(a, b):
    ac, ai = version(a); bc, bi = version(b)
    if ac != bc:
        return (ac > bc) - (ac < bc)
    if not ai or not bi:
        return int(not ai) - int(not bi)
    for x, y in zip(ai, bi):
        if x == y:
            continue
        if x.isdecimal() and y.isdecimal():
            return (int(x) > int(y)) - (int(x) < int(y))
        if x.isdecimal() != y.isdecimal():
            return -1 if x.isdecimal() else 1
        return (x > y) - (x < y)
    return (len(ai) > len(bi)) - (len(ai) < len(bi))

def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()

def validate(tag, channel, archive, metadata):
    m = strict_json(metadata.read_bytes(), 65536)
    require(isinstance(m, dict) and set(m) == FIELDS, "Missing/unknown metadata fields")
    require(type(m["schemaVersion"]) is int and m["schemaVersion"] == 1 and type(m["patchSchemaVersion"]) is int and m["patchSchemaVersion"] == 1, "Schema mismatch")
    require(m["channel"] == channel and channel in ("stable", "test"), "Channel mismatch")
    target = m["toVersion"]; version(target)
    require(compare(target, "2.0.0") > 0 and tag == m["tag"] == "client-v" + target, "Post-cutover tag/version mismatch")
    is_test = re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+-test\.(0|[1-9][0-9]*)", target) is not None
    require(is_test if channel == "test" else not version(target)[1], "Stable/TEST prerelease mismatch")
    require(archive.name == m["assetName"] == "SGP_ClientPatch_" + target + ".zip" and metadata.name == "SGP_ClientPatch_" + target + ".meta.json", "Exact filename mismatch")
    require(m["targetPackId"] == "sgp-neoforge-1.21.1-client" and m["minecraft"] == "1.21.1" and m["neoforge"] == "21.1.249", "Platform mismatch")
    require(isinstance(m["patchId"], str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", m["patchId"]) is not None, "patchId mismatch")
    sources = m["fromVersions"]
    require(isinstance(sources, list) and 0 < len(sources) <= 1000 and all(isinstance(s, str) for s in sources) and len(set(sources)) == len(sources), "Invalid/duplicate source versions")
    for source in sources:
        require(compare(source, "2.0.0") >= 0 and compare(source, target) < 0, "Backward/legacy edge")
    require(not version(m["minInstallerVersion"])[1] and compare(m["minInstallerVersion"], "2.0.0") >= 0, "Chain-capable minimum Installer required")
    require(type(m["assetSize"]) is int and 0 < m["assetSize"] <= 2 * 1024**3 and archive.stat().st_size == m["assetSize"], "ZIP size mismatch")
    require(isinstance(m["sha256"], str) and re.fullmatch(r"[0-9A-Fa-f]{64}", m["sha256"]) is not None and digest(archive) == m["sha256"].lower(), "ZIP SHA mismatch")
    with zipfile.ZipFile(archive) as z:
        entries = [e for e in z.infolist() if e.filename == "patch.json"]
        require(len(entries) == 1 and 0 < entries[0].file_size <= 4 * 1024**2, "Exactly one bounded patch.json required")
        p = strict_json(z.read(entries[0]), 4 * 1024**2)
    require(isinstance(p, dict) and type(p.get("schemaVersion")) is int, "Manifest schema type")
    for key in ("schemaVersion", "patchId", "targetPackId", "minecraft", "neoforge", "fromVersions", "toVersion"):
        require(p.get(key) == (m["patchSchemaVersion"] if key == "schemaVersion" else m[key]), "patch.json binding mismatch: " + key)
    return m

def gh(*args, check=True):
    return subprocess.run(["gh", *args], check=check, capture_output=True, text=True)

def activation(m):
    a = strict_json((ROOT / "client-channel.json").read_bytes(), 65536)
    require(a["state"] == "ACTIVE" and a["livePublicSelfUpdate"] == "PASS", "Installer cutover gate incomplete")
    r = json.loads(gh("api", "repos/" + REPO + "/releases/tags/" + a["installerTag"]).stdout)
    require(not r["draft"] and not r["prerelease"] and r["id"] == a["installerReleaseId"], "Accepted Installer is not exact public stable")
    assets = {v["name"]: v for v in r["assets"]}
    require(len(r["assets"]) == 2 and set(assets) == {"SGP-Patch-Installer.exe", "SGP-Patch-Installer.exe.sha256"}, "Installer assets mismatch")
    exe = assets["SGP-Patch-Installer.exe"]
    require(exe["state"] == "uploaded" and exe["size"] == a["installerBytes"] and exe["digest"] == "sha256:" + a["installerSHA256"].lower(), "Installer exact identity mismatch")
    for pinned in a["installerAssets"]:
        asset = assets[pinned["name"]]
        require(asset["state"] == "uploaded" and all(asset[key] == pinned[key] for key in ("id", "size", "digest")), "Accepted Installer asset identity changed")
    require(compare(m["minInstallerVersion"], a["installerVersion"]) <= 0, "Minimum Installer has not been accepted")

def publish(args, m):
    require(args.notes is not None, "--publish requires reviewed --notes and prior package/runtime/owner authorization")
    activation(m)
    existing = gh("release", "view", args.tag, "--repo", REPO, "--json", "apiUrl", check=False)
    require(existing.returncode != 0 and "release not found" in existing.stderr.lower(), "Existing release/Draft or inconclusive lookup")
    for endpoint in ("releases/tags/", "git/ref/tags/"):
        response = gh("api", "repos/" + REPO + "/" + endpoint + args.tag, check=False)
        require(response.returncode != 0 and "HTTP 404" in response.stderr, "Existing tag/release or inconclusive identity check")
    gh("release", "create", args.tag, str(args.zip), str(args.metadata), "--repo", REPO, "--draft", "--title", args.tag, "--notes-file", str(args.notes), *(["--prerelease"] if args.channel == "test" else []))
    with tempfile.TemporaryDirectory(prefix="SGP-draft-binding-") as temp:
        gh("release", "download", args.tag, "--repo", REPO, "--dir", temp)
        files = list(pathlib.Path(temp).iterdir())
        require({p.name for p in files} == {args.zip.name, args.metadata.name} and len(files) == 2, "Draft asset set mismatch; left Draft")
        for original in (args.zip, args.metadata):
            downloaded = pathlib.Path(temp) / original.name
            require(downloaded.stat().st_size == original.stat().st_size and digest(downloaded) == digest(original), "Draft bytes mismatch; left Draft")
        require(validate(args.tag, args.channel, pathlib.Path(temp) / args.zip.name, pathlib.Path(temp) / args.metadata.name) == m, "Draft differs from initially reviewed metadata; left Draft")
    activation(m)
    gh("release", "edit", args.tag, "--repo", REPO, "--draft=false", "--prerelease=" + str(args.channel == "test").lower(), "--latest=false")
    print("Published verified exact pair; required live-public binding/package smoke remains mandatory.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tag", required=True)
    parser.add_argument("--channel", required=True, choices=("stable", "test"))
    parser.add_argument("--zip", required=True, type=pathlib.Path)
    parser.add_argument("--metadata", required=True, type=pathlib.Path)
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--notes", type=pathlib.Path)
    args = parser.parse_args()
    metadata = validate(args.tag, args.channel, args.zip, args.metadata)
    print("PASS: canonical client tag/channel/metadata/ZIP binding")
    if args.publish:
        publish(args, metadata)
