import hashlib, io, json, sys, zipfile
from pathlib import Path

ROOT=Path.cwd()
BASE=ROOT/"SGP_ClientPatch_1.8.0.zip"
CHIPPED=ROOT/"chipped-neoforge-1.21.1-4.0.2.jar"
OUT=ROOT/"release-staging/1.8.1-test.1/compatmod/src/main/java/sgp/createchippedcutting/ChippedFamilies.java"

BASE_SHA="34c6f2b223892b92a1c6f1da0074802de474cfe4116fcd5c90e3d869081ef9bb"
CHIPPED_SHA="18ac6fd6b30db4922ccc6ee8bea5b113f69587505b7529834f37ace506427291"
OLD_DP="files/config/paxi/datapacks/SGP_Create_Chipped_Cutting_MC1.21.1.zip"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

assert sha(BASE)==BASE_SHA
assert sha(CHIPPED)==CHIPPED_SHA

with zipfile.ZipFile(BASE) as z:
    assert z.testzip() is None
    dp=z.read(OLD_DP)

old_routes=set()
with zipfile.ZipFile(io.BytesIO(dp)) as z:
    assert z.testzip() is None
    recipes=[n for n in z.namelist() if n.startswith("data/sgp_create_chipped_cutting/recipe/") and n.endswith(".json")]
    assert len(recipes)==6968
    for n in recipes:
        r=json.loads(z.read(n))
        old_routes.add((r["ingredients"][0]["tag"], r["results"][0]["id"]))
assert len(old_routes)==6968

families=set()
routes=set()
with zipfile.ZipFile(CHIPPED) as z:
    assert z.testzip() is None
    names=set(z.namelist())
    for name in sorted(names):
        if not (name.startswith("data/chipped/recipe/") and name.endswith(".json")):
            continue
        try:
            r=json.loads(z.read(name))
        except Exception:
            continue
        if r.get("type")!="chipped:workbench":
            continue
        for ing in r.get("ingredients",[]):
            tag=ing.get("tag") if isinstance(ing,dict) else None
            if isinstance(tag,str) and tag.startswith("chipped:"):
                families.add(tag)

    assert len(families)==277, len(families)
    for family in sorted(families):
        path=family.split(":",1)[1]
        name=f"data/chipped/tags/item/{path}.json"
        assert name in names, family
        t=json.loads(z.read(name))
        vals=t["values"]
        for raw in vals:
            if isinstance(raw,dict):
                raw=raw["id"]
            if ":" not in raw:
                raw="minecraft:"+raw
            if raw.startswith("chipped:"):
                routes.add((family,raw))

assert len(routes)==6968, len(routes)
assert routes==old_routes, (len(routes-old_routes),len(old_routes-routes))

lines=[
    "package sgp.createchippedcutting;",
    "",
    "import java.util.List;",
    "",
    "import net.minecraft.core.registries.Registries;",
    "import net.minecraft.resources.ResourceLocation;",
    "import net.minecraft.tags.TagKey;",
    "import net.minecraft.world.item.Item;",
    "",
    "final class ChippedFamilies {",
    "    private ChippedFamilies() {}",
    "",
    "    static final List<TagKey<Item>> TAGS = List.of("
]
for i,family in enumerate(sorted(families)):
    path=family.split(":",1)[1]
    comma="," if i<len(families)-1 else ""
    lines.append(f'        TagKey.create(Registries.ITEM, ResourceLocation.fromNamespaceAndPath("chipped", "{path}")){comma}')
lines += [
    "    );",
    "}",
    ""
]
OUT.parent.mkdir(parents=True,exist_ok=True)
OUT.write_text("\n".join(lines),"utf-8")

Path("hotfix_family_count.txt").write_text(str(len(families))+"\n","utf-8")
Path("hotfix_route_count.txt").write_text(str(len(routes))+"\n","utf-8")
print("HOTFIX_FAMILY_ROUTE_EQUIVALENCE_PASS")
print("FAMILIES="+str(len(families)))
print("OLD_REGISTERED_ROUTES="+str(len(old_routes)))
print("DYNAMIC_ROUTES="+str(len(routes)))
