#!/usr/bin/env bash
set -euo pipefail

REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.3"
ZIP="SGP_ClientPatch_2.0.3.zip"
META="SGP_ClientPatch_2.0.3.meta.json"

python3 release-staging/2.0.3/build_client_203.py | tee build-client-203.txt

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing release $TAG" >&2
  exit 1
fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then
  echo "Unexpected existing tag $TAG" >&2
  exit 1
fi

cat > notes.md <<'EOF'
## SGP Client 2.0.3

Owner-authorized direct stable ArmorHUD correction.

Exact sequential edge: 2.0.2 -> 2.0.3.

Changes:
- restore the left ArmorHUD group to its pre-2.0.2 positions:
  - helmPosX, chestPosX, mainPosX, arrPosX: 111 -> 136;
- move the right ArmorHUD group to the matching symmetric spacing:
  - legPosX, bootPosX, offPosX, invPosX: -111 -> -136.

Create schematic settings introduced in 2.0.2 remain unchanged. No mods, datapacks, resource packs, options, server configs, or unrelated client config values are changed.
EOF

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" \
  --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2

rm -rf live-client && mkdir live-client
gh release download "$TAG" --repo "$REPO" --dir live-client
test -f "live-client/$ZIP"
test -f "live-client/$META"
cmp "$ZIP" "live-client/$ZIP"
cmp "$META" "live-client/$META"

python3 scripts/client-release-guard.py \
  --tag "$TAG" --channel stable --zip "live-client/$ZIP" --metadata "live-client/$META"

python3 - <<'PY'
import json, zipfile
with zipfile.ZipFile("live-client/SGP_ClientPatch_2.0.3.zip") as z:
    assert z.testzip() is None
    assert sorted(z.namelist()) == ["README.txt","patch.json"]
    p=json.loads(z.read("patch.json"))
    assert p["fromVersions"] == ["2.0.2"]
    assert p["toVersion"] == "2.0.3"
    assert len(p["actions"]) == 1
    a=p["actions"][0]
    assert a["target"] == "config/inventoryhud-client.toml"
    assert [(e["path"],e["value"]) for e in a["edits"]] == [
      ("positions.helmPosX",136),
      ("positions.chestPosX",136),
      ("positions.mainPosX",136),
      ("positions.arrPosX",136),
      ("positions.legPosX",-136),
      ("positions.bootPosX",-136),
      ("positions.offPosX",-136),
      ("positions.invPosX",-136),
    ]
print("LIVE_CLIENT_203_VERIFY_PASS")
PY

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"

{
  echo "CLIENT_203_RELEASE_VERIFY_PASS"
  echo "PUBLISHED_RELEASE_ID=$RID"
  echo "PUBLISHED_ASSET_ID=$AID"
  echo "PUBLISHED_META_ASSET_ID=$MID"
  echo "PUBLISHED_SHA=$(cat client203_sha.txt)"
  echo "PUBLISHED_SIZE=$(cat client203_size.txt)"
  echo "META_SHA=$(cat client203_meta_sha.txt)"
  echo "META_SIZE=$(cat client203_meta_size.txt)"
  echo "HUD_SHA=$(cat hud203_sha.txt)"
  echo "HUD_SIZE=$(cat hud203_size.txt)"
  echo "SOURCE_COMMIT=$GITHUB_SHA"
} | tee release-client-203-result.txt
