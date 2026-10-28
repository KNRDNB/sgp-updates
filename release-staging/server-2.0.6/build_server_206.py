from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ServerPatch_2.0.6.zip"
BASE_DIR=ROOT/".server-206-base"
CLIENT_DIR=ROOT/".server-206-client"
BASE_SERVER=BASE_DIR/"SGP_ServerPatch_2.0.5.zip"
CLIENT_ZIP=CLIENT_DIR/"SGP_ClientPatch_2.0.6.zip"

BASE_RUN="40719262243"
BASE_ARTIFACT="sgp-server-2.0.5-handoff"
BASE_SHA="ad7ec12554db1dd33a5066b5ce535bacbcd500ca89a6e11d16768e92b343872b"
BASE_SIZE=12242

CLIENT_TAG="client-v2.0.6"
CLIENT_SHA="3d52f8c9d2192098b90d724ab9a3f69f084f511d65edb35db8a363bb6f629040"
CLIENT_SIZE=13789

OLD_ADDON="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
NEW_SOURCE="files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"
NEW_TARGET="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"
NEW_SHA="537f31e8a3c3904681fa6e089087514117e372d63a3361a30ee1675cc594eaea"
NEW_SIZE=13475

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

BASE_DIR.mkdir(exist_ok=True); CLIENT_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","run","download",BASE_RUN,"--repo","KNRDNB/sgp-updates","--name",BASE_ARTIFACT,"--dir",str(BASE_DIR)],check=True)
if not BASE_SERVER.is_file():
    c=list(BASE_DIR.rglob("SGP_ServerPatch_2.0.5.zip")); assert len(c)==1,c; BASE_SERVER=c[0]
assert BASE_SERVER.stat().st_size==BASE_SIZE and sha_file(BASE_SERVER)==BASE_SHA
with zipfile.ZipFile(BASE_SERVER) as z:
    assert z.testzip() is None
    base_pack=json.loads(z.read(".sgp/pack.json"))
    base_hist=json.loads(z.read(".sgp/history.json"))
    assert base_pack["version"]=="2.0.5"
    assert base_hist["currentVersion"]=="2.0.5"
    assert OLD_ADDON in z.namelist()

subprocess.run(["gh","release","download",CLIENT_TAG,"--repo","KNRDNB/sgp-updates","--pattern",CLIENT_ZIP.name,"--dir",str(CLIENT_DIR)],check=True)
assert CLIENT_ZIP.stat().st_size==CLIENT_SIZE and sha_file(CLIENT_ZIP)==CLIENT_SHA
with zipfile.ZipFile(CLIENT_ZIP) as z:
    assert z.testzip() is None
    cp=json.loads(z.read("patch.json"))
    assert cp["fromVersions"]==["2.0.4","2.0.5"] and cp["toVersion"]=="2.0.6"
    addon=z.read(NEW_SOURCE)
assert len(addon)==NEW_SIZE and sha_bytes(addon)==NEW_SHA

pack=dict(base_pack)
pack["version"]="2.0.6"; pack["baseline"]=False
pack["lastUpdate"]={"id":"sgp-server-2.0.6","type":"release","version":"2.0.6","releaseDate":"2026-10-28"}
hist=dict(base_hist)
hist["currentVersion"]="2.0.6"
hist["entries"]=list(base_hist["entries"])+[{"id":"sgp-server-2.0.6","type":"release","version":"2.0.6","releaseDate":"2026-10-28","installer":"manual"}]

pack_b=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode()
hist_b=(json.dumps(hist,ensure_ascii=False,indent=2)+"\n").encode()
files={".sgp/pack.json":pack_b,".sgp/history.json":hist_b,NEW_TARGET:addon}
fixed=(2026,10,28,19,20,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in files.items():
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    assert OLD_ADDON not in z.namelist()
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    assert not any(n.startswith("world/") or n.startswith("config/") for n in z.namelist())
    assert sha_bytes(z.read(NEW_TARGET))==NEW_SHA
    rp=json.loads(z.read(".sgp/pack.json")); rh=json.loads(z.read(".sgp/history.json"))
    assert rp["version"]=="2.0.6" and rh["currentVersion"]=="2.0.6"
    assert [e["version"] for e in rh["entries"]][-2:]==["2.0.5","2.0.6"]

for name,val in [
 ("server206_sha.txt",sha_file(OUT)),("server206_size.txt",str(OUT.stat().st_size)),
 ("server206_pack_sha.txt",sha_bytes(pack_b)),("server206_pack_size.txt",str(len(pack_b))),
 ("server206_history_sha.txt",sha_bytes(hist_b)),("server206_history_size.txt",str(len(hist_b))),
 ("server206_delete.txt",OLD_ADDON)]:
    pathlib.Path(name).write_text(val+"\n")
print("SERVER_206_BASE_205_AUDIT_PASS")
print("SERVER_206_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+sha_file(OUT)); print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+sha_bytes(pack_b)); print("PACK_SIZE="+str(len(pack_b)))
print("HISTORY_SHA="+sha_bytes(hist_b)); print("HISTORY_SIZE="+str(len(hist_b)))
print("ADDON_SHA="+NEW_SHA); print("ADDON_SIZE="+str(NEW_SIZE))
print("DELETE_BEFORE_COPY="+OLD_ADDON)
