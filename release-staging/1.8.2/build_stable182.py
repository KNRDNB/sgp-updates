import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.2-test.4.zip"
OUT=ROOT/"SGP_ClientPatch_1.8.2.zip"
WORK=ROOT/".work-182-stable"
BUILD=WORK/"build"
BASE_SHA="170ba57c169b1466e918beafc32c5ac683368c78fed3183966c16ff0c1f5433f"

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert BASE.is_file() and shaf(BASE)==BASE_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

mp=BUILD/"patch.json"
p=json.loads(mp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.8.2-test.4"
assert p["toVersion"]=="1.8.2-test.4"
assert p["fromVersions"][-3:]==["1.8.2-test.1","1.8.2-test.2","1.8.2-test.3"]

actions=json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))
before={
    f.relative_to(BUILD).as_posix():shaf(f)
    for f in BUILD.rglob("*") if f.is_file()
}

p["patchId"]="sgp-client-1.8.2"
p["name"]="SGP Client 1.8.2"
p["toVersion"]="1.8.2"
p["fromVersions"]=list(p["fromVersions"])+["1.8.2-test.4"]
p["summary"]=[
  "Stable 1.8.2 promoted from owner-runtime-PASS 1.8.2-test.4.",
  "Potion Charms support Soulbound through the tested narrow Apotheosis compatibility bridge.",
  "Curios adds six Amulet Pocket equipment cells through the tested targeted curios-common.toml edit.",
  "SGP RU Localization 1.9 provides Очки and Кармашек для амулетов.",
  "Payload/action set is identical to runtime-tested 1.8.2-test.4."
]
assert json.dumps(p["actions"],ensure_ascii=False,separators=(",",":"))==actions

# exact tested action invariants
curios=[
    a for a in p["actions"]
    if a.get("type")=="tomlEdit" and a.get("target")=="config/curios-common.toml"
]
matching=[
    e for a in curios for e in a.get("edits",[])
    if e.get("op")=="arrayAddUnique"
    and e.get("path")=="slots"
    and e.get("value")=="id=amulet_pocket;size=6;order=-70"
    and e.get("createIfMissing") is False
]
assert len(matching)==1

mp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
    "SGP Client 1.8.2\n"
    "Stable promotion of owner-runtime-PASS 1.8.2-test.4.\n"
    "Payload/action set is unchanged.\n"
    "Potion Charm Soulbound + 6-slot Amulet Pocket + Curios RU localization.\n",
    "utf-8"
)

after={
    f.relative_to(BUILD).as_posix():shaf(f)
    for f in BUILD.rglob("*") if f.is_file()
}
for k,v in before.items():
    if k not in {"patch.json","README.txt"}:
        assert after[k]==v,k

for a in p["actions"]:
    if a["type"]=="copy":
        f=BUILD/a["source"]
        assert f.is_file(),a["source"]
        assert f.stat().st_size==a["size"],a["actionId"]
        assert shaf(f).lower()==a["sha256"].lower(),a["actionId"]

fixed=(2026,10,5,22,15,0)
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
    assert q["patchId"]=="sgp-client-1.8.2"
    assert q["toVersion"]=="1.8.2"
    assert q["fromVersions"][-1]=="1.8.2-test.4"
    assert json.dumps(q["actions"],ensure_ascii=False,separators=(",",":"))==actions
    assert "1.5.4" not in q["fromVersions"]

print("STABLE_182_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
