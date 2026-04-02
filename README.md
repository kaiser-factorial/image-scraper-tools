# Image Scraping + Render Capture Tools

[![Smoke Test](https://github.com/kaiser-factorial/image-scraper-tools/actions/workflows/smoke-test.yml/badge.svg)](https://github.com/kaiser-factorial/image-scraper-tools/actions/workflows/smoke-test.yml)

Small CLI toolkit for collecting images from websites, including:

- standard image URL scraping from HTML/JS
- optional same-site crawling
- URL verification (keep only real image responses)
- iframe/embed traversal
- optional export of embedded `data:image/...` assets
- rendered screenshot capture for JS/canvas-heavy apps

## Included Scripts

- `scripts/scrape_images.py`
  - Main scraper for image URLs and optional downloads
  - Best for static + semi-dynamic sites
- `scripts/capture_rendered_page.py`
  - Playwright-based screenshot capture
  - Best for app-rendered pages (canvas/WebGL/SPA UIs)

## Quick Start

Scrape image URLs only:

```bash
python3 scripts/scrape_images.py "https://example.com" \
  --include-js \
  --max-pages 5 \
  --verify-urls \
  --no-download
```

Capture rendered page screenshot:

```bash
.venv/bin/python scripts/capture_rendered_page.py "https://example.com" \
  --out rendered.png \
  --wait-ms 2500
```

Run quick smoke test:

```bash
bash scripts/smoke_test.sh
```

## Docs

- Detailed scraper guide: [docs/IMAGE_SCRAPER.md](docs/IMAGE_SCRAPER.md)
- Detailed render-capture guide: [docs/RENDER_CAPTURE.md](docs/RENDER_CAPTURE.md)

## Notes

- `capture_rendered_page.py` requires Playwright + Chromium.
- If your Python is system-managed (PEP 668), use a virtual environment (`.venv`) for installs.

## Known Limitations

- Auth-gated/personalized pages (for example social feeds after login) may only expose public/static assets unless run in an authenticated browser context.
- Very JS-heavy pages can produce many candidate URLs; `--verify-urls` improves accuracy but may run slower.
- `--include-js` can surface image-like strings from third-party bundles that are not actually used by the target page. Use `--verify-urls` and/or domain filters to reduce noise.
- Some app-rendered visuals (canvas/WebGL) are not downloadable image files. Use `capture_rendered_page.py` for screenshot-based capture in those cases.
- Some sites only expose transformed/resized derivatives, not original full-resolution source files.

## Troubleshooting

- `error: externally-managed-environment` during pip install  
  Use a virtual environment:
  `python3 -m venv .venv && .venv/bin/python -m pip install playwright`

- `Playwright is required` or Chromium executable missing  
  Install both package and browser:
  `python -m pip install playwright && python -m playwright install chromium`

- Scraper returns too many irrelevant URLs  
  Add `--verify-urls`, and optionally constrain hosts with `--include-domain` or `--exclude-domain`.

- Scraper returns 0 URLs on app-like pages  
  Try `scripts/capture_rendered_page.py` instead; the page may be canvas/WebGL-rendered with no direct image files.

- `--verify-urls` feels slow  
  Run once without verification for discovery speed, then re-run with `--verify-urls` (or domain filters) for cleanup.
