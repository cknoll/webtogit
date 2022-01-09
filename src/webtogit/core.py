import os
import sys
import shutil
import requests
from typing import List
import pathlib
import textwrap
import logging

import git
import yaml
import appdirs
from ipydex import IPS, activate_ips_on_exception, TracerFactory

from . import util as u


# debugging facilities
activate_ips_on_exception()
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
.webtogit
"""

APPNAME = "webtogit"

DEFAULT_DATADIR_PATH = appdirs.user_data_dir(appname=APPNAME)
DEFAULT_CONFIGFILE_PATH = os.path.join(appdirs.user_config_dir(appname=APPNAME), "settings.yml")


# Initialize logging based on https://stackoverflow.com/a/16066513/333403

class InfoFilter(logging.Filter):
    def filter(self, rec):
        return rec.levelno in (logging.DEBUG, logging.INFO)


logger = logging.getLogger(APPNAME)


logger.setLevel(logging.DEBUG)

h1 = logging.StreamHandler(sys.stdout)
h1.setLevel(logging.DEBUG)
h1.addFilter(InfoFilter())
h2 = logging.StreamHandler()
h2.setLevel(logging.WARNING)

logger.addHandler(h1)
logger.addHandler(h2)

logging.basicConfig(format='%(levelname)s:%(message)s')


def generate_default_configfile_content(datadir_path: str) -> str:
    DEFAULT_CONFIGFILE_CONTENT = f"""
    ---
    # This is the configuration file for {APPNAME}. It uses key-value-pairs in YAML format.

    # this is the parent directories where alll repositories are located
    datadir_path: "{datadir_path}"

    default_repo_name: "archived-webdocs"

    readme_content: "This repo was generated by webtogit\\n"
    """

    return textwrap.dedent(DEFAULT_CONFIGFILE_CONTENT)


def generate_default_sources_content():
    default_sources_content = f"""
    ---
    # This is a comment and will be ignored. Same for empty lines.

    # The top YAML-element is a list. Entries are strings or dicts.
    # The following two list entries are just simple literal strings
    # (one url per line):

    - https://etherpad.wikimedia.org/p/webtogit_testpad1
    - "https://etherpad.wikimedia.org/p/webtogit_testpad2":
        name: renamed_testpad.md
    - https://etherpad.wikimedia.org/p/webtogit_testpad3
    """

    return textwrap.dedent(default_sources_content)


CHECKFILE_NAME = f".{APPNAME}"

# name of the directory inside the repo which contains the actual data
REPO_DATA_DIR_NAME = "pads"


class ObsoleteFunctionError(RuntimeError):
    pass


class Core:
    """
    Main class which holds all information
    """

    def __init__(self, configfile_path=None, datadir_path=None):

        self.datadir_path = resolve_path_arg(datadir_path, "DATA")
        self.configfile_path = resolve_path_arg(configfile_path, "CONFIG")
        self.configdir = os.path.split(self.configfile_path)[0]

        self.config = None

        self._ensure_existing_dirs()
        self.load_settings()

        self.repo_paths = None
        self.find_repos()

    def _ensure_existing_dirs(self):

        os.makedirs(self.datadir_path, exist_ok=True)

        os.makedirs(self.configdir, exist_ok=True)

    def load_settings(self):

        self.config = load_config(self.configfile_path)

    def find_repos(self) -> tuple:

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

        self.repo_paths = tuple(repos)

        return self.repo_paths

    def init_archive_repo(self, repo_name: str) -> git.Repo:
        """

        Handle the following cases:
        - dir exists
            - valid repo -> logger.info status
            - no or invalid repo -> raise error
        - dir does not exist -> create dir and init repo

        """
        os.chdir(self.datadir_path)

        repodir_path = os.path.join(self.datadir_path, repo_name)
        if repodir_path in self.repo_paths:
            logger.info(f"{repodir_path} is already a valid repo. Nothing to do.")
            _check_archive_repo(repodir_path)
            return git.Repo.init(repodir_path)
        else:
            return self._init_archive_repo(repodir_path)

    def _init_archive_repo(self, repodir_path: str) -> git.Repo:
        """
        Handle the following cases:
        - dir exists -> error
        - dir does not exist -> create dir and init repo

        :param repodir_path:
        :return:
        """

        if os.path.exists(repodir_path):
            raise FileExistsError(f"{repodir_path} already exists. This si")

        r = git.Repo.init(repodir_path)
        os.chdir(repodir_path)

        # prevent the directory from being accidentally deleted
        # this file will be ignored by git due to .gitignore
        fname = CHECKFILE_NAME
        with open(fname, "w") as txtfile:
            txtfile.write(safty_explanation)

        # Create the first files for the repo
        fname = "README.md"
        with open(fname, "w") as txtfile:
            txtfile.write(self.config["readme_content"])
        r.index.add([fname])

        fname = ".gitignore"
        with open(fname, "w") as txtfile:
            txtfile.write(gitignore_content)
        r.index.add([fname])

        r.index.commit("initial commit")

        # {APPNAME}-sources.yml is not (automatically) part of the repo
        fname = f"{APPNAME}-sources.yml"
        sources_content = generate_default_sources_content()
        with open(fname, "w") as txtfile:
            txtfile.write(sources_content)

        return r

    @staticmethod
    def load_webdoc_sources(repo_dir: str) -> list:

        sources_path = os.path.join(repo_dir, f"{APPNAME}-sources.yml")

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

    @staticmethod
    def goto_repo_data_dir(repodir_path):
        paddir = os.path.join(repodir_path, REPO_DATA_DIR_NAME)
        os.makedirs(paddir, exist_ok=True)
        os.chdir(paddir)

    def download_source_contents(self, repo_dir: str):
        """
        iterate over sources dict, download url and save result in file insisde the repo
        """
        sources = self.load_webdoc_sources(repo_dir)

        self.goto_repo_data_dir(repo_dir)

        for sdict in sources:
            fname = sdict["name"]
            url = sdict["url"]

            res = requests.get(url)
            if not res.status_code == 200:
                raise ValueError(f"unexpected status code for url {url}")

            with open(fname, "wb") as txtfile:
                txtfile.write(res.content)

    def get_repo(self, repodir_path: str) -> git.Repo:
        assert repodir_path in self.repo_paths
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
        keys = ("configfile_path", "datadir_path", "repos")

        print(f"\n{APPNAME} configuration:")

        tmpdict = {}

        for key in keys:
            value = getattr(self, key, None)
            tmpdict[key] = value

        # use yaml to render the data structures
        print(yaml.safe_dump(tmpdict))

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

        testfile = f"{APPNAME}-sources.yml"

        for name in content:
            full_path = os.path.join(self.datadir_path, name)
            if not os.path.isdir(full_path):
                continue
            if not os.path.isfile(os.path.join(full_path, testfile)):
                msg = (
                    f"file {testfile} is not present in {full_path} "
                    f"-> do not consider it as relevant repo."
                )
                if print_flag:
                    logger.info(msg)
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

        self.download_source_contents(repodir_path)
        changed_files = self.make_commit(repodir_path)

        if print_flag:
            logger.info(f"\nrepo {u.bright(repodir_path)}:")
            logger.info(self.make_report(changed_files))

        return changed_files


# https://etherpad.wikimedia.org/p/webtogit_testpad1/export/txt


def get_padname_from_url(url, append=".txt") -> str:
    if not url.startswith("http"):
        raise ValueError(f"invalid url: {url}")

    url = url.rstrip("/")
    url = url.rstrip("/export/txt")

    # assume that padnames cannot contain slashes
    padname = url.split("/")[-1]
    return f"{padname}{append}"


def _create_new_config_file(configfile_path, datadir_path=None):

    if os.path.isfile(configfile_path):
        raise FileExistsError(configfile_path)

    containing_dir = os.path.split(configfile_path)[0]
    os.makedirs(containing_dir, exist_ok=True)

    # use default in case of `None`
    datadir_path = datadir_path or DEFAULT_DATADIR_PATH
    DEFAULT_CONFIGFILE_CONTENT = generate_default_configfile_content(datadir_path)

    with open(configfile_path, "w", encoding="utf8") as txtfile:
        txtfile.write(DEFAULT_CONFIGFILE_CONTENT)

    logger.info(f'{u.bgreen("✓")} {configfile_path} created')


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
        missing_keys_str = "\n- ".join(missing_keys)
        msg = f"The following keys are missing in {configfile_path}:" f"{missing_keys_str}\n."
        raise KeyError(msg)

    if print_flag:
        logger.info(f'{u.bgreen("✓")} config file check passed: {configfile_path}')


def _check_archive_repo(repodir_path: str) -> bool:
    """
    Check if provided archive repo has the expected structure

    :param repodir_path:

    :return:    True (or raise an error)
    """

    if not os.path.isdir(repodir_path):
        raise FileNotFoundError(repodir_path)

    path1 = os.path.join(repodir_path, f"{APPNAME}-sources.yml")

    if not os.path.isfile(path1):
        raise FileNotFoundError(path1)

    # this will raise an error if the repo is not valid
    test_repo = git.Repo.init(repodir_path)
    assert test_repo is not None

    return True


def resolve_path_arg(path: str, type_: str) -> str:
    """
    Handle the `None`-case. Leave unchanged else

    :param path:    path to handle or None
    :param type_:   one of "CONFIG" or "DATA"

    :return:
    """
    if type_ == "CONFIG":
        if path is None:
            path = os.getenv(f"{APPNAME}_CONFIGFILE_PATH") or DEFAULT_CONFIGFILE_PATH

        return path
    elif type_ == "DATA":
        if path is None:
            path = os.getenv(f"{APPNAME}_DATADIR_PATH") or DEFAULT_DATADIR_PATH

        return path
    else:
        raise ValueError(f"Unkown type-string: {type_}")


def bootstrap_config(configfile_path=None, datadir_path=None):
    """
    Try to load configfile. If it does not exist: create. Anyway: check

    :param configfile_path:     path to where the config file should be located (optional)
    :param datadir_path:        path which is written inside the config file
                                (if it is newly created)
    """

    configfile_path = resolve_path_arg(configfile_path, "CONFIG")

    if not os.path.isfile(configfile_path):
        # create new config file
        _create_new_config_file(configfile_path, datadir_path)
        # call this function again to perform the check

        _check_config_file(configfile_path)

    else:
        _check_config_file(configfile_path)
        logger.info("Configuration was already bootstrapped. Nothing done.")

    return configfile_path


def load_config(configfile_path):
    with open(configfile_path, "r") as txtfile:
        config_dict = yaml.safe_load(txtfile)

    return config_dict


def bootstrap_datadir(configfile_path=None, datadir_path=None, omit_config_check=False):
    """
    Try to check datadir. If it does not exist: create. Anyway: check

    :param configfile_path:
    :param datadir_path:
    :param omit_config_check:   Boolean flag to avoid unnecessary checking
    :return:
    """
    configfile_path = resolve_path_arg(configfile_path, "CONFIG")

    if not omit_config_check:
        _check_config_file(configfile_path=configfile_path)
    config_dict = load_config(configfile_path)

    c = Core(configfile_path=configfile_path, datadir_path=datadir_path)

    default_repo_path = os.path.join(c.datadir_path, config_dict["default_repo_name"])
    if not os.path.isdir(default_repo_path):
        c.init_archive_repo(config_dict["default_repo_name"])
    else:
        logger.info("Datadir was already bootstrapped. Nothing done.")
        logger.info(f"Default repo found: {default_repo_path}")
    repos = c.find_repos()

    assert len(repos) > 0

    repo_str = "\n -".join(repos)

    logger.info(f"The following repos where found:\n{repo_str}\n")

    return c.datadir_path


def bootstrap_app(configfile_path=None, datadir_path=None):
    bootstrap_config(configfile_path=configfile_path, datadir_path=datadir_path)
    bootstrap_datadir(configfile_path=configfile_path, datadir_path=datadir_path, omit_config_check=True)


def purge_pad_repo(repodir_path, ignore_errors=False):

    checkfile_path = os.path.join(repodir_path, CHECKFILE_NAME)

    if os.path.exists(checkfile_path):
        # the special file that it is an directory of this app indicates
        # that it is safe to delete
        shutil.rmtree(repodir_path, ignore_errors)
    elif not ignore_errors:
        msg = f"The file `{self.checkfile}` is missing. Abort deletion of `{repodir_path}`."
        raise FileNotFoundError(msg)
