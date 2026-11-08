from __future__ import annotations
import hashlib
import io
import json
import pathlib
import zipfile

ROOT=pathlib.Path.cwd()
VERSION="2.1.0-test.1"
ZIP=ROOT / ("SGP_ClientPatch_"+VERSION+".zip")
META=ROOT / ("SGP_ClientPatch_"+VERSION+".meta.json")
PAXEL=ROOT / "SGP-Wands-Paxel-Compat-1.0.3.jar"
GLASS=ROOT / "SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"
FROM=["2.0.10","2.0.11-test.1","2.0.11-test.2","2.0.11-test.3"]
# Replace with exact SHA from independent build-only workflow before publish.
EXPECTED_PAXEL_SHA="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
EXPECTED_GLASS_SHA="60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"

def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

paxel=PAXEL.read_bytes()
glass=GLASS.read_bytes()
assert EXPECTED_PAXEL_SHA!="PENDING_AUDIT", "Paxel build-only gate not pinned"
assert sha(paxel)==EXPECTED_PAXEL_SHA
assert sha(glass)==EXPECTED_GLASS_SHA
with zipfile.ZipFile(io.BytesIO(paxel)) as z:
    assert z.testzip() is None
    assert z.read("META-INF/neoforge.mods.toml").count(b'version="1.0.3"') == 1
    assert "sgp/wandspaxel/PaxelRules.class" in z.namelist()
    assert "sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class" in z.namelist()
    assert not any(p.startswith("net/nicguzzo/wands/") or p.startswith("create_ironworks/")
                   for p in z.namelist())
with zipfile.ZipFile(io.BytesIO(glass)) as z:
    assert z.testzip() is None
    assert "sgp/glasscompat/mixin/SodiumNeoForgeBlockAccessMixin.class" in z.namelist()
    assert not any(p.startswith("assets/betternether/") for p in z.namelist())

actions=[]
for v in ["1.0.0","1.0.1","1.0.2"]:
    actions.append({
        "actionId":"remove-old-sgp-paxel-"+v.replace(".","-"),
        "type":"delete",
        "description":"Удалить предыдущий SGP Wands Paxel Compat "+v,
        "target":"mods/SGP-Wands-Paxel-Compat-"+v+".jar",
        "optional":True
    })
for name,b,description in [
    (PAXEL.name,paxel,"Исправленный SGP Wands Paxel Compat 1.0.3"),
    (GLASS.name,glass,"Без изменений восстановить стекольный compat 1.0.0")
]:
    actions.append({
        "actionId":"install-"+name.removesuffix(".jar").lower().replace(".","-"),
        "type":"copy",
        "description":description,
        "source":"files/mods/"+name,
        "target":"mods/"+name,
        "sha256":sha(b),
        "size":len(b)
    })
actions.append({
    "actionId":"preserve-sodium-safe",
    "type":"jsonEdit",
    "description":"Сохранить Sodium SAFE после отклонённого UNLIMITED",
    "target":"config/sodium-options.json",
    "precondition":{"state":"exists"},
    "edits":[{"op":"set","path":"/performance/quad_splitting_mode",
              "value":"SAFE","createIfMissing":False}]
})
patch={
    "schemaVersion":1,
    "patchId":"sgp-client-"+VERSION,
    "name":"SGP Client "+VERSION,
    "targetPackId":"sgp-neoforge-1.21.1-client",
    "minecraft":"1.21.1",
    "neoforge":"21.1.249",
    "fromVersions":FROM,
    "toVersion":VERSION,
    "restartRequired":True,
    "summary":[
        "Paxel Compat 1.0.3: Building Wands 3.0.5 теперь определяет фактические Ironworks TieredItem без DataComponents.TOOL и учитывает собственную корректность tier/drop + скорость.",
        "В режиме Use выбранный паксель применяет подтверждённые NeoForge AXE_STRIP/AXE_SCRAPE/AXE_WAX_OFF/SHOVEL_FLATTEN через getToolModifiedState вместо неработающего ItemStack.useOn.",
        "Слоты 0..35, полная выбранность, прочность >5, Wands undo/XP, без добавления hoe/shears действий. Нативные инструменты не меняются.",
        "Quartz Glass: exact SGP-BetterNether-Quartz-Glass-Compat 1.0.0 byte-for-byte; Sodium SAFE, текстуры и alpha не меняются."
    ],
    "actions":actions
}
readme=(
    "SGP Client "+VERSION+"\n\n"
    "Owner result: test.3 glass visual PASS; paxel still FAIL.\n"
    "Exact upstream bytecode confirmed Ironworks 4.0.3 paxels are TieredItem "
    "without TOOL and have NeoForge abilities but no useOn override.\n"
    "Candidate updates only SGP Wands Paxel Compat to 1.0.3; "
    "keeps original glass compat 1.0.0 exact bytes and Sodium SAFE.\n"
    "Test ONLY singleplayer/integrated server. Select a paxel via wand menu.\n"
    "Verify glass and ordinary block Replace/Destroy, real drops/tier/Silk Touch, "
    "log strip, copper scrape/wax-off, path flatten, no hoe/shears, low durability "
    "stop <=5, no tool when unselected, and vanilla tools unchanged.\n"
    "This is TEST; static/build verification is not owner runtime PASS.\n"
).encode("utf-8")
patchBytes=(json.dumps(patch,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
fixed=(2026,11,8,19,0,0)
with zipfile.ZipFile(ZIP,"w",zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [
        ("patch.json",patchBytes),
        ("README.txt",readme),
        ("files/mods/"+PAXEL.name,paxel),
        ("files/mods/"+GLASS.name,glass)
    ]:
        info=zipfile.ZipInfo(name,fixed)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644<<16
        z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
with zipfile.ZipFile(ZIP) as z:
    assert z.testzip() is None
    assert len(z.namelist())==4 and len(set(z.namelist()))==4
    assert json.loads(z.read("patch.json"))==patch
    assert [a["type"] for a in patch["actions"]]==[
        "delete","delete","delete","copy","copy","jsonEdit"]
    assert patch["fromVersions"]==FROM
meta={
    "schemaVersion":1,
    "channel":"test",
    "tag":"client-v"+VERSION,
    "patchId":patch["patchId"],
    "targetPackId":patch["targetPackId"],
    "minecraft":"1.21.1",
    "neoforge":"21.1.249",
    "patchSchemaVersion":1,
    "fromVersions":FROM,
    "toVersion":VERSION,
    "assetName":ZIP.name,
    "assetSize":ZIP.stat().st_size,
    "sha256":sha(ZIP.read_bytes()),
    "minInstallerVersion":"2.0.0"
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")
audit={
    "version":VERSION,
    "sources":FROM,
    "paxel_sha256":sha(paxel),"paxel_size":len(paxel),
    "glass_sha256":sha(glass),"glass_size":len(glass),
    "zip_sha256":sha(ZIP.read_bytes()),"zip_size":ZIP.stat().st_size,
    "metadata_sha256":sha(META.read_bytes()),
    "metadata_size":META.stat().st_size,
    "runtime":"PENDING_OWNER"
}
pathlib.Path("client210_test1_audit.json").write_text(
    json.dumps(audit,ensure_ascii=False,indent=2)+"\n","utf-8")
print(json.dumps(audit,ensure_ascii=False,indent=2))
print("SGP_CLIENT_210_TEST1_STATIC_PACKAGE_PASS")
