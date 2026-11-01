# Official SGP release transport

Client conventions are defined in `README.md` and authoritative
`KNRDNB/sgp-context/SGP_CLIENT_CONTEXT.md`. Existing client/server runtime and
owner authorization gates remain mandatory. Installer acceptance is not a
Minecraft runtime PASS.

For every new client release above 2.0.0, use `scripts/client-release-guard.py`
before publication. Stable: `client-vX.Y.Z`; TEST: `client-vX.Y.Z-test.N`. Release title: `SGP Client X.Y.Z` / `SGP Client X.Y.Z-test.N`; the tag remains the authoritative identity.
Publish exactly the canonical ZIP and strict `.meta.json` pair. The guarded
`--publish` path verifies accepted Installer identity, rejects existing
tags/releases, creates Draft, downloads/verifies both assets, then publishes.
Run the mandatory live-public exact-pair/package smoke afterward; on product
FAIL return only the newly created failed release to Draft and diagnose.

Never modify historical workflows/releases/tags/assets or the pinned corrected
legacy `v2.0.0` bridge. New publication workflows must invoke this guard before
creating/promoting Draft. Never publish a client patch merely to activate this
channel. Use only marked synthetic packs for destructive Installer tests.


## Dedicated server channel (owner decision 2026-11-01)

Future finalized server handoffs use durable stable `server-vX.Y.Z` releases with exact `SGP_ServerPatch_X.Y.Z.zip` + strict `.meta.json`; bounded static `server/latest.json` activates last. See `server/README.md`, `scripts/server-release-guard.py` and explicitly dispatched `publish-server-release.yml`. Never rebuild/repack an existing handoff for promotion. Retain run/artifact/SHA/size evidence, use Draft IDs before tag creation, verify downloaded Draft/public bytes, preserve all accepted historical assets. Initial2.0.10 uses original immutable bytes; historical manual installs/accepted-good facts are unchanged.

Explicit owner release authorization is still required before server packaging/publication; do not build server candidates in client TEST iterations or infer authorization from client runtime PASS. Russian changelog, exact deletions/fromVersions/minInstallerVersion, and reviewed `files|snapshot` risk mode are mandatory. Snapshot for world/persistent/worldgen/Minecraft/NeoForge risk; panel Backup/Stop/Start stays manual. Patch data never supplies shell/scripts/commands/arbitrary URLs. Server/client/Installer namespaces and selection remain separate. Installer2.2.0 candidate is not public until its owner visual + read-only live SFTP gates pass.
