import unittest
import os
import glob
from padstogit import Core, APPNAME
import subprocess

from ipydex import IPS, activate_ips_on_exception, TracerFactory

ST = TracerFactory()  # useful for debugging
# activate_ips_on_exception()


TEST_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test-data"))
TEST_SOURCES = os.path.join(TEST_DATA_DIR, "sources.yml")

# noinspection PyPep8Naming
class PTG_TestCase(unittest.TestCase):
    def _set_workdir_to_project_root(self):

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


class TestCore(PTG_TestCase):
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

        self.c.init_pad_repo()
        sources = self.c.load_pad_sources(TEST_SOURCES)

        self.assertEqual(len(sources), 3)

        self.assertEqual(sources[0]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad1")
        self.assertEqual(sources[0]["name"], "padstogit_testpad1.txt")

        self.assertEqual(sources[1]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad2")
        self.assertEqual(sources[1]["name"], "renamed_testpad.md")

    def test_download_and_commit(self):

        self.c.init_pad_repo()
        self.c.download_pad_contents(sources_path=TEST_SOURCES)

        res_txt = glob.glob(os.path.join(self.c.repo_dir, "pads", "*.txt"))
        res_md = glob.glob(os.path.join(self.c.repo_dir, "pads", "*.md"))

        self.assertEqual(len(res_txt), 2)
        self.assertEqual(len(res_md), 1)

        changed_files = self.c.make_commit()

        self.assertEqual(len(changed_files), 3)

        changed_files = self.c.make_commit()
        self.assertEqual(len(changed_files), 0)

        pad_path = os.path.join(
            self.c.repo_parent_path, self.c.repo_name, "pads", "padstogit_testpad1.txt"
        )
        with open(pad_path, "w") as txtfile:
            txtfile.write("unittest!\n")

        changed_files = self.c.make_commit()
        self.assertEqual(len(changed_files), 1)


def run(cmd):

    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    assert isinstance(cmd, list)

    res = subprocess.run(cmd, capture_output=True)
    res.stdout = res.stdout.decode("utf8")
    res.stderr = res.stderr.decode("utf8")

    return res


class TestCommandLine(PTG_TestCase):
    def test_print_config(self):
        res = run([APPNAME, "--print-config"])

        self.assertEqual(res.returncode, 0)
        self.assertNotIn("None", res.stdout)


if __name__ == "__main__":
    unittest.main()
