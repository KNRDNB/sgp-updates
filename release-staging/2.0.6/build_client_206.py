from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.6.zip"
META=ROOT/"SGP_ClientPatch_2.0.6.meta.json"
ADDON=ROOT/"SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"

OLD_100="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.0.jar"
OLD_101="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.1.jar"
NEW="mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"
ADDON_SHA="537f31e8a3c3904681fa6e089087514117e372d63a3361a30ee1675cc594eaea"
ADDON_SIZE=13475

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f: return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()

assert ADDON.is_file()
assert sha_file(ADDON)==ADDON_SHA
assert ADDON.stat().st_size==ADDON_SIZE
with zipfile.ZipFile(ADDON) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert "sgp/ftbspawnguard/ArchitecturyEventAccess.class" in names
    assert "sgp/ftbspawnguard/ManualTogglePayload.class" in names
    assert "sgp/ftbspawnguard/mixin/SpawnGuardClientEventsMixin.class" in names
    assert 'version="1.0.2"' in toml
    assert 'versionRange="[1.0.4,1.0.5)"' in toml

for tag,name,sha,size,to_version in [
    ("client-v2.0.4","SGP_ClientPatch_2.0.4.zip","e6f7e45dffd6ae61c517c19ca6bc16f83762b2f305958be5f395ed79bece97ce",55218,"2.0.4"),
    ("client-v2.0.5","SGP_ClientPatch_2.0.5.zip","74a94847c1ae4520d7ab222d6bcad2587d61d492a7a0a3138ce3f467561c1d40",13136,"2.0.5"),
]:
    d=ROOT/f".audit-{to_version}"
    d.mkdir(exist_ok=True)
    p=d/name
    subprocess.run(["gh","release","download",tag,"--repo","KNRDNB/sgp-updates","--pattern",name,"--dir",str(d)],check=True)
    assert p.stat().st_size==size
    assert sha_file(p)==sha
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        patch=json.loads(z.read("patch.json"))
        assert patch["toVersion"]==to_version

payload_name="files/mods/SGP-FTB-Spawn-Guard-Auto-Protect-1.0.2.jar"
payload=ADDON.read_bytes()

PATCH={
 "schemaVersion":1,
 "patchId":"sgp-client-2.0.6",
 "name":"SGP Client 2.0.6",
 "targetPackId":"sgp-neoforge-1.21.1-client",
 "minecraft":"1.21.1",
 "neoforge":"21.1.249",
 "fromVersions":["2.0.4","2.0.5"],
 "toVersion":"2.0.6",
 "restartRequired":True,
 "summary":[
   "Исправлен аварийный запуск 2.0.5: регистрация FTB AFTER_CLAIM теперь идёт через публичный Architectury Event API.",
   "Сохранены исправления auto-protect и безопасного manual Mob Control toggle без vanilla command-spam path.",
   "Можно обновиться напрямую как с 2.0.4, так и с аварийного 2.0.5."
 ],
 "actions":[
   {"actionId":"remove-sgp-ftb-auto-protect-1-0-0","type":"delete","description":"Удалить старый SGP Auto Protect 1.0.0, если он ещё установлен","target":OLD_100,"optional":True},
   {"actionId":"remove-sgp-ftb-auto-protect-1-0-1","type":"delete","description":"Удалить аварийный SGP Auto Protect 1.0.1, если он установлен","target":OLD_101,"optional":True},
   {"actionId":"install-sgp-ftb-auto-protect-1-0-2","type":"copy","description":"Установить SGP Auto Protect 1.0.2","source":payload_name,"target":NEW,"sha256":ADDON_SHA,"size":ADDON_SIZE},
 ],
}
patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode()
readme=("SGP Client 2.0.6\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
"Production hotfix после аварийного 2.0.5.\n"
"- исправлен IllegalAccessException при регистрации FTB AFTER_CLAIM через Architectury;\n"
"- регистрация вызывается через публичный dev.architectury.event.Event API;\n"
"- сохранены direct AFTER_CLAIM auto-protect и SGP serverbound manual-toggle transport;\n"
"- Spawn Guard 1.0.4 не перепаковывается; protected_chunks.properties не меняется;\n"
"- поддерживается прямое восстановление с 2.0.4 и 2.0.5.\n\n"
"Отдельного тестового сервера нет; релиз выполняется по явному разрешению владельца, runtime PASS остаётся PENDING до запуска на рабочем сервере.\n").encode("utf-8")

fixed=(2026,10,28,19,15,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),(payload_name,payload)]:
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={"patch.json","README.txt",payload_name}
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.4","2.0.5"]
    assert [a["type"] for a in p["actions"]]==["delete","delete","copy"]
    assert p["actions"][0]["optional"] is True and p["actions"][1]["optional"] is True
    data=z.read(payload_name); assert sha_bytes(data)==ADDON_SHA and len(data)==ADDON_SIZE
    assert not any("protected_chunks.properties" in n for n in z.namelist())

meta={
 "schemaVersion":1,"channel":"stable","tag":"client-v2.0.6","patchId":PATCH["patchId"],
 "targetPackId":PATCH["targetPackId"],"minecraft":"1.21.1","neoforge":"21.1.249",
 "patchSchemaVersion":1,"fromVersions":PATCH["fromVersions"],"toVersion":"2.0.6",
 "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),"minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
for name,val in [
 ("client206_sha.txt",sha_file(OUT)),("client206_size.txt",str(OUT.stat().st_size)),
 ("client206_meta_sha.txt",sha_file(META)),("client206_meta_size.txt",str(META.stat().st_size))]:
    pathlib.Path(name).write_text(val+"\n")
print("CLIENT_206_STATIC_AUDIT_PASS")
print("CLIENT_SHA="+sha_file(OUT)); print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META)); print("META_SIZE="+str(META.stat().st_size))
