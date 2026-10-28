from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ServerPatch_2.0.5.zip"
BASE_DIR=ROOT/".server-205-base"
CLIENT_DIR=ROOT/".server-205-client"
BASE_SERVER=BASE_DIR/"SGP_ServerPatch_2.0.4.zip"
CLIENT_ZIP=CLIENT_DIR/"SGP_ClientPatch_2.0.5.zip"

BASE_RUN="40657586429"
BASE_ARTIFACT="sgp-server-2.0.4-handoff"
BASE_SHA="ba9adcdb0d6c660f3acac438e518cc11b8bee960d0a6a9170749492f5dfd5304"
BASE_SIZE=54008

CLIENT_TAG="client-v2.0.5"
CLIENT_SHA="74a94847c1ae4520d7ab222d6bcad2587d61d492a7a0a3138ce3f467561c1d40"
CLIENT_SIZE=13136

OLD_ADDON="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"
NEW_ADDON_SOURCE="files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
NEW_ADDON_TARGET="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
NEW_ADDON_SHA="206c05efb483a1ac88e76e7406fbb22a7fe7bb142699bb9fc17934fc2e646bef"
NEW_ADDON_SIZE=12587

def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path:pathlib.Path)->str:
    with path.open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()

BASE_DIR.mkdir(exist_ok=True)
CLIENT_DIR.mkdir(exist_ok=True)

subprocess.run([
    "gh","run","download",BASE_RUN,
    "--repo","KNRDNB/sgp-updates",
    "--name",BASE_ARTIFACT,
    "--dir",str(BASE_DIR),
],check=True)
if not BASE_SERVER.is_file():
    candidates=list(BASE_DIR.rglob("SGP_ServerPatch_2.0.4.zip"))
    assert len(candidates)==1,candidates
    BASE_SERVER=candidates[0]
assert BASE_SERVER.stat().st_size==BASE_SIZE
assert sha_file(BASE_SERVER)==BASE_SHA

with zipfile.ZipFile(BASE_SERVER) as bz:
    assert bz.testzip() is None
    names=set(bz.namelist())
    assert OLD_ADDON in names
    assert NEW_ADDON_TARGET not in names
    base_pack=json.loads(bz.read(".sgp/pack.json"))
    base_history=json.loads(bz.read(".sgp/history.json"))
    assert base_pack["version"]=="2.0.4"
    assert base_history["currentVersion"]=="2.0.4"
    assert [e["version"] for e in base_history["entries"]]==[
        "1.0.0","1.2.0","1.2.1","2.0.0","2.0.1","2.0.2","2.0.4"
    ]

subprocess.run([
    "gh","release","download",CLIENT_TAG,
    "--repo","KNRDNB/sgp-updates",
    "--pattern",CLIENT_ZIP.name,
    "--dir",str(CLIENT_DIR),
],check=True)
assert CLIENT_ZIP.stat().st_size==CLIENT_SIZE
assert sha_file(CLIENT_ZIP)==CLIENT_SHA

with zipfile.ZipFile(CLIENT_ZIP) as cz:
    assert cz.testzip() is None
    cp=json.loads(cz.read("patch.json"))
    assert cp["fromVersions"]==["2.0.4"]
    assert cp["toVersion"]=="2.0.5"
    assert [a["type"] for a in cp["actions"]]==["delete","copy"]
    assert cp["actions"][0]["target"]==OLD_ADDON
    addon=cz.read(NEW_ADDON_SOURCE)

assert len(addon)==NEW_ADDON_SIZE
assert sha_bytes(addon)==NEW_ADDON_SHA

pack=dict(base_pack)
pack["version"]="2.0.5"
pack["baseline"]=False
pack["lastUpdate"]={
    "id":"sgp-server-2.0.5",
    "type":"release",
    "version":"2.0.5",
    "releaseDate":"2026-10-28",
}

history=dict(base_history)
history["currentVersion"]="2.0.5"
history["entries"]=list(base_history["entries"])+[{
    "id":"sgp-server-2.0.5",
    "type":"release",
    "version":"2.0.5",
    "releaseDate":"2026-10-28",
    "installer":"manual",
}]

pack_bytes=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
history_bytes=(json.dumps(history,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
files={
    ".sgp/pack.json":pack_bytes,
    ".sgp/history.json":history_bytes,
    NEW_ADDON_TARGET:addon,
}

fixed=(2026,10,28,16,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in files.items():
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    assert OLD_ADDON not in z.namelist()
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    assert not any(n.startswith("world/") for n in z.namelist())
    assert not any(n.startswith("config/") for n in z.namelist())
    assert sha_bytes(z.read(NEW_ADDON_TARGET))==NEW_ADDON_SHA
    rp=json.loads(z.read(".sgp/pack.json"))
    rh=json.loads(z.read(".sgp/history.json"))
    assert rp["version"]=="2.0.5"
    assert rh["currentVersion"]=="2.0.5"
    assert [e["version"] for e in rh["entries"]]==[
        "1.0.0","1.2.0","1.2.1","2.0.0","2.0.1","2.0.2","2.0.4","2.0.5"
    ]

pathlib.Path("server205_sha.txt").write_text(sha_file(OUT)+"\n")
pathlib.Path("server205_size.txt").write_text(str(OUT.stat().st_size)+"\n")
pathlib.Path("server205_pack_sha.txt").write_text(sha_bytes(pack_bytes)+"\n")
pathlib.Path("server205_pack_size.txt").write_text(str(len(pack_bytes))+"\n")
pathlib.Path("server205_history_sha.txt").write_text(sha_bytes(history_bytes)+"\n")
pathlib.Path("server205_history_size.txt").write_text(str(len(history_bytes))+"\n")
pathlib.Path("server205_delete.txt").write_text(OLD_ADDON+"\n")

print("SERVER_205_BASE_204_AUDIT_PASS")
print("SERVER_205_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+sha_file(OUT))
print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+sha_bytes(pack_bytes))
print("PACK_SIZE="+str(len(pack_bytes)))
print("HISTORY_SHA="+sha_bytes(history_bytes))
print("HISTORY_SIZE="+str(len(history_bytes)))
print("ADDON_SHA="+NEW_ADDON_SHA)
print("ADDON_SIZE="+str(NEW_ADDON_SIZE))
print("DELETE_BEFORE_COPY="+OLD_ADDON)
