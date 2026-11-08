#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.11-test.3"
OLD_TAG="client-v2.0.11-test.2"
ZIP="SGP_ClientPatch_2.0.11-test.3.zip"
META="SGP_ClientPatch_2.0.11-test.3.meta.json"
PAXEL="SGP-Wands-Paxel-Compat-1.0.2.jar"
GLASS="SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar"

bash release-staging/2.0.11-test.3/ci_build_glass_compat.sh

# Reuse the exact already-published paxel 1.0.2 bytes; do not rebuild/repack them.
rm -rf source-test2 && mkdir source-test2
gh release download "$OLD_TAG" --repo "$REPO" --pattern "SGP_ClientPatch_2.0.11-test.2.zip" --dir source-test2
python3 - <<'PY'
from pathlib import Path
import hashlib, zipfile
z=Path("source-test2/SGP_ClientPatch_2.0.11-test.2.zip")
with zipfile.ZipFile(z) as f:
    b=f.read("files/mods/SGP-Wands-Paxel-Compat-1.0.2.jar")
Path("SGP-Wands-Paxel-Compat-1.0.2.jar").write_bytes(b)
assert len(b)==6094
assert hashlib.sha256(b).hexdigest()=="6e379cd0a3af008b0e5a7b12f2d54153e2306ff7107630cb423d1cea14eb63f7"
print("EXACT_PAXEL_102_REUSE_PASS")
PY

python3 release-staging/2.0.11-test.3/build_client_2011_test3.py | tee build-client-2011-test3.txt

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing tag $TAG" >&2
  exit 1
fi

cat > notes.md <<'EOF'
Corrective TEST после runtime FAIL стекольной части 2.0.11-test.2.

Quartz Glass:
- Sodium UNLIMITED не изменил observed flowing-water effect и больше не используется как fix.
- test.3 возвращает quad_splitting_mode в SAFE.
- добавлен client-only SGP BetterNether Quartz Glass Compat 1.0.0.
- compat использует уже существующий NeoForge/Sodium fluid-overlay hook: для воды рядом с exact 68 BetterNether Quartz Glass ID выбирается fluid overlay вместо flowing side texture.
- BetterNether textures, RGB и alpha не меняются и не входят в patch.
- black quartz glass сохраняет исходную alpha.
- vanilla glass, obsidian glass и blue obsidian glass исключены.

Paxel:
- exact SGP Wands Paxel Compat 1.0.2 переиспользован байт-в-байт из test.2.
- в новом singleplayer мире выбранные инструменты Building Wands не переносятся с сервера: Shift+Alt+H → клик по paxel → слот должен стать зелёным перед тестом.

Runtime только singleplayer/integrated server. Никакого server TEST/candidate не создаётся.
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

rm -rf live-client && mkdir live-client
gh release download "$TAG" --repo "$REPO" --dir live-client
cmp "$ZIP" "live-client/$ZIP"
cmp "$META" "live-client/$META"
python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel test --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import hashlib, io, json, zipfile
zpath="live-client/SGP_ClientPatch_2.0.11-test.3.zip"
with zipfile.ZipFile(zpath) as z:
    assert z.testzip() is None
    names=sorted(z.namelist())
    assert names==sorted([
        "README.txt",
        "patch.json",
        "files/mods/SGP-Wands-Paxel-Compat-1.0.2.jar",
        "files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar",
    ])
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"]==["2.0.10","2.0.11-test.1","2.0.11-test.2"]
    assert p["toVersion"]=="2.0.11-test.3"
    assert [a["type"] for a in p["actions"]]==["delete","delete","copy","copy","jsonEdit"]
    assert p["actions"][4]["edits"]==[{
        "op":"set",
        "path":"/performance/quad_splitting_mode",
        "value":"SAFE",
        "createIfMissing":False,
    }]
    paxel=z.read("files/mods/SGP-Wands-Paxel-Compat-1.0.2.jar")
    assert hashlib.sha256(paxel).hexdigest()=="6e379cd0a3af008b0e5a7b12f2d54153e2306ff7107630cb423d1cea14eb63f7"
    glass=z.read("files/mods/SGP-BetterNether-Quartz-Glass-Compat-1.0.0.jar")
    assert hashlib.sha256(glass).hexdigest()==p["actions"][3]["sha256"]
    with zipfile.ZipFile(io.BytesIO(glass)) as g:
        assert not any(n.startswith("assets/betternether/") or "textures/" in n for n in g.namelist())
        assert "sgp/glasscompat/mixin/SodiumNeoForgeBlockAccessMixin.class" in g.namelist()
print("LIVE_CLIENT_2011_TEST3_EXACT_VERIFY_PASS")
PY

# Retire failed test.2 only after test.3 is public and exact-byte verified.
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
ZIP_SHA="$(sha256sum "$ZIP" | awk '{print $1}')"
META_SHA="$(sha256sum "$META" | awk '{print $1}')"
GLASS_SHA="$(sha256sum "$GLASS" | awk '{print $1}')"

{
  echo "CLIENT_2011_TEST3_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$ZIP_SHA"
  echo "PUBLISHED_SIZE=$(stat -c '%s' "$ZIP")"
  echo "META_SHA=$META_SHA"
  echo "META_SIZE=$(stat -c '%s' "$META")"
  echo "GLASS_COMPAT_SHA=$GLASS_SHA"
  echo "GLASS_COMPAT_SIZE=$(stat -c '%s' "$GLASS")"
  echo "PAXEL_COMPAT_SHA=6e379cd0a3af008b0e5a7b12f2d54153e2306ff7107630cb423d1cea14eb63f7"
  echo "PAXEL_COMPAT_SIZE=6094"
  echo "FAILED_TEST2_RETIRED=PASS"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-2011-test3-result.txt
