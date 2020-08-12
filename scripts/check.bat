@echo off

flake8 pypsutil tests && isort --check pypsutil tests
rem flake8 pypsutil tests && isort --check pypsutil tests && mypy --show-error-codes --strict -p pypsutil -p tests && pylint pypsutil tests