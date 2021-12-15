import unittest
import os
import glob
import subprocess
import shutil
import tempfile
import time

import padstogit as appmod
from padstogit import Core, APPNAME

from ipydex import IPS, activate_ips_on_exception, TracerFactory

ST = TracerFactory()  # useful for debugging
# activate_ips_on_exception()

timestr = time.strftime('%Y-%m-%d--%H-%M-%S')


TEST_WORK_DIR = tempfile.mkdtemp(prefix=timestr)

# This is where the persistent test data is stored
# (not where data is created and manipulated) during tests
TEST_DATA_STORAGE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "test-data"))

TEST_CONFIGFILE_PATH = os.path.abspath(
    os.path.join(TEST_WORK_DIR, "test-config", "settings.yml")
)


# TEST_SOURCES = os.path.join(TEST_DATA_STORAGE_DIR, "sources.yml")  #!!

# noinspection PyPep8Naming
class PTG_TestCase(unittest.TestCase):
    def _set_workdir(self):

        # the unit test framework seems to mess up the current working dir
        # -> we better set it explicitly
        os.chdir(TEST_WORK_DIR)

    def _store_otddc(self):

        self._set_workdir()
        self.original_test_data_dir_content = os.listdir(".")


    def _setup_env(self):
        self._set_workdir()
        # this is necessary because we will call scripts via subprocess
        self.environ = {}
        self.environ[f"{APPNAME}_DATADIR_PATH"] = TEST_WORK_DIR
        self.environ[f"{APPNAME}_CONFIGFILE_PATH"] = TEST_CONFIGFILE_PATH
        self._store_otddc()


    def setUp(self):
        self._setup_env()
        os.environ.update(self.environ)
        appmod.bootstrap_app(configfile_path=TEST_CONFIGFILE_PATH)
        self.c = Core()

    def _restore_otddc(self):

        # delete all files and directories which have not been present before this test:
        self._set_workdir()

        new_content = [
            name for name in os.listdir("./") if name not in self.original_test_data_dir_content
        ]

        for name in new_content:
            if os.path.isfile(name):
                os.remove(name)
            elif os.path.isdir(name):
                shutil.rmtree(name)

    def tearDown(self) -> None:
        self._restore_otddc()


class TestCore(PTG_TestCase):
    
    @unittest.expectedFailure
    def test_core1(self):

        self.assertEqual(self.c.repo_name, "padstogit-test-repo")
        self.assertFalse(os.path.exists(self.c.default_repo_dir))
        self.c.init_archive_repo()
        self.assertTrue(os.path.isdir(self.c.default_repo_dir))
        self.assertTrue(os.path.isfile(self.c.checkfile))
        self.assertTrue(os.path.isdir(os.path.join(self.c.default_repo_dir, ".git")))

        self.assertRaises(FileExistsError, self.c.init_archive_repo)

        self.c.purge_pad_repo()
        self.assertFalse(os.path.exists(self.c.default_repo_dir))

        self.assertRaises(FileNotFoundError, self.c.purge_pad_repo)

        # ensure that the directory is only deleted if the special file is present
        self.c.init_archive_repo()
        os.rename(self.c.checkfile, f"{self.c.checkfile}_backup")
        self.assertRaises(FileNotFoundError, self.c.purge_pad_repo)
        self.assertTrue(os.path.isdir(self.c.default_repo_dir))

        # now delete the repo
        os.rename(f"{self.c.checkfile}_backup", self.c.checkfile)
        self.c.purge_pad_repo()
        self.assertFalse(os.path.exists(self.c.default_repo_dir))

    def test_load_sources1(self):

        repodir = self.c.repo_paths[0]
        self.assertTrue(repodir.startswith(TEST_WORK_DIR))
        sources = self.c.load_webdoc_sources(repodir)

        self.assertEqual(len(sources), 3)

        self.assertEqual(sources[0]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad1")
        self.assertEqual(sources[0]["name"], "padstogit_testpad1.txt")

        self.assertEqual(sources[1]["url"], "https://etherpad.wikimedia.org/p/padstogit_testpad2")
        self.assertEqual(sources[1]["name"], "renamed_testpad.md")

    def test_download_and_commit(self):

        repo_path = self.c.repo_paths[0]
        self.c.download_pad_contents(repo_path)

        res_txt = glob.glob(os.path.join(self.c.repo_paths[0], appmod.REPO_DATA_DIR_NAME, "*.txt"))
        res_md = glob.glob(os.path.join(self.c.repo_paths[0], appmod.REPO_DATA_DIR_NAME, "*.md"))

        self.assertEqual(len(res_txt), 2)
        self.assertEqual(len(res_md), 1)

        changed_files = self.c.make_commit(repo_path)

        self.assertEqual(len(changed_files), 3)

        changed_files = self.c.make_commit(repo_path)
        self.assertEqual(len(changed_files), 0)

        pad_path = os.path.join(repo_path, appmod.REPO_DATA_DIR_NAME, "padstogit_testpad1.txt")
        with open(pad_path, "w") as txtfile:
            txtfile.write("unittest!\n")

        changed_files = self.c.make_commit(repo_path)
        self.assertEqual(len(changed_files), 1)

    def test_handle_all_repos(self):
        res = self.c.handle_all_repos()


def run_command(cmd, env: dict) -> subprocess.CompletedProcess:

    complete_env = {**os.environ, "NO_IPS_EXCEPTHOOK": "True", **env}

    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    assert isinstance(cmd, list)

    res = subprocess.run(cmd, capture_output=True, env=complete_env)
    res.stdout = res.stdout.decode("utf8")
    res.stderr = res.stderr.decode("utf8")

    return res


class TestCommandLine(PTG_TestCase):
    def test_print_config(self):

        res1 = run_command([APPNAME, "--bootstrap-config"], self.environ)
        self.assertEqual(res1.returncode, 0)

        res2 = run_command([APPNAME, "--print-config"], self.environ)
        self.assertEqual(res2.returncode, 0)
        self.assertNotIn("None", res2.stdout)

    def test_run_main(self):
        res = run_command([APPNAME], self.environ)

        self.assertEqual(res.returncode, 0)


class TestBootstrap(PTG_TestCase):
    def setUp(self):
        self.environ = {}
        self.environ[f"{APPNAME}_DATADIR_PATH"] = TEST_WORK_DIR
        os.environ.update(self.environ)
        self._store_otddc()

    def tearDown(self):
        os.remove(TEST_CONFIGFILE_PATH)
        self._restore_otddc()

    def test_bootstrap_config(self):

        self.assertFalse(os.path.isfile(TEST_CONFIGFILE_PATH))

        appmod.bootstrap_config(TEST_CONFIGFILE_PATH)
        config_dict = appmod.load_config(TEST_CONFIGFILE_PATH)

        self.assertIsInstance(config_dict, dict)

    def test_bootstrap_data_work_dir(self):

        with self.assertRaises(FileNotFoundError) as cm:
            appmod.bootstrap_datadir(configfile_path=TEST_CONFIGFILE_PATH)

        appmod.bootstrap_config(TEST_CONFIGFILE_PATH)
        config_dict = appmod.load_config(TEST_CONFIGFILE_PATH)

        datadir_path = appmod.bootstrap_datadir(configfile_path=TEST_CONFIGFILE_PATH)
        self.assertEqual(datadir_path, TEST_WORK_DIR)



if __name__ == "__main__":
    unittest.main()
