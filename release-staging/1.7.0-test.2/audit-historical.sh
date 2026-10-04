#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN missing}"
: "${REPO:?REPO missing}"
rm -rf audit && mkdir audit && cd audit

gh release download v1.6.1 --repo "$REPO" -p SGP_ClientPatch_1.6.1.zip
gh release download v1.6.2 --repo "$REPO" -p SGP_ClientPatch_1.6.2.zip
gh release download v1.7.0-test.1 --repo "$REPO" -p SGP_ClientPatch_1.7.0-test.1.zip

echo "83d7849366efe854f055edf5a148d2ca0494b2ed60f19c4ae064a8028c8aa63f  SGP_ClientPatch_1.6.1.zip" | sha256sum -c -
echo "1a864e6187875304319418b09f1b48082b782b77130530686060f7eb442c8896  SGP_ClientPatch_1.6.2.zip" | sha256sum -c -
echo "ae66f323b358b6b965573e1405a7a0c7f103c4ca39b1a61cfcff1401dfbed421  SGP_ClientPatch_1.7.0-test.1.zip" | sha256sum -c -

python3 - <<'PY'
import json, zipfile
for fn in ["SGP_ClientPatch_1.6.1.zip","SGP_ClientPatch_1.6.2.zip","SGP_ClientPatch_1.7.0-test.1.zip"]:
    with zipfile.ZipFile(fn) as z:
        p=json.loads(z.read("patch.json"))
    print("===== "+fn+" =====")
    print(json.dumps(p, ensure_ascii=False, indent=2))
    print("===== END "+fn+" =====")
PY
