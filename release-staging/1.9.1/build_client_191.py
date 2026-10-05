import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.2.zip"
MOD=ROOT/"SGP-Shapeless-Nether-Portals-1.1.3.jar"
OUT=ROOT/"SGP_ClientPatch_1.9.1.zip"
WORK=ROOT/".work-191-stable"
BUILD=WORK/"build"

BASE_SHA="d98e8a24eb297e6caea115e5e758d34c9237c0b7c294c0a804ac08282a2f83cd"
OLD_MODS=[
 "mods/SGP-Shapeless-Nether-Portals-1.0.0.jar",
 "mods/SGP-Shapeless-Nether-Portals-1.1.0.jar",
 "mods/SGP-Shapeless-Nether-Portals-1.1.1.jar",
 "mods/SGP-Shapeless-Nether-Portals-1.1.2.jar",
]
MOD_TARGET="mods/SGP-Shapeless-Nether-Portals-1.1.3.jar"
MOD_SOURCE="files/"+MOD_TARGET
ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2"
]
FORWARD=["1.9.0","1.9.1-test.1","1.9.1-test.2","1.9.1-test.3"]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert MOD.is_file()
mod_sha=shaf(MOD); mod_size=MOD.stat().st_size

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.2" and p["toVersion"]=="1.8.2"
for v in ACCEPTED[:-1]: assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"] and "1.8.2" not in p["fromVersions"]
before=hashes(BUILD)

payload=BUILD/MOD_SOURCE
payload.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(MOD,payload)

p["patchId"]="sgp-client-1.9.1"
p["name"]="SGP Client 1.9.1"
p["toVersion"]="1.9.1"
p["fromVersions"]=list(p["fromVersions"])+["1.8.2"]+FORWARD
for v in ACCEPTED+FORWARD: assert v in p["fromVersions"],v
assert p["fromVersions"][-4:]==FORWARD and "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "SGP Shapeless Nether Portals 1.1.3.",
 "Arbitrary enclosed vertical Nether portal shapes remain supported.",
 "SGP no longer adds crying obsidian or BetterNether obsidian variants as portal-frame materials; intended SGP frame material is normal obsidian.",
 "Only the exact vanilla zombified-piglin EntityType.spawn call inside NetherPortalBlock.randomTick is suppressed.",
 "Forward repair removes portal mod 1.0.0, 1.1.0, 1.1.1 and failed 1.1.2 before installing 1.1.3."
]
for old in OLD_MODS:
    ver=old.split("-")[-1].replace(".jar","")
    # explicit stable IDs below avoid deriving ambiguous dotted version pieces
ids_targets=[
 ("remove-sgp-shapeless-nether-portals-1-0-0",OLD_MODS[0]),
 ("remove-sgp-shapeless-nether-portals-1-1-0",OLD_MODS[1]),
 ("remove-sgp-shapeless-nether-portals-1-1-1",OLD_MODS[2]),
 ("remove-sgp-shapeless-nether-portals-1-1-2",OLD_MODS[3]),
]
for aid,target in ids_targets:
    p["actions"].append({"actionId":aid,"type":"delete","description":"Удалить superseded/failed SGP Shapeless Nether Portals, если он установлен","target":target,"optional":True})
p["actions"].append({
 "actionId":"install-sgp-shapeless-nether-portals-1-1-3","type":"copy",
 "description":"Установить SGP Shapeless Nether Portals 1.1.3",
 "source":MOD_SOURCE,"target":MOD_TARGET,"sha256":mod_sha,"size":mod_size
})
ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
for old in OLD_MODS:
    assert sum(a.get("type")=="delete" and a.get("target")==old and a.get("optional") is True for a in p["actions"])==1
for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]; assert f.is_file() and f.stat().st_size==a["size"] and shaf(f).lower()==a["sha256"].lower()

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.9.1\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "SGP Shapeless Nether Portals 1.1.3\n"
 "- Arbitrary enclosed vertical portal shapes (circles/arches/irregular outlines).\n"
 "- SGP crying-obsidian and BetterNether frame additions were removed.\n"
 "- Intended SGP frame material: normal obsidian.\n"
 "- Only the vanilla portal-generated zombified-piglin spawn call is suppressed.\n"
 "- Vanilla portal blocks, travel and linking remain in use.\n"
 "- Forward repair from retired 1.9.0 and failed/superseded 1.9.1 tests is supported.\n","utf-8")

after=hashes(BUILD)
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed=={"patch.json","README.txt",MOD_SOURCE},changed

fixed=(2026,10,6,4,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.9.1" and q["toVersion"]=="1.9.1"
    for v in ACCEPTED+FORWARD: assert v in q["fromVersions"],v
    for old in OLD_MODS:
        assert any(x.get("type")=="delete" and x.get("target")==old and x.get("optional") is True for x in q["actions"])
        assert "files/"+old not in z.namelist()
    a=[x for x in q["actions"] if x.get("target")==MOD_TARGET]; assert len(a)==1
    b=z.read(a[0]["source"]); assert hashlib.sha256(b).hexdigest()==mod_sha and len(b)==mod_size

Path("portal_mod_sha.txt").write_text(mod_sha+"\n","utf-8")
Path("portal_mod_size.txt").write_text(str(mod_size)+"\n","utf-8")
print("CLIENT_191_STABLE_CUMULATIVE_AUDIT_PASS")
print("MOD_SHA="+mod_sha); print("MOD_SIZE="+str(mod_size))
print("FINAL_SHA="+shaf(OUT)); print("FINAL_SIZE="+str(OUT.stat().st_size))
