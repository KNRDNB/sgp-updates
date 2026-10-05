import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.2.zip"
MOD=ROOT/"SGP-Shapeless-Nether-Portals-1.1.2.jar"
OUT=ROOT/"SGP_ClientPatch_1.9.1-test.3.zip"
WORK=ROOT/".work-191-test3"
BUILD=WORK/"build"

BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"
OLD_MOD_100="mods/SGP-Shapeless-Nether-Portals-1.0.0.jar"
OLD_MOD_110="mods/SGP-Shapeless-Nether-Portals-1.1.0.jar"
OLD_MOD_111="mods/SGP-Shapeless-Nether-Portals-1.1.1.jar"
MOD_TARGET="mods/SGP-Shapeless-Nether-Portals-1.1.2.jar"
MOD_SOURCE="files/"+MOD_TARGET

ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3",
 "1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3",
 "1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2",
 "1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"
]

def shaf(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def hashes(root):
    return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file()
mod_sha=shaf(MOD)
mod_size=MOD.stat().st_size

if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.2"
assert p["toVersion"]=="1.8.2"
for v in ACCEPTED[:-1]:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]
assert "1.8.2" not in p["fromVersions"]

before=hashes(BUILD)

payload=BUILD/MOD_SOURCE
payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,payload)

p["patchId"]="sgp-client-1.9.1-test.3"
p["name"]="SGP Client 1.9.1-test.3"
p["toVersion"]="1.9.1-test.3"
p["fromVersions"]=list(p["fromVersions"])+["1.8.2","1.9.0","1.9.1-test.1","1.9.1-test.2"]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert p["fromVersions"][-3:]==["1.9.0","1.9.1-test.1","1.9.1-test.2"]
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "TEST.3: SGP Shapeless Nether Portals 1.1.2.",
 "Arbitrary enclosed vertical Nether portal shapes are supported.",
 "Regular obsidian and crying obsidian are both valid frame materials, including mixed frames and the ignition path.",
 "Only the exact vanilla zombified-piglin EntityType.spawn call inside NetherPortalBlock.randomTick is suppressed; the rest of randomTick remains available to other mod injections.",
 "Forward repair removes retired portal mod 1.0.0 and superseded TEST mod 1.1.0 before installing 1.1.1."
]

p["actions"] += [
  {
    "actionId":"remove-sgp-shapeless-nether-portals-1-0-0",
    "type":"delete",
    "description":"Удалить retired SGP Shapeless Nether Portals 1.0.0, если он установлен",
    "target":OLD_MOD_100,
    "optional":True
  },
  {
    "actionId":"remove-sgp-shapeless-nether-portals-1-1-0",
    "type":"delete",
    "description":"Удалить superseded SGP Shapeless Nether Portals 1.1.0, если он установлен",
    "target":OLD_MOD_110,
    "optional":True
  },
  {
    "actionId":"install-sgp-shapeless-nether-portals-1-1-1",
    "type":"copy",
    "description":"Установить SGP Shapeless Nether Portals 1.1.1",
    "source":MOD_SOURCE,
    "target":MOD_TARGET,
    "sha256":mod_sha,
    "size":mod_size
  }
]

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
assert sum(a.get("actionId")=="remove-sgp-shapeless-nether-portals-1-0-0" for a in p["actions"])==1
assert sum(a.get("actionId")=="remove-sgp-shapeless-nether-portals-1-1-0" for a in p["actions"])==1
assert sum(a.get("actionId")=="install-sgp-shapeless-nether-portals-1-1-1" for a in p["actions"])==1

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.9.1-test.3\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "TEST.3: SGP Shapeless Nether Portals 1.1.2\n"
 "- Arbitrary enclosed vertical portal shapes (circles/arches/irregular outlines).\n"
 "- One shared portal-frame rule is used by ignition and arbitrary-shape scanning.\n"
 "- minecraft:crying_obsidian is added to c:nether_pframe.\n"
 "- BetterNether weeping_obsidian, blue_crying_obsidian and blue_weeping_obsidian are added as optional tag entries.\n"
 "- Only the vanilla zombified-piglin spawn call from portal randomTick is suppressed.\n"
 "- Vanilla portal blocks, travel and linking remain in use.\n"
 "- Forward repair from retired 1.9.0, test.1 and failed test.2 is supported.\n",
 "utf-8"
)

after=hashes(BUILD)
allowed={"patch.json","README.txt",MOD_SOURCE}
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed==allowed,changed

fixed=(2026,10,6,3,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.9.1-test.3"
    assert q["toVersion"]=="1.9.1-test.3"
    for v in ACCEPTED:
        assert v in q["fromVersions"],v
    assert q["fromVersions"][-3:]==["1.9.0","1.9.1-test.1","1.9.1-test.2"]
    assert "1.5.4" not in q["fromVersions"]
    assert any(x.get("type")=="delete" and x.get("target")==OLD_MOD_100 and x.get("optional") is True for x in q["actions"])
    assert any(x.get("type")=="delete" and x.get("target")==OLD_MOD_110 and x.get("optional") is True for x in q["actions"])
    assert any(x.get("type")=="delete" and x.get("target")==OLD_MOD_111 and x.get("optional") is True for x in q["actions"])
    a=[x for x in q["actions"] if x.get("target")==MOD_TARGET]
    assert len(a)==1
    b=z.read(a[0]["source"])
    assert hashlib.sha256(b).hexdigest()==mod_sha
    assert len(b)==mod_size
    assert "files/mods/SGP-Shapeless-Nether-Portals-1.0.0.jar" not in z.namelist()
    assert "files/mods/SGP-Shapeless-Nether-Portals-1.1.0.jar" not in z.namelist()
    assert "files/mods/SGP-Shapeless-Nether-Portals-1.1.1.jar" not in z.namelist()

Path("portal_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("portal_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")
print("CLIENT_191_TEST3_CUMULATIVE_AUDIT_PASS")
print("MOD_SHA="+mod_sha)
print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
