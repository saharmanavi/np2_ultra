Current to do list:
Documentation
Tools for data cube exploration.
Tools for basic figure generation.

Neuropixels Ultra ETL & analysis tools
==============================

Package for extracting data from NP ultra experiments to storage drives, running Kilosort and first pass data processing, basic figure generation.

Code by Sahar Manavi except where otherwise specified.

Readme info mostly copied from Justin Kiggins.

## Installation
This package is designed to be installed using standard Python packaging tools. For example,

    python setup.py install

If you are using pip to manage packages and versions (recommended), you can also install using pip:

    pip install ./

If you are plan to contribute to the development of the package, I recommend installing in "editable" mode:

    pip install -e ./

This ensures that Python uses the current, active files in the folder (even while switching between branches).

## Required Libraries
AllenSDK
glob2
Numpy
pandas

to run kilosort:
Matlab engine + Matlab and Kilosort installed, in addition to appropriate hardware specs.

## API

Current entry points are located in top-level folder:
  backup_session.py
  process_session.py 

Each script in scripts can also be run independently.

More documentation to come.


## Contributing

Pull requests are welcome.

1. Fork the repo
2. Create a feature branch
3. Commit your changes
4. Create a pull request
5. Tag `saharm` to review

## Contributors:

- Sahar Manavi - saharm@alleninstitute.org
