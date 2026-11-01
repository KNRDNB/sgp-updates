from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.9.zip"
META=ROOT/"SGP_ClientPatch_2.0.9.meta.json"
RU=ROOT/"regions-unexplored-0.6.3-neoforge-21.1.jar"

OLD="mods/regions-unexplored-0.6.2-neoforge-21.1.jar"
NEW="mods/regions-unexplored-0.6.3-neoforge-21.1.jar"
RU_SHA="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"
RU_SIZE=6641783

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

assert RU.is_file()
assert sha_file(RU)==RU_SHA
assert RU.stat().st_size==RU_SIZE
with zipfile.ZipFile(RU) as z:
    assert z.testzip() is None
    toml=z.read("META-INF/neoforge.mods.toml").decode("utf-8",errors="replace")
    assert 'regions_unexplored' in toml
    assert '0.6.3' in toml

for tag,ver,sha,size in [
    ("client-v2.0.6","2.0.6","3d52f8c9d2192098b90d724ab9a3f69f084f511d65edb35db8a363bb6f629040",13789),
    ("client-v2.0.7","2.0.7","a6e69fdb764187597a87f4e2de9342b9e70d7fc2ed7ce3cf3c9e2860bb44bbed",15671),
    ("client-v2.0.8","2.0.8","e852c7ccda9ceb754624ac670a1f3f9bc463ef327804d4f8c73e828ffa995fff",62734),
]:
    d=ROOT/f".audit-{ver}"
    d.mkdir(exist_ok=True)
    p=d/f"SGP_ClientPatch_{ver}.zip"
    subprocess.run(["gh","release","download",tag,"--repo","KNRDNB/sgp-updates","--pattern",p.name,"--dir",str(d)],check=True)
    assert p.stat().st_size==size and sha_file(p)==sha
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        patch=json.loads(z.read("patch.json"))
        assert patch["toVersion"]==ver
        txt=json.dumps(patch,ensure_ascii=False).lower()
        assert "regions-unexplored" not in txt and "regions_unexplored" not in txt

payload_name="files/mods/regions-unexplored-0.6.3-neoforge-21.1.jar"
payload=RU.read_bytes()

PATCH={
 "schemaVersion":1,
 "patchId":"sgp-client-2.0.9",
 "name":"SGP Client 2.0.9",
 "targetPackId":"sgp-neoforge-1.21.1-client",
 "minecraft":"1.21.1",
 "neoforge":"21.1.249",
 "fromVersions":["2.0.8"],
 "toVersion":"2.0.9",
 "restartRequired":True,
 "summary":[
   "Regions Unexplored обновлён с 0.6.2 до 0.6.3 для NeoForge 1.21.1.",
   "Исправлен upstream-баг: обычные еловые саженцы больше не должны иногда выращивать RU Pine.",
   "Старый JAR 0.6.2 удаляется перед установкой 0.6.3; дубликаты версий не допускаются."
 ],
 "actions":[
   {"actionId":"remove-regions-unexplored-0-6-2","type":"delete","description":"Удалить Regions Unexplored 0.6.2","target":OLD,"optional":False},
   {"actionId":"install-regions-unexplored-0-6-3","type":"copy","description":"Установить Regions Unexplored 0.6.3","source":payload_name,"target":NEW,"sha256":RU_SHA,"size":RU_SIZE},
 ],
}
patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=("SGP Client 2.0.9\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
"Точечное обновление Regions Unexplored 0.6.2 -> 0.6.3.\n"
"- исправлен upstream-баг, из-за которого vanilla spruce saplings иногда выращивали RU Pine;\n"
"- exact old JAR удаляется перед установкой нового;\n"
"- мод остаётся client+server;\n"
"- другие SGP файлы не меняются.\n\n"
"RU 0.6.3 также содержит upstream-исправление генерации Prismachasm/Redstone Caves при некоторых сочетаниях biome-модов. Существующие чанки патч не переписывает; потенциальная разница касается будущей генерации новых чанков. Перед обновлением dedicated server обязателен backup.\n\n"
"Релиз выполнен напрямую stable по явному разрешению владельца; runtime PASS остаётся PENDING до проверки рабочего клиента/сервера.\n").encode("utf-8")

fixed=(2026,11,1,11,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),(payload_name,payload)]:
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={"patch.json","README.txt",payload_name}
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.8"] and p["toVersion"]=="2.0.9"
    assert [a["type"] for a in p["actions"]]==["delete","copy"]
    assert p["actions"][0]["target"]==OLD and p["actions"][0]["optional"] is False
    assert p["actions"][1]["target"]==NEW
    data=z.read(payload_name)
    assert sha_bytes(data)==RU_SHA and len(data)==RU_SIZE

meta={
 "schemaVersion":1,"channel":"stable","tag":"client-v2.0.9","patchId":PATCH["patchId"],
 "targetPackId":PATCH["targetPackId"],"minecraft":"1.21.1","neoforge":"21.1.249",
 "patchSchemaVersion":1,"fromVersions":["2.0.8"],"toVersion":"2.0.9",
 "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),"minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
for name,val in [
 ("client209_sha.txt",sha_file(OUT)),("client209_size.txt",str(OUT.stat().st_size)),
 ("client209_meta_sha.txt",sha_file(META)),("client209_meta_size.txt",str(META.stat().st_size)),
 ("ru063_sha.txt",RU_SHA),("ru063_size.txt",str(RU_SIZE))
]:
    pathlib.Path(name).write_text(val+"\n")

print("CLIENT_209_STATIC_AUDIT_PASS")
print("RU_SHA="+RU_SHA); print("RU_SIZE="+str(RU_SIZE))
print("CLIENT_SHA="+sha_file(OUT)); print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META)); print("META_SIZE="+str(META.stat().st_size))
