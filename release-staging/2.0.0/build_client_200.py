import copy, hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.10.0-test.4.zip"
OUT=ROOT/"SGP_ClientPatch_2.0.0.zip"
WORK=ROOT/".work-client-200"
BUILD=WORK/"build"

BASE_SHA="08cee43906d18ed02b588c826061d2ed535686606a87bcbbb3edd7349e4f8ef2"
ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2","1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]
TESTS=["1.10.0-test.1","1.10.0-test.2","1.10.0-test.3","1.10.0-test.4"]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.10.0-test.4"
assert p["toVersion"]=="1.10.0-test.4"
for v in ACCEPTED: assert v in p["fromVersions"],v
for v in TESTS[:-1]: assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

actions_before=copy.deepcopy(p["actions"])
payload_before={k:v for k,v in hashes(BUILD).items() if k.startswith("files/")}

# Owner-authorized correction of the first defective v2.0.0 bridge:
# Puzzles Lib 21.1.60 already exists in the accepted client baseline under
# a different versioned filename. Remove that exact old JAR before copying
# the tested 21.1.62 payload. Optional=true keeps this cumulative/idempotent
# for source states where the old JAR is already absent.
PUZ_OLD_TARGET="mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar"
PUZ_NEW_TARGET="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"
puz_index=next(i for i,a in enumerate(p["actions"]) if a.get("type")=="copy" and a.get("target")==PUZ_NEW_TARGET)
delete_action={
 "actionId":"remove-puzzleslib-21-1-60",
 "type":"delete",
 "description":"Удалить старый Puzzles Lib 21.1.60 перед установкой 21.1.62",
 "target":PUZ_OLD_TARGET,
 "optional":True
}
assert not any(a.get("actionId")==delete_action["actionId"] for a in p["actions"])
assert not any(a.get("target")==PUZ_OLD_TARGET for a in p["actions"])
p["actions"].insert(puz_index,delete_action)

# Owner-authorized emergency packaging correction:
# client baseline already contains Puzzles Lib 21.1.60 under a versioned filename,
# so stable 2.0.0 must explicitly remove it before installing 21.1.62.
OLD_PUZ_TARGET="mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar"
NEW_PUZ_TARGET="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"
old_delete={
 "actionId":"remove-old-puzzleslib-21-1-60",
 "type":"delete",
 "description":"Удалить старый Puzzles Lib 21.1.60 перед установкой 21.1.62",
 "target":OLD_PUZ_TARGET,
 "optional":True
}
assert not any(a.get("target")==OLD_PUZ_TARGET for a in p["actions"])
puz_i=next(i for i,a in enumerate(p["actions"]) if a.get("type")=="copy" and a.get("target")==NEW_PUZ_TARGET)
p["actions"].insert(puz_i,old_delete)

p["patchId"]="sgp-client-2.0.0"
p["name"]="SGP Client 2.0.0"
p["toVersion"]="2.0.0"
p["fromVersions"]=list(p["fromVersions"])+["1.10.0-test.4"]
for v in ACCEPTED+TESTS: assert v in p["fromVersions"],v
assert len(p["actions"])==len(actions_before)+1
assert [a for a in p["actions"] if a.get("actionId")=="remove-old-puzzleslib-21-1-60"]==[old_delete]
assert p["actions"].index(old_delete) < next(i for i,a in enumerate(p["actions"]) if a.get("type")=="copy" and a.get("target")==NEW_PUZ_TARGET)
assert "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "Stable 2.0.0 emergency packaging correction authorized by owner after live client evidence showed both Puzzles Lib 21.1.60 and 21.1.62 present.",
 "Delete exact old client JAR PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar if present, then install Puzzles Lib 21.1.62.",
 "All runtime-tested gameplay/config payload bytes from 1.10.0-test.4 remain unchanged.",
 "ArmorHUD right-side spacing remains -111 for leggings/boots/offhand/inventory icon.",
 "Permanent Sponges 21.1.0 + SGP Fixes rev 1.15 + RU Localization 1.10 remain exactly as tested.",
 "Existing Unbreakable Catalyst remains a baseline component and is not installed/replaced/deleted by this patch."
]
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 2.0.0\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Owner-authorized corrected stable 2.0.0.\n"
 "Live client evidence showed both Puzzles Lib 21.1.60 and 21.1.62.\n"
 "- Exact old JAR PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar is deleted if present.\n"
 "- Puzzles Lib 21.1.62 is then installed under its correct filename.\n"
 "- All gameplay/config payload bytes from runtime-PASS 1.10.0-test.4 are unchanged.\n"
 "- ArmorHUD, Permanent Sponges, Soulbound compatibility and RU localization remain unchanged.\n"
 "- Existing Unbreakable Catalyst remains untouched.\n",
 "utf-8"
)

payload_after={k:v for k,v in hashes(BUILD).items() if k.startswith("files/")}
assert payload_after==payload_before

fixed=(2026,10,6,20,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-2.0.0" and q["toVersion"]=="2.0.0"
    for v in ACCEPTED+TESTS: assert v in q["fromVersions"],v
    assert len(q["actions"])==len(actions_before)+1
    d=next(a for a in q["actions"] if a.get("actionId")=="remove-old-puzzleslib-21-1-60")
    assert d==old_delete
    di=q["actions"].index(d)
    ni=next(i for i,a in enumerate(q["actions"]) if a.get("type")=="copy" and a.get("target")==NEW_PUZ_TARGET)
    assert di < ni
    # Existing-component regression guards.
    assert not any(a.get("target")=="mods/unbreakablecatalyst-1.0.2.jar" for a in q["actions"])
    assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in q["actions"])
    assert any(a.get("target")==NEW_PUZ_TARGET for a in q["actions"])
    h=next(a for a in q["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
    assert [e["value"] for e in h["edits"]]==[-111,-111,-111,-111]

Path("client200_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client200_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
print("CLIENT_200_PUZZLESLIB_CLEANUP_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
