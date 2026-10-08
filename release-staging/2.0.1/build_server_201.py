import hashlib, json, shutil, tomllib, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/"release-staging/2.0.1"
BASE=STAGE/"create-server-2.0.0-base.toml"
OUT=ROOT/"SGP_ServerPatch_2.0.1.zip"
WORK=ROOT/".work-server-201"
BUILD=WORK/"server-root"

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

assert BASE.is_file()
base_bytes=BASE.read_bytes()
repls=[
 (b"\t\trollerFillDepth = 12", b"\t\trollerFillDepth = 64"),
 (b"\tfluidTankCapacity = 8", b"\tfluidTankCapacity = 32"),
 (b"\thosePulleyBlockThreshold = 10000", b"\thosePulleyBlockThreshold = 1000"),
 (b"\tfillInfinite = false", b"\tfillInfinite = true"),
]
target=base_bytes
for old,new in repls:
    assert target.count(old)==1,(old,target.count(old))
    target=target.replace(old,new,1)

base=tomllib.loads(base_bytes.decode("utf-8"))
new=tomllib.loads(target.decode("utf-8"))
expected={
 ("kinetics","contraptions","rollerFillDepth"):(12,64),
 ("fluids","fluidTankCapacity"):(8,32),
 ("fluids","hosePulleyBlockThreshold"):(10000,1000),
 ("fluids","fillInfinite"):(False,True),
}
def flatten(obj,prefix=()):
    out={}
    for k,v in obj.items():
        if isinstance(v,dict): out.update(flatten(v,prefix+(k,)))
        else: out[prefix+(k,)]=v
    return out
fb,fn=flatten(base),flatten(new)
changed={k:(fb.get(k),fn.get(k)) for k in set(fb)|set(fn) if fb.get(k)!=fn.get(k)}
assert changed==expected,changed
assert fn[("kinetics","contraptions","maxRopeLength")]==512
assert fn[("fluids","hosePulleyRange")]==128

if WORK.exists(): shutil.rmtree(WORK)
cfg=BUILD/"world/serverconfig/create-server.toml"
cfg.parent.mkdir(parents=True)
cfg.write_bytes(target)

pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"2.0.1",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{"id":"sgp-server-2.0.1","type":"release","version":"2.0.1","releaseDate":"2026-10-08"}
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"2.0.1",
 "versionFormat":"semver",
 "entries":[
  {"id":"sgp-baseline-1.0.0","type":"baseline","version":"1.0.0","releaseDate":"2026-09-22","installer":"manual"},
  {"id":"sgp-server-1.2.0","type":"release","version":"1.2.0","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-1.2.1","type":"release","version":"1.2.1","releaseDate":"2026-10-05","installer":"manual"},
  {"id":"sgp-server-2.0.0","type":"release","version":"2.0.0","releaseDate":"2026-10-06","installer":"manual"},
  {"id":"sgp-server-2.0.1","type":"release","version":"2.0.1","releaseDate":"2026-10-08","installer":"manual"}
 ]
}
sgp=BUILD/".sgp";sgp.mkdir(parents=True)
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

expected_files=[
 ".sgp/history.json",
 ".sgp/pack.json",
 "world/serverconfig/create-server.toml"
]
files=sorted(p for p in BUILD.rglob("*") if p.is_file())
assert [p.relative_to(BUILD).as_posix() for p in files]==expected_files

fixed=(2026,10,8,18,5,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in files:
        zi=zipfile.ZipInfo(f.relative_to(BUILD).as_posix(),fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==expected_files
    conf=tomllib.loads(z.read("world/serverconfig/create-server.toml").decode("utf-8"))
    assert conf["kinetics"]["contraptions"]["rollerFillDepth"]==64
    assert conf["fluids"]["fluidTankCapacity"]==32
    assert conf["fluids"]["hosePulleyBlockThreshold"]==1000
    assert conf["fluids"]["fillInfinite"] is True
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="2.0.1"
    h=json.loads(z.read(".sgp/history.json"))
    assert h["currentVersion"]=="2.0.1"
    assert [e["version"] for e in h["entries"]]==["1.0.0","1.2.0","1.2.1","2.0.0","2.0.1"]

Path("server201_sha.txt").write_text(sha(OUT)+"\n","utf-8")
Path("server201_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("server201_config_sha.txt").write_text(sha(cfg)+"\n","utf-8")
Path("server201_config_size.txt").write_text(str(cfg.stat().st_size)+"\n","utf-8")
Path("server201_pack_sha.txt").write_text(sha(sgp/"pack.json")+"\n","utf-8")
Path("server201_history_sha.txt").write_text(sha(sgp/"history.json")+"\n","utf-8")
print("SERVER_201_CONFIG_ONLY_AUDIT_PASS")
print("SERVER_SHA="+sha(OUT))
print("SERVER_SIZE="+str(OUT.stat().st_size))
print("CONFIG_SHA="+sha(cfg))
