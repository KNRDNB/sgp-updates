from __future__ import annotations
import hashlib
import io
import json
import pathlib
import subprocess
import zipfile

ROOT=pathlib.Path.cwd()
VERSION="2.1.1"
BASE_VERSION="2.1.0"
RELEASE_DATE="2026-11-08"
REPO="KNRDNB/sgp-updates"
SERVER_TAG="server-v2.1.0"
CLIENT_TAG="client-v2.1.0"
SERVER_ZIP="SGP_ServerPatch_2.1.0.zip"
CLIENT_ZIP="SGP_ClientPatch_2.1.0.zip"
SERVER_SHA="ce27ea4e157d7d2138609b29ba20768edf220fc21996bd7c6e64c00e24dd8e51"
SERVER_SIZE=3847313
CLIENT_SHA="b5c7661f49ca0fd06034ca004e874cd61f841bd97cfa0d1a2527fa5efbe613d0"
CLIENT_SIZE=13082
PACK_BASE_SHA="ade04b12f8a414026992f1a61ce18c49cf4dacc0e4fbf9b8e4ccbbfa6615a973"
PACK_BASE_SIZE=529
HISTORY_BASE_SHA="ecd46ddeda01d61265b04e80f8b2dd65c69dc020fc5528df4ad455a8535cf1b4"
HISTORY_BASE_SIZE=2375
PAXEL_NAME="SGP-Wands-Paxel-Compat-1.0.3.jar"
PAXEL_SHA="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
PAXEL_SIZE=7673
OLD_NAME="SGP-Wands-Paxel-Compat-1.0.0.jar"
OLD_SHA="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
OUT=ROOT/"SGP_ServerPatch_2.1.1.zip"
BASE_DIR=ROOT/".server211-exact"
BASE_DIR.mkdir(exist_ok=True)

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def get_release(tag,name,expected_hash,expected_size):
    target=BASE_DIR/name
    subprocess.run(["gh","release","download",tag,"--repo",REPO,"--pattern",name,"--dir",str(BASE_DIR)],check=True)
    actual=target.read_bytes()
    assert len(actual)==expected_size,(name,"size mismatch",len(actual))
    assert sha(actual)==expected_hash,(name,"SHA mismatch",sha(actual))
    return actual

base=get_release(SERVER_TAG,SERVER_ZIP,SERVER_SHA,SERVER_SIZE)
client=get_release(CLIENT_TAG,CLIENT_ZIP,CLIENT_SHA,CLIENT_SIZE)

with zipfile.ZipFile(io.BytesIO(base)) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={
        ".sgp/pack.json",".sgp/history.json","mods/journeymap-neoforge-1.21.1-6.0.8.jar"}
    raw_pack=z.read(".sgp/pack.json")
    raw_hist=z.read(".sgp/history.json")
    assert len(raw_pack)==PACK_BASE_SIZE and sha(raw_pack)==PACK_BASE_SHA
    assert len(raw_hist)==HISTORY_BASE_SIZE and sha(raw_hist)==HISTORY_BASE_SHA
    pack=json.loads(raw_pack)
    history=json.loads(raw_hist)
    assert pack["version"]==history["currentVersion"]==BASE_VERSION
    assert pack["packId"]==history["packId"]=="sgp-neoforge-1.21.1-server"
    assert pack["familyId"]=="sgp-neoforge-1.21.1"
    assert pack["side"]=="server"
    assert history["entries"][-1]["version"]==BASE_VERSION
    lineage=[entry["version"] for entry in history["entries"]]
    assert lineage==[
        "1.0.0","1.2.0","1.2.1","2.0.0","2.0.1","2.0.2","2.0.4",
        "2.0.5","2.0.6","2.0.7","2.0.8","2.0.9","2.0.10","2.1.0"
    ],"Unexpected installed-by-handoff history; stop, do not invent versions."

with zipfile.ZipFile(io.BytesIO(client)) as z:
    assert z.testzip() is None
    cp=json.loads(z.read("patch.json"))
    assert cp["toVersion"]=="2.1.0" and cp["targetPackId"]=="sgp-neoforge-1.21.1-client"
    paxel=z.read("files/mods/"+PAXEL_NAME)
    assert len(paxel)==PAXEL_SIZE and sha(paxel)==PAXEL_SHA
    assert "files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar" in z.namelist()

with zipfile.ZipFile(io.BytesIO(paxel)) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    assert {"META-INF/neoforge.mods.toml",
            "sgp_wands_paxel_compat.mixins.json",
            "sgp/wandspaxel/PaxelRules.class",
            "sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class"}<=names
    assert not any(n.startswith(("net/nicguzzo/wands/","create_ironworks/","assets/")) for n in names)
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'version="1.0.3"' in toml
    assert 'versionRange="[3.0.5,3.0.6)"' in toml
    assert 'versionRange="[4.0.3,4.1)"' in toml
    assert "clientSideOnly = true" not in toml
    assert "CLIENT" not in toml, "Unexpected client-only side declaration"

pack["version"]=VERSION
pack["baseline"]=False
pack["lastUpdate"]={
  "id":"sgp-server-"+VERSION,
  "type":"release",
  "version":VERSION,
  "releaseDate":RELEASE_DATE
}
history["currentVersion"]=VERSION
history["entries"]=list(history["entries"])+[{
   "id":"sgp-server-"+VERSION,
   "type":"release",
   "version":VERSION,
   "releaseDate":RELEASE_DATE,
   "installer":"manual"
}]
pack_bytes=(json.dumps(pack,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
history_bytes=(json.dumps(history,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
payload={
   ".sgp/pack.json":pack_bytes,
   ".sgp/history.json":history_bytes,
   "mods/"+PAXEL_NAME:paxel
}
fixed=(2026,11,8,19,0,0)
with zipfile.ZipFile(OUT,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in payload.items():
        info=zipfile.ZipInfo(name,fixed)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644<<16
        z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(payload) and len(z.namelist())==3
    assert all(z.read(n)==payload[n] for n in payload)
    assert not any(n.startswith(("world/","config/","journeymap/")) for n in z.namelist())
    assert not any("Glass" in n or "Quartz" in n for n in z.namelist())
    new_pack=json.loads(z.read(".sgp/pack.json"))
    new_hist=json.loads(z.read(".sgp/history.json"))
    assert new_pack["version"]==new_hist["currentVersion"]==VERSION
    assert [x["version"] for x in new_hist["entries"]]==lineage+[VERSION]
    assert len(new_hist["entries"])==len(lineage)+1
    assert new_pack["lastUpdate"]["id"]=="sgp-server-"+VERSION
    assert not any(k in new_pack["lastUpdate"] for k in ("transactionId","backupPath","backupManifestHash"))

audit={
  "target_version":VERSION,
  "source_server":BASE_VERSION,
  "source_server_public_zip_sha256":SERVER_SHA,
  "source_server_pack_sha256":PACK_BASE_SHA,
  "source_server_history_sha256":HISTORY_BASE_SHA,
  "accepted_client_version":"2.1.0",
  "accepted_client_public_zip_sha256":CLIENT_SHA,
  "paxel_name":PAXEL_NAME,
  "paxel_sha256":sha(paxel),"paxel_size":len(paxel),
  "old_paxel_name":OLD_NAME,"old_paxel_sha256":OLD_SHA,
  "deletions":["mods/"+OLD_NAME],
  "root_overlay_files":sorted(payload),
  "pack_sha256":sha(pack_bytes),"pack_size":len(pack_bytes),
  "history_sha256":sha(history_bytes),"history_size":len(history_bytes),
  "zip_sha256":sha(OUT.read_bytes()),"zip_size":OUT.stat().st_size,
  "worldgen_changes":False,
  "client_only_glass_included":False,
  "journeymap_mod_included":False,
  "journeymap_live_config_changed":False,
  "owner_dedicated_server_runtime":"PENDING"
}
(ROOT/"server211_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(audit,ensure_ascii=False,indent=2))
print("SERVER_211_CANONICAL_SOURCE_210_AND_ACCEPTED_PAXEL_SHA_PASS")
print("SERVER_211_ROOT_OVERLAY_STATIC_PASS")
