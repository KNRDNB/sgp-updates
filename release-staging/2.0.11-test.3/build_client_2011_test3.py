from __future__ import annotations
import hashlib, io, json, pathlib, zipfile

ROOT = pathlib.Path.cwd()
OUT = ROOT / "SGP_ClientPatch_2.0.11-test.3.zip"
META = ROOT / "SGP_ClientPatch_2.0.11-test.3.meta.json"
PAXEL = ROOT / "SGP-Wands-Paxel-Compat-1.0.2.jar"
GLASS = ROOT / "SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"

def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha_file(path: pathlib.Path) -> str:
    return sha_bytes(path.read_bytes())

for path in (PAXEL, GLASS):
    if not path.is_file():
        raise FileNotFoundError(path)

paxel_bytes=PAXEL.read_bytes()
glass_bytes=GLASS.read_bytes()

assert sha_bytes(paxel_bytes) == "6e379cd0a3af008b0e5a7b12f2d54153e2306ff7107630cb423d1cea14eb63f7"
assert len(paxel_bytes) == 6094

with zipfile.ZipFile(io.BytesIO(glass_bytes)) as z:
    assert z.testzip() is None
    assert "sgp/glasscompat/QuartzGlassIds.class" in z.namelist()
    assert "sgp/glasscompat/mixin/SodiumNeoForgeBlockAccessMixin.class" in z.namelist()
    assert not any(n.startswith("assets/betternether/") for n in z.namelist())
    assert not any(n.startswith("textures/") for n in z.namelist())

paxel_payload="files/mods/"+PAXEL.name
glass_payload="files/mods/"+GLASS.name

patch={
    "schemaVersion":1,
    "patchId":"sgp-client-2.0.11-test.3",
    "name":"SGP Client 2.0.11-test.3",
    "targetPackId":"sgp-neoforge-1.21.1-client",
    "minecraft":"1.21.1",
    "neoforge":"21.1.249",
    "fromVersions":["2.0.10","2.0.11-test.1","2.0.11-test.2"],
    "toVersion":"2.0.11-test.3",
    "restartRequired":True,
    "summary":[
        "Quartz Glass: отказ от неэффективного Sodium UNLIMITED; добавлен client-only compat, который через NeoForge/Sodium fluid-overlay hook заменяет flowing side воды на overlay только рядом со всей BetterNether Quartz Glass family (68 ID).",
        "Исходные BetterNether texture/RGB/alpha не изменяются; black glass остаётся с исходной прозрачностью.",
        "SGP Wands Paxel Compat 1.0.2 сохраняется без изменения; в новом singleplayer мире инструмент нужно один раз выбрать в меню палочки (Shift+Alt+H) до появления зелёной подсветки слота."
    ],
    "actions":[
        {
            "actionId":"remove-sgp-wands-paxel-compat-1-0-0",
            "type":"delete","description":"Удалить SGP Wands Paxel Compat 1.0.0",
            "target":"mods/SGP-Wands-Paxel-Compat-1.0.0.jar","optional":True
        },
        {
            "actionId":"remove-failed-sgp-wands-paxel-compat-1-0-1",
            "type":"delete","description":"Удалить failed SGP Wands Paxel Compat 1.0.1",
            "target":"mods/SGP-Wands-Paxel-Compat-1.0.1.jar","optional":True
        },
        {
            "actionId":"install-sgp-wands-paxel-compat-1-0-2",
            "type":"copy","description":"Установить/восстановить exact SGP Wands Paxel Compat 1.0.2",
            "source":paxel_payload,"target":"mods/SGP-Wands-Paxel-Compat-1.0.2.jar",
            "sha256":sha_bytes(paxel_bytes),"size":len(paxel_bytes)
        },
        {
            "actionId":"install-betternether-quartz-glass-compat-1-0-0",
            "type":"copy","description":"Установить client-only SGP BetterNether Quartz Glass Compat 1.0.0",
            "source":glass_payload,"target":"mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar",
            "sha256":sha_bytes(glass_bytes),"size":len(glass_bytes)
        },
        {
            "actionId":"restore-sodium-safe-transparency-mode",
            "type":"jsonEdit",
            "description":"Вернуть Sodium quad_splitting_mode в SAFE: UNLIMITED не устранил Quartz Glass issue",
            "target":"config/sodium-options.json",
            "precondition":{"state":"exists"},
            "edits":[{"op":"set","path":"/performance/quad_splitting_mode","value":"SAFE","createIfMissing":False}]
        }
    ]
}

patch_bytes=(json.dumps(patch,ensure_ascii=False,indent=2)+"\n").encode("utf-8")
readme="""SGP Client 2.0.11-test.3

Corrective TEST after owner runtime FAIL of Quartz Glass mitigation in test.2.

Quartz Glass:
- test.2 Sodium UNLIMITED mitigation did not change the observed flowing-water effect.
- test.3 restores Sodium SAFE.
- new client-only SGP BetterNether Quartz Glass Compat uses Sodium's NeoForge fluid-overlay hook.
- only water adjacent to the exact 68 BetterNether Quartz Glass family IDs is affected.
- flowing side sprite is replaced by the fluid overlay path.
- BetterNether textures, RGB and alpha are not modified or bundled.
- obsidian glass, blue obsidian glass, vanilla glass and non-BetterNether blocks are excluded.

Paxel:
- exact SGP Wands Paxel Compat 1.0.2 is unchanged from test.2.
- IMPORTANT in a new singleplayer world: Building Wands stores selected tool slots in player/world data.
- open the wand tools menu with Shift+Alt+H and click the paxel slot once.
- the slot must show a green highlight before testing Replace/Use.
- if there is no green highlight, Building Wands has no selected tool and will correctly show the red no-tool message.

Runtime:
1) startup;
2) select paxel until green-highlighted, then test glass Replace and the full paxel matrix;
3) Quartz Glass: clear + black + framed block + pane with water, shaders OFF and Complementary ON;
4) confirm black glass transparency is preserved;
5) verify ordinary vanilla glass and BetterNether obsidian glass did not change.

No dedicated-server TEST is built or handed off.
""".encode("utf-8")

fixed=(2026,11,8,19,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for name,data in [
        ("patch.json",patch_bytes),("README.txt",readme),
        (paxel_payload,paxel_bytes),(glass_payload,glass_bytes)
    ]:
        info=zipfile.ZipInfo(name,fixed)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644<<16
        z.writestr(info,data,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted(["patch.json","README.txt",paxel_payload,glass_payload])
    p=json.loads(z.read("patch.json"))
    assert p==patch
    assert p["fromVersions"]==["2.0.10","2.0.11-test.1","2.0.11-test.2"]
    assert p["toVersion"]=="2.0.11-test.3"
    assert [a["type"] for a in p["actions"]]==["delete","delete","copy","copy","jsonEdit"]
    assert p["actions"][4]["edits"][0]["value"]=="SAFE"
    assert not any(n.startswith("files/assets/") or "betternether/textures" in n.lower() for n in z.namelist())

meta={
    "schemaVersion":1,"channel":"test","tag":"client-v2.0.11-test.3",
    "patchId":patch["patchId"],"targetPackId":patch["targetPackId"],
    "minecraft":"1.21.1","neoforge":"21.1.249","patchSchemaVersion":1,
    "fromVersions":patch["fromVersions"],"toVersion":patch["toVersion"],
    "assetName":OUT.name,"assetSize":OUT.stat().st_size,"sha256":sha_file(OUT),
    "minInstallerVersion":"2.0.0"
}
META.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n","utf-8")

audit={
    "target":patch["toVersion"],
    "sources":patch["fromVersions"],
    "paxel_sha256":sha_file(PAXEL),"paxel_size":PAXEL.stat().st_size,
    "glass_sha256":sha_file(GLASS),"glass_size":GLASS.stat().st_size,
    "zip_sha256":sha_file(OUT),"zip_size":OUT.stat().st_size,
    "meta_sha256":sha_file(META),"meta_size":META.stat().st_size,
    "quartz_glass_ids":68,
    "betternether_texture_payloads":0,
    "sodium_quad_splitting_target":"SAFE",
    "server_test_artifacts":0,
    "runtime":"PENDING_OWNER"
}
pathlib.Path("client2011_test3_audit.json").write_text(json.dumps(audit,ensure_ascii=False,indent=2)+"\n","utf-8")
print(json.dumps(audit,ensure_ascii=False,indent=2))
print("CLIENT_2011_TEST3_STATIC_PACKAGE_PASS")
