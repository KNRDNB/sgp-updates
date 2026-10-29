from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile, io

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ServerPatch_2.0.8.zip"
BASE_DIR=ROOT/".server-208-base"
CLIENT_DIR=ROOT/".server-208-client"
BASE_SERVER=BASE_DIR/"SGP_ServerPatch_2.0.7.zip"
CLIENT_ZIP=CLIENT_DIR/"SGP_ClientPatch_2.0.8.zip"

BASE_RUN="40728936834"
BASE_ARTIFACT="sgp-server-2.0.7-handoff"
BASE_SHA="83317a3e02de9157adb80f1658dd929e433d92c1f7b575a4ea36d766580a2650"
BASE_SIZE=15004

CLIENT_TAG="client-v2.0.8"
CLIENT_SHA="e852c7ccda9ceb754624ac670a1f3f9bc463ef327804d4f8c73e828ffa995fff"
CLIENT_SIZE=62734
FIX_SOURCE="files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
FIX_SHA="88c70d736e0393202975c09db6a975c37c9137715f15a4081560b384f6d4cb8f"
FIX_SIZE=138191

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

BASE_DIR.mkdir(exist_ok=True); CLIENT_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","run","download",BASE_RUN,"--repo","KNRDNB/sgp-updates","--name",BASE_ARTIFACT,"--dir",str(BASE_DIR)],check=True)
if not BASE_SERVER.is_file():
    c=list(BASE_DIR.rglob("SGP_ServerPatch_2.0.7.zip")); assert len(c)==1,c; BASE_SERVER=c[0]
assert BASE_SERVER.stat().st_size==BASE_SIZE and sha_file(BASE_SERVER)==BASE_SHA
with zipfile.ZipFile(BASE_SERVER) as z:
    assert z.testzip() is None
    base_pack=json.loads(z.read(".sgp/pack.json"))
    base_hist=json.loads(z.read(".sgp/history.json"))
    assert base_pack["version"]=="2.0.7"
    assert base_hist["currentVersion"]=="2.0.7"

subprocess.run(["gh","release","download",CLIENT_TAG,"--repo","KNRDNB/sgp-updates","--pattern",CLIENT_ZIP.name,"--dir",str(CLIENT_DIR)],check=True)
assert CLIENT_ZIP.stat().st_size==CLIENT_SIZE and sha_file(CLIENT_ZIP)==CLIENT_SHA
with zipfile.ZipFile(CLIENT_ZIP) as z:
    assert z.testzip() is None
    cp=json.loads(z.read("patch.json"))
    assert cp["fromVersions"]==["2.0.7"] and cp["toVersion"]=="2.0.8"
    assert len(cp["actions"])==1 and cp["actions"][0]["target"]==FIX_TARGET
    fix=z.read(FIX_SOURCE)
assert len(fix)==FIX_SIZE and sha_bytes(fix)==FIX_SHA
with zipfile.ZipFile(io.BytesIO(fix)) as fz:
    assert fz.testzip() is None
    assert json.loads(fz.read("data/ftbultimine/tags/item/included_tools.json"))=={"replace":False,"values":["minecraft:shears"]}
    assert json.loads(fz.read("pack.mcmeta"))["pack"]["description"].endswith("internal rev 1.16")

pack=dict(base_pack)
pack["version"]="2.0.8"; pack["baseline"]=False
pack["lastUpdate"]={"id":"sgp-server-2.0.8","type":"release","version":"2.0.8","releaseDate":"2026-10-29"}
hist=dict(base_hist)
hist["currentVersion"]="2.0.8"
hist["entries"]=list(base_hist["entries"])+[{"id":"sgp-server-2.0.8","type":"release","version":"2.0.8","releaseDate":"2026-10-29","installer":"manual"}]

pack_b=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
hist_b=(json.dumps(hist,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
files={".sgp/pack.json":pack_b,".sgp/history.json":hist_b,FIX_TARGET:fix}
fixed=(2026,10,29,16,35,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in files.items():
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)
    assert not any(n.startswith("mods/") for n in z.namelist())
    assert not any("protected_chunks.properties" in n for n in z.namelist())
    assert not any(n.startswith("world/") for n in z.namelist())
    assert sha_bytes(z.read(FIX_TARGET))==FIX_SHA
    rp=json.loads(z.read(".sgp/pack.json")); rh=json.loads(z.read(".sgp/history.json"))
    assert rp["version"]=="2.0.8" and rh["currentVersion"]=="2.0.8"
    assert [e["version"] for e in rh["entries"]][-2:]==["2.0.7","2.0.8"]

for name,val in [
 ("server208_sha.txt",sha_file(OUT)),("server208_size.txt",str(OUT.stat().st_size)),
 ("server208_pack_sha.txt",sha_bytes(pack_b)),("server208_pack_size.txt",str(len(pack_b))),
 ("server208_history_sha.txt",sha_bytes(hist_b)),("server208_history_size.txt",str(len(hist_b))),
 ("server208_fixes_sha.txt",FIX_SHA),("server208_fixes_size.txt",str(FIX_SIZE))
]:
    pathlib.Path(name).write_text(val+"\n")
print("SERVER_208_BASE_207_AUDIT_PASS")
print("SERVER_208_EXACT_OVERLAY_AUDIT_PASS")
print("SERVER_SHA="+sha_file(OUT)); print("SERVER_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+sha_bytes(pack_b)); print("PACK_SIZE="+str(len(pack_b)))
print("HISTORY_SHA="+sha_bytes(hist_b)); print("HISTORY_SIZE="+str(len(hist_b)))
print("FIX_SHA="+FIX_SHA); print("FIX_SIZE="+str(FIX_SIZE))
