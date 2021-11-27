import unittest
import os
from padstogit import Core

from ipydex import IPS, activate_ips_on_exception
# activate_ips_on_exception()

# noinspection PyPep8Naming
class TestCore(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self) -> None:

        try:
            cwd = os.getcwd()
        except FileNotFoundError:
            # this happens before any test is run. Seems to be a quirk of unittest.
            return
        c = Core()
        c.purge_pad_repo(ignore_errors=True)
        

    def test_core1(self):
        c = Core()
        self.assertFalse(os.path.exists(c.repo_dir))
        c.init_pad_repo()
        self.assertTrue(os.path.isdir(c.repo_dir))
        self.assertTrue(os.path.isfile(c.checkfile))
        self.assertTrue(os.path.isdir(os.path.join(c.repo_dir, ".git")))

        self.assertRaises(FileExistsError, c.init_pad_repo)

        c.purge_pad_repo()
        self.assertFalse(os.path.exists(c.repo_dir))

        self.assertRaises(FileNotFoundError, c.purge_pad_repo)

        # ensure that the directory is only deleted if the special file is present
        c.init_pad_repo()
        os.rename(c.checkfile, f"{c.checkfile}_backup")
        self.assertRaises(FileNotFoundError, c.purge_pad_repo)
        self.assertTrue(os.path.isdir(c.repo_dir))

        # now delete the repo
        os.rename(f"{c.checkfile}_backup", c.checkfile)
        c.purge_pad_repo()
        self.assertFalse(os.path.exists(c.repo_dir))
