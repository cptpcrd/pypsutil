@echo off

black pypsutil tests && autopep8 --in-place --recursive pypsutil tests && isort pypsutil tests
