from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ServerPatch_2.0.10.zip"
BASE_DIR=ROOT/".server-210-base"
CLIENT_DIR=ROOT/".server-210-client"
BASE_SERVER=BASE_DIR/"SGP_ServerPatch_2.0.9.zip"
CLIENT_ZIP=CLIENT_DIR/"SGP_ClientPatch_2.0.10.zip"

BASE_RUN="41297370384"
BASE_ARTIFACT="sgp-server-2.0.9-handoff"
BASE_SHA="26432e990dfcb7a7d84f05a45bd89b898f93b3fe29a2c33eae74f97bcedde79c"
BASE_SIZE=5013946

CLIENT_TAG="client-v2.0.10"
CLIENT_SHA="56ee83fb0f42a7b1bd0114c7a5c7c423a5f3351843e7f3e92056df9370efbe15"
CLIENT_SIZE=7958036

TARGETS={
 "mods/regions-unexplored-0.6.3-neoforge-21.1.jar":("files/mods/regions-unexplored-0.6.3-neoforge-21.1.jar","e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b",6641783),
 "mods/lithostitched-1.8.1-neoforge-21.1.jar":("files/mods/lithostitched-1.8.1-neoforge-21.1.jar","e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca",1023751),
 "mods/everycomp-1.21-2.11.55-neoforge.jar":("files/mods/everycomp-1.21-2.11.55-neoforge.jar","0a2bc786302bbea682b667815edacdf2a46506e0f3c2b033377f5ec2d0e08321",2657174),
}
DELETES=[
 "mods/regions-unexplored-0.6.2-neoforge-21.1.jar",
 "mods/lithostitched-1.8.0+beta6-neoforge-21.1.jar",
 "mods/everycomp-1.21-2.11.52-neoforge.jar",
]

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

BASE_DIR.mkdir(exist_ok=True); CLIENT_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","run","download",BASE_RUN,"--repo","KNRDNB/sgp-updates","--name",BASE_ARTIFACT,"--dir",str(BASE_DIR)],check=True)
if not BASE_SERVER.is_file():
    c=list(BASE_DIR.rglob("SGP_ServerPatch_2.0.9.zip")); assert len(c)==1,c; BASE_SERVER=c[0]
assert BASE_SERVER.stat().st_size==BASE_SIZE and sha_file(BASE_SERVER)==BASE_SHA
with zipfile.ZipFile(BASE_SERVER) as z:
    assert z.testzip() is None
    base_pack=json.loads(z.read(".sgp/pack.json"))
    base_hist=json.loads(z.read(".sgp/history.json"))
    assert base_pack["version"]=="2.0.9"
    assert base_hist["currentVersion"]=="2.0.9"

subprocess.run(["gh","release","download",CLIENT_TAG,"--repo","KNRDNB/sgp-updates","--pattern",CLIENT_ZIP.name,"--dir",str(CLIENT_DIR)],check=True)
assert CLIENT_ZIP.stat().st_size==CLIENT_SIZE and sha_file(CLIENT_ZIP)==CLIENT_SHA
with zipfile.ZipFile(CLIENT_ZIP) as z:
    assert z.testzip() is None
    cp=json.loads(z.read("patch.json"))
    assert cp["fromVersions"]==["2.0.8","2.0.9"] and cp["toVersion"]=="2.0.10"
    payload={}
    for target,(src,sha,size) in TARGETS.items():
        data=z.read(src)
        assert len(data)==size and sha_bytes(data)==sha
        payload[target]=data

pack=dict(base_pack)
pack["version"]="2.0.10"; pack["baseline"]=False
pack["lastUpdate"]={"id":"sgp-server-2.0.10","type":"release","version":"2.0.10","releaseDate":"2026-11-01"}
hist=dict(base_hist)
hist["currentVersion"]="2.0.10"
hist["entries"]=list(base_hist["entries"])+[{"id":"sgp-server-2.0.10","type":"release","version":"2.0.10","releaseDate":"2026-11-01","installer":"manual"}]

pack_b=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode()
hist_b=(json.dumps(hist,ensure_ascii=False,indent=2)+"\n").encode()
files={".sgp/pack.json":pack_b,".sgp/history.json":hist_b,**payload}

fixed=(2026,11,1,11,35,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in files.items():
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    assert not any(n.startswith("world/") or n.startswith("config/") or n.startswith("serverconfig/") for n in z.namelist())
    for d in DELETES: assert d not in z.namelist()
    rp=json.loads(z.read(".sgp/pack.json")); rh=json.loads(z.read(".sgp/history.json"))
    assert rp["version"]=="2.0.10" and rh["currentVersion"]=="2.0.10"
    assert [e["version"] for e in rh["entries"]][-2:]==["2.0.9","2.0.10"]
    for target,(src,sha,size) in TARGETS.items():
        data=z.read(target); assert len(data)==size and sha_bytes(data)==sha

for name,val in [
 ("server210_sha.txt",sha_file(OUT)),("server210_size.txt",str(OUT.stat().st_size)),
 ("server210_pack_sha.txt",sha_bytes(pack_b)),("server210_pack_size.txt",str(len(pack_b))),
 ("server210_history_sha.txt",sha_bytes(hist_b)),("server210_history_size.txt",str(len(hist_b))),
 ("server210_delete.txt","\\n".join(DELETES))
]:
 pathlib.Path(name).write_text(val+"\n")

print("SERVER_210_BASE_209_AUDIT_PASS")
print("SERVER_210_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+sha_file(OUT)); print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+sha_bytes(pack_b)); print("PACK_SIZE="+str(len(pack_b)))
print("HISTORY_SHA="+sha_bytes(hist_b)); print("HISTORY_SIZE="+str(len(hist_b)))
for d in DELETES: print("DELETE_BEFORE_COPY="+d)
