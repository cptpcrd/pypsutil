#!/bin/bash
cd "$(dirname -- "$(dirname -- "$(readlink -f "$0")")")"

for cmd in flake8 isort mypy pylint pytype; do
    if [[ ! -x "$(which "$cmd")" ]]; then
        echo "Could not find $cmd. Please make sure that flake8, isort, mypy, pylint, and pytype are all installed."
        exit 1
    fi
done

flake8 pypsutil tests && isort --recursive --check pypsutil tests && mypy --strict -p pypsutil -p tests && pytype pypsutil tests && pylint pypsutil tests
