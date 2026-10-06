import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.9.1.zip"
OUT=ROOT/"SGP_ClientPatch_1.10.0-test.1.zip"
WORK=ROOT/".work-1100-test1"
BUILD=WORK/"build"

BASE_SHA="74cc8f88725588548f6ffa1a8cc902ce8a967835a47aa08aa84adb4441093ad2"
PERM=ROOT/"PermanentSponges-v21.1.0-1.21.1-NeoForge.jar"
PUZ=ROOT/"puzzleslib-v21.1.62-mc1.21.1+neoforge.jar"
PERM_TARGET="mods/"+PERM.name
PUZ_TARGET="mods/"+PUZ.name

ACCEPTED=[
 "1.0.0","1.0.1","1.0.2","1.0.3",
 "1.1.0","1.2.0","1.2.1",
 "1.3.0","1.3.1","1.3.2","1.3.3",
 "1.4.0","1.5.0","1.5.1","1.5.2","1.5.3",
 "1.6.0","1.6.1","1.6.2",
 "1.7.0","1.7.1","1.8.0","1.8.1","1.8.2","1.9.1"
]

def shaf(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def hashes(root): return {p.relative_to(root).as_posix():shaf(p) for p in root.rglob("*") if p.is_file()}

assert BASE.is_file() and shaf(BASE)==BASE_SHA
assert PERM.is_file() and PUZ.is_file()

if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    z.extractall(BUILD)

pp=BUILD/"patch.json"
p=json.loads(pp.read_text("utf-8"))
assert p["patchId"]=="sgp-client-1.9.1"
assert p["toVersion"]=="1.9.1"
for v in ACCEPTED[:-1]:
    assert v in p["fromVersions"],v
assert "1.9.1" not in p["fromVersions"]
assert "1.5.4" not in p["fromVersions"]

before=hashes(BUILD)

for src,target in [(PERM,PERM_TARGET),(PUZ,PUZ_TARGET)]:
    dst=BUILD/("files/"+target)
    dst.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(src,dst)

# Right-side ArmorStatus HUD: small nudge only.
# Previous opposite-side SGP adjustment is 103 -> 136 (+33).
# This candidate moves the untouched side only 8 units: -103 -> -111.
hud_action={
  "actionId":"shift-right-armorhud-8px",
  "type":"tomlEdit",
  "description":"ArmorHUD: слегка сдвинуть правую колонку, чтобы счётчик 2x не обрезался",
  "target":"config/inventoryhud-client.toml",
  "edits":[
    {"op":"set","path":"positions.legPosX","value":-111,"createIfMissing":False},
    {"op":"set","path":"positions.bootPosX","value":-111,"createIfMissing":False},
    {"op":"set","path":"positions.offPosX","value":-111,"createIfMissing":False},
    {"op":"set","path":"positions.invPosX","value":-111,"createIfMissing":False}
  ]
}

p["actions"].append(hud_action)
for aid,src,target,desc in [
 ("install-puzzles-lib-21-1-62",PUZ,PUZ_TARGET,"Установить Puzzles Lib 21.1.62 для Permanent Sponges"),
 ("install-permanent-sponges-21-1-0",PERM,PERM_TARGET,"Установить Permanent Sponges 21.1.0: губки и губки на палочке"),
]:
    p["actions"].append({
      "actionId":aid,
      "type":"copy",
      "description":desc,
      "source":"files/"+target,
      "target":target,
      "sha256":shaf(src),
      "size":src.stat().st_size
    })

p["patchId"]="sgp-client-1.10.0-test.1"
p["name"]="SGP Client 1.10.0-test.1"
p["toVersion"]="1.10.0-test.1"
p["fromVersions"]=list(p["fromVersions"])+["1.9.1"]
for v in ACCEPTED:
    assert v in p["fromVersions"],v
assert p["fromVersions"][-1]=="1.9.1"
assert "1.5.4" not in p["fromVersions"]

p["summary"]=[
 "TEST.1: ArmorHUD right-side spacing + Permanent Sponges.",
 "ArmorHUD right-side leggings/boots/offhand/inventory-icon X positions move only -103 -> -111; the already-adjusted opposite side stays at 136.",
 "Adds Permanent Sponges 21.1.0 for NeoForge 1.21.1, including aqueous/magmatic sponges on sticks.",
 "Adds required Puzzles Lib 21.1.62 for NeoForge 1.21.1.",
 "Permanent Sponges is a BOTH-side mod; dedicated-server parity is intentionally deferred until explicit owner release instruction."
]

ids=[a["actionId"] for a in p["actions"]]
assert len(ids)==len(set(ids))
h=[a for a in p["actions"] if a.get("actionId")=="shift-right-armorhud-8px"]
assert len(h)==1 and h[0]==hud_action
for target in [PERM_TARGET,PUZ_TARGET]:
    a=[x for x in p["actions"] if x.get("type")=="copy" and x.get("target")==target]
    assert len(a)==1
    f=BUILD/a[0]["source"]
    assert f.is_file()
    assert f.stat().st_size==a[0]["size"]
    assert shaf(f)==a[0]["sha256"]

pp.write_text(json.dumps(p,ensure_ascii=False,indent=2)+"\n","utf-8")
(BUILD/"README.txt").write_text(
 "SGP Client 1.10.0-test.1\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "TEST:\n"
 "- ArmorHUD: правую колонку сдвинули совсем немного (-103 -> -111), чтобы 2x читался полностью.\n"
 "- Уже настроенная противоположная сторона остаётся без изменений (136).\n"
 "- Permanent Sponges 21.1.0: постоянные губки + водяная/магматическая губка на палочке.\n"
 "- Puzzles Lib 21.1.62 — обязательная NeoForge-зависимость.\n"
 "- Permanent Sponges требует клиент и сервер. Во время TEST серверный патч не готовится; функциональность губок проверять в singleplayer/integrated server.\n",
 "utf-8"
)

after=hashes(BUILD)
allowed={"patch.json","README.txt","files/"+PERM_TARGET,"files/"+PUZ_TARGET}
changed={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
assert changed==allowed,changed

fixed=(2026,10,6,11,0,0)
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
    assert q["patchId"]=="sgp-client-1.10.0-test.1"
    assert q["toVersion"]=="1.10.0-test.1"
    for v in ACCEPTED: assert v in q["fromVersions"],v
    assert q["fromVersions"][-1]=="1.9.1"
    ha=next(a for a in q["actions"] if a.get("actionId")=="shift-right-armorhud-8px")
    assert ha["edits"]==hud_action["edits"]
    for target in [PERM_TARGET,PUZ_TARGET]:
        a=next(x for x in q["actions"] if x.get("type")=="copy" and x.get("target")==target)
        b=z.read(a["source"])
        assert len(b)==a["size"]
        assert hashlib.sha256(b).hexdigest()==a["sha256"]

Path("client1100test1_sha.txt").write_text(shaf(OUT)+"\n","utf-8")
Path("client1100test1_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("perm_sha.txt").write_text(shaf(PERM)+"\n","utf-8")
Path("perm_size.txt").write_text(str(PERM.stat().st_size)+"\n","utf-8")
Path("puzzles_sha.txt").write_text(shaf(PUZ)+"\n","utf-8")
Path("puzzles_size.txt").write_text(str(PUZ.stat().st_size)+"\n","utf-8")
print("CLIENT_1100_TEST1_CUMULATIVE_AUDIT_PASS")
print("FINAL_SHA="+shaf(OUT))
print("FINAL_SIZE="+str(OUT.stat().st_size))
