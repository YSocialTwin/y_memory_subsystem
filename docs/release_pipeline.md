# Release Pipeline

This repository is prepared to build a pip-installable package and publish it to PyPI.

## What Was Added

- enriched package metadata in [`pyproject.toml`](../pyproject.toml)
- source-distribution manifest in [`MANIFEST.in`](../MANIFEST.in)
- MIT license file in [`LICENSE`](../LICENSE)
- validation workflow in [package.yml](../.github/workflows/package.yml)
- publishing workflow in [publish-pypi.yml](../.github/workflows/publish-pypi.yml)

## Local Build Commands

Build distributions:

```bash
python -m pip install .[release]
python -m build
```

Validate the generated artifacts:

```bash
python -m twine check dist/*
```

Install the built wheel locally:

```bash
python -m pip install dist/*.whl
```

## CI Validation Workflow

The package validation workflow does the following on pushes, pull requests, and manual dispatch:

1. installs the package with `dev` and `release` extras
2. runs the test suite
3. builds `sdist` and wheel artifacts
4. runs `twine check` on the generated distributions

## PyPI Publishing Workflow

The publish workflow triggers on:

- GitHub release publication
- manual workflow dispatch

It:

1. builds the distributions
2. validates them with `twine check`
3. uploads the artifacts between jobs
4. publishes them with `pypa/gh-action-pypi-publish`

## Recommended PyPI Setup

Preferred option: Trusted Publishing.

Configure the PyPI project to trust:

- repository: `YSocialTwin/y_memory_subsystem`
- workflow: `publish-pypi.yml`
- environment: `pypi`

The workflow also accepts `PYPI_API_TOKEN` as a fallback secret through the action input.

## Release Steps

1. update [`src/yclient_memory/__init__.py`](../src/yclient_memory/__init__.py) version
2. ensure `pytest -q` passes
3. ensure `python -m build` and `twine check dist/*` pass locally
4. commit and tag the release
5. create a GitHub release for that tag
6. let the publish workflow upload the artifacts to PyPI

## Version Source

The published package version is taken from:

- [`src/yclient_memory/__init__.py`](../src/yclient_memory/__init__.py)

via setuptools dynamic versioning configured in [`pyproject.toml`](../pyproject.toml).
