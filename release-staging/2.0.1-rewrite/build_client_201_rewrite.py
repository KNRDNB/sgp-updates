from __future__ import annotations
import hashlib, json, shutil, subprocess, zipfile
from pathlib import Path

ROOT=Path.cwd()
STAGE=ROOT/"release-staging/2.0.1-rewrite"
BASE=ROOT/"SGP_ClientPatch_2.0.0.zip"
GSON=ROOT/"gson-2.11.0.jar"
WORK=ROOT/".work-client-201-rewrite"
OUT=ROOT/"SGP_ClientPatch_2.0.1.zip"
META=ROOT/"SGP_ClientPatch_2.0.1.meta.json"

BASE_SHA="1fd2139e0aeee986cd57728eec9b8783b2e37691b212da9e5951b0cf07bc263a"
OLD_BRAND_SHA="7f3f308ccbe4324d7e4e3c20ae9f3ecf9e67fa34d8351d1e2aa1af2c6d474244"
OLD_BRAND_SIZE=17001
LOGO_SHA="67c9973d3f5e277e318ef077f9d98b5ade0a6a83ae5fe751c9732534edbc1221"

def sha_bytes(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path:Path)->str:
    return sha_bytes(path.read_bytes())

def run(*args:str):
    cp=subprocess.run(args,check=False,text=True,capture_output=True)
    if cp.returncode!=0:
        print("COMMAND FAILED:",args)
        print(cp.stdout)
        print(cp.stderr)
        cp.check_returncode()
    return cp

assert BASE.is_file() and sha_file(BASE)==BASE_SHA
assert GSON.is_file() and GSON.stat().st_size==298435
if WORK.exists(): shutil.rmtree(WORK)
WORK.mkdir(parents=True)

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    manifest=json.loads(z.read("patch.json"))
    matches=[n for n in z.namelist() if n.endswith("/SGP-Client-Branding-1.2.14.jar")]
    assert len(matches)==1,matches
    old_name=matches[0]
    old_bytes=z.read(old_name)
    assert len(old_bytes)==OLD_BRAND_SIZE and sha_bytes(old_bytes)==OLD_BRAND_SHA
    actions=[a for a in manifest["actions"] if a.get("type")=="copy" and a.get("target")=="mods/SGP-Client-Branding-1.2.14.jar"]
    assert len(actions)==1 and actions[0]["source"]==old_name
    assert actions[0]["sha256"].lower()==OLD_BRAND_SHA and actions[0]["size"]==OLD_BRAND_SIZE

old=WORK/"SGP-Client-Branding-1.2.14.jar"
old.write_bytes(old_bytes)

classes=WORK/"classes"; classes.mkdir()
patch_classes=WORK/"patch-classes"; patch_classes.mkdir()
helper_src=STAGE/"PostCutoverReleaseFinder.java"
probe_src=STAGE/"BrandingFinderProbe.java"
patcher_src=STAGE/"BrandingFixV1215.java"

run("javac","--release","21","-cp",str(GSON),str(helper_src),str(probe_src),"-d",str(classes))
exports=[
    "--add-exports","java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED",
    "--add-exports","java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED",
]
run("javac",*exports,str(patcher_src),"-d",str(patch_classes))

helper_class=classes/"sgp/client/branding/PostCutoverReleaseFinder.class"
assert helper_class.is_file()
new=WORK/"SGP-Client-Branding-1.2.15.jar"
run("java",*exports,"-cp",str(patch_classes),"BrandingFixV1215",str(old),str(helper_class),str(new))
assert new.is_file() and new.stat().st_size>0

probe_cp=str(classes)+":"+str(GSON)
probe=run("java","-cp",probe_cp,"BrandingFinderProbe")
assert "BRANDING_POST_CUTOVER_DISCOVERY_PROBE_PASS" in probe.stdout

with zipfile.ZipFile(old) as before, zipfile.ZipFile(new) as after:
    assert before.testzip() is None and after.testzip() is None
    before_names=set(before.namelist())
    after_names=set(after.namelist())
    helper_name="sgp/client/branding/PostCutoverReleaseFinder.class"
    assert after_names==before_names|{helper_name}
    main_name="sgp/client/branding/SgpClientBranding.class"
    toml_name="META-INF/neoforge.mods.toml"
    for name in before_names-{main_name,toml_name}:
        assert before.read(name)==after.read(name),name
    assert before.read(main_name)!=after.read(main_name)
    old_toml=before.read(toml_name).decode("utf-8")
    new_toml=after.read(toml_name).decode("utf-8")
    assert 'version="1.2.14"' in old_toml
    assert 'version="1.2.15"' in new_toml and 'version="1.2.14"' not in new_toml
    assert sha_bytes(before.read("assets/sgp_client_branding/textures/gui/sgp_logo.png"))==LOGO_SHA
    assert before.read("assets/sgp_client_branding/textures/gui/sgp_logo.png")==after.read("assets/sgp_client_branding/textures/gui/sgp_logo.png")

main_javap=run("javap","-classpath",str(new),"-p","-c","sgp.client.branding.SgpClientBranding").stdout
finder_start=main_javap.index("private static java.lang.String findLatestStableRelease")
finder_end=main_javap.index("private static void showInstallerError")
finder=main_javap[finder_start:finder_end]
assert "PostCutoverReleaseFinder.find" in finder
assert "JsonParser.parseString" not in finder
render=main_javap[main_javap.index("private static void onScreenRenderPost"):main_javap.index("private static void startUpdateCheck")]
for token in ["computePlaqueRight","bipush        19","bipush        28","bipush        14","bipush        41"]:
    assert token in render,token
assert "bipush        9" not in render
assert "bipush        25" not in render

helper_javap=run("javap","-classpath",str(new),"-p","-c","sgp.client.branding.PostCutoverReleaseFinder").stdout
for token in ["client-v","SGP_ClientPatch_","meta.json","prerelease","draft"]:
    assert token in helper_javap,token

new_sha=sha_file(new)
new_size=new.stat().st_size

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
    "Create server-config maintenance: Roller fill depth 64, Fluid Tank 32 buckets/block, Hose Pulley threshold 1000 and fillInfinite=true.",
    "SGP Client Branding 1.2.15: stable update discovery supports both legacy v2.0.0 and post-cutover client-v* releases.",
    "Post-cutover Branding discovery requires the exact ZIP + .meta.json asset pair; TEST/prerelease releases remain ignored."
  ],
  "actions":[
    {
      "actionId":"remove-sgp-client-branding-1-2-14",
      "type":"delete",
      "description":"Удалить SGP Client Branding 1.2.14 перед обновлением discovery",
      "target":"mods/SGP-Client-Branding-1.2.14.jar",
      "optional":False
    },
    {
      "actionId":"install-sgp-client-branding-1-2-15",
      "type":"copy",
      "description":"Установить SGP Client Branding 1.2.15 с post-cutover discovery",
      "source":"files/mods/SGP-Client-Branding-1.2.15.jar",
      "target":"mods/SGP-Client-Branding-1.2.15.jar",
      "sha256":new_sha,
      "size":new_size
    },
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

patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=(
 "SGP Client 2.0.1\n"
 "Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
 "Owner-authorized direct stable replacement before use of the withdrawn first 2.0.1 client release.\n\n"
 "Changes from accepted client 2.0.0:\n"
 "- Create rollerFillDepth: 12 -> 64\n"
 "- Create fluidTankCapacity: 8 -> 32\n"
 "- Create hosePulleyBlockThreshold: 10000 -> 1000\n"
 "- Create fillInfinite: false -> true\n"
 "- SGP Client Branding 1.2.14 -> 1.2.15\n"
 "- Branding stable discovery now accepts legacy v2.0.0 and post-cutover client-vX.Y.Z.\n"
 "- Post-cutover releases require exactly ZIP + matching .meta.json assets.\n"
 "- TEST/prerelease releases remain excluded from the normal update notice.\n"
).encode("utf-8")

payload_name="files/mods/SGP-Client-Branding-1.2.15.jar"
fixed=(2026,10,8,19,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in sorted([
        ("patch.json",patch_bytes),
        ("README.txt",readme),
        (payload_name,new.read_bytes()),
    ]):
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={"patch.json","README.txt",payload_name}
    p=json.loads(z.read("patch.json"))
    assert p==PATCH
    assert p["fromVersions"]==["2.0.0"] and p["toVersion"]=="2.0.1"
    ids=[a["actionId"] for a in p["actions"]]
    assert len(ids)==len(set(ids))
    copy=[a for a in p["actions"] if a["type"]=="copy"]
    assert len(copy)==1 and copy[0]["target"]=="mods/SGP-Client-Branding-1.2.15.jar"
    assert sha_bytes(z.read(payload_name))==new_sha and len(z.read(payload_name))==new_size

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
  "sha256":sha_file(OUT),
  "minInstallerVersion":"2.0.0"
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")

Path("client201_sha.txt").write_text(sha_file(OUT)+"\n","utf-8")
Path("client201_size.txt").write_text(str(OUT.stat().st_size)+"\n","utf-8")
Path("client201_meta_sha.txt").write_text(sha_file(META)+"\n","utf-8")
Path("client201_meta_size.txt").write_text(str(META.stat().st_size)+"\n","utf-8")
Path("branding1215_sha.txt").write_text(new_sha+"\n","utf-8")
Path("branding1215_size.txt").write_text(str(new_size)+"\n","utf-8")

print("BRANDING_1215_STATIC_AUDIT_PASS")
print("BRANDING_SHA="+new_sha)
print("BRANDING_SIZE="+str(new_size))
print("CLIENT_201_REWRITE_STATIC_AUDIT_PASS")
print("CLIENT_SHA="+sha_file(OUT))
print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META))
print("META_SIZE="+str(META.stat().st_size))
