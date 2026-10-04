from __future__ import annotations
import base64, hashlib, io, json, re, shutil, subprocess, sys, zipfile
from pathlib import Path

ROOT = Path.cwd()
STAGE = ROOT / "release-staging/1.7.0-test.3"
WORK = ROOT / ".work-170t3"
BASE_ZIP = ROOT / "SGP_ClientPatch_1.7.0-test.2.zip"
OUT = ROOT / "SGP_ClientPatch_1.7.0-test.3.zip"

BASE_SHA = "f1a0b2d47cc9f32958a9cf59124dadaecdbb1be4d746b884374fb4c7c677c081"
WANDS_SHA = "565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
COMPAT_SHA = "00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
LOC_OLD_SHA = "194775c451f3e9e977b8fd2cadd7229e94cf7252d5c7719ebd30b288da525576"
LOC_NEW_SHA = "057aa280d9e0a6d058da93e4cb0c8201b5536cad98c17c9cc4881f4f808da730"
RU_SHA = "fe645f5dddf548ece2890679fbc4e28903a3bba7d025592605f3b8199ab13c15"
BRANDING_OLD_SHA = "b3c51decf117aec2d7edbc336e2617925d7c692bf44a9eb91caf07dd7ec5b0aa"
BRANDING_NEW_SHA = "cac3fa22d7189615dcc4a329e2ac1d39c3eba9e018c3daa11c751a7fe14a6d90"
STABLE = ["1.0.0","1.0.1","1.0.2","1.0.3","1.1.0","1.2.0","1.2.1","1.3.0","1.3.1","1.3.2","1.3.3","1.4.0","1.5.0","1.5.1","1.5.2","1.5.3","1.6.0","1.6.1","1.6.2"]

def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())

def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=True, text=True, capture_output=True)

def copy_action(p: dict, suffix: str) -> dict:
    found = [a for a in p["actions"] if a["type"] == "copy" and (a.get("target") or "").endswith(suffix)]
    assert len(found) == 1, (suffix, found)
    return found[0]

assert BASE_ZIP.exists()
assert sha_file(BASE_ZIP) == BASE_SHA
with zipfile.ZipFile(BASE_ZIP) as z:
    assert z.testzip() is None

if WORK.exists():
    shutil.rmtree(WORK)
BASE = WORK / "base"
BASE.mkdir(parents=True)
with zipfile.ZipFile(BASE_ZIP) as z:
    z.extractall(BASE)

manifest_path = BASE / "patch.json"
p = json.loads(manifest_path.read_text(encoding="utf-8"))
assert p["patchId"] == "sgp-client-1.7.0-test.2"
assert p["toVersion"] == "1.7.0-test.2"
assert p["fromVersions"] == STABLE + ["1.7.0-test.1"]
assert len(p["actions"]) == 89 or len(p["actions"]) == 88

# Reconstruct exact curated Russian file.
parts = [(STAGE / "wands_ru_part1.frag").read_bytes()]
for name in ["wands_ru_part2a.b64","wands_ru_part2b.b64","wands_ru_part3a.b64","wands_ru_part3b.b64","wands_ru_part4.b64"]:
    parts.append(base64.b64decode((STAGE / name).read_text(encoding="ascii")))
ru_bytes = b"".join(parts)
assert sha_bytes(ru_bytes) == RU_SHA
ru = json.loads(ru_bytes)

# Audit against exact Wands 3.0.5 payload.
wa = copy_action(p, "BuildingWands-neoforge-MC1.21.1-3.0.5.jar")
wands = BASE / wa["source"]
assert wands.stat().st_size == 465238 and sha_file(wands) == WANDS_SHA
with zipfile.ZipFile(wands) as z:
    en = json.loads(z.read("assets/wands/lang/en_us.json"))
    upstream_ru = json.loads(z.read("assets/wands/lang/ru_ru.json"))
assert len(en) == 348 and len(upstream_ru) == 192
assert len(set(en) - set(upstream_ru)) == 207
assert len(ru) == 348 and set(ru) == set(en)
ph = re.compile(r'%(?:\d+\$)?[a-zA-Z]')
for key in en:
    assert sorted(ph.findall(en[key])) == sorted(ph.findall(ru[key])), key
assert ru["option.wands.check_advancements"] == "Проверять достижения"
assert ru["screen.wands.plane"] == "Плоскость"
assert ru["wands.modes.vein"] == "Жила"
assert ru["wands.target.block"] == "Блок"
print("Wands localization audit: PASS")

# Update existing SGP RU Localization, no parallel pack.
la = copy_action(p, "SGP_RU_Localization_MC1.21.1.zip")
loc_zip = BASE / la["source"]
assert loc_zip.stat().st_size == 404348 and sha_file(loc_zip) == LOC_OLD_SHA
target = "assets/wands/lang/ru_ru.json"
wands_json = (json.dumps(ru, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
tmp = loc_zip.with_suffix(".new.zip")
with zipfile.ZipFile(loc_zip, "r") as zin:
    infos = zin.infolist()
    original = {i.filename: zin.read(i.filename) for i in infos}
    pm = json.loads(original["pack.mcmeta"])
    assert pm["pack"]["description"] == "SGP RU Localization 1.7 — Soulbound, Curios, Ping Wheel, Target Dummy"
    pm["pack"]["description"] = "SGP RU Localization 1.8 — Building Wands 3.0.5 full Russian localization"
    pm_bytes = (json.dumps(pm, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    with zipfile.ZipFile(tmp, "w") as zout:
        saw = False
        for old in infos:
            zi = zipfile.ZipInfo(old.filename, old.date_time)
            zi.compress_type = old.compress_type
            zi.comment = old.comment
            zi.extra = old.extra
            zi.internal_attr = old.internal_attr
            zi.external_attr = old.external_attr
            zi.create_system = old.create_system
            zi.flag_bits = old.flag_bits
            if old.filename == "pack.mcmeta":
                data = pm_bytes
            elif old.filename == target:
                data = wands_json
                saw = True
            else:
                data = original[old.filename]
            zout.writestr(zi, data)
        if not saw:
            zi = zipfile.ZipInfo(target, (2026,10,4,0,0,0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            zout.writestr(zi, wands_json, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
with zipfile.ZipFile(tmp) as z:
    assert z.testzip() is None
    assert json.loads(z.read(target)) == ru
    for n,b in original.items():
        if n not in {"pack.mcmeta", target}:
            assert z.read(n) == b, n
    for n in z.namelist():
        if n.endswith(".json"):
            json.loads(z.read(n))
tmp.replace(loc_zip)
assert loc_zip.stat().st_size == 409369 and sha_file(loc_zip) == LOC_NEW_SHA
print("SGP RU Localization 1.8: PASS")

# Build SGP Client Branding 1.2.2 from exact accepted 1.2.1.
ba = copy_action(p, "SGP-Client-Branding-1.2.1.jar")
old_brand = BASE / ba["source"]
assert old_brand.stat().st_size == 12359 and sha_file(old_brand) == BRANDING_OLD_SHA
new_brand = BASE / "files/mods/SGP-Client-Branding-1.2.2.jar"
new_brand.parent.mkdir(parents=True, exist_ok=True)
classes = WORK / "branding-patcher"
classes.mkdir()
run("javac",
    "--add-exports","java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED",
    "--add-exports","java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED",
    str(STAGE/"BrandingPatch.java"),"-d",str(classes))
run("java",
    "--add-exports","java.base/jdk.internal.org.objectweb.asm=ALL-UNNAMED",
    "--add-exports","java.base/jdk.internal.org.objectweb.asm.tree=ALL-UNNAMED",
    "-cp",str(classes),"BrandingPatch",str(old_brand),str(new_brand))
assert new_brand.stat().st_size == 12273 and sha_file(new_brand) == BRANDING_NEW_SHA
with zipfile.ZipFile(old_brand) as a, zipfile.ZipFile(new_brand) as b:
    assert a.testzip() is None and b.testzip() is None
    assert a.namelist() == b.namelist()
    changed = [n for n in a.namelist() if a.read(n) != b.read(n)]
    assert set(changed) == {"META-INF/neoforge.mods.toml","sgp/client/branding/SgpClientBranding.class"}
    toml = b.read("META-INF/neoforge.mods.toml").decode("utf-8")
    assert 'version="1.2.2"' in toml and 'version="1.2.1"' not in toml
javap = run("javap","-classpath",str(new_brand),"-p","-v","sgp.client.branding.SgpClientBranding").stdout
assert "major version: 65" in javap
assert r"^v(\\\\d+)\\\\.(\\\\d+)\\\\.(\\\\d+)(?:-test\\\\.(\\\\d+))?$" in javap
assert "java/util/Objects.requireNonNullElse" in javap
assert "java/util/regex/Matcher.group:(I)Ljava/lang/String;" in javap

rx = re.compile(r"^v(\d+)\.(\d+)\.(\d+)(?:-test\.(\d+))?$")
def sv(v: str):
    m = rx.fullmatch("v" + v.removeprefix("v")); assert m
    return tuple(map(int,m.groups()[:3])) + (int(m.group(4)) if m.group(4) else 2147483647,)
assert sv("1.7.0") > sv("1.7.0-test.999")
assert sv("1.7.0-test.3") > sv("1.7.0-test.2")
assert sv("1.7.1-test.1") > sv("1.7.0")
print("SGP Client Branding 1.2.2: PASS")

# Transform manifest, preserving cumulative test.2 state.
p["patchId"] = "sgp-client-1.7.0-test.3"
p["name"] = "SGP Client 1.7.0-test.3"
p["toVersion"] = "1.7.0-test.3"
p["fromVersions"] = STABLE + ["1.7.0-test.1","1.7.0-test.2"]
p["summary"] = [
    "Полный cumulative-to-latest update со всех accepted stable SGP Client 1.0.0–1.6.2.",
    "Building Wands 3.0.5 + Create: Ironworks paxel compat + настроенные лимиты.",
    "Полная русская локализация всех 348 текущих Building Wands 3.0.5 language keys через SGP RU Localization 1.8.",
    "SGP Client Branding 1.2.2: отображение и сравнение stable/test prerelease SemVer X.Y.Z-test.N.",
    "End's Delight × BetterEnd Chorus Succulent compat остаётся в SGP Fixes rev 1.10; worldgen не меняется."
]
la["description"] = "Обновить SGP RU Localization до internal 1.8: полная локализация Building Wands 3.0.5"
la["sha256"] = sha_file(loc_zip)
la["size"] = loc_zip.stat().st_size

bi = p["actions"].index(ba)
delete_old = {
    "actionId":"remove-sgp-client-branding-1-2-1",
    "type":"delete",
    "description":"Удалить SGP Client Branding 1.2.1 перед обновлением",
    "target":"mods/SGP-Client-Branding-1.2.1.jar",
    "optional":True
}
install_new = {
    "actionId":"install-sgp-client-branding-1-2-2",
    "type":"copy",
    "description":"Установить SGP Client Branding 1.2.2 с поддержкой test prerelease SemVer",
    "source":"files/mods/SGP-Client-Branding-1.2.2.jar",
    "target":"mods/SGP-Client-Branding-1.2.2.jar",
    "sha256":sha_file(new_brand),
    "size":new_brand.stat().st_size
}
p["actions"][bi:bi+1] = [delete_old, install_new]
old_brand.unlink()

ids = [a["actionId"] for a in p["actions"]]
assert len(ids) == len(set(ids))
assert "1.5.4" not in p["fromVersions"]
for a in p["actions"]:
    target_path = (a.get("target") or "").replace("\\","/")
    assert not target_path.startswith((".sgp/","saves/","journeymap/"))
    assert target_path != "servers.dat" and ".." not in target_path.split("/")
    if a["type"] == "copy":
        f = BASE / a["source"]
        assert f.is_file(), (a["actionId"], a["source"])
        assert f.stat().st_size == a["size"]
        assert sha_file(f).lower() == a["sha256"].lower()
assert not (BASE/"files/config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip").exists()
assert not (BASE/"files/mods/SGP-Client-Branding-1.2.1.jar").exists()

# Re-run exact final Mixin preflight.
compat = BASE/"files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar"
assert sha_file(compat) == COMPAT_SHA
mx = run("javap","-classpath",str(compat),"-p","-v","sgp.wands.paxelcompat.mixin.WandPaxelMixin").stdout
for needle in ["major version: 65","RuntimeInvisibleAnnotations","org.spongepowered.asm.mixin.Mixin(","org.spongepowered.asm.mixin.injection.Inject(","can_dig(Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z","require=1","cancellable=true"]:
    assert needle in mx, needle
assert 'targets=["net.nicguzzo.wands.wand.Wand"]' in mx
wv = run("javap","-classpath",str(wands),"-p","-s","net.nicguzzo.wands.wand.Wand").stdout
assert "descriptor: (Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z" in wv
print("Wands Mixin preflight: PASS")

manifest_path.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(BASE/"README.txt").write_text("""SGP Client 1.7.0-test.3
Minecraft 1.21.1 / NeoForge 21.1.249

TEST PRERELEASE — planned stable line 1.7.0.

CUMULATIVE:
Direct install is supported from every accepted stable SGP Client version 1.0.0 through 1.6.2.
Unofficial 1.5.4 is intentionally excluded.
Forward repair is additionally supported from 1.7.0-test.1 and 1.7.0-test.2.

Changes relative to test.2:
- SGP Client Branding 1.2.2 accepts/renders X.Y.Z-test.N and orders stable X.Y.Z above same-base test builds.
- SGP RU Localization internal 1.8 provides Russian overrides for all 348 current Building Wands 3.0.5 en_us keys.
- Building Wands gameplay, Wands Paxel Compat, limits and SGP Fixes rev 1.10 remain unchanged.

Owner Minecraft runtime test is mandatory before stable 1.7.0.
""", encoding="utf-8")

fixed = (2026,10,4,0,0,0)
with zipfile.ZipFile(OUT,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for f in sorted(x for x in BASE.rglob("*") if x.is_file()):
        arc = f.relative_to(BASE).as_posix()
        zi = zipfile.ZipInfo(arc, fixed)
        zi.compress_type = zipfile.ZIP_DEFLATED
        zi.external_attr = 0o644 << 16
        z.writestr(zi, f.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

with zipfile.ZipFile(OUT) as z:
    assert z.testzip() is None
    names = z.namelist()
    assert len(names) == len(set(names))
    for n in names:
        assert not n.startswith("/") and ".." not in Path(n).parts
        assert not n.startswith((".sgp/","saves/","journeymap/")) and n != "servers.dat"
    q = json.loads(z.read("patch.json"))
    assert q["patchId"] == "sgp-client-1.7.0-test.3"
    assert q["toVersion"] == "1.7.0-test.3"
    assert q["fromVersions"] == STABLE + ["1.7.0-test.1","1.7.0-test.2"]
    for a in q["actions"]:
        if a["type"] == "copy":
            b = z.read(a["source"])
            assert len(b) == a["size"]
            assert sha_bytes(b).lower() == a["sha256"].lower(), a["actionId"]
    assert sha_bytes(z.read("files/mods/SGP-Client-Branding-1.2.2.jar")) == BRANDING_NEW_SHA
    rp = z.read(copy_action(q,"SGP_RU_Localization_MC1.21.1.zip")["source"])
    with zipfile.ZipFile(io.BytesIO(rp)) as rz:
        assert rz.testzip() is None
        assert len(json.loads(rz.read(target))) == 348

print("STATIC_OFFLINE_PASS")
print("CANDIDATE_SHA="+sha_file(OUT))
print("CANDIDATE_SIZE="+str(OUT.stat().st_size))
