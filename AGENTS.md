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
