import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.9.0.zip"
OUT=ROOT/"SGP_ClientPatch_1.9.0-test.1.zip"
WORK=ROOT/".work-190-test1"
BUILD=WORK/"build"

BASE_SHA="723f5b8c231bf0e25eb9e4c04026533e819b30040987b6553e15ea3b7385c605"
PORTAL_SHA="0572091fc8b7692ae33a6b1288090cf8034479ea3f60d2cbb951cfb0798b36e8"
PORTAL_TARGET="mods/SGP-Shapeless-Nether-Portals-1.0.0.jar"

def shaf(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def tree_hashes(root):
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*") if p.is_file()
    }

assert BASE.is_file() and shaf(BASE)==BASE_SHA

if WORK.exists():
    shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

before=tree_hashes(BUILD)
patch_path=BUILD/"patch.json"
patch=json.loads(patch_path.read_text("utf-8"))

assert patch["patchId"]=="sgp-client-1.9.0"
assert patch["toVersion"]=="1.9.0"
assert patch["fromVersions"][-1]=="1.8.2"
assert "1.5.4" not in patch["fromVersions"]

actions_before=json.dumps(patch["actions"],ensure_ascii=False,separators=(",",":"))
portal_actions=[
    a for a in patch["actions"]
    if a.get("type")=="copy" and a.get("target")==PORTAL_TARGET
]
assert len(portal_actions)==1
portal=BUILD/portal_actions[0]["source"]
assert portal.is_file()
assert shaf(portal)==PORTAL_SHA
assert portal_actions[0]["sha256"].lower()==PORTAL_SHA

patch["patchId"]="sgp-client-1.9.0-test.1"
patch["name"]="SGP Client 1.9.0-test.1"
patch["toVersion"]="1.9.0-test.1"
patch["summary"]=[
    "TEST: SGP Shapeless Nether Portals 1.0.0.",
    "This candidate uses the exact payload/action set previously published as withdrawn stable 1.9.0; only release identity/status changed.",
    "Build enclosed vertical obsidian Nether portal frames in arbitrary shapes (circles, arches, irregular closed outlines) and ignite normally.",
    "Portal runtime must pass owner Minecraft testing before stable 1.9.0 is republished."
]
assert json.dumps(patch["actions"],ensure_ascii=False,separators=(",",":"))==actions_before

patch_path.write_text(json.dumps(patch,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
    "SGP Client 1.9.0-test.1\n"
    "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
    "Runtime TEST for SGP Shapeless Nether Portals 1.0.0.\n"
    "Payload/action set is byte-identical to withdrawn stable 1.9.0.\n"
    "Test round/irregular enclosed vertical obsidian portals, ignition, travel, return linking and persistence after restart.\n",
    "utf-8"
)

after=tree_hashes(BUILD)
changed=sorted(
    k for k in set(before)|set(after)
    if before.get(k)!=after.get(k)
)
assert set(changed)=={"patch.json","README.txt"},changed

for a in patch["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

fixed=(2026,10,6,2,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(p for p in BUILD.rglob("*") if p.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-1.9.0-test.1"
    assert q["toVersion"]=="1.9.0-test.1"
    assert q["fromVersions"][-1]=="1.8.2"
    assert json.dumps(q["actions"],ensure_ascii=False,separators=(",",":"))==actions_before
    pa=next(a for a in q["actions"] if a.get("target")==PORTAL_TARGET)
    assert hashlib.sha256(z.read(pa["source"])).hexdigest()==PORTAL_SHA

print("CLIENT_190_TEST1_EXACT_RECLASSIFY_AUDIT_PASS")
print("PORTAL_SHA="+PORTAL_SHA)
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
