# Contributing

Thanks for contributing to `image-scraper-tools`.

## Local Setup

```bash
git clone git@github.com:kaiser-factorial/image-scraper-tools.git
cd image-scraper-tools
python3 -m venv .venv
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium
```

## Quick Validation

Run the smoke test before opening a PR:

```bash
bash scripts/smoke_test.sh
```

This checks:
- scraper CLI basic functionality
- render-capture CLI basic functionality (when Playwright is available)

## Style and Scope

- Keep changes focused and minimal.
- Prefer small, reviewable commits.
- Update docs when CLI flags/behavior change.
- Avoid committing generated output files (URL dumps, manifests, downloaded images).

## Pull Requests

Please include:
- what changed
- why it changed
- how you tested it (commands + results)
- any limitations or follow-up work

## Release Notes

This repo uses semantic-ish tags (`v1.0.x`) for patch releases.
If your change affects users, include a short release-note-ready summary in the PR description.
