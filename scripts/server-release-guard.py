#!/usr/bin/env python3
"""Strict data-only server release guard. Never builds or repacks the supplied ZIP."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, re, sys, zipfile

PACK = "sgp-neoforge-1.21.1-server"
FAMILY = "sgp-neoforge-1.21.1"
FIELDS = set("schemaVersion channel tag packId familyId side fromVersions toVersion minInstallerVersion assetName sha256 size deletions changelog backupMode".split())

def require(ok, message):
    if not ok: raise ValueError(message)

def pairs(values):
    result = {}
    for key, value in values:
        require(key not in result, "Duplicate JSON property")
        result[key] = value
    return result

def parse(data, limit=65536):
    require(len(data) <= limit, "JSON too large")
    return json.loads(data.decode("utf-8", errors="strict"), object_pairs_hook=pairs)

def version(value):
    require(isinstance(value, str) and len(value) <= 128 and re.fullmatch(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)", value), "Invalid stable SemVer")
    result = tuple(map(int, value.split(".")))
    require(max(result) <= 2147483647, "Version component overflow")
    return result

def relative(path):
    require(isinstance(path, str) and 0 < len(path) <= 512 and not any(ord(c) < 32 or c in '\\:%*?"<>|' for c in path), "Unsafe path")
    for part in path.split("/"):
        require(0 < len(part) <= 128 and part not in (".", "..") and part.strip() == part and not part.endswith("."), "Ambiguous path")
        require(not re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?", part), "Reserved path")
    return path

def target(path, mode):
    relative(path)
    require(path.startswith(("mods/", "config/", "defaultconfigs/")) or path == "server.properties" or mode == "snapshot" and path.startswith("world/"), "Protected path")
    ext = pathlib.PurePosixPath(path).suffix.lower()
    require(ext not in {".exe", ".msi", ".dll", ".ps1", ".bat", ".cmd", ".sh", ".py", ".js", ".vbs"}, "Executable payload forbidden")
    require(ext != ".jar" or path.startswith("mods/"), "JAR outside mods")

def validate_metadata(meta):
    require(isinstance(meta, dict) and set(meta) == FIELDS, "Unknown/missing metadata fields")
    v = meta["toVersion"]; to = version(v); version(meta["minInstallerVersion"])
    require(type(meta["schemaVersion"]) is int and meta["schemaVersion"] == 1 and meta["channel"] == "stable" and meta["tag"] == "server-v" + v, "Channel identity")
    require((meta["packId"], meta["familyId"], meta["side"]) == (PACK, FAMILY, "server"), "Server identity")
    require(meta["assetName"] == "SGP_ServerPatch_" + v + ".zip", "Asset identity")
    require(type(meta["size"]) is int and 0 < meta["size"] <= 2 * 1024**3 and re.fullmatch(r"[0-9a-fA-F]{64}", meta["sha256"]), "ZIP binding")
    require(meta["backupMode"] in ("files", "snapshot"), "Backup risk mode")
    require(isinstance(meta["fromVersions"], list) and 0 < len(meta["fromVersions"]) <= 32 and len(set(meta["fromVersions"])) == len(meta["fromVersions"]), "Source versions")
    for source in meta["fromVersions"]: require(version(source) < to, "Non-forward source")
    require(isinstance(meta["deletions"], list) and len(meta["deletions"]) <= 10000 and len({p.lower() for p in meta["deletions"]}) == len(meta["deletions"]), "Deletion list")
    for path in meta["deletions"]: target(path, meta["backupMode"])
    notes = meta["changelog"]
    require(isinstance(notes, str) and 0 < len(notes) <= 4000 and any('\u0400' <= c <= '\u04ff' for c in notes) and '\r' not in notes and '\ufffd' not in notes and '??' not in notes, "Russian changelog required")
    require(not re.search(r"https?://|<[^>]*>|```|\*\*", notes), "Changelog must be bounded plain text")

def validate_zip(path, meta):
    require(path.name == meta["assetName"] and path.stat().st_size == meta["size"], "Exact ZIP filename/size mismatch")
    with path.open("rb") as f: sha = hashlib.file_digest(f, "sha256").hexdigest()
    require(sha == meta["sha256"].lower(), "Exact ZIP SHA mismatch")
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist(); require(0 < len(entries) <= 10000, "ZIP entry count")
        names = set(); total = 0
        for entry in entries:
            relative(entry.filename); lower = entry.filename.lower()
            require(lower not in names, "Duplicate ZIP entry"); names.add(lower)
            require((entry.external_attr >> 16) & 0xf000 in (0, 0x8000) and not entry.is_dir(), "Symlink/special/directory entry")
            require(0 <= entry.file_size <= 1024**3, "File size"); total += entry.file_size
            require(total <= 4 * 1024**3, "Expanded size")
            require(lower not in {p.lower() for p in meta["deletions"]}, "Replace/delete overlap")
            if entry.filename not in (".sgp/pack.json", ".sgp/history.json"): target(entry.filename, meta["backupMode"])
            with archive.open(entry) as source:
                count = 0
                while data := source.read(1024 * 1024):
                    count += len(data); require(count <= entry.file_size, "Expanded size mismatch")
                require(count == entry.file_size, "Truncated entry")
        pack = parse(archive.read(".sgp/pack.json"), 4 * 1024**2); hist = parse(archive.read(".sgp/history.json"), 4 * 1024**2)
        require(pack["schemaVersion"] == hist["schemaVersion"] == 1 and pack["packId"] == hist["packId"] == PACK and pack["familyId"] == FAMILY and pack["side"] == "server", "ZIP .sgp identity")
        require(pack["version"] == hist["currentVersion"] == meta["toVersion"] and pack["versionFormat"] == hist["versionFormat"] == "semver", "ZIP target version")
        require(pack["minecraft"] == "1.21.1" and pack["loader"] == "neoforge" and pack["neoforge"] == "21.1.249", "ZIP platform")
        require(pack["lastUpdate"]["type"] == "release" and pack["lastUpdate"]["version"] == meta["toVersion"] and hist["entries"][-1]["version"] == meta["toVersion"], "Final manual-release state required")
        require(not any(k in pack["lastUpdate"] for k in ("transactionId", "backupPath", "backupManifestHash")), "Do not fabricate Installer lineage")
    return sha

def json_bytes(value): return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--zip", type=pathlib.Path, required=True); p.add_argument("--version", required=True)
    sources=p.add_mutually_exclusive_group(required=True)
    sources.add_argument("--from-versions"); sources.add_argument("--from-versions-file", type=pathlib.Path)
    p.add_argument("--expected-sha", required=True); p.add_argument("--expected-size", type=int, required=True)
    p.add_argument("--deletions", type=pathlib.Path, required=True); p.add_argument("--changelog", type=pathlib.Path, required=True)
    p.add_argument("--backup-mode", choices=("files", "snapshot"), required=True); p.add_argument("--min-installer", default="2.2.0")
    p.add_argument("--output", type=pathlib.Path, required=True)
    args = p.parse_args(); version(args.version)
    meta = dict(schemaVersion=1, channel="stable", tag="server-v" + args.version, packId=PACK, familyId=FAMILY, side="server",
                fromVersions=parse(args.from_versions_file.read_bytes() if args.from_versions_file else args.from_versions.encode()), toVersion=args.version, minInstallerVersion=args.min_installer,
                assetName="SGP_ServerPatch_" + args.version + ".zip", sha256=args.expected_sha.lower(), size=args.expected_size,
                deletions=parse(args.deletions.read_bytes()), changelog=args.changelog.read_text(encoding="utf-8").strip(), backupMode=args.backup_mode)
    validate_metadata(meta); validate_zip(args.zip, meta)
    output = args.output; output.mkdir(parents=True, exist_ok=True)
    data = json_bytes(meta); require(len(data) <= 65536, "Metadata exceeds cap")
    metadata_name = "SGP_ServerPatch_" + args.version + ".meta.json"
    (output / metadata_name).write_bytes(data)
    pointer = dict(schemaVersion=1, version=args.version, tag=meta["tag"], metadataName=metadata_name,
                   metadataSha256=hashlib.sha256(data).hexdigest(), metadataSize=len(data))
    (output / "latest.json").write_bytes(json_bytes(pointer))
    (output / "binding.json").write_bytes(json_bytes(dict(result="PASS", zipSha256=meta["sha256"], zipSize=meta["size"], metadataSha256=pointer["metadataSha256"], metadataSize=len(data), repacked=False)))
    print("SERVER_CHANNEL_EXACT_PACKAGE_GUARD_PASS")

if __name__ == "__main__":
    try: main()
    except Exception as exc: print("SERVER_CHANNEL_GUARD_FAIL: " + str(exc), file=sys.stderr); sys.exit(1)
