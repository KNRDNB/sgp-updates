#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.1.0-test.1"
OLD_TAG="client-v2.0.11-test.3"
ZIP="SGP_ClientPatch_2.1.0-test.1.zip"
META="SGP_ClientPatch_2.1.0-test.1.meta.json"
PAXEL="SGP-Wands-Paxel-Compat-1.0.3.jar"
GLASS="SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"
PAXEL_SHA="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
GLASS_SHA="60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"

# Gate published identity *before* any destructive or mutating action.
if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Refusing to reuse existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Refusing to reuse existing tag $TAG" >&2
  exit 1
fi
gh api "repos/$REPO/releases/tags/$OLD_TAG" >/dev/null

# Independent upstream bytecode audit of exact Wands/Ironworks artifacts,
# not the upstream HEAD or a Fabric edition. No runtime PASS is inferred.
bash release-staging/2.1.0-test.1/ci_exact_target_preflight.sh \
  | tee exact-wands-ironworks-target-preflight.log

# Reuse the exact already compiled/passed build-only JAR, not a rebuild.
# GitHub Actions artifact 13625701236 was created by successful run 42500474897.
rm -rf source-paxel103 && mkdir source-paxel103
gh run download 42500474897 \
  --repo "$REPO" \
  --name "sgp-wands-paxel-1.0.3-build-only" \
  --dir source-paxel103
test -f "source-paxel103/$PAXEL"
cp "source-paxel103/$PAXEL" "$PAXEL"
test "$(sha256sum "$PAXEL" | awk '{print $1}')" = "$PAXEL_SHA"
test "$(stat -c %s "$PAXEL")" = "7673"
unzip -t "$PAXEL" >/dev/null
javap -p -v -classpath "$PAXEL" sgp.wandspaxel.mixin.SgpWandsPaxelCompatMixin \
  > paxel103-release-javap.txt
for sym in 'can_dig' 'can_destroy_or_use' 'place_block' \
    'sgp$mining' 'sgp$selectForUse' 'sgp$useAbility' \
    'AXE_STRIP' 'AXE_SCRAPE' 'AXE_WAX_OFF' 'SHOVEL_FLATTEN' \
    'getToolModifiedState' 'isCorrectToolForDrops' 'getIntArray'; do
  grep -Fq "$sym" paxel103-release-javap.txt || { echo "NO MIXIN SYMBOL $sym"; exit 1; }
done
echo "EXACT_PAXEL_103_BYTE_REUSE_PASS"

# Glass was visually confirmed by the owner on TEST3. Reuse exactly those
# glass mod bytes. Do not alter Quartz Glass alpha, textures or Sodium beyond SAFE.
rm -rf source-test3 && mkdir source-test3
gh release download "$OLD_TAG" \
  --repo "$REPO" \
  --pattern "SGP_ClientPatch_2.0.11-test.3.zip" \
  --dir source-test3
python3 - <<'PY'
from pathlib import Path
import hashlib, zipfile
z=Path("source-test3/SGP_ClientPatch_2.0.11-test.3.zip")
assert hashlib.sha256(z.read_bytes()).hexdigest()=="12e0b431d1d9165751d881cd987aeb0f5a0e1872fd60ca50866f1a2f7c33f4bc"
with zipfile.ZipFile(z) as f:
    b=f.read("files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar")
assert hashlib.sha256(b).hexdigest()=="60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"
assert len(b)==4811
Path("SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar").write_bytes(b)
print("EXACT_GLASS_100_BYTE_REUSE_PASS")
PY

python3 release-staging/2.1.0-test.1/build_client_210_test1.py \
  | tee build-client-210-test1.log

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META"

cat > notes.md <<'EOF'
Клиент SGP 2.1.0-test.1. Corrective TEST после owner runtime FAIL пакселя в 2.0.11-test.3. Не stable.

Paxel:
- новый SGP-Wands-Paxel-Compat 1.0.3 для восьми точных Create: Ironworks 4.0.3 paxel ID;
- Building Wands 3.0.5 отбрасывал TieredItem без DataComponents.TOOL, хотя Ironworks реализует собственные проверки tier/drop и NeoForge ItemAbilities;
- добыча и Replace используют реальную скорость, mining-domain, drop/tier и ограничения Wands;
- axe strip/scrape/wax-off и shovel flatten используют NeoForge getToolModifiedState для выбранного пакселя вместо неработающего vanilla useOn;
- выбранные слоты только 0..35; нет невыбранного/почти сломанного инструмента; no hoe/shears grants;
- Wands undo, XP и durability flow не подменяются.
- build-only run 42500474897: compiled PASS, 82 independent rules checks PASS, exact packaged Mixin symbols PASS; this publication also audits exact upstream bytecode.

Quartz Glass:
- exact 1.0.0 JAR reused BYTE FOR BYTE from successful visual result on 2.0.11-test.3;
- Sodium SAFE; 68 BetterNether quartz glass variants only;
- no BetterNether textures, alpha or RGB changes.

Only client singleplayer/integrated-server owner runtime is requested. No server release/test artifact.
After verifying this candidate, final stable client will be 2.1.0 with the same payload/action set; runtime PASS is not claimed here.
Forward repair includes installed 2.0.11-test.1/.2/.3, plus accepted 2.0.10.
EOF

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META" \
  --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = true
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2
test "$(printf '%s' "$ASSETS" | jq -r '.[].name' | sort)" = "$(printf '%s\n%s\n' "$META" "$ZIP" | sort)"

rm -rf live-client210 && mkdir live-client210
gh release download "$TAG" --repo "$REPO" --dir live-client210
cmp "$ZIP" "live-client210/$ZIP"
cmp "$META" "live-client210/$META"
python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test \
  --zip "live-client210/$ZIP" \
  --metadata "live-client210/$META"

python3 - <<'PY'
from pathlib import Path
import hashlib, io, json, zipfile
zip_path=Path("live-client210/SGP_ClientPatch_2.1.0-test.1.zip")
with zipfile.ZipFile(zip_path) as z:
    assert z.testzip() is None
    assert sorted(z.namelist())==sorted([
        "patch.json",
        "README.txt",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.3.jar",
        "files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"
    ])
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.10","2.0.11-test.1","2.0.11-test.2","2.0.11-test.3"]
    assert p["toVersion"]=="2.1.0-test.1"
    assert [a["type"] for a in p["actions"]]==["delete","delete","delete","copy","copy","jsonEdit"]
    assert {a["target"] for a in p["actions"][:3]}=={
        "mods/SGP-Wands-Paxel-Compat-1.0.0.jar",
        "mods/SGP-Wands-Paxel-Compat-1.0.1.jar",
        "mods/SGP-Wands-Paxel-Compat-1.0.2.jar"
    }
    assert p["actions"][-1]["edits"]==[{
        "op":"set","path":"/performance/quad_splitting_mode",
        "value":"SAFE","createIfMissing":False
    }]
    paxel=z.read("files/mods/SGP-Wands-Paxel-Compat-1.0.3.jar")
    glass=z.read("files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar")
    assert hashlib.sha256(paxel).hexdigest()=="52a8993070fd3bab43660d3f26df87d9cdcdda2e2711a01504a4d981ff034692"
    assert hashlib.sha256(glass).hexdigest()=="60ce0f3a584b22f63c1b956629c49eac4b7d2514f6bd0ac1ba639f426661d5a7"
    with zipfile.ZipFile(io.BytesIO(paxel)) as f:
        assert f.testzip() is None
        assert not any(n.startswith(("net/nicguzzo/wands/","create_ironworks/")) for n in f.namelist())
        assert "sgp/wandspaxel/mixin/SgpWandsPaxelCompatMixin.class" in f.namelist()
    with zipfile.ZipFile(io.BytesIO(glass)) as f:
        assert f.testzip() is None
        assert "sgp/glasscompat/mixin/SodiumNeoForgeBlockAccessMixin.class" in f.namelist()
        assert not any("textures/" in n or n.startswith("assets/betternether/") for n in f.namelist())
print("LIVE_CLIENT_210_TEST1_EXACT_VERIFY_PASS")
PY

# Retire old TEST only after new TEST public + live exact-pair PASS.
if gh api "repos/$REPO/releases/tags/$OLD_TAG" >/dev/null 2>&1; then
  gh release delete "$OLD_TAG" --repo "$REPO" --cleanup-tag --yes
fi
if gh api "repos/$REPO/git/ref/tags/$OLD_TAG" >/dev/null 2>&1; then
  gh api -X DELETE "repos/$REPO/git/refs/tags/$OLD_TAG"
fi
! gh api "repos/$REPO/releases/tags/$OLD_TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$OLD_TAG" >/dev/null 2>&1

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
  echo "SGP_CLIENT_210_TEST1_PUBLIC_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "ZIP_SHA=$(sha256sum "$ZIP" | awk '{print $1}')"
  echo "ZIP_SIZE=$(stat -c %s "$ZIP")"
  echo "META_SHA=$(sha256sum "$META" | awk '{print $1}')"
  echo "META_SIZE=$(stat -c %s "$META")"
  echo "PAXEL_SHA=$PAXEL_SHA"
  echo "PAXEL_SIZE=7673"
  echo "GLASS_SHA=$GLASS_SHA"
  echo "GLASS_SIZE=4811"
  echo "RUNTIME=PENDING_OWNER"
  echo "PREVIOUS_FAILED_TEST3_RETIRED=PASS"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-210-test1-result.txt
