#!/usr/bin/env bash
set -euo pipefail
REPO="KNRDNB/sgp-updates"
TAG="client-v2.0.10"
ZIP="SGP_ClientPatch_2.0.10.zip"
META="SGP_ClientPatch_2.0.10.meta.json"
CAND_RUN="41298462300"
CAND_HEAD="f2ea675afc60085ab46f7f372058c240db892a98"
PROBE_RUN="41298601570"
PROBE_HEAD="61984c04fd6a0af1c613d792dbe3179516b69625"

for pair in "$CAND_RUN:$CAND_HEAD" "$PROBE_RUN:$PROBE_HEAD"; do
  run="$(printf '%s' "$pair" | cut -d: -f1)"
  head="$(printf '%s' "$pair" | cut -d: -f2)"
  j="$(gh run view "$run" --repo "$REPO" --json conclusion,headSha)"
  test "$(printf '%s' "$j"|jq -r '.conclusion')" = success
  test "$(printf '%s' "$j"|jq -r '.headSha')" = "$head"
done

rm -rf .cand && mkdir .cand
gh run download "$CAND_RUN" --repo "$REPO" --name sgp-2.0.10-candidates --dir .cand
cp .cand/lithostitched-1.8.1-neoforge-21.1.jar .
cp .cand/everycomp-1.21-2.11.55-neoforge.jar .
curl -fL --retry 3 --retry-delay 2 \
  "https://mediafilez.forgecdn.net/files/9252/522/regions-unexplored-0.6.3-neoforge-21.1.jar" \
  -o regions-unexplored-0.6.3-neoforge-21.1.jar

python3 release-staging/2.0.10/build_client_210.py | tee build-client-210.txt
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META"

if gh api "repos/$REPO/releases/tags/$TAG" >/dev/null 2>&1; then echo "Existing release" >&2; exit 1; fi
if gh api "repos/$REPO/git/ref/tags/$TAG" >/dev/null 2>&1; then echo "Existing tag" >&2; exit 1; fi

cat > notes.md <<'EOF'
Corrective recovery после нерабочего client 2.0.9.

Изменения:
- поддерживается прямое обновление как с 2.0.8, так и с 2.0.9;
- Regions Unexplored остаётся на 0.6.3 — это версия с upstream-фиксом spruce saplings → RU Pine;
- Lithostitched обновлён с 1.8.0+beta6 до 1.8.1, где присутствует holder-set targeting, используемый RU 0.6.3;
- Every Compat обновлён с 2.11.52 до 2.11.55; upstream 2.11.55 прямо исправляет Regions Unexplored ShrubBlock class update;
- Moonlight 3.6.5 и Create 6.0.10 удовлетворяют dependency ranges нового Every Compat и не меняются;
- config/world payload отсутствует.

Перед публикацией exact candidate прошёл bytecode/dependency audit и отдельный минимальный NeoForge 21.1.249 dedicated-server startup probe с RU 0.6.3 + Lithostitched 1.8.1 + Every Compat 2.11.55 + Moonlight 3.6.5.

2.0.9 остаётся immutable failed evidence и не должен использоваться как конечное состояние.
EOF

python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "$ZIP" --metadata "$META" --publish --notes notes.md

REL="$(gh api "repos/$REPO/releases/tags/$TAG")"
test "$(printf '%s' "$REL"|jq -r '.draft')" = false
test "$(printf '%s' "$REL"|jq -r '.prerelease')" = false
RID="$(printf '%s' "$REL"|jq -r '.id')"
ASSETS="$(gh api "repos/$REPO/releases/$RID/assets")"
test "$(printf '%s' "$ASSETS"|jq 'length')" = 2
rm -rf live210 && mkdir live210
gh release download "$TAG" --repo "$REPO" --dir live210
cmp "$ZIP" "live210/$ZIP"; cmp "$META" "live210/$META"
python3 scripts/client-release-guard.py --tag "$TAG" --channel stable --zip "live210/$ZIP" --metadata "live210/$META"

AID="$(printf '%s' "$ASSETS"|jq -r --arg n "$ZIP" '.[]|select(.name==$n)|.id')"
MID="$(printf '%s' "$ASSETS"|jq -r --arg n "$META" '.[]|select(.name==$n)|.id')"
{
 echo CLIENT_210_RELEASE_VERIFY_PASS
 echo PUBLISHED_RELEASE_ID=$RID
 echo PUBLISHED_ASSET_ID=$AID
 echo PUBLISHED_META_ASSET_ID=$MID
 echo PUBLISHED_SHA=$(cat client210_sha.txt)
 echo PUBLISHED_SIZE=$(cat client210_size.txt)
 echo META_SHA=$(cat client210_meta_sha.txt)
 echo META_SIZE=$(cat client210_meta_size.txt)
 echo SOURCE_COMMIT=$GITHUB_SHA
} | tee release-client-210-result.txt
