#!/usr/bin/env python3
import hashlib, json, urllib.parse, urllib.request
from pathlib import Path

UA={"User-Agent":"SGP-release-builder/1.0 (KNRDNB/sgp-updates)"}

def get_json(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=60) as r:
        return json.load(r)

def fetch_file(url,path,sha512):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=120) as r:
        data=r.read()
    assert hashlib.sha512(data).hexdigest().lower()==sha512.lower()
    Path(path).write_bytes(data)
    return {
      "filename":path,
      "size":len(data),
      "sha256":hashlib.sha256(data).hexdigest(),
      "sha512":hashlib.sha512(data).hexdigest(),
    }

# Permanent Sponges: exact NeoForge 1.21.1 release.
perm=get_json("https://api.modrinth.com/v2/version/9EBHr4tP")
assert perm["version_number"]=="v21.1.0-1.21.1-NeoForge",perm["version_number"]
assert "neoforge" in perm["loaders"]
assert "1.21.1" in perm["game_versions"]
perm_name="PermanentSponges-v21.1.0-1.21.1-NeoForge.jar"
perm_file=next(f for f in perm["files"] if f["filename"]==perm_name)
perm_meta=fetch_file(perm_file["url"],perm_name,perm_file["hashes"]["sha512"])
perm_meta["version_id"]=perm["id"]
perm_meta["version_number"]=perm["version_number"]

# Puzzles Lib: pin the current exact NeoForge 1.21.1 library release.
qs=urllib.parse.urlencode({
  "loaders":json.dumps(["neoforge"]),
  "game_versions":json.dumps(["1.21.1"])
})
versions=get_json("https://api.modrinth.com/v2/project/puzzles-lib/version?"+qs)
target_version="v21.1.62-mc1.21.1+neoforge"
puz=next(v for v in versions if v["version_number"]==target_version)
assert "neoforge" in puz["loaders"]
assert "1.21.1" in puz["game_versions"]
puz_name="puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"
puz_file=next(f for f in puz["files"] if f["filename"]==puz_name)
puz_meta=fetch_file(puz_file["url"],puz_name,puz_file["hashes"]["sha512"])
puz_meta["version_id"]=puz["id"]
puz_meta["version_number"]=puz["version_number"]

meta={"permanent_sponges":perm_meta,"puzzles_lib":puz_meta}
Path("mod_meta.json").write_text(json.dumps(meta,indent=2)+"\n","utf-8")
print("EXACT_MOD_DOWNLOAD_PASS")
print(json.dumps(meta,indent=2))
