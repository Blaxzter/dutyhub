#!/usr/bin/env bash

set -e
set -x

# `source` and `concurrency = ["greenlet"]` come from [tool.coverage.run] in
# pyproject.toml so this script and `just test-backend` cannot diverge.
coverage run -m pytest

# Reports first, gate last. `fail_under` in [tool.coverage.report] makes
# `coverage report` exit non-zero below the floor, and this script runs under
# `set -e` — so generating htmlcov/ and coverage.xml beforehand means the
# smokeshow artifact and the diff-cover input still exist on a failing run,
# which is exactly when you want to look at them.
coverage html --title "${@-coverage}"
coverage xml
coverage report --show-missing
