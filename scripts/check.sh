#!/bin/bash
cd "$(dirname -- "$(dirname -- "$(readlink -f "$0")")")"

for cmd in flake8 isort mypy pylint; do
    if [[ ! -x "$(which "$cmd")" ]]; then
        echo "Could not find $cmd. Please make sure that flake8, isort, mypy, and pylint are all installed."
        exit 1
    fi
done

flake8 pypsutil tests && isort --check pypsutil tests && mypy --show-error-codes --strict -p pypsutil -p tests && pylint pypsutil tests
