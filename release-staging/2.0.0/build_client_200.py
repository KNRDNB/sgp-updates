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

# Stable identity only. Runtime-tested actions and payload bytes must not change.
p["patchId"]="sgp-client-2.0.0"
p["name"]="SGP Client 2.0.0"
p["toVersion"]="2.0.0"
p["fromVersions"]=list(p["fromVersions"])+["1.10.0-test.4"]
for v in ACCEPTED+TESTS: assert v in p["fromVersions"],v
assert p["actions"]==actions_before
assert "1.5.4" not in p["fromVersions"]
p["summary"]=[
 "Stable 2.0.0 promoted from owner-runtime-PASS 1.10.0-test.4 with identical payload/actions.",
 "ArmorHUD right-side spacing remains -111 for leggings/boots/offhand/inventory icon.",
 "Permanent Sponges 21.1.0 + Puzzles Lib 21.1.62 remain exactly as tested.",
 "SGP Fixes rev 1.15 keeps Soulbound eligibility for both sponge-on-a-stick items.",
 "Existing Unbreakable Catalyst remains a baseline component and is not installed/replaced/deleted by this patch.",
 "SGP RU Localization 1.10 provides all five Permanent Sponges Russian strings."
]
pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 2.0.0\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Owner-runtime-PASS payload promoted from 1.10.0-test.4.\n"
 "Stable identity chosen by owner: 2.0.0 (stable 1.10.0 is intentionally skipped).\n"
 "- ArmorHUD right-side spacing fix.\n"
 "- Permanent Sponges + Puzzles Lib.\n"
 "- Soulbound compatibility for both sponge sticks.\n"
 "- Existing Unbreakable Catalyst remains untouched.\n"
 "- Permanent Sponges Russian localization via SGP RU Localization 1.10.\n",
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
    assert q["actions"]==actions_before
    for v in ACCEPTED+TESTS: assert v in q["fromVersions"],v
    # Existing-component regression guard.
    assert not any(a.get("target")=="mods/unbreakablecatalyst-1.0.2.jar" for a in q["actions"])
    # Exact tested components preserved.
    assert any(a.get("target")=="mods/PermanentSponges-v21.1.0-1.21.1-NeoForge.jar" for a in q["actions"])
    assert any(a.get("target")=="mods/puzzleslib-v21.1.62-mc1.21.1+neoforge.jar" for a in q["actions"])
    h=next(a for a in q["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
    assert [e["value"] for e in h["edits"]]==[-111,-111,-111,-111]

Path("client200_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client200_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
print("CLIENT_200_STABLE_IDENTITY_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
