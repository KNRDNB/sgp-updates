import hashlib, json, shutil, zipfile
from pathlib import Path

ROOT=Path.cwd()
CLIENT=ROOT/"SGP_ClientPatch_1.7.0-test.16.zip"
OUT=ROOT/"SGP_ServerPatch_1.1.0_TEST.zip"
WORK=ROOT/".work-server-110"
BUILD=WORK/"server-root"

CLIENT_SHA="80535ebbf29aa9167e8ef8408dcb907069561d95a9e0d5fe95a9764395b93419"
WANDS_SHA="565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
COMPAT_SHA="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
FIXES_SHA="ddca482dca046951892a1e849ebd07c7a50eff78858b6d1036ecd5f64c33a5ff"

def shab(b): return hashlib.sha256(b).hexdigest()
def shaf(p): return shab(Path(p).read_bytes())

assert shaf(CLIENT)==CLIENT_SHA
if WORK.exists(): shutil.rmtree(WORK)
BUILD.mkdir(parents=True)

with zipfile.ZipFile(CLIENT) as z:
    assert z.testzip() is None
    pm=json.loads(z.read("patch.json"))
    assert pm["patchId"]=="sgp-client-1.7.0-test.16"
    assert pm["toVersion"]=="1.7.0-test.16"
    payloads={
      "mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar":
        "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "mods/SGP-Wands-Paxel-Compat-1.0.0.jar":
        "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip":
        "files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
    }
    for dst,src in payloads.items():
        p=BUILD/dst
        p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(z.read(src))

assert shaf(BUILD/"mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar")==WANDS_SHA
assert shaf(BUILD/"mods/SGP-Wands-Paxel-Compat-1.0.0.jar")==COMPAT_SHA
assert shaf(BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip")==FIXES_SHA

with zipfile.ZipFile(BUILD/"config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip") as z:
    assert z.testzip() is None
    pm=json.loads(z.read("pack.mcmeta"))
    assert "internal rev 1.10" in pm["pack"]["description"]
    recipe="data/sgp_fixes/recipe/compat/ends_delight/chorus_succulent.json"
    assert recipe in z.namelist()
    r=json.loads(z.read(recipe))
    assert r["result"]["id"]=="ends_delight:chorus_succulent"

# Exact target server metadata, based on canonical 1.0.0 snapshot.
pack={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "familyId":"sgp-neoforge-1.21.1",
 "displayName":"SGP Minecraft 1.21.1 (Server)",
 "side":"server",
 "version":"1.1.0",
 "versionFormat":"semver",
 "minecraft":"1.21.1",
 "loader":"neoforge",
 "neoforge":"21.1.249",
 "javaMajor":21,
 "releaseChannel":"stable",
 "baseline":False,
 "stateSchemaVersion":1,
 "lastUpdate":{
   "id":"sgp-server-1.1.0",
   "type":"release",
   "version":"1.1.0",
   "releaseDate":"2026-10-04"
 }
}
history={
 "schemaVersion":1,
 "packId":"sgp-neoforge-1.21.1-server",
 "currentVersion":"1.1.0",
 "versionFormat":"semver",
 "entries":[
  {
   "id":"sgp-baseline-1.0.0",
   "type":"baseline",
   "version":"1.0.0",
   "releaseDate":"2026-09-22",
   "installer":"manual"
  },
  {
   "id":"sgp-server-1.1.0",
   "type":"release",
   "version":"1.1.0",
   "releaseDate":"2026-10-04",
   "installer":"manual"
  }
 ]
}
sgp=BUILD/".sgp";sgp.mkdir()
(sgp/"pack.json").write_text(json.dumps(pack,ensure_ascii=False,indent=2)+"\n","utf-8")
(sgp/"history.json").write_text(json.dumps(history,ensure_ascii=False,indent=2)+"\n","utf-8")

(BUILD/"DELETE_BEFORE_COPY.txt").write_text(
"mods/BuildingWands-neoforge-MC1.21-2.14.jar\n","utf-8")

script=r'''#!/usr/bin/env bash
set -euo pipefail

WANDS="config/wands.json"
CREATE="config/create-server.toml"

fail(){ echo "SGP Server 1.1.0 config edit FAILED: $*" >&2; exit 1; }
[[ -f "$WANDS" ]] || fail "$WANDS not found"
[[ -f "$CREATE" ]] || fail "$CREATE not found"

set_json_num(){
  local key="$1" value="$2"
  local count
  count="$(grep -Ec "\"$key\"[[:space:]]*:[[:space:]]*[0-9]+" "$WANDS" || true)"
  [[ "$count" == "1" ]] || fail "$WANDS: expected exactly one numeric key $key, got $count"
  sed -i -E "s/(\"$key\"[[:space:]]*:[[:space:]]*)[0-9]+/\1$value/" "$WANDS"
  grep -Eq "\"$key\"[[:space:]]*:[[:space:]]*$value([,[:space:]]|$)" "$WANDS" || fail "$key verification failed"
}

set_json_num "max_limit___increment_this_if_your_machine_can_handle_it" 8192
set_json_num "stone_wand_limit" 128
set_json_num "copper_wand_limit" 256
set_json_num "iron_wand_limit" 512
set_json_num "diamond_wand_limit" 1024
set_json_num "netherite_wand_limit" 4096
set_json_num "creative_wand_limit" 8192

count="$(grep -Ec '^[[:space:]]*maxRopeLength[[:space:]]*=[[:space:]]*[0-9]+[[:space:]]*$' "$CREATE" || true)"
[[ "$count" == "1" ]] || fail "$CREATE: expected exactly one maxRopeLength, got $count"
sed -i -E 's/^([[:space:]]*maxRopeLength[[:space:]]*=[[:space:]]*)[0-9]+([[:space:]]*)$/\1512\2/' "$CREATE"
grep -Eq '^[[:space:]]*maxRopeLength[[:space:]]*=[[:space:]]*512[[:space:]]*$' "$CREATE" || fail "maxRopeLength verification failed"

echo "SGP Server 1.1.0 targeted config edits: PASS"
'''
(BUILD/"APPLY_CONFIG_CHANGES.sh").write_text(script,"utf-8")

readme='''SGP Server 1.1.0 TEST
Minecraft 1.21.1 / NeoForge 21.1.249 / Java 21

This is the first formal versioned server patch after legacy server 1.0.0.

SCOPE
- Building Wands 2.14 -> 3.0.5
- SGP-Wands-Paxel-Compat 1.0.0
- SGP Fixes internal rev 1.10 (End's Delight x BetterEnd Chorus Succulent acquisition recipe)
- Wands limits: 128 / 256 / 512 / 1024 / 4096 / 8192; global 8192
- Create Rope Pulley maxRopeLength = 512
- Server .sgp metadata -> 1.1.0

INSTALL
1. STOP server.
2. Make a full backup.
3. Delete every path listed in DELETE_BEFORE_COPY.txt.
4. Extract this ZIP into server root with replacement.
5. From server root run: bash APPLY_CONFIG_CHANGES.sh
6. Confirm the script prints PASS.
7. Start server and inspect latest log/runtime.
8. After successful test you may remove APPLY_CONFIG_CHANGES.sh and DELETE_BEFORE_COPY.txt.

The config script edits only named Wands numeric keys and Create maxRopeLength.
It does NOT replace config/create-server.toml or config/wands.json wholesale.
'''
(BUILD/"SERVER_PATCH_README.txt").write_text(readme,"utf-8")

# Basic safety.
assert json.loads((sgp/"pack.json").read_text())["version"]=="1.1.0"
assert json.loads((sgp/"history.json").read_text())["currentVersion"]=="1.1.0"
assert not (BUILD/"config/create-server.toml").exists()
assert not (BUILD/"config/wands.json").exists()

fixed=(2026,10,4,18,10,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BUILD.rglob("*") if x.is_file()):
        arc=f.relative_to(BUILD).as_posix()
        zi=zipfile.ZipInfo(arc,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=((0o755 if arc=="APPLY_CONFIG_CHANGES.sh" else 0o644)<<16)
        z.writestr(zi,f.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    required={
      ".sgp/pack.json",".sgp/history.json",
      "mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip",
      "DELETE_BEFORE_COPY.txt","APPLY_CONFIG_CHANGES.sh","SERVER_PATCH_README.txt"
    }
    assert names==required
    assert json.loads(z.read(".sgp/pack.json"))["version"]=="1.1.0"
    assert json.loads(z.read(".sgp/history.json"))["currentVersion"]=="1.1.0"

print("SERVER_110_STATIC_AUDIT_PASS")
print("SERVER_ZIP_SHA="+shaf(OUT))
print("SERVER_ZIP_SIZE="+str(OUT.stat().st_size))
print("PACK_SHA="+shaf(sgp/"pack.json"))
print("PACK_SIZE="+str((sgp/"pack.json").stat().st_size))
print("HISTORY_SHA="+shaf(sgp/"history.json"))
print("HISTORY_SIZE="+str((sgp/"history.json").stat().st_size))
