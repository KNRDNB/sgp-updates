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
OLD_PUZ="mods/PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar"
NEW_PUZ="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"

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
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

actions_before=copy.deepcopy(p["actions"])
from_before=list(p["fromVersions"])
payload_before={k:v for k,v in hashes(BUILD).items() if k.startswith("files/")}

# Owner-authorized correction of the defective first v2.0.0 publication.
# Puzzles Lib 21.1.60 is an existing baseline component under a different
# versioned filename. Delete that exact old JAR before copying the already
# runtime-tested 21.1.62 payload. optional=True keeps the cumulative bridge
# safe for supported sources where the old file is already absent.
new_i=next(i for i,a in enumerate(p["actions"])
           if a.get("type")=="copy" and a.get("target")==NEW_PUZ)
delete_action={
 "actionId":"remove-old-puzzleslib-21-1-60",
 "type":"delete",
 "description":"Удалить старый Puzzles Lib 21.1.60 перед установкой 21.1.62",
 "target":OLD_PUZ,
 "optional":True
}
assert not any(a.get("target")==OLD_PUZ for a in p["actions"])
assert not any(a.get("actionId")==delete_action["actionId"] for a in p["actions"])
p["actions"].insert(new_i,delete_action)

# Stable identity. Preserve the complete cumulative/forward-repair source set
# from the runtime-PASS TEST4 and add TEST4 itself as the final forward source.
p["patchId"]="sgp-client-2.0.0"
p["name"]="SGP Client 2.0.0"
p["toVersion"]="2.0.0"
p["fromVersions"]=from_before+["1.10.0-test.4"]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert "1.5.4" not in p["fromVersions"]

assert len(p["actions"])==len(actions_before)+1
assert p["actions"][:new_i]==actions_before[:new_i]
assert p["actions"][new_i]==delete_action
assert p["actions"][new_i+1:]==actions_before[new_i:]

p["summary"]=[
 "Stable 2.0.0 corrected cumulative bridge: remove baseline Puzzles Lib 21.1.60 before installing tested 21.1.62.",
 "All runtime-tested gameplay/config/resource payload bytes from 1.10.0-test.4 remain unchanged.",
 "ArmorHUD right-side spacing remains -111 for leggings/boots/offhand/inventory icon.",
 "Permanent Sponges 21.1.0 + SGP Fixes rev 1.15 + RU Localization 1.10 remain exactly as tested.",
 "Existing Unbreakable Catalyst remains a baseline component and is not installed/replaced/deleted by this patch."
]
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 2.0.0\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Owner-authorized corrected cumulative stable 2.0.0.\n"
 "- Exact old JAR PuzzlesLib-v21.1.60-mc1.21.1-NeoForge.jar is deleted if present.\n"
 "- Puzzles Lib 21.1.62 is then installed under its correct filename.\n"
 "- Complete TEST4 cumulative/forward-repair source lineage is preserved.\n"
 "- All runtime-tested gameplay/config/resource payload bytes are unchanged.\n"
 "- Existing Unbreakable Catalyst remains untouched.\n",
 "utf-8"
)

payload_after={k:v for k,v in hashes(BUILD).items() if k.startswith("files/")}
assert payload_after==payload_before

fixed=(2026,10,6,20,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for file in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        zi=zipfile.ZipInfo(file.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,file.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    q=json.loads(z.read("patch.json"))
    assert q["patchId"]=="sgp-client-2.0.0"
    assert q["toVersion"]=="2.0.0"
    assert q["fromVersions"]==from_before+["1.10.0-test.4"]
    for v in ACCEPTED:
        assert v in q["fromVersions"],v
    assert "1.5.4" not in q["fromVersions"]

    deletes=[(i,a) for i,a in enumerate(q["actions"])
             if a.get("type")=="delete" and a.get("target")==OLD_PUZ]
    assert len(deletes)==1,deletes
    di,d=deletes[0]
    assert d==delete_action
    copies=[(i,a) for i,a in enumerate(q["actions"])
            if a.get("type")=="copy" and a.get("target")==NEW_PUZ]
    assert len(copies)==1,copies
    ni,_=copies[0]
    assert di < ni

    assert not any(a.get("target")=="mods/unbreakablecatalyst-1.0.2.jar" for a in q["actions"])
    assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in q["actions"])
    h=next(a for a in q["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
    assert [e["value"] for e in h["edits"]]==[-111,-111,-111,-111]

Path("client200_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client200_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
print("CLIENT_200_PUZZLESLIB_CLEANUP_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
