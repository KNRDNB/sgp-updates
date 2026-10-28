from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.7.zip"
META=ROOT/"SGP_ClientPatch_2.0.7.meta.json"
ADDON=ROOT/"SGP-FTB-Spawn-Guard-Auto-Protect-1.0.3.jar"
BASE_DIR=ROOT/".audit-206"
BASE=BASE_DIR/"SGP_ClientPatch_2.0.6.zip"

BASE_TAG="client-v2.0.6"
BASE_SHA="3d52f8c9d2192098b90d724ab9a3f69f084f511d65edb35db8a363bb6f629040"
BASE_SIZE=13789
OLD="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"
NEW="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.3.jar"

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

expected_sha=pathlib.Path("sgp207_addon_sha.txt").read_text("utf-8").split()[0]
expected_size=int(pathlib.Path("sgp207_addon_size.txt").read_text("utf-8").strip())
assert ADDON.is_file()
assert sha_file(ADDON)==expected_sha
assert ADDON.stat().st_size==expected_size
with zipfile.ZipFile(ADDON) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert "sgp/ftbspawnguard/GuiSyncRequestPayload.class" in names
    assert "sgp/ftbspawnguard/ManualTogglePayload.class" in names
    assert "sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class" in names
    assert 'version="1.0.3"' in toml

BASE_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","release","download",BASE_TAG,"--repo","KNRDNB/sgp-updates","--pattern",BASE.name,"--dir",str(BASE_DIR)],check=True)
assert BASE.stat().st_size==BASE_SIZE and sha_file(BASE)==BASE_SHA
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    assert p["toVersion"]=="2.0.6"
    assert any(a.get("target")==OLD for a in p["actions"])
    assert not any("1.0.3.jar" in n for n in z.namelist())

payload_name="files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.3.jar"
payload=ADDON.read_bytes()

PATCH={
 "schemaVersion":1,
 "patchId":"sgp-client-2.0.7",
 "name":"SGP Client 2.0.7",
 "targetPackId":"sgp-neoforge-1.21.1-client",
 "minecraft":"1.21.1",
 "neoforge":"21.1.249",
 "fromVersions":["2.0.6"],
 "toVersion":"2.0.7",
 "restartRequired":True,
 "summary":[
   "Устранён оставшийся vanilla command-spam путь Mob Control GUI sync.",
   "Ручной toggle и отложенный GUI sync теперь оба используют SGP custom payload вместо sendCommand.",
   "Auto-protect после FTB claim и штатные Spawn Guard permission/UI semantics сохранены."
 ],
 "actions":[
   {"actionId":"remove-sgp-ftb-auto-protect-1-0-2","type":"delete","description":"Удалить SGP Auto Protect 1.0.2","target":OLD,"optional":False},
   {"actionId":"install-sgp-ftb-auto-protect-1-0-3","type":"copy","description":"Установить SGP Auto Protect 1.0.3 с command-spam-free GUI sync","source":payload_name,"target":NEW,"sha256":expected_sha,"size":expected_size},
 ],
}
patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=("SGP Client 2.0.7\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
"Production hotfix для оставшегося Mob Control command-spam path.\n"
"- manual gui_toggle уже идёт через SGP serverbound payload;\n"
"- delayed gui_sync теперь также идёт через отдельный SGP serverbound payload;\n"
"- сервер вызывает штатный Spawn Guard CommandBridge.guiSync, поэтому формат UI sync и permission semantics сохраняются;\n"
"- глобальный vanilla anti-spam не меняется;\n"
"- protected_chunks.properties не распространяется и не перезаписывается.\n\n"
"Отдельного тестового сервера нет; runtime verification выполняется на рабочем сервере после релиза по явному разрешению владельца.\n").encode("utf-8")

fixed=(2026,10,28,19,45,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),(payload_name,payload)]:
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={"patch.json","README.txt",payload_name}
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.6"] and p["toVersion"]=="2.0.7"
    assert [a["type"] for a in p["actions"]]==["delete","copy"]
    assert p["actions"][0]["optional"] is False and p["actions"][0]["target"]==OLD
    data=z.read(payload_name); assert sha_bytes(data)==expected_sha and len(data)==expected_size
    assert not any("protected_chunks.properties" in n for n in z.namelist())

meta={
 "schemaVersion":1,"channel":"stable","tag":"client-v2.0.7","patchId":PATCH["patchId"],
 "targetPackId":PATCH["targetPackId"],"minecraft":"1.21.1","neoforge":"21.1.249",
 "patchSchemaVersion":1,"fromVersions":["2.0.6"],"toVersion":"2.0.7",
 "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),"minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
for name,val in [
 ("client207_sha.txt",sha_file(OUT)),("client207_size.txt",str(OUT.stat().st_size)),
 ("client207_meta_sha.txt",sha_file(META)),("client207_meta_size.txt",str(META.stat().st_size))]:
    pathlib.Path(name).write_text(val+"\n")

print("CLIENT_207_STATIC_AUDIT_PASS")
print("ADDON_SHA="+expected_sha); print("ADDON_SIZE="+str(expected_size))
print("CLIENT_SHA="+sha_file(OUT)); print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META)); print("META_SIZE="+str(META.stat().st_size))
