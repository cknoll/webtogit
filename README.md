[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# PadsToGit

PadsToGit is a simple command line tool to facilitate archiving of web based pads (colaboratively edited texts).

## Usage

- Rename directory `src/package_name`
- Edit `setupy.py`: replace dummy data with real data.
- Add your source. a) Either to [`core.py`](src/package_name/core.py) or b) to your own separate file(s).
    - a) simplifies importing your module
    - b) is more flexible but you have to take care of importability yourself.


# Development Notes

- basic unittest
- `script.py` and associated entrypoint in `setup.py` (allows to call some functionality of the package directly from command line (try `package_name cmd1`))

For local development it is recommended to install this package in [editable mode](https://pip.pypa.io/en/latest/cli/pip_wheel/?highlight=editable#cmdoption-e): `pip install -e .` (run from where `setup.py` lives).


## Contributing

Contributions are very welcome. Please file a merge/pull request or reach out otherwise. Contact information can be found in `setup.py`.
