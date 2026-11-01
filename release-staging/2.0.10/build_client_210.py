from __future__ import annotations
import hashlib, json, pathlib, subprocess, zipfile

ROOT=pathlib.Path.cwd()
OUT=ROOT/"SGP_ClientPatch_2.0.10.zip"
META=ROOT/"SGP_ClientPatch_2.0.10.meta.json"

RU=ROOT/"regions-unexplored-0.6.3-neoforge-21.1.jar"
LITHO=ROOT/"lithostitched-1.8.1-neoforge-21.1.jar"
EVERY=ROOT/"everycomp-1.21-2.11.55-neoforge.jar"

RU_SHA="e7f2edd7bab869c2e566b1b251ea54c6b95834205276bf3a302859d72d9d0c9b"; RU_SIZE=6641783
LITHO_SHA="e0da669fa5facc61a09b9b7bae21b322993de1fcd1eb05787adffb7309598cca"; LITHO_SIZE=1023751
EVERY_SHA="0a2bc786302bbea682b667815edacdf2a46506e0f3c2b033377f5ec2d0e08321"; EVERY_SIZE=2657174

def sha_file(p:pathlib.Path)->str:
    with p.open("rb") as f:return hashlib.file_digest(f,"sha256").hexdigest()
def sha_bytes(b:bytes)->str:return hashlib.sha256(b).hexdigest()

for p,sha,size in [(RU,RU_SHA,RU_SIZE),(LITHO,LITHO_SHA,LITHO_SIZE),(EVERY,EVERY_SHA,EVERY_SIZE)]:
    assert p.is_file(), p
    assert p.stat().st_size==size and sha_file(p)==sha
    with zipfile.ZipFile(p) as z: assert z.testzip() is None

sources=[
 ("client-v2.0.8","2.0.8","e852c7ccda9ceb754624ac670a1f3f9bc463ef327804d4f8c73e828ffa995fff",62734),
 ("client-v2.0.9","2.0.9","d25a4c69eba6fbf1babb5b38c735bc42b23aa15ccca3096faede9478ebc1dda0",5014670),
]
for tag,ver,sha,size in sources:
    d=ROOT/f".audit-{ver}"; d.mkdir(exist_ok=True)
    p=d/f"SGP_ClientPatch_{ver}.zip"
    subprocess.run(["gh","release","download",tag,"--repo","KNRDNB/sgp-updates","--pattern",p.name,"--dir",str(d)],check=True)
    assert p.stat().st_size==size and sha_file(p)==sha
    with zipfile.ZipFile(p) as z:
        assert z.testzip() is None
        patch=json.loads(z.read("patch.json"))
        assert patch["toVersion"]==ver
        txt=json.dumps(patch,ensure_ascii=False)
        if ver=="2.0.8":
            assert "regions-unexplored" not in txt and "regions_unexplored" not in txt
        else:
            assert "regions-unexplored-0.6.3-neoforge-21.1.jar" in txt

with zipfile.ZipFile(EVERY) as z:
    old=b"net/regions_unexplored/world/level/block/plant/tall/ShrubBlock"
    new=b"net/regions_unexplored/block/type/shrub/ShrubBlock"
    old_hits=[]; new_hits=[]
    for n in z.namelist():
        if n.endswith(".class"):
            b=z.read(n)
            if old in b: old_hits.append(n)
            if new in b: new_hits.append(n)
    assert not old_hits
    assert new_hits==["net/mehvahdjukaar/every_compat/modules/neoforge/regions_unexplored/RegionsUnexploredModule.class"]

with zipfile.ZipFile(LITHO) as z:
    assert "dev/worldgen/lithostitched/impl/worldgen/modifier/target/HolderSetTarget.class" in z.namelist()
    jarjar=z.read("META-INF/jarjar/metadata.json").decode()
    assert "apollib-1.2.0-neoforge-21.1.jar" in jarjar

payloads={
 "files/mods/regions-unexplored-0.6.3-neoforge-21.1.jar":RU.read_bytes(),
 "files/mods/lithostitched-1.8.1-neoforge-21.1.jar":LITHO.read_bytes(),
 "files/mods/everycomp-1.21-2.11.55-neoforge.jar":EVERY.read_bytes(),
}

PATCH={
 "schemaVersion":1,
 "patchId":"sgp-client-2.0.10",
 "name":"SGP Client 2.0.10",
 "targetPackId":"sgp-neoforge-1.21.1-client",
 "minecraft":"1.21.1",
 "neoforge":"21.1.249",
 "fromVersions":["2.0.8","2.0.9"],
 "toVersion":"2.0.10",
 "restartRequired":True,
 "summary":[
   "Corrective recovery после нерабочего 2.0.9.",
   "Regions Unexplored 0.6.3 сохраняется, Lithostitched обновлён до 1.8.1 для поддержки RU worldgen holder-set targeting.",
   "Every Compat обновлён до 2.11.55 с upstream-фиксом Regions Unexplored ShrubBlock."
 ],
 "actions":[
   {"actionId":"remove-old-regions-unexplored","type":"delete","description":"Удалить Regions Unexplored 0.6.2, если он ещё остался","target":"mods/regions-unexplored-0.6.2-neoforge-21.1.jar","optional":True},
   {"actionId":"install-regions-unexplored-0-6-3","type":"copy","description":"Установить/восстановить Regions Unexplored 0.6.3","source":"files/mods/regions-unexplored-0.6.3-neoforge-21.1.jar","target":"mods/regions-unexplored-0.6.3-neoforge-21.1.jar","sha256":RU_SHA,"size":RU_SIZE},
   {"actionId":"remove-old-lithostitched","type":"delete","description":"Удалить Lithostitched 1.8.0+beta6","target":"mods/lithostitched-1.8.0+beta6-neoforge-21.1.jar","optional":False},
   {"actionId":"install-lithostitched-1-8-1","type":"copy","description":"Установить Lithostitched 1.8.1","source":"files/mods/lithostitched-1.8.1-neoforge-21.1.jar","target":"mods/lithostitched-1.8.1-neoforge-21.1.jar","sha256":LITHO_SHA,"size":LITHO_SIZE},
   {"actionId":"remove-old-everycomp","type":"delete","description":"Удалить Every Compat 2.11.52","target":"mods/everycomp-1.21-2.11.52-neoforge.jar","optional":False},
   {"actionId":"install-everycomp-2-11-55","type":"copy","description":"Установить Every Compat 2.11.55","source":"files/mods/everycomp-1.21-2.11.55-neoforge.jar","target":"mods/everycomp-1.21-2.11.55-neoforge.jar","sha256":EVERY_SHA,"size":EVERY_SIZE}
 ],
}
patch_bytes=(json.dumps(PATCH,ensure_ascii=False,indent=2)+"\n").encode()
readme=("SGP Client 2.0.10\nMinecraft 1.21.1 / NeoForge 21.1.249 / Java 21\n\n"
"Corrective recovery после 2.0.9.\n"
"- поддерживает обновление напрямую с 2.0.8 и с нерабочего 2.0.9;\n"
"- Regions Unexplored остаётся 0.6.3;\n"
"- Lithostitched 1.8.0+beta6 -> 1.8.1: исправляет фактический runtime-разрыв RU 0.6.3 по lithostitched:holder_set;\n"
"- Every Compat 2.11.52 -> 2.11.55: содержит upstream fix для нового RU ShrubBlock class path;\n"
"- Moonlight 3.6.5 и Create 6.0.10 уже удовлетворяют dependency ranges Every Compat 2.11.55 и не меняются;\n"
"- world/config payload не меняется.\n\n"
"2.0.9 считается runtime FAIL и не должен оставаться конечным состоянием.\n").encode()

fixed=(2026,11,1,11,30,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [("patch.json",patch_bytes),("README.txt",readme),*payloads.items()]:
        zi=zipfile.ZipInfo(name,fixed); zi.compress_type=zipfile.ZIP_DEFLATED; zi.external_attr=0o644<<16
        z.writestr(zi,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.8","2.0.9"] and p["toVersion"]=="2.0.10"
    for a in p["actions"]:
        if a["type"]=="copy":
            data=z.read(a["source"])
            assert len(data)==a["size"] and sha_bytes(data)==a["sha256"]

meta={
 "schemaVersion":1,"channel":"stable","tag":"client-v2.0.10","patchId":PATCH["patchId"],
 "targetPackId":PATCH["targetPackId"],"minecraft":"1.21.1","neoforge":"21.1.249",
 "patchSchemaVersion":1,"fromVersions":["2.0.8","2.0.9"],"toVersion":"2.0.10",
 "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),"minInstallerVersion":"2.0.0",
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
for name,val in [
 ("client210_sha.txt",sha_file(OUT)),("client210_size.txt",str(OUT.stat().st_size)),
 ("client210_meta_sha.txt",sha_file(META)),("client210_meta_size.txt",str(META.stat().st_size))
]:
 pathlib.Path(name).write_text(val+"\n")
print("CLIENT_210_STATIC_AUDIT_PASS")
print("CLIENT_SHA="+sha_file(OUT)); print("CLIENT_SIZE="+str(OUT.stat().st_size))
print("META_SHA="+sha_file(META)); print("META_SIZE="+str(META.stat().st_size))
