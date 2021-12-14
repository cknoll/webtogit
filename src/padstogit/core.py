import os
import shutil
import requests
from typing import List
import pathlib

import git
import yaml
import appdirs
from ipydex import IPS, activate_ips_on_exception, TracerFactory

from . import util as u


ST = TracerFactory()

activate_ips_on_exception()


safty_explanation = """
# The presence (not the content) of this file is checked before the repo is purged.
# This should prevent the software from accidentally deleting an unwanted directory
# e.g. due to mistakes in configuration file.
"""

gitignore_content = f"""

log.txt

{safty_explanation}
.padstogit
"""

APPNAME = "padstogit"

DEFAULT_DATADIR_PATH = appdirs.user_data_dir(appname=APPNAME)
DEFAULT_CONFIGFILE_PATH = os.path.join(appdirs.user_config_dir(appname=APPNAME), "settings.yml")


DEFAULT_CONFIGFILE_CONTENT = f"""
# This is the configuration file for {APPNAME}. It uses key-value-pairs in YAML format.

# this is the parent directories where alll repositories are located
datadir_path: "{DEFAULT_DATADIR_PATH}"

default_repo_name: "archived-webdocs"

readme_content: "This repo was generated by padstogit\\n"
"""

CHECKFILE_NAME = f".{APPNAME}"



class Core:
    """
    Main class which holds all information
    """

    def __init__(self, testmode=None, configfile_path=None, datadir_path=None):

        self.datadir_path = (
            datadir_path or os.getenv(f"{APPNAME}_DATADIR_PATH") or DEFAULT_DATA_PATH
        )
        self.configfile_path = (
            configfile_path
            or os.getenv(f"{APPNAME}_CONFIGFILE_PATH")
            or DEFAULT_CONFIGFILE_PATH
        )
        self.sources_path = None
        self.settings = None
        self.repo_parent_path = None
        self.repo_name = None

        if testmode is None:
            testmode = os.getenv(f"{APPNAME}_TESTMODE")
        self.testmode = testmode

        self._ensure_existing_dirs()
        self.load_settings()

        self.repos = None
        self._find_repos()


    def _ensure_existing_dirs(self):

        os.makedirs(self.datadir_path, exist_ok=True)
        os.makedirs(self.configfile_path, exist_ok=True)

    def load_settings(self):

        os.chdir(self.configfile_path)

        if self.testmode or os.getenv(f"{APPNAME}_TESTMODE"):
            repo_name = f"{APPNAME}-test-repo"
        else:
            repo_name = "archived-pads"

        self.sources_path = os.path.join(self.datadir_path, "sources.yml")


        # this simplifies testing
        project_root = pathlib.Path(__file__).parents[2]
        if os.path.isfile(os.path.join(project_root, "setup.py")):
            self.settings["sources"] = os.path.join(project_root, "example-data", "sources.yml")

        self.repo_parent_path = os.path.abspath(self.settings["repo_parent_path"])
        self.repo_name = self.settings["repo_name"]

    def _find_repos(self):

        os.chdir(self.datadir_path)
        dircontent = os.listdir("./")
        repos = []
        for name in dircontent:
            if not os.path.isdir(name):
                continue
            if not os.path.isfile(os.path.join(name, CHECKFILE_NAME)):
                continue

            try:
                r = git.Repo(name)
            except (git.InvalidGitRepositoryError, git.NoSuchPathError) as err:
                continue

            repos.append(os.path.join(self.datadir_path, name))

        self.repos = tuple(repos)


    def init_archive_repo(self, repo_name: str) -> git.Repo:
        """

        Handle the following possibilities:
        - dir exists
            - valid repo -> print status
            - no or invalid repo -> raise error
        - dir does not exist -> create dir and init repo

        """
        os.chdir(self.datadir_path)

        repodir_path = os.path.join(self.datadir_path, repo_name)
        if repodir_path in self.repos:
            print(f"{repodir_path} is already a valid repo. Nothing to do.")


        if os.path.exists(repodir_path):
            raise FileExistsError(
                f"{repodir_path} already exists. Please move dir and retry."
            )

        r = git.Repo.init(repodir_path)
        os.chdir(repodir_path)

        # prevent the directory from being accidentally deleted
        # this file will be ignored by git due to .gitignore
        fname = self.checkfile
        with open(fname, "w") as txtfile:
            txtfile.write(safty_explanation)

        self.checkfile = os.path.join(repodir_path, fname)

        # Create the first files for the repo
        fname = "README.md"
        with open(fname, "w") as txtfile:
            txtfile.write(self.settings["readme_content"])
        r.index.add([fname])

        fname = ".gitignore"
        with open(fname, "w") as txtfile:
            txtfile.write(gitignore_content)
        r.index.add([fname])

        fname = ".padstogit"
        with open(fname, "w") as txtfile:
            txtfile.write(gitignore_content)
        r.index.add([fname])

        r.index.commit("initial commit")

        return r

    def purge_pad_repo(self, ignore_errors=False):

        assert self.checkfile is not None

        if not ignore_errors and not os.path.exists(self.checkfile):
            msg = f"The file `{self.checkfile}` is missing. Abort deletion of `{repodir_path}`."
            raise FileNotFoundError(msg)

        shutil.rmtree(repodir_path, ignore_errors)

    def load_pad_sources(self, repo_dir: str) -> list:

        sources_path = os.path.join(repo_dir, "sources.yml")

        assert os.path.isfile(sources_path)

        with open(sources_path, "r") as txtfile:
            raw_sources = yaml.safe_load(txtfile)
        assert isinstance(raw_sources, list)

        sources = []
        for s in raw_sources:
            if isinstance(s, str):
                d = {
                    "name": get_padname_from_url(s),
                    "url": s,
                }
                sources.append(d)
            elif isinstance(s, dict):
                assert len(s) == 1
                url, value_obj = list(s.items())[0]

                # assume that there is an inner dict
                assert isinstance(value_obj, dict)
                if not "name" in value_obj:
                    value_obj["name"] = get_padname_from_url(url)
                value_obj["url"] = url

                sources.append(value_obj)
            else:
                raise TypeError(f"unexpexted:{type(s)}")
        return sources

    def goto_paddir(self, repodir_path):
        paddir = os.path.join(repodir_path, "pads")
        os.makedirs(paddir, exist_ok=True)
        os.chdir(paddir)

    def download_pad_contents(self, repo_dir: str):
        """
        create and change to the directory where the pads are actually placed
        (to avoind name collissions)
        """
        sources = self.load_pad_sources(repo_dir)

        self.goto_paddir()

        for sdict in sources:
            fname = sdict["name"]
            url = sdict["url"]

            res = requests.get(url)
            if not res.status_code == 200:
                raise ValueError(f"unexpected status code for url {url}")

            with open(fname, "wb") as txtfile:
                txtfile.write(res.content)

    def get_repo(self, repodir_path: str) -> git.Repo:
        assert repodir_path in self.repos
        r = git.Repo(repodir_path)
        return r

    def make_commit(self, repodir_path: str) -> List[str]:

        os.chdir(repodir_path)
        r = self.get_repo(repodir_path)

        r.git.add("pads/")
        diff_objects = r.index.diff(r.head.commit)

        changedFiles = [do.a_path for do in diff_objects]

        if changedFiles:

            r.git.commit(message="track changes to pads")

        return changedFiles

    def print_config(self):
        keys = ("config_path", "repo_dir", "sources_path")

        print(f"\n{APPNAME} configuration:")
        for key in keys:
            value = getattr(self, key, None)
            print(f" {key}: {value}")

    @staticmethod
    def make_report(changed_files: List[str]) -> str:
        assert isinstance(changed_files, list)
        report_lines = ["\n", f"{len(changed_files)} files changed:"] + changed_files

        report = "\n".join(report_lines)
        return report

    def handle_all_repos(self, print_flag: str = True):
        content = os.listdir(self.datadir_path)

        if print_flag:
            self.print_config()

        for name in content:
            full_path = os.path.join(self.datadir_path, name)
            if not os.path.isdir(full_path):
                continue
            if not os.path.isfile(os.path.join(full_path, f".{APPNAME}")):
                msg = (
                    f"file .{APPNAME} is not present in {full_path} "
                    f"-> do not consider it as relevant repo."
                )
                if print_flag:
                    print(msg)
                continue

            self.handle_repo(full_path, print_flag)

    def handle_repo(self, repodir_path: str, print_flag: str = True):
        """
        This is the main method for one repo. It performs the following steps:

        1. get or create repo
        1. load sources.yml
        2. download files
        3. commit to repo
        4. return and print a report of what as changed
        """

        # obsolete self.get_or_create_repo(repodir_path)
        sources = self.load_pad_sources(repodir_path)
        self.download_pad_contents(repodir_path)
        changed_files = self.make_commit(repodir_path)

        if print_flag:
            print(f"\nrepo {u.bright(repodir_path)}:")
            print(self.make_report(changed_files))

        return changed_files


# https://etherpad.wikimedia.org/p/padstogit_testpad1/export/txt


def get_padname_from_url(url, append=".txt") -> str:
    if not url.startswith("http"):
        raise ValueError(f"invalid url: {url}")

    url = url.rstrip("/")
    url = url.rstrip("/export/txt")

    # assume that padnames cannot contain slashes
    padname = url.split("/")[-1]
    return f"{padname}{append}"

def _create_new_config_file(configfile_path):

    if os.path.isfile(configfile_path):
        raise FileExistsError(configfile_path)

    containing_dir = os.path.split(configfile_path)[0]
    os.makedirs(containing_dir, exist_ok=True)

    with open(configfile_path, "w", encoding="utf8") as txtfile:
        txtfile.write(DEFAULT_CONFIGFILE_CONTENT)
    
    print(configfile_path, "created", u.bgreen("✓"))

def _check_config_file(configfile_path, print_flag=True):
    # load config file
    # this will raise an error if the yaml syntax is not correct
    with open(configfile_path, "r") as txtfile:
        config_dict = yaml.safe_load(txtfile)

    if not isinstance(config_dict, dict):
        msg = (
            f"Expected dict but got {type(config_dict)}. "
            f"Perhaps wrong yaml syntax in {configfile_path}."
        )
        raise TypeError(msg)
    # this will raise an error if the relevant keys are missing

    relevant_keys = ["datadir_path"]
    missing_keys = [key for key in relevant_keys if key not in config_dict]

    if missing_keys:
        missing_keys_str = '\n- '.join(missing_keys)
        msg = (
            f"The following keys are missing in {configfile_path}:"
            f"{missing_keys_str}\n."
        )
        raise KeyError(msg)

    if print_flag:
        print("config file check passed", u.bgreen("✓"))


def bootstrap_config(configfile_path=None, print_flag=True):

    if configfile_path is None:
        configfile_path = DEFAULT_CONFIGFILE_PATH

    if not os.path.isfile(configfile_path):
        # create new config file
        _create_new_config_file(configfile_path)
        # call this function again to perform the check
        return bootstrap_config(configfile_path=configfile_path, print_flag=print_flag)

    else:
        _check_config_file(configfile_path)

def load_config(configfile_path):
    with open(configfile_path, "r") as txtfile:
        config_dict = yaml.safe_load(txtfile)
    
    return config_dict


def bootstrap_datadir(configfile_path=None, datadir_path=None):
    _check_config_file(configfile_path=configfile_path)
    config_dict = load_config(configfile_path)

    c = Core(configfile_path=configfile_path, datadir_path=datadir_path)

    c.init_archive_repo(config_dict["default_repo_name"])
    repos = c._find_repos()

    assert len(repos) > 0

    repo_str = "\n -".join(repos)

    print(f"The following repos where found: {repo_str}")



def bootstrap_app():
    bootstrap_config()
    bootstrap_datadir()
