from __future__ import annotations
import hashlib, io, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.8.zip"
META=ROOT/"SGP_ClientPatch_2.0.8.meta.json"
BASE_DIR=ROOT/".audit-207"
LEGACY_DIR=ROOT/".audit-200"
BASE=BASE_DIR/"SGP_ClientPatch_2.0.7.zip"
LEGACY=LEGACY_DIR/"SGP_ClientPatch_2.0.0.zip"

BASE_TAG="client-v2.0.7"
BASE_SHA="a6e69fdb764187597a87f4e2de9342b9e70d7fc2ed7ce3cf3c9e2860bb44bbed"
BASE_SIZE=15671
LEGACY_TAG="v2.0.0"
LEGACY_SHA="1fd2139e0aeee986cd57728eec9b8783b2e37691b212da9e5951b0cf07bc263a"
LEGACY_SIZE=21752630
FIX_TARGET="config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
FIX_SOURCE="files/config/paxi/datapacks/SGP_Fixes_NeoForge_1.21.1.zip"
TAG_PATH="data/ftbultimine/tags/item/included_tools.json"

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

BASE_DIR.mkdir(exist_ok=True); LEGACY_DIR.mkdir(exist_ok=True)
subprocess.run(["gh","release","download",BASE_TAG,"--repo","KNRDNB/sgp-updates","--pattern",BASE.name,"--dir",str(BASE_DIR)],check=True)
assert BASE.stat().st_size==BASE_SIZE and sha_file(BASE)==BASE_SHA
with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    assert p["toVersion"]=="2.0.7"

subprocess.run(["gh","release","download",LEGACY_TAG,"--repo","KNRDNB/sgp-updates","--pattern",LEGACY.name,"--dir",str(LEGACY_DIR)],check=True)
assert LEGACY.stat().st_size==LEGACY_SIZE and sha_file(LEGACY)==LEGACY_SHA
with zipfile.ZipFile(LEGACY) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    action=next(a for a in p["actions"] if a.get("type")=="copy" and a.get("target")==FIX_TARGET)
    old_fix=z.read(action["source"])

with zipfile.ZipFile(io.BytesIO(old_fix)) as z:
    assert z.testzip() is None
    old_names=[n for n in z.namelist() if not n.endswith("/")]
    old_entries={n:z.read(n) for n in old_names}
    mcmeta=json.loads(old_entries["pack.mcmeta"])
    assert mcmeta["pack"]["description"].endswith("internal rev 1.15")
    assert TAG_PATH not in old_entries

old_hashes={n:sha_bytes(b) for n,b in old_entries.items()}
mcmeta["pack"]["description"]=mcmeta["pack"]["description"].replace("internal rev 1.15","internal rev 1.16")
new_mcmeta=(json.dumps(mcmeta,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
tag_bytes=(json.dumps({"replace":False,"values":["minecraft:shears"]},ensure_ascii=False,indent=2)+"\n").encode("utf-8")

new_entries=dict(old_entries)
new_entries["pack.mcmeta"]=new_mcmeta
new_entries[TAG_PATH]=tag_bytes

fix_buf=io.BytesIO()
fixed=(2026,10,29,16,30,0)
with zipfile.ZipFile(fix_buf,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name in sorted(new_entries):
        zi=zipfile.ZipInfo(name,fixed)
        zi.compress_type=zipfile.ZIP_DEFLATED
        zi.external_attr=0o644<<16
        z.writestr(zi,new_entries[name],compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
new_fix=fix_buf.getvalue()

with zipfile.ZipFile(io.BytesIO(new_fix)) as z:
    assert z.testzip() is None
    names=[n for n in z.namelist() if not n.endswith("/")]
    assert set(names)==set(old_names)|{TAG_PATH}
    desc=json.loads(z.read("pack.mcmeta"))["pack"]["description"]
    assert desc.endswith("internal rev 1.16")
    tag=json.loads(z.read(TAG_PATH))
    assert tag=={"replace":False,"values":["minecraft:shears"]}
    for n,h in old_hashes.items():
        if n=="pack.mcmeta": continue
        assert sha_bytes(z.read(n))==h, n

FIX_SHA=sha_bytes(new_fix); FIX_SIZE=len(new_fix)

PATCH={
 "schemaVersion":1,
 "patchId":"sgp-client-2.0.8",
 "name":"SGP Client 2.0.8",
 "targetPackId":"sgp-neoforge-1.21.1-client",
 "minecraft":"1.21.1",
 "neoforge":"21.1.249",
 "fromVersions":["2.0.7"],
 "toVersion":"2.0.8",
 "restartRequired":True,
 "summary":[
   "SGP Fixes rev 1.16: ножницы добавлены в ftbultimine:included_tools.",
   "FTB Ultimine снова принимает ножницы с компонентом Неразрушимость как подходящий инструмент.",
   "Другие файлы SGP Fixes rev 1.15 не изменены."
 ],
 "actions":[
   {"actionId":"update-sgp-fixes-1-16","type":"copy","description":"Обновить SGP Fixes до rev 1.16","source":FIX_SOURCE,"target":FIX_TARGET,"sha256":FIX_SHA,"size":FIX_SIZE}
 ],
}
patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme=("SGP Client 2.0.8\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
"Точечный compatibility hotfix для FTB Ultimine 2101.1.15.\n"
"- SGP Fixes rev 1.15 -> rev 1.16;\n"
"- добавлен data/ftbultimine/tags/item/included_tools.json;\n"
"- в included_tools добавлены только minecraft:shears;\n"
"- это позволяет Ultimine принимать ножницы с minecraft:unbreakable, которые ItemStack.isDamageableItem() больше не считает damageable;\n"
"- require_tool/require_valid_tool_for_block и другие глобальные настройки Ultimine не меняются;\n"
"- остальные файлы SGP Fixes содержательно идентичны rev 1.15.\n\n"
"Релиз выполнен напрямую stable по явному разрешению владельца; runtime verification остаётся PENDING до проверки на рабочем клиенте/сервере.\n").encode("utf-8")

with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),(FIX_SOURCE,new_fix)]:
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert set(z.namelist())=={"patch.json","README.txt",FIX_SOURCE}
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.7"] and p["toVersion"]=="2.0.8"
    assert len(p["actions"])==1 and p["actions"][0]["target"]==FIX_TARGET
    fb=z.read(FIX_SOURCE)
    assert sha_bytes(fb)==FIX_SHA and len(fb)==FIX_SIZE
    with zipfile.ZipFile(io.BytesIO(fb)) as fz:
        assert json.loads(fz.read(TAG_PATH))=={"replace":False,"values":["minecraft:shears"]}

meta={
 "schemaVersion":1,"channel":"stable","tag":"client-v2.0.8","patchId":PATCH["patchId"],
 "targetPackId":PATCH["targetPackId"],"minecraft":"1.21.1","neoforge":"21.1.249",
 "patchSchemaVersion":1,"fromVersions":["2.0.7"],"toVersion":"2.0.8",
 "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),"minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
for name,val in [
 ("client208_sha.txt",sha_file(OUT)),("client208_size.txt",str(OUT.stat().st_size)),
 ("client208_meta_sha.txt",sha_file(META)),("client208_meta_size.txt",str(META.stat().st_size)),
 ("fixes116_sha.txt",FIX_SHA),("fixes116_size.txt",str(FIX_SIZE))
]:
    pathlib.Path(name).write_text(val+"\n")

print("CLIENT_208_STATIC_AUDIT_PASS")
print("FIX_SHA="+FIX_SHA); print("FIX_SIZE="+str(FIX_SIZE))
print("CLIENT_SHA="+sha_file(OUT)); print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META)); print("META_SIZE="+str(META.stat().st_size))
