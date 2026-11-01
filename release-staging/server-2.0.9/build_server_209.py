from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ServerPatch_2.0.9.zip"
BASE_DIR=ROOT/".server-209-base"
CLIENT_DIR=ROOT/".server-209-client"
BASE_SERVER=BASE_DIR/"SGP_ServerPatch_2.0.8.zip"
CLIENT_ZIP=CLIENT_DIR/"SGP_ClientPatch_2.0.9.zip"

BASE_RUN="40855766218"
BASE_ARTIFACT="sgp-server-2.0.8-handoff"
BASE_SHA="c1072e14b291f804ea8eb060d673083e76616e0d2bb86c94c76d0e88ff2dcd67"
BASE_SIZE=62125

CLIENT_TAG="client-v2.0.9"
CLIENT_SHA="d25a4c69eba6fbf1babb5b38c735bc42b23aa15ccca3096faede9478ebc1dda0"
CLIENT_SIZE=5014670

OLD_RU="mods/regions-unexplored-0.6.2-neoforge-21.1.jar"
NEW_SOURCE="files/mods/regions-unexplored-0.6.3-neoforge-21.1.jar"
NEW_TARGET="mods/regions-unexplored-0.6.3-neoforge-21.1.jar"
NEW_SHA="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"
NEW_SIZE=6641783

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

BASE_DIR.mkdir(exist_ok=True); CLIENT_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","run","download",BASE_RUN,"--repo","KNRDNB/sgp-updates","--name",BASE_ARTIFACT,"--dir",str(BASE_DIR)],check=True)
if not BASE_SERVER.is_file():
    c=list(BASE_DIR.rglob("SGP_ServerPatch_2.0.8.zip")); assert len(c)==1,c; BASE_SERVER=c[0]
assert BASE_SERVER.stat().st_size==BASE_SIZE and sha_file(BASE_SERVER)==BASE_SHA
with zipfile.ZipFile(BASE_SERVER) as z:
    assert z.testzip() is None
    base_pack=json.loads(z.read(".sgp/pack.json"))
    base_hist=json.loads(z.read(".sgp/history.json"))
    assert base_pack["version"]=="2.0.8"
    assert base_hist["currentVersion"]=="2.0.8"

subprocess.run(["gh","release","download",CLIENT_TAG,"--repo","KNRDNB/sgp-updates","--pattern",CLIENT_ZIP.name,"--dir",str(CLIENT_DIR)],check=True)
assert CLIENT_ZIP.stat().st_size==CLIENT_SIZE and sha_file(CLIENT_ZIP)==CLIENT_SHA
with zipfile.ZipFile(CLIENT_ZIP) as z:
    assert z.testzip() is None
    cp=json.loads(z.read("patch.json"))
    assert cp["fromVersions"]==["2.0.8"] and cp["toVersion"]=="2.0.9"
    assert [a["type"] for a in cp["actions"]]==["delete","copy"]
    assert cp["actions"][0]["target"]==OLD_RU
    assert cp["actions"][1]["target"]==NEW_TARGET
    ru=z.read(NEW_SOURCE)

assert len(ru)==NEW_SIZE and sha_bytes(ru)==NEW_SHA
with zipfile.ZipFile(pathlib.Path(CLIENT_DIR/CLIENT_ZIP.name)) as z:
    pass

pack=dict(base_pack)
pack["version"]="2.0.9"; pack["baseline"]=False
pack["lastUpdate"]={"id":"sgp-server-2.0.9","type":"release","version":"2.0.9","releaseDate":"2026-11-01"}
hist=dict(base_hist)
hist["currentVersion"]="2.0.9"
hist["entries"]=list(base_hist["entries"])+[{"id":"sgp-server-2.0.9","type":"release","version":"2.0.9","releaseDate":"2026-11-01","installer":"manual"}]

pack_b=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
hist_b=(json.dumps(hist,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
files={".sgp/pack.json":pack_b,".sgp/history.json":hist_b,NEW_TARGET:ru}

fixed=(2026,11,1,11,5,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in files.items():
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    assert OLD_RU not in z.namelist()
    assert not any(n.startswith("world/") or n.startswith("config/") for n in z.namelist())
    assert sha_bytes(z.read(NEW_TARGET))==NEW_SHA
    rp=json.loads(z.read(".sgp/pack.json")); rh=json.loads(z.read(".sgp/history.json"))
    assert rp["version"]=="2.0.9" and rh["currentVersion"]=="2.0.9"
    assert [e["version"] for e in rh["entries"]][-2:]==["2.0.8","2.0.9"]

for name,val in [
 ("server209_sha.txt",sha_file(OUT)),("server209_size.txt",str(OUT.stat().st_size)),
 ("server209_pack_sha.txt",sha_bytes(pack_b)),("server209_pack_size.txt",str(len(pack_b))),
 ("server209_history_sha.txt",sha_bytes(hist_b)),("server209_history_size.txt",str(len(hist_b))),
 ("server209_ru_sha.txt",NEW_SHA),("server209_ru_size.txt",str(NEW_SIZE)),
 ("server209_delete.txt",OLD_RU)
]:
    pathlib.Path(name).write_text(val+"\n")

print("SERVER_209_BASE_208_AUDIT_PASS")
print("SERVER_209_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+sha_file(OUT)); print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+sha_bytes(pack_b)); print("PACK_SIZE="+str(len(pack_b)))
print("HISTORY_SHA="+sha_bytes(hist_b)); print("HISTORY_SIZE="+str(len(hist_b)))
print("RU_SHA="+NEW_SHA); print("RU_SIZE="+str(NEW_SIZE))
print("DELETE_BEFORE_COPY="+OLD_RU)
