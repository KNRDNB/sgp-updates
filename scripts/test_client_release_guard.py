import importlib.util
import json
import pathlib
import tempfile
import unittest
import zipfile
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("guard", pathlib.Path(__file__).with_name("client-release-guard.py"))
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="SGP-guard-synthetic-")
        self.root = pathlib.Path(self.temp.name)
        (self.root / ".synthetic-fixture").write_text("Metadata guard fixture only")
        self.zip = self.root / "SGP_ClientPatch_2.1.0.zip"
        self.meta = self.root / "SGP_ClientPatch_2.1.0.meta.json"
        self.m = dict(schemaVersion=1, channel="stable", tag="client-v2.1.0", patchId="synthetic-2.1.0", targetPackId="sgp-neoforge-1.21.1-client", minecraft="1.21.1", neoforge="21.1.249", patchSchemaVersion=1, fromVersions=["2.0.0"], toVersion="2.1.0", assetName=self.zip.name, minInstallerVersion="2.0.0", assetSize=0, sha256="")
        p = {k: self.m[k] for k in ("schemaVersion", "patchId", "targetPackId", "minecraft", "neoforge", "fromVersions", "toVersion")}
        p["actions"] = []
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr("patch.json", json.dumps(p))
        self.m.update(assetSize=self.zip.stat().st_size, sha256=guard.digest(self.zip))
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.meta.write_text(json.dumps(self.m), encoding="utf-8")

    def check(self, tag="client-v2.1.0", channel="stable"):
        return guard.validate(tag, channel, self.zip, self.meta)

    def test_exact_pair(self):
        self.assertEqual(self.check(), self.m)

    def test_legacy_tag(self):
        with self.assertRaises(ValueError): self.check("v2.1.0")

    def test_unknown_field(self):
        self.m["downloadUrl"] = "https://example.invalid/evil"; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_duplicate_property(self):
        self.meta.write_text('{"schemaVersion":1,' + self.meta.read_text()[1:])
        with self.assertRaises(ValueError): self.check()

    def test_hash_size_binding(self):
        for key, value in (("sha256", "0" * 64), ("assetSize", self.m["assetSize"]+1), ("assetSize", True)):
            with self.subTest(key=key, value=value):
                previous = self.m[key]; self.m[key] = value; self.save()
                with self.assertRaises(ValueError): self.check()
                self.m[key] = previous

    def test_manifest_binding(self):
        self.m["patchId"] = "different-id"; self.save()
        with self.assertRaises(ValueError): self.check()

    def test_downgrade_duplicate_legacy_sources(self):
        for sources in (["2.1.0"], ["1.9.1"], ["2.0.0", "2.0.0"], [], ["02.0.0"]):
            with self.subTest(sources=sources):
                self.m["fromVersions"] = sources; self.save()
                with self.assertRaises(ValueError): self.check()

    def test_channel(self):
        with self.assertRaises(ValueError): self.check(channel="test")

    def test_valid_test_pair(self):
        target = "2.1.0-test.0"
        self.zip = self.root / ("SGP_ClientPatch_" + target + ".zip")
        self.meta = self.root / ("SGP_ClientPatch_" + target + ".meta.json")
        self.m.update(channel="test", tag="client-v" + target, toVersion=target, assetName=self.zip.name)
        p = {k: self.m[k] for k in ("schemaVersion", "patchId", "targetPackId", "minecraft", "neoforge", "fromVersions", "toVersion")}
        with zipfile.ZipFile(self.zip, "w") as z: z.writestr("patch.json", json.dumps(p))
        self.m.update(assetSize=self.zip.stat().st_size, sha256=guard.digest(self.zip)); self.save()
        self.assertEqual(self.check("client-v" + target, "test"), self.m)

    def test_minimum_installer(self):
        for minimum in ("1.2.8", "2.0.0-test.1", "02.0.0"):
            self.m["minInstallerVersion"] = minimum; self.save()
            with self.assertRaises(ValueError): self.check()

    def test_semver_order(self):
        self.assertLess(guard.compare("2.1.0-test.9", "2.1.0-test.10"), 0)
        self.assertLess(guard.compare("2.1.0-test.10", "2.1.0"), 0)
        self.assertLess(guard.compare("2.1.0", "2.10.0"), 0)

    def test_bounded_utf8(self):
        for raw in (b"\xef\xbb\xbf{}", b"\xff", b"x"*65537):
            self.meta.write_bytes(raw)
            with self.assertRaises((ValueError, UnicodeError)): self.check()

    def test_revoked_or_changed_installer_blocks_publication(self):
        assets = [dict(name="SGP-Patch-Installer.exe", id=123, size=140428583, digest="sha256:"+"a"*64, state="uploaded"), dict(name="SGP-Patch-Installer.exe.sha256", id=124, size=91, digest="sha256:"+"b"*64, state="uploaded")]
        config = dict(state="ACTIVE", livePublicSelfUpdate="PASS", installerTag="installer-v2.0.0", installerReleaseId=11, installerVersion="2.0.0", installerSHA256="a"*64, installerBytes=140428583, installerAssets=assets)
        (self.root / "client-channel.json").write_text(json.dumps(config))
        release = dict(draft=False, prerelease=False, id=11, assets=assets)
        with patch.object(guard, "ROOT", self.root), patch.object(guard, "gh", return_value=SimpleNamespace(stdout=json.dumps(release))):
            guard.activation(self.m)
        for changed in (dict(release, draft=True), dict(release, prerelease=True), dict(release, assets=[assets[0], dict(assets[1], digest="sha256:"+"c"*64)])):
            with patch.object(guard, "ROOT", self.root), patch.object(guard, "gh", return_value=SimpleNamespace(stdout=json.dumps(changed))):
                with self.assertRaises(ValueError): guard.activation(self.m)


    def test_release_title_convention(self):
        self.assertEqual("SGP Client " + self.m["toVersion"], "SGP Client 2.1.0")

    def test_existing_tag_is_never_replaced(self):
        args = SimpleNamespace(notes=self.root / "notes.md", tag="client-v2.1.0")
        with patch.object(guard, "activation"), patch.object(guard, "gh", return_value=SimpleNamespace(returncode=0, stderr="")) as call:
            with self.assertRaises(ValueError): guard.publish(args, self.m)
            self.assertEqual(call.call_count, 1)
            self.assertEqual(call.call_args.args[:2], ("release", "view"))

    def test_orphan_tag_is_never_replaced(self):
        args = SimpleNamespace(notes=self.root / "notes.md", tag="client-v2.1.0")
        responses = [SimpleNamespace(returncode=1, stderr="release not found"), SimpleNamespace(returncode=1, stderr="gh: Not Found (HTTP 404)"), SimpleNamespace(returncode=0, stderr="")]
        with patch.object(guard, "activation"), patch.object(guard, "gh", side_effect=responses) as call:
            with self.assertRaises(ValueError): guard.publish(args, self.m)
            self.assertEqual(call.call_count, 3)
            self.assertEqual(call.call_args.args[1], "repos/KNRDNB/sgp-updates/git/ref/tags/client-v2.1.0")

    def test_unavailable_installer_blocks_publication(self):
        config = dict(state="INACTIVE", livePublicSelfUpdate="PENDING")
        (self.root / "client-channel.json").write_text(json.dumps(config))
        with patch.object(guard, "ROOT", self.root), patch.object(guard, "gh") as network:
            with self.assertRaises(ValueError): guard.activation(self.m)
            network.assert_not_called()

if __name__ == "__main__":
    unittest.main()
