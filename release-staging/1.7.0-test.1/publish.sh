#!/usr/bin/env bash
set -euo pipefail

: "${GH_TOKEN:?GH_TOKEN missing}"
: "${REPO:?REPO missing}"
: "${GITHUB_SHA:?GITHUB_SHA missing}"

TAG="v1.7.0-test.1"
ASSET="SGP_ClientPatch_1.7.0-test.1.zip"
WANDS_FILE="BuildingWands-neoforge-MC1.21.1-3.0.5.jar"
WANDS_SHA="565c7c31926a7d4f5dd365bae79fc891d5d21f09d3beb0026e7743b9f8bcc57f"
COMPAT_FILE="SGP-Wands-Paxel-Compat-1.0.0.jar"
COMPAT_SHA="00a5c8dbcf4853e40786b3e2cb8756ac6423a9b286df1be75aa49e0adbaf69de"
DATAPACK_FILE="SGP_EndCompat_MC1.21.1.zip"
DATAPACK_SHA="cc769ba1b578bb91cc622886b898caa7e04249a2546100b0cd2ddb552d7102f1"

rm -rf build
mkdir -p build/files/mods build/files/config/paxi/datapacks

echo "::group::Download and verify Building Wands 3.0.5"
curl -fsSL -A "SGP-Publisher/1.0" "https://api.modrinth.com/v2/version/nvMyIx0w" -o modrinth-version.json
python3 - <<'PY' > wands-url.txt
import json
data=json.load(open("modrinth-version.json", encoding="utf-8"))
matches=[f for f in data["files"] if f["filename"]=="BuildingWands-neoforge-MC1.21.1-3.0.5.jar"]
assert len(matches)==1, matches
print(matches[0]["url"])
PY
curl -fL --retry 3 "$(cat wands-url.txt)" -o "build/files/mods/$WANDS_FILE"
echo "$WANDS_SHA  build/files/mods/$WANDS_FILE" | sha256sum -c -
test "$(stat -c %s "build/files/mods/$WANDS_FILE")" = "465238"
echo "::endgroup::"

echo "::group::Restore and verify SGP custom payloads"
cat > compat.b64 <<'EOF'
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
EOF
base64 -d compat.b64 > "build/files/mods/$COMPAT_FILE"
echo "$COMPAT_SHA  build/files/mods/$COMPAT_FILE" | sha256sum -c -
test "$(stat -c %s "build/files/mods/$COMPAT_FILE")" = "3472"

cat > datapack.b64 <<'EOF'
UEsDBBQAAAAIANq2Q12iGkh5mgAAAKgBAAAlAAAAZGF0YS9zZ3AvcmVjaXBlL2Nob3J1c19zdWNjdWxlbnQuanNvbtWQuwrDMAxFd3+F0Zyla36lBOPaSmLwI1jyEEL+vX6UDv2DLneQzpHgXkJK4PNAmCUEF9FkvfLc08VN0a4P9EgEUyONZtxSPgdNZkwrmNE6jEx18awjKa+ebckYfo7vKRdSay6OoWP39M/OK0VUAbX/CDWX3ktGKp4rPGRwtokYLSmL3m379x8VY4qvBcL4BiaV2MyHaAdv8QZQSwMEFAAAAAgA2rZDXbWaoRZgAAAAbQAAAAsAAABwYWNrLm1jbWV0YavmUlBQKkhMzlayUqgGsqG8+LT8otzEEqCgiYUORDgltTi5KLOgJDM/DyisFOweYKXgmpeiXqzgkpqTmZ5RolCh4JRaUpJaBBRVSM7PLUgsyUzKzMksqVQCmlDLVcsFAFBLAQIUAxQAAAAIANq2Q12iGkh5mgAAAKgBAAAlAAAAAAAAAAAAAACkgQAAAABkYXRhL3NncC9yZWNpcGUvY2hvcnVzX3N1Y2N1bGVudC5qc29uUEsBAhQDFAAAAAgA2rZDXbWaoRZgAAAAbQAAAAsAAAAAAAAAAAAAAKSB3QAAAHBhY2subWNtZXRhUEsFBgAAAAACAAIAjAAAAGYBAAAAAA==
EOF
base64 -d datapack.b64 > "build/files/config/paxi/datapacks/$DATAPACK_FILE"
echo "$DATAPACK_SHA  build/files/config/paxi/datapacks/$DATAPACK_FILE" | sha256sum -c -
test "$(stat -c %s "build/files/config/paxi/datapacks/$DATAPACK_FILE")" = "520"
echo "::endgroup::"

echo "::group::Mixin and target preflight"
javap -classpath "build/files/mods/$COMPAT_FILE" -p -v sgp.wands.paxelcompat.mixin.WandPaxelMixin > mixin.txt
grep -Fq "major version: 65" mixin.txt
grep -Fq "RuntimeInvisibleAnnotations" mixin.txt
grep -Fq "org.spongepowered.asm.mixin.Mixin(" mixin.txt
grep -Fq 'targets=["net.nicguzzo.wands.wand.Wand"]' mixin.txt
grep -Fq "RuntimeVisibleAnnotations" mixin.txt
grep -Fq "org.spongepowered.asm.mixin.injection.Inject(" mixin.txt
grep -Fq "can_dig(Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z" mixin.txt
grep -Fq "require=1" mixin.txt
grep -Fq "cancellable=true" mixin.txt

javap -classpath "build/files/mods/$WANDS_FILE" -p -s net.nicguzzo.wands.wand.Wand > wands.txt
grep -Fq "boolean can_dig(net.minecraft.world.level.block.state.BlockState, boolean, net.minecraft.world.item.ItemStack);" wands.txt
grep -Fq "descriptor: (Lnet/minecraft/world/level/block/state/BlockState;ZLnet/minecraft/world/item/ItemStack;)Z" wands.txt
echo "::endgroup::"

cat > build/patch.json <<'EOF'
{
  "schemaVersion": 1,
  "patchId": "sgp-client-1.7.0-test.1",
  "name": "SGP Client 1.7.0-test.1",
  "targetPackId": "sgp-neoforge-1.21.1-client",
  "minecraft": "1.21.1",
  "neoforge": "21.1.249",
  "fromVersions": ["1.6.2"],
  "toVersion": "1.7.0-test.1",
  "restartRequired": true,
  "summary": [
    "Building Wands 2.14 -> 3.0.5",
    "Лимиты палочек: 128 / 256 / 512 / 1024 / 4096 / 8192",
    "Поддержка Create: Ironworks 4.0.3 paxel",
    "Рецепт получения End's Delight Chorus Succulent в мире с BetterEnd"
  ],
  "actions": [
    {
      "actionId": "remove-building-wands-2-14",
      "type": "delete",
      "description": "Удалить Building Wands 2.14",
      "target": "mods/BuildingWands-neoforge-MC1.21-2.14.jar",
      "precondition": {
        "state": "exists",
        "sha256": "79FA863EBB0822F2A3482C0FDFC98BC30975C2D9509F7AE0F632A28F8F0249E8"
      },
      "optional": false
    },
    {
      "actionId": "install-building-wands-3-0-5",
      "type": "copy",
      "description": "Установить Building Wands 3.0.5",
      "source": "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "target": "mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
      "sha256": "565C7C31926A7D4F5DD365BAE79FC891D5D21F09D3BEB0026E7743B9F8BCC57F",
      "size": 465238
    },
    {
      "actionId": "install-wands-paxel-compat",
      "type": "copy",
      "description": "Установить SGP compat для Create: Ironworks paxel",
      "source": "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "target": "mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
      "sha256": "00A5C8DBCF4853E40786B3E2CB8756AC6423A9B286DF1BE75AA49E0ADBAF69DE",
      "size": 3472
    },
    {
      "actionId": "install-end-compat-datapack",
      "type": "copy",
      "description": "Добавить способ получения Chorus Succulent при BetterEnd",
      "source": "files/config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip",
      "target": "config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip",
      "sha256": "CC769BA1B578BB91CC622886B898CAA7E04249A2546100B0CD2DDB552D7102F1",
      "size": 520
    },
    {
      "actionId": "configure-wand-limits",
      "type": "jsonEdit",
      "description": "Настроить лимиты Building Wands",
      "target": "config/wands.json",
      "precondition": {"state": "exists"},
      "edits": [
        {"op": "set", "path": "/max_limit___increment_this_if_your_machine_can_handle_it", "value": 8192, "createIfMissing": false},
        {"op": "set", "path": "/stone_wand_limit", "value": 128, "createIfMissing": false},
        {"op": "set", "path": "/copper_wand_limit", "value": 256, "createIfMissing": false},
        {"op": "set", "path": "/iron_wand_limit", "value": 512, "createIfMissing": false},
        {"op": "set", "path": "/diamond_wand_limit", "value": 1024, "createIfMissing": false},
        {"op": "set", "path": "/netherite_wand_limit", "value": 4096, "createIfMissing": false},
        {"op": "set", "path": "/creative_wand_limit", "value": 8192, "createIfMissing": false}
      ]
    }
  ]
}
EOF

cat > build/README.txt <<'EOF'
SGP Client 1.7.0-test.1
Minecraft 1.21.1 / NeoForge 21.1.249

Planned stable line: 1.7.0.
Canonical prerelease candidate for the SGP client test channel.

Changes:
- Building Wands 2.14 -> 3.0.5.
- Wands limits: Stone 128, Copper 256, Iron 512, Diamond 1024, Netherite 4096, Creative 8192, Global max 8192.
- SGP Wands Paxel Compat 1.0.0 for Create: Ironworks 4.0.3.
- Paxi datapack SGP_EndCompat_MC1.21.1.zip.
- Chorus Succulent recipe: 4x chorus fruit + 1x bone meal -> 1x ends_delight:chorus_succulent.
- End worldgen is not changed.

Status: TEST CANDIDATE.
Owner runtime test is required before stable 1.7.0.
EOF

echo "::group::Build and validate exact prerelease ZIP"
python3 - <<'PY'
from pathlib import Path
import zipfile
root=Path("build")
out=Path("SGP_ClientPatch_1.7.0-test.1.zip")
files=[
    root/"patch.json",
    root/"README.txt",
    root/"files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
    root/"files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
    root/"files/config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip",
]
fixed=(2026,10,4,0,0,0)
with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    for p in files:
        arc=p.relative_to(root).as_posix()
        info=zipfile.ZipInfo(arc,fixed)
        info.compress_type=zipfile.ZIP_DEFLATED
        info.external_attr=0o644 << 16
        z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
PY

unzip -t "$ASSET" >/dev/null
python3 - <<'PY'
import hashlib, json, zipfile
fn="SGP_ClientPatch_1.7.0-test.1.zip"
with zipfile.ZipFile(fn) as z:
    names=z.namelist()
    assert len(names)==len(set(names))
    assert set(names)=={
        "patch.json",
        "README.txt",
        "files/mods/BuildingWands-neoforge-MC1.21.1-3.0.5.jar",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
        "files/config/paxi/datapacks/SGP_EndCompat_MC1.21.1.zip",
    }
    p=json.loads(z.read("patch.json"))
    assert p["schemaVersion"]==1
    assert p["patchId"]=="sgp-client-1.7.0-test.1"
    assert p["toVersion"]=="1.7.0-test.1"
    assert p["fromVersions"]==["1.6.2"]
    assert len(p["actions"])==5
    for a in p["actions"]:
        if a["type"]=="copy":
            b=z.read(a["source"])
            assert len(b)==a["size"]
            assert hashlib.sha256(b).hexdigest().upper()==a["sha256"]
digest=hashlib.sha256(open(fn,"rb").read()).hexdigest()
print("EXACT_SHA="+digest)
open("exact-sha.txt","w",encoding="ascii").write(digest+"\n")
PY
echo "::endgroup::"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Release/tag $TAG already exists; refusing to replace bytes under the same TEST identity." >&2
  exit 1
fi

cat > release-notes.md <<'EOF'
## SGP Client 1.7.0-test.1

Тестовый prerelease planned stable линии **1.7.0**.

- Building Wands 2.14 → 3.0.5.
- Лимиты палочек: 128 / 256 / 512 / 1024 / 4096 / 8192.
- Compat для Create: Ironworks 4.0.3 paxel.
- Способ получения End's Delight Chorus Succulent в pregenerated BetterEnd: 4 chorus fruit + 1 bone meal.
- Worldgen не меняется.

Owner Minecraft runtime test обязателен. При FAIL этот prerelease удаляется из test channel, а исправление выходит как следующий test.N.
EOF

echo "::group::Create prerelease"
gh release create "$TAG" "$ASSET" --repo "$REPO" --target "$GITHUB_SHA" --title "SGP Client 1.7.0-test.1" --notes-file release-notes.md --prerelease
echo "::endgroup::"

echo "::group::Verify live prerelease exact asset"
EXPECTED="$(cat exact-sha.txt)"
REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = "false"
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = "true"
test -n "$(printf '%s' "$REL" | jq -r '.published_at')"
RID="$(printf '%s' "$REL" | jq -r '.id')"

ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = "1"
test "$(printf '%s' "$ASSETS" | jq -r '.[0].name')" = "$ASSET"
test "$(printf '%s' "$ASSETS" | jq -r '.[0].state')" = "uploaded"
AID="$(printf '%s' "$ASSETS" | jq -r '.[0].id')"
SIZE="$(printf '%s' "$ASSETS" | jq -r '.[0].size')"
test "$AID" -gt 0
test "$SIZE" -gt 0
test "$SIZE" -le 2147483648

gh api -H "Accept: application/octet-stream" "repos/$REPO/releases/assets/$AID" > verify.zip
ACTUAL="$(sha256sum verify.zip | awk '{print $1}')"
test "$ACTUAL" = "$EXPECTED"
unzip -t verify.zip >/dev/null
python3 - <<'PY'
import json, zipfile
with zipfile.ZipFile("verify.zip") as z:
    p=json.loads(z.read("patch.json"))
assert p["patchId"]=="sgp-client-1.7.0-test.1"
assert p["toVersion"]=="1.7.0-test.1"
assert p["fromVersions"]==["1.6.2"]
print("Live prerelease exact-asset SHA/ZIP/manifest smoke: PASS")
PY
echo "Published SHA-256: $EXPECTED"
echo "Published size: $SIZE"
echo "::endgroup::"
