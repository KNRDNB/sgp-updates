#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN missing}"
: "${REPO:?REPO missing}"
rm -rf audit && mkdir audit && cd audit

for V in 1.6.1 1.6.2 1.7.0-test.1; do
  gh release download "v$V" --repo "$REPO" -p "SGP_ClientPatch_$V.zip"
done

echo "83d7849366efe854f055edf5a148d2ca0494b2ed60f19c4ae064a8028c8aa63f  SGP_ClientPatch_1.6.1.zip" | sha256sum -c -
echo "1a864e6187875304319418b09f1b48082b782b77130530686060f7eb442c8896  SGP_ClientPatch_1.6.2.zip" | sha256sum -c -
echo "ae66f323b358b6b965573e1405a7a0c7f103c4ca39b1a61cfcff1401dfbed421  SGP_ClientPatch_1.7.0-test.1.zip" | sha256sum -c -

python3 - <<'PY'
import json, zipfile, collections
for fn in ["SGP_ClientPatch_1.6.1.zip","SGP_ClientPatch_1.6.2.zip","SGP_ClientPatch_1.7.0-test.1.zip"]:
    with zipfile.ZipFile(fn) as z:
        p=json.loads(z.read("patch.json"))
    print("===== "+fn+" =====")
    print("FROM", json.dumps(p["fromVersions"], ensure_ascii=False))
    print("TO", p["toVersion"], "ACTIONS", len(p["actions"]))
    print("TYPE_COUNTS", dict(collections.Counter(a["type"] for a in p["actions"])))
    for idx,a in enumerate(p["actions"]):
        out={"i":idx,"id":a["actionId"],"type":a["type"],"target":a.get("target"),"optional":a.get("optional"),"precondition":a.get("precondition")}
        if a["type"]=="copy":
            out.update(source=a.get("source"),sha256=a.get("sha256"),size=a.get("size"))
        elif a["type"]=="textReplaceExact":
            out.update(expectedOccurrences=a.get("expectedOccurrences"),hasAlreadyAppliedText=bool(a.get("alreadyAppliedText")))
        elif a["type"] in {"optionsEdit","tomlEdit","jsonEdit","iniEdit","propertiesEdit"}:
            out["edits"]=a.get("edits")
        elif a["type"]=="deleteGlob":
            out["pattern"]=a.get("pattern")
        print(json.dumps(out, ensure_ascii=False, separators=(",",":")))
    print("===== END =====")
PY
