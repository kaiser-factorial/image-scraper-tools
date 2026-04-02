# Image Scraping + Render Capture Tools

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

## Docs

- Detailed scraper guide: [docs/IMAGE_SCRAPER.md](docs/IMAGE_SCRAPER.md)
- Detailed render-capture guide: [docs/RENDER_CAPTURE.md](docs/RENDER_CAPTURE.md)

## Notes

- `capture_rendered_page.py` requires Playwright + Chromium.
- If your Python is system-managed (PEP 668), use a virtual environment (`.venv`) for installs.
