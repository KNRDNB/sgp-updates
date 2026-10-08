import hashlib, json, zipfile
from pathlib import Path

ROOT=Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.1.zip"
META=ROOT/"SGP_ClientPatch_2.0.1.meta.json"

PATCH={
  "schemaVersion":1,
  "patchId":"sgp-client-2.0.1",
  "name":"SGP Client 2.0.1",
  "targetPackId":"sgp-neoforge-1.21.1-client",
  "minecraft":"1.21.1",
  "neoforge":"21.1.249",
  "fromVersions":["2.0.0"],
  "toVersion":"2.0.1",
  "restartRequired":True,
  "summary":[
    "Create server-config maintenance: larger Roller fill depth and Fluid Tank capacity.",
    "Hose Pulley marks 1000-block reservoirs as bottomless and may continue filling them.",
    "No mods, datapacks, resource packs, options, or unrelated config values are changed."
  ],
  "actions":[
    {
      "actionId":"create-server-fluid-and-roller-tuning",
      "type":"tomlEdit",
      "description":"Настроить Create Roller, Hose Pulley и Fluid Tank",
      "target":"config/create-server.toml",
      "edits":[
        {"op":"set","path":"kinetics.contraptions.rollerFillDepth","value":64,"createIfMissing":False},
        {"op":"set","path":"fluids.fluidTankCapacity","value":32,"createIfMissing":False},
        {"op":"set","path":"fluids.hosePulleyBlockThreshold","value":1000,"createIfMissing":False},
        {"op":"set","path":"fluids.fillInfinite","value":True,"createIfMissing":False}
      ]
    }
  ]
}

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=(
 "SGP Client 2.0.1\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Direct-stable maintenance release explicitly authorized by owner.\n"
 "Exact Create config delta from 2.0.0:\n"
 "- kinetics.contraptions.rollerFillDepth: 12 -> 64\n"
 "- fluids.fluidTankCapacity: 8 -> 32\n"
 "- fluids.hosePulleyBlockThreshold: 10000 -> 1000\n"
 "- fluids.fillInfinite: false -> true\n"
 "All other settings and payloads are untouched.\n"
).encode("utf-8")

fixed=(2026,10,8,18,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme)]:
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==["README.txt","patch.json"]
    p=json.loads(z.read("patch.json"))
    assert p==PATCH
    assert p["fromVersions"]==["2.0.0"] and p["toVersion"]=="2.0.1"
    a=p["actions"]
    assert len(a)==1 and a[0]["type"]=="tomlEdit"
    assert [(e["path"],e["value"]) for e in a[0]["edits"]]==[
      ("kinetics.contraptions.rollerFillDepth",64),
      ("fluids.fluidTankCapacity",32),
      ("fluids.hosePulleyBlockThreshold",1000),
      ("fluids.fillInfinite",True)
    ]

meta={
  "schemaVersion":1,
  "channel":"stable",
  "tag":"client-v2.0.1",
  "patchId":"sgp-client-2.0.1",
  "targetPackId":"sgp-neoforge-1.21.1-client",
  "minecraft":"1.21.1",
  "neoforge":"21.1.249",
  "patchSchemaVersion":1,
  "fromVersions":["2.0.0"],
  "toVersion":"2.0.1",
  "assetName":"SGP_ClientPatch_2.0.1.zip",
  "assetSize":OUT.stat().st_size,
  "sha256":sha(OUT),
  "minInstallerVersion":"2.0.0"
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
print("CLIENT_201_EXACT_CONFIG_DELTA_AUDIT_PASS")
print("CLIENT_SHA="+sha(OUT))
print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha(META))
print("META_SIZE="+str(META.stat().st_size))
