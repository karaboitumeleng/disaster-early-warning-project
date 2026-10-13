# Pre-commit setup

    pip install pre-commit
    pre-commit install

Runs ruff, black and basic hygiene checks (large-file, private-key detection) on every commit.
Run once against the whole tree after installing: `pre-commit run --all-files`.
