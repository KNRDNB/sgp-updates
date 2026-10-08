#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.1"
ZIP="SGP_ClientPatch_2.0.1.zip"
META="SGP_ClientPatch_2.0.1.meta.json"

! gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1
! gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1

python3 release-staging/2.0.1/build_client_201.py | tee client-build.txt
python3 release-staging/2.0.1/build_server_201.py | tee server-build.txt

python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

cat > notes.md <<'EOF'
## SGP Client 2.0.1

Direct-stable maintenance release explicitly authorized by the owner.

Create server-config changes only:
- Mechanical Roller fill depth: 12 → 64.
- Fluid Tank capacity per block: 8 → 32 buckets.
- Hose Pulley bottomless threshold: 10000 → 1000 fluid blocks.
- Hose Pulley may continue filling above-threshold reservoirs: false → true.

This is the first post-cutover sequential stable edge and supports exactly client 2.0.0.
No mods, datapacks, resource packs, options, or unrelated config values are changed.
EOF

python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"   --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL" | jq -r '.draft')" = false
test "$(printf '%s' "$REL" | jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL" | jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS" | jq 'length')" = 2

mkdir live
gh release download "$TAG" --repo "$REPO" --dir live
test -f "live/$ZIP"
test -f "live/$META"
cmp "$ZIP" "live/$ZIP"
cmp "$META" "live/$META"
python3 scripts/client-release-guard.py   --tag "$TAG" --channel stable --zip "live/$ZIP" --metadata "live/$META"

AID="$(printf '%s' "$ASSETS" | jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS" | jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
echo "LIVE_CLIENT_201_PAIR_VERIFY_PASS"
echo "PUBLISHED_RELEASE_ID=$RID"
echo "PUBLISHED_ASSET_ID=$AID"
echo "PUBLISHED_META_ASSET_ID=$MID"
echo "PUBLISHED_SHA=$(cat client200_dummy 2>/dev/null || sha256sum "$ZIP" | awk '{print $1}')"
echo "PUBLISHED_SIZE=$(stat -c%s "$ZIP")"
echo "META_SHA=$(sha256sum "$META" | awk '{print $1}')"
echo "META_SIZE=$(stat -c%s "$META")"
echo "SERVER_SHA=$(cat server201_sha.txt)"
echo "SERVER_SIZE=$(cat server201_size.txt)"
echo "SERVER_CONFIG_SHA=$(cat server201_config_sha.txt)"
echo "SERVER_CONFIG_SIZE=$(cat server201_config_size.txt)"
echo "SERVER_PACK_SHA=$(cat server201_pack_sha.txt)"
echo "SERVER_HISTORY_SHA=$(cat server201_history_sha.txt)"
