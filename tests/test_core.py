import unittest
import os
from padstogit import Core

from ipydex import IPS, activate_ips_on_exception
# activate_ips_on_exception()


TEST_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test-data"))

# noinspection PyPep8Naming
class TestCore(unittest.TestCase):

    def _set_workdir_to_project_root(self):
        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            # this happens before any test is run. Seems to be a quirk of unittest.
            project_root = os.path.dirname(os.path.dirname(__file__))
            os.chdir(project_root)

    def setUp(self):
        self._set_workdir_to_project_root()
        self.c = Core(testmode=True)

    def tearDown(self) -> None:
        self._set_workdir_to_project_root()
        
        self.c.purge_pad_repo(ignore_errors=True)
        del self.c

    def test_core1(self):

        self.assertEqual(self.c.repo_name, "padstogit-test-repo")
        self.assertFalse(os.path.exists(self.c.repo_dir))
        self.c.init_pad_repo()
        self.assertTrue(os.path.isdir(self.c.repo_dir))
        self.assertTrue(os.path.isfile(self.c.checkfile))
        self.assertTrue(os.path.isdir(os.path.join(self.c.repo_dir, ".git")))

        self.assertRaises(FileExistsError, self.c.init_pad_repo)

        self.c.purge_pad_repo()
        self.assertFalse(os.path.exists(self.c.repo_dir))

        self.assertRaises(FileNotFoundError, self.c.purge_pad_repo)

        # ensure that the directory is only deleted if the special file is present
        self.c.init_pad_repo()
        os.rename(self.c.checkfile, f"{self.c.checkfile}_backup")
        self.assertRaises(FileNotFoundError, self.c.purge_pad_repo)
        self.assertTrue(os.path.isdir(self.c.repo_dir))

        # now delete the repo
        os.rename(f"{self.c.checkfile}_backup", self.c.checkfile)
        self.c.purge_pad_repo()
        self.assertFalse(os.path.exists(self.c.repo_dir))

    def test_load_sources(self):

        self.c = self.c
        self.c.init_pad_repo()
        sources = self.c.load_pad_sources(os.path.join(TEST_DATA_DIR, "sources.yml"))

        self.assertEqual(len(sources), 3)
        
        self.assertEqual(sources[0]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad1")
        self.assertEqual(sources[0]["name"], "padstogit_testpad1.txt"        )
        
        self.assertEqual(sources[1]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad2")
        self.assertEqual(sources[1]["name"], "renamed_testpad.md"        )


    def test_download(self):
        
        self.c.init_pad_repo()
        



        

        


