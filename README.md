# sgp-updates
Official SGP Minecraft client patch releases for SGP Patch Installer

Post-cutover client channel: stable `client-vX.Y.Z`, TEST
`client-vX.Y.Z-test.N` (GitHub `prerelease=true`). Stable uses
`prerelease=false`. Future client versions must be greater than 2.0.0.
Exact assets are `SGP_ClientPatch_X.Y.Z.zip` and
`SGP_ClientPatch_X.Y.Z.meta.json`, including the `-test.N` suffix for TEST.
Names/bodies and GitHub global Latest do not identify a client release.
Activation is recorded in `client-channel.json` after accepted public Installer
2.0.0 and successful actual 1.2.8-to-2.0.0 live self-update. This file records
publisher activation and accepted Installer identity; the client graph remains
defined by immutable per-release metadata.

Corrected legacy client `v2.0.0` is the permanent last cumulative bridge:
release 405053216, ZIP asset 616399206, 21752630 bytes, SHA-256
`1fd2139e0aeee986cd57728eec9b8783b2e37691b212da9e5951b0cf07bc263a`.
Historical releases/tags/assets stay immutable. Installer 1.2.8 ignores the
new client namespace; Installer 2.0.0 bridges older supported installations
before applying independently committed sequential hops. No new client patch
is published by channel activation.

Metadata is UTF-8 JSON, at most 65536 bytes, with exactly these required fields:
`schemaVersion`, `channel`, `tag`, `patchId`, `targetPackId`, `minecraft`,
`neoforge`, `patchSchemaVersion`, `fromVersions`, `toVersion`, `assetName`,
`assetSize`, `sha256`, `minInstallerVersion`. Both schema values are 1;
platform is `sgp-neoforge-1.21.1-client` / Minecraft 1.21.1 / NeoForge 21.1.249.
Metadata must match exact ZIP bytes and internal `patch.json` bindings.
No duplicate/unknown fields or download URLs. Minimum Installer is at least
2.0.0 and must already be accepted. Source versions are unique, at least
2.0.0 and strictly below the target. Ordinary new stable patches are deltas
from the immediate accepted predecessor, plus only justified/tested forward
repair sources. TEST is never an intermediate stable route node.

All future publishers must run the guard (Python 3.11+, standard library):

```powershell
python scripts/client-release-guard.py --tag client-vX.Y.Z --channel stable --zip SGP_ClientPatch_X.Y.Z.zip --metadata SGP_ClientPatch_X.Y.Z.meta.json
```

This command is read-only. After the existing package, runtime and owner
authorization gates, add `--publish --notes reviewed-release-notes.md` to
create a new Draft, download and verify both assets, and make it public.
For TEST use `--channel test` and the exact TEST version in every identity.
Existing tags/releases are refused, including orphan tags. Failed Draft
verification leaves Draft. A mandatory live-public exact-pair/package smoke
still follows publication; product FAIL immediately returns that new release
to Draft. This binding guard does not prove filesystem compatibility or
Minecraft gameplay. Existing single-current-TEST lifecycle remains in force.

Guard self-checks: `python scripts/test_client_release_guard.py`.
Authoritative product context: private `KNRDNB/sgp-context` and
`KNRDNB/SGPPatchInstaller`; canonical pointer `SGP_PROJECT_POINTER.md` in
the context repository.

Release title is `SGP Client X.Y.Z` (or `SGP Client X.Y.Z-test.N`); the `client-v...` tag remains the authoritative release identity.
