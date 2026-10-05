import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.1-test.1.zip"
MOD=ROOT/"SGP-Create-Chipped-Cutting-1.0.1.jar"
OUT=ROOT/"SGP_ClientPatch_1.8.1-test.2.zip"
WORK=ROOT/".work-181-test2"
BUILD=WORK/"build"

BASE_SHA="10cdfdcec2c34815cce6f6dc7293d5b52a2b6609a5c16b3ae0973f759d560952"
OLD_DP_TARGET="config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip"
OLD_MOD_TARGET="mods/SGP-Create-Chipped-Cutting-1.0.0.jar"
OLD_MOD_SOURCE="files/"+OLD_MOD_TARGET
MOD_TARGET="mods/SGP-Create-Chipped-Cutting-1.0.1.jar"
MOD_SOURCE="files/"+MOD_TARGET
ACCEPTED=["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0"]

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
assert p["patchId"]=="sgp-client-1.8.1-test.1"
assert p["toVersion"]=="1.8.1-test.1"
for v in ACCEPTED:
    assert v in p["fromVersions"], v
assert p["fromVersions"][-1]=="1.8.0"
assert "1.5.4" not in p["fromVersions"]

old_actions=list(p["actions"])
assert sum(a.get("actionId")=="install-sgp-create-chipped-cutting-runtime-1-0-0" for a in old_actions)==1
assert sum(a.get("actionId")=="remove-sgp-create-chipped-cutting-datapack" for a in old_actions)==1
new_actions=[a for a in old_actions if a.get("actionId")!="install-sgp-create-chipped-cutting-runtime-1-0-0"]

old_payload=BUILD/OLD_MOD_SOURCE
assert old_payload.is_file()
old_payload.unlink()

mod_payload=BUILD/MOD_SOURCE
mod_payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,mod_payload)

new_actions += [
  {
    "actionId":"remove-sgp-create-chipped-cutting-runtime-1-0-0",
    "type":"delete",
    "description":"Удалить runtime bridge 1.0.0 без JEI synthetic recipes",
    "target":OLD_MOD_TARGET,
    "optional":True
  },
  {
    "actionId":"install-sgp-create-chipped-cutting-runtime-1-0-1",
    "type":"copy",
    "description":"Установить runtime-efficient Create × Chipped bridge 1.0.1 с JEI-only Saw recipes",
    "source":MOD_SOURCE,
    "target":MOD_TARGET,
    "sha256":mod_sha,
    "size":mod_size
  }
]

p["patchId"]="sgp-client-1.8.1-test.2"
p["name"]="SGP Client 1.8.1-test.2"
p["toVersion"]="1.8.1-test.2"
p["fromVersions"]=list(p["fromVersions"])+["1.8.1-test.1"]
p["summary"]=[
  "HOTFIX TEST.2: keep the server performance fix from test.1 and restore JEI visibility for Create × Chipped Saw conversions.",
  "The runtime bridge registers zero recipe JSONs; 6,968 synthetic recipes are exposed only to JEI on the client.",
  "The same 277 Chipped 4.0.2 family tags, Saw output-filter behavior and 50-tick processing are preserved.",
  "Cumulative direct update remains supported from every accepted stable SGP Client version through 1.8.0, plus forward repair from 1.8.1-test.1."
]
p["actions"]=new_actions

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
for v in ACCEPTED:
    assert v in p["fromVersions"], v
assert p["fromVersions"][-1]=="1.8.1-test.1"
assert "1.5.4" not in p["fromVersions"]
assert sum(a.get("actionId")=="remove-sgp-create-chipped-cutting-datapack" for a in p["actions"])==1
assert sum(a.get("actionId")=="remove-sgp-create-chipped-cutting-runtime-1-0-0" for a in p["actions"])==1
assert sum(a.get("actionId")=="install-sgp-create-chipped-cutting-runtime-1-0-1" for a in p["actions"])==1
assert not any(a.get("actionId")=="install-sgp-create-chipped-cutting-runtime-1-0-0" for a in p["actions"])

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.8.1-test.2\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Create x Chipped performance hotfix with JEI visibility.\n"
 "- Old 6,968-recipe datapack remains explicitly removed.\n"
 "- Runtime Saw bridge registers zero recipe JSONs.\n"
 "- JEI gets client-only synthetic Saw entries for all 6,968 family-to-output routes.\n"
 "- Cumulative from every accepted stable through 1.8.0; forward repair from 1.8.1-test.1.\n"
 "- No MineColonies, distance, JVM/GC or unrelated config changes.\n",
 "utf-8"
)

fixed=(2026,10,5,15,30,0)
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
    assert "files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip" not in names
    assert OLD_MOD_SOURCE not in names
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.8.1-test.2"
    assert q["toVersion"]=="1.8.1-test.2"
    for v in ACCEPTED:
        assert v in q["fromVersions"],v
    assert q["fromVersions"][-1]=="1.8.1-test.1"
    m=z.read(MOD_SOURCE)
    assert len(m)==mod_size and shab(m)==mod_sha

Path("hotfix_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("hotfix_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")
print("CLIENT_181_TEST2_CUMULATIVE_AUDIT_PASS")
print("MOD_SHA="+mod_sha)
print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
