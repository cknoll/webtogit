import sys
from io import StringIO
import unittest
import os
from contextlib import contextmanager
import glob
import subprocess
import shutil
import tempfile
import time
import logging

import webtogit as appmod
from webtogit import Core, APPNAME, DEFAULT_REPO_NAME

# useful for debugging:
from ipydex import IPS, activate_ips_on_exception, TracerFactory

ST = TracerFactory()
# activate_ips_on_exception()
DEBUG = False

timestr = time.strftime("%Y-%m-%d--%H-%M-%S")


TEST_WORK_DIR = tempfile.mkdtemp(prefix=timestr)


TEST_CONFIGFILE_PATH = os.path.abspath(os.path.join(TEST_WORK_DIR, "test-config", "settings.yml"))


# noinspection PyPep8Naming
class Abstract_WTG_TestCase(unittest.TestCase):
    @staticmethod
    def _set_workdir():

        # the unit test framework seems to mess up the current working dir
        # -> we better set it explicitly
        os.chdir(TEST_WORK_DIR)

    def _store_otddc(self):
        """
        Store original test data dir content
        :return:
        """

        self._set_workdir()
        self.original_test_data_dir_content = os.listdir(".")

    def _setup_env(self):
        self._set_workdir()
        # this is necessary because we will call scripts via subprocess
        self.environ = {
            f"{APPNAME}_DATADIR_PATH": TEST_WORK_DIR,
            f"{APPNAME}_CONFIGFILE_PATH": TEST_CONFIGFILE_PATH,
        }
        self._store_otddc()

    @staticmethod
    def _bootstrap_app():
        logging.disable(logging.CRITICAL)
        appmod.bootstrap_app(configfile_path=TEST_CONFIGFILE_PATH)
        logging.disable(logging.NOTSET)

    def setUp(self):

        if DEBUG:
            print(f"--------- {self.__class__.__name__}.{self._testMethodName} --------------")

        self._setup_env()
        os.environ.update(self.environ)

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


class TestCore(Abstract_WTG_TestCase):
    def setUp(self):
        super().setUp()
        self._bootstrap_app()
        self.c = Core()

    def test_load_sources1(self):

        repodir = self.c.repo_paths[0]
        self.assertTrue(repodir.startswith(TEST_WORK_DIR))
        sources = self.c.load_webdoc_sources(repodir)

        self.assertEqual(len(sources), 3)

        self.assertEqual(sources[0]["url"], "https://etherpad.wikimedia.org/p/webtogit_testpad1")
        self.assertEqual(sources[0]["name"], "webtogit_testpad1.txt")

        self.assertEqual(sources[1]["url"], "https://etherpad.wikimedia.org/p/webtogit_testpad2")
        self.assertEqual(sources[1]["name"], "renamed_testpad.md")

    def test_download_and_commit(self):

        repo_path = self.c.repo_paths[0]
        self.c.download_source_contents(repo_path)

        res_txt = glob.glob(os.path.join(self.c.repo_paths[0], appmod.REPO_DATA_DIR_NAME, "*.txt"))
        res_md = glob.glob(os.path.join(self.c.repo_paths[0], appmod.REPO_DATA_DIR_NAME, "*.md"))

        self.assertEqual(len(res_txt), 2)
        self.assertEqual(len(res_md), 1)

        changed_files = self.c.make_commit(repo_path)

        self.assertEqual(len(changed_files), 3)

        changed_files = self.c.make_commit(repo_path)
        self.assertEqual(len(changed_files), 0)

        pad_path = os.path.join(repo_path, appmod.REPO_DATA_DIR_NAME, "webtogit_testpad1.txt")
        with open(pad_path, "w") as txtfile:
            txtfile.write("unittest!\n")

        changed_files = self.c.make_commit(repo_path)
        self.assertEqual(len(changed_files), 1)

    def test_handle_all_repos(self):
        res = self.c.handle_all_repos(print_flag=False)
        # TODO!!: add actual test


def run_command(cmd, env: dict, print_full_cmd=False) -> subprocess.CompletedProcess:
    """

    :param cmd:
    :param env:
    :param print_full_cmd:  boolean flag; usefull to debug that exact command (with that env)
    :return:
    """
    complete_env = {**os.environ, "NO_IPS_EXCEPTHOOK": "True", **env}

    if isinstance(cmd, str):
        cmd = cmd.split(" ")
    assert isinstance(cmd, list)

    tokes = [f'{key}="{value}";' for key, value in complete_env.items()] + cmd
    full_command = " ".join(tokes)
    if print_full_cmd:
        print(f"→ CMD: {full_command}")

    res = subprocess.run(cmd, capture_output=True, env=complete_env)
    res.stdout = res.stdout.decode("utf8")
    res.stderr = res.stderr.decode("utf8")
    res.full_command = full_command

    return res


class TestCommandLine(Abstract_WTG_TestCase):
    def test_print_config(self):
        # first, run without any bootstrapping:
        res = run_command([APPNAME, "--print-config"], self.environ)
        self.assertEqual(res.returncode, 2)
        self.assertIn("`--bootstrap` first", res.stderr)

        res1 = run_command([APPNAME, "--bootstrap-config"], self.environ)
        self.assertEqual(res1.returncode, 0)

        res2 = run_command([APPNAME, "--print-config"], self.environ)
        self.assertEqual(res2.returncode, 0)
        self.assertNotIn("None", res2.stdout)

    def test_run_main_regular(self):

        self._bootstrap_app()

        res = run_command([APPNAME], self.environ)
        self.assertEqual(res.returncode, 0)

        res = run_command([APPNAME, DEFAULT_REPO_NAME], self.environ)
        self.assertEqual(res.returncode, 0)

        res = run_command([APPNAME, "--update-all-repos"], self.environ)
        self.assertEqual(res.returncode, 0)

    def test_run_main_nonedefault_reponame(self):

        self._bootstrap_app()

        res = run_command([APPNAME, "--print-config"], self.environ)
        self.assertIn("number_of_repos: 1", res.stdout)

        res = run_command([APPNAME, "nonedefault_reponame"], self.environ)
        self.assertEqual(res.returncode, 3)

        res = run_command([APPNAME, "--bootstrap-repo", "nonedefault_reponame"], self.environ)
        self.assertEqual(res.returncode, 0)
        self.assertNotIn("Nothing done", res.stdout)

        res = run_command([APPNAME, "--print-config"], self.environ)
        self.assertIn("number_of_repos: 2", res.stdout)

        # ensure idempotence
        res = run_command([APPNAME, "--bootstrap-repo", "nonedefault_reponame"], self.environ)
        self.assertEqual(res.returncode, 0)
        self.assertIn("Nothing done", res.stdout)

        res = run_command([APPNAME, "nonedefault_reponame"], self.environ)
        self.assertEqual(res.returncode, 0)

        res = run_command([APPNAME, "--update-all-repos"], self.environ)
        self.assertEqual(res.returncode, 0)

        self.assertIn(DEFAULT_REPO_NAME, res.stdout)
        self.assertIn("nonedefault_reponame", res.stdout)


    def test_run_main_without_bootstrap(self):
        # first, run without any bootstrapping:

        res = run_command([APPNAME], self.environ)
        self.assertEqual(res.returncode, 2)
        self.assertIn("--bootstrap", res.stderr)

        # now, run with only stage 1 bootstrapping (config):
        res = run_command([APPNAME, "--bootstrap-config"], self.environ)
        self.assertEqual(res.returncode, 0)

        res = run_command([APPNAME], self.environ)
        self.assertEqual(res.returncode, 3)
        self.assertIn("--bootstrap", res.stderr)

    def test_run_bootstrap_repo(self):
        res = run_command([APPNAME, "--bootstrap"], self.environ)
        self.assertEqual(res.returncode, 0)

        # the app is already bootstrapped
        res = run_command([APPNAME, "--bootstrap"], self.environ)
        self.assertEqual(res.returncode, 0)
        self.assertIn("already bootstrapped", res.stdout)


class TestBootstrap(Abstract_WTG_TestCase):
    def setUp(self):
        self.environ = {f"{APPNAME}_DATADIR_PATH": TEST_WORK_DIR}
        os.environ.update(self.environ)
        self._store_otddc()
        logging.disable(logging.CRITICAL)

    def tearDown(self):
        logging.disable(logging.NOTSET)
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

    def test_bootstrap_new_repo(self):

        appmod.bootstrap_config(TEST_CONFIGFILE_PATH)
        c = Core(configfile_path=TEST_CONFIGFILE_PATH)

        dirname = "test_repo_2"
        c.init_archive_repo(dirname)
        repos = c.find_repos()

        self.assertTrue(dirname in str(repos))


if __name__ == "__main__":
    unittest.main()
