#!/usr/bin/env bash

set -e
set -x

# `source` and `concurrency = ["greenlet"]` come from [tool.coverage.run] in
# pyproject.toml so this script and `just test-backend` cannot diverge.
coverage run -m pytest
coverage report --show-missing
coverage html --title "${@-coverage}"
