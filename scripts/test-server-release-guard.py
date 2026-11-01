import importlib.util, pathlib, unittest

spec=importlib.util.spec_from_file_location('guard',pathlib.Path(__file__).with_name('server-release-guard.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class GuardTests(unittest.TestCase):
    def metadata(self):
        return dict(schemaVersion=1,channel='stable',tag='server-v2.0.10',packId=g.PACK,familyId=g.FAMILY,side='server',fromVersions=['2.0.9'],toVersion='2.0.10',minInstallerVersion='2.2.0',assetName='SGP_ServerPatch_2.0.10.zip',sha256='a'*64,size=100,deletions=['mods/old.jar'],changelog='Исправление сервера.',backupMode='snapshot')
    def test_official_identity(self):
        g.validate_metadata(self.metadata())
        for key,value in [('tag','client-v2.0.10'),('packId','foreign'),('side','client'),('backupMode','execute'),('assetName','other.zip'),('url','https://evil.invalid'),('command','rm -rf /')]:
            with self.subTest(key=key),self.assertRaises(ValueError):
                m=self.metadata();m[key]=value;g.validate_metadata(m)
    def test_duplicate_and_size(self):
        with self.assertRaises(ValueError):g.parse(b'{"x":1,"x":2}')
        with self.assertRaises(ValueError):g.parse(b' '*65537)
    def test_confined_exact_paths(self):
        for path in ['../mods/a.jar','/mods/a.jar','mods\\a.jar','mods//a.jar','mods/CON.jar','.sgp/pack.json','mods/a.exe','config/a.ps1','world/level.dat']:
            with self.subTest(path=path),self.assertRaises(ValueError):g.target(path,'files')
        g.target('world/level.dat','snapshot')
    def test_forward_only_and_minimum(self):
        for source in ['2.0.10','2.0.11','02.0.9','2.0.9-test.1']:
            with self.subTest(source=source),self.assertRaises(ValueError):
                m=self.metadata();m['fromVersions']=[source];g.validate_metadata(m)

if __name__=='__main__':unittest.main()
