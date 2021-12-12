[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# PadsToGit

PadsToGit is a simple command line tool to facilitate archiving of web based pads (colaboratively edited texts).

## How it works

There are the following files:

- settings.yml
- sources.yml
Example:
    ```yaml
        # This is a comment and will be ignored. Same for empty lines.

        # The top YAML-element is a list. Entries are strings or dicts.
        # The following two list entries are just simple literal strings
        # (one url per line):

        - https://pad.url1.org/p/some-pad
        - https://pad.url1.org/p/some-other-pad

        # The next url needs some additional information.
        # It is thus stored as yaml-dictionary.

        - "https://pad.url1.org/p/some-third-pad":
            name: explicit_filename.txt
            key2: value2

        - https://pad.url2.org/p/yet-another-pad
    ```

During installation a new git repository is created.

The program is expected to be executed regularly (e.g. once a day). It parses `sources.yml` and downloads the content into the working dir of the repo and adds the file to the index. Then if there are changes, it makes a commit to the repo.


## Usage

- call `padstogit` from the command line
- TODO: add information about cron-integration here

# Development Notes

For local development it is recommended to install this package in [editable mode](https://pip.pypa.io/en/latest/cli/pip_wheel/?highlight=editable#cmdoption-e): `pip install -e .` (run from where `setup.py` lives).


## Contributing

Contributions are very welcome. Please file a merge/pull request or reach out otherwise. Contact information can be found in `setup.py`.
