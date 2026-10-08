#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.1"
OLD_ORPHAN_SHA="ae3b1ad32e0af8600e3b60b6578abba40081c550"
ZIP="SGP_ClientPatch_2.0.1.zip"
META="SGP_ClientPatch_2.0.1.meta.json"
GSON="gson-2.11.0.jar"

gh release download v2.0.0 --repo "$REPO" --pattern SGP_ClientPatch_2.0.0.zip --clobber
echo "1fd2139e0aeee986cd57728eec9b8783b2e37691b212da9e5951b0cf07bc263a  SGP_ClientPatch_2.0.0.zip" | sha256sum -c -

curl --fail --location --retry 3   https://repo1.maven.org/maven2/com/google/code/gson/gson/2.11.0/gson-2.11.0.jar   --output "$GSON"
test "$(stat -c%s "$GSON")" = "298435"

python3 release-staging/2.0.1-rewrite/build_client_201_rewrite.py | tee client-201-rewrite-build.txt
python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
TAG_SHA="$(gh api "repos/$REPO/git/ref/tags/$TAG" --jq '.object.sha')"
test "$TAG_SHA" = "$OLD_ORPHAN_SHA"

cat > notes.md <<'EOF'
## SGP Client 2.0.1

Owner-authorized direct stable replacement of the withdrawn, unused first 2.0.1 publication.

Changes from SGP Client 2.0.0:
- Create Mechanical Roller fill depth: 12 → 64.
- Create Fluid Tank capacity: 8 → 32 buckets per block.
- Create Hose Pulley bottomless threshold: 10000 → 1000 fluid blocks.
- Create Hose Pulley may continue filling above-threshold reservoirs: false → true.
- SGP Client Branding 1.2.14 → 1.2.15.

Branding 1.2.15 fixes the post-cutover main-menu update check:
- legacy stable v2.0.0 remains supported;
- post-cutover stable client-vX.Y.Z is supported;
- post-cutover discovery requires exactly the matching ZIP + .meta.json pair;
- TEST/prerelease releases are ignored by the normal stable update notice;
- existing title-screen visual layout and Installer-launch behavior remain unchanged.

This is still the exact sequential stable edge 2.0.0 → 2.0.1.
EOF

gh api --method DELETE "repos/$REPO/git/refs/tags/$TAG"
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Old orphan tag still exists" >&2
  exit 1
fi

python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"   --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2

rm -rf live && mkdir live
gh release download "$TAG" --repo "$REPO" --dir live
test -f "live/$ZIP"
test -f "live/$META"
cmp "$ZIP" "live/$ZIP"
cmp "$META" "live/$META"
python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "live/$ZIP" --metadata "live/$META"

python3 - <<'PY'
import hashlib,json,zipfile
from pathlib import Path
z=Path("live/SGP_ClientPatch_2.0.1.zip")
with zipfile.ZipFile(z) as f:
    assert f.testzip() is None
    p=json.loads(f.read("patch.json"))
    assert p["fromVersions"]==["2.0.0"] and p["toVersion"]=="2.0.1"
    assert [a["type"] for a in p["actions"]]==["delete","copy","tomlEdit"]
    assert p["actions"][0]["target"]=="mods/SGP-Client-Branding-1.2.14.jar"
    assert p["actions"][1]["target"]=="mods/SGP-Client-Branding-1.2.15.jar"
    b=f.read("files/mods/SGP-Client-Branding-1.2.15.jar")
    assert hashlib.sha256(b).hexdigest()==Path("branding1215_sha.txt").read_text().strip()
print("LIVE_CLIENT_201_BRANDING_PACKAGE_SMOKE_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "LIVE_CLIENT_201_REWRITE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client201_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client201_size.txt)"
  echo "META_SHA=$(cat client201_meta_sha.txt)"
  echo "META_SIZE=$(cat client201_meta_size.txt)"
  echo "BRANDING_1215_SHA=$(cat branding1215_sha.txt)"
  echo "BRANDING_1215_SIZE=$(cat branding1215_size.txt)"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee client-201-rewrite-result.txt
