import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.0.zip"
MOD=ROOT/"SGP-Create-Chipped-Cutting-1.0.0.jar"
OUT=ROOT/"SGP_ClientPatch_1.8.1-test.1.zip"
WORK=ROOT/".work-181-test1"
BUILD=WORK/"build"

BASE_SHA="34c6f2b223892b92a1c6f1da0074802de474cfe4116fcd5c90e3d869081ef9bb"
OLD_DP_TARGET="config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip"
OLD_DP_SOURCE="files/"+OLD_DP_TARGET
MOD_TARGET="mods/SGP-Create-Chipped-Cutting-1.0.0.jar"
MOD_SOURCE="files/"+MOD_TARGET

def shaf(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def shab(b):
    return hashlib.sha256(b).hexdigest()

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file()
mod_sha=shaf(MOD)
mod_size=MOD.stat().st_size

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

mp=BUILD/"patch.json"
p=json.loads(mp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.0"
assert p["toVersion"]=="1.8.0"
assert "1.7.1" in p["fromVersions"]
assert p["fromVersions"][-1]=="1.8.0-test.1"

old_actions=list(p["actions"])
old_dp=[a for a in old_actions if a.get("actionId")=="install-sgp-create-chipped-cutting"]
assert len(old_dp)==1
new_actions=[a for a in old_actions if a.get("actionId")!="install-sgp-create-chipped-cutting"]

old_payload=BUILD/OLD_DP_SOURCE
assert old_payload.is_file()
old_payload.unlink()

mod_payload=BUILD/MOD_SOURCE
mod_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,mod_payload)

new_actions += [
  {
    "actionId":"remove-sgp-create-chipped-cutting-datapack",
    "type":"delete",
    "description":"Удалить recipe-heavy SGP Create × Chipped datapack 1.8.0",
    "target":OLD_DP_TARGET,
    "optional":True
  },
  {
    "actionId":"install-sgp-create-chipped-cutting-runtime-1-0-0",
    "type":"copy",
    "description":"Установить runtime-efficient SGP Create × Chipped Cutting 1.0.0",
    "source":MOD_SOURCE,
    "target":MOD_TARGET,
    "sha256":mod_sha,
    "size":mod_size
  }
]

p["patchId"]="sgp-client-1.8.1-test.1"
p["name"]="SGP Client 1.8.1-test.1"
p["toVersion"]="1.8.1-test.1"
p["fromVersions"]=list(p["fromVersions"])+["1.8.0"]
p["summary"]=[
  "HOTFIX TEST: remove the 6,968 registered Create Mechanical Saw recipes introduced in 1.8.0.",
  "Replace the recipe-heavy datapack with SGP Create Chipped Cutting runtime bridge 1.0.0.",
  "The bridge derives Chipped family outputs dynamically from the same 277 Chipped 4.0.2 item tags only for the current saw input.",
  "Mechanical Saw filter semantics and 50-tick processing are preserved; no MineColonies, simulation-distance, JVM or unrelated server config changes."
]
p["actions"]=new_actions

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
assert "1.8.0" in p["fromVersions"]
assert "1.5.4" not in p["fromVersions"]
assert not any(a.get("actionId")=="install-sgp-create-chipped-cutting" for a in p["actions"])
assert sum(a.get("actionId")=="remove-sgp-create-chipped-cutting-datapack" for a in p["actions"])==1
assert sum(a.get("actionId")=="install-sgp-create-chipped-cutting-runtime-1-0-0" for a in p["actions"])==1

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(), a["source"]
        assert f.stat().st_size==a["size"], a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(), a["actionId"]

mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
  "SGP Client 1.8.1-test.1\n"
  "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
  "Performance hotfix TEST for Create x Chipped Mechanical Saw integration.\n"
  "- Removes the 6,968-recipe datapack from 1.8.0.\n"
  "- Installs SGP-Create-Chipped-Cutting-1.0.0.jar dynamic bridge.\n"
  "- Same 277 Chipped 4.0.2 family tags, same selectable filtered outputs, same 50-tick processing.\n"
  "- Does not alter MineColonies, simulation distance, JVM flags or unrelated configs.\n",
  "utf-8"
)

fixed=(2026,10,5,14,30,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    assert OLD_DP_SOURCE not in names
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.8.1-test.1"
    assert q["toVersion"]=="1.8.1-test.1"
    assert q["fromVersions"][-1]=="1.8.0"
    assert not any(a.get("actionId")=="install-sgp-create-chipped-cutting" for a in q["actions"])
    m=z.read(MOD_SOURCE)
    assert len(m)==mod_size and shab(m)==mod_sha

Path("hotfix_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("hotfix_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")
print("CLIENT_181_TEST1_STATIC_AUDIT_PASS")
print("MOD_SHA="+mod_sha)
print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
