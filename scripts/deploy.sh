#!/usr/bin/env bash

# Python 3.6 could not build "build"
# TODO: Convert this to a Docker build.
rm dist/synology_abfb_log_parser-*
python3.10 -m venv env
source env/bin/activate
python --version
python -m pip install --upgrade pip build hatchling twine
python -m build

# Use this to export the .env variables into the current environment
export $(grep -vE "^(#.*|\s*)$" .env)
python -m twine upload --verbose --config-file .pypirc dist/synology_abfb_log_parser-*
deactivate
