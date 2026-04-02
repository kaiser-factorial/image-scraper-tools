# Image Scraper CLI

A reusable script for collecting image URLs from a webpage and optionally downloading files.

Script: `scripts/scrape_images.py`

## What it does

- Scrapes image URLs from HTML (`src`, `srcset`, `data-*`, inline `style` URLs)
- Optionally scans linked JavaScript bundles for embedded image URLs
- Optionally crawls additional internal pages on the same site
- Follows same-site embedded frame pages (`iframe`, `frame`, `embed`, `object`)
- Downloads images into a folder
- Writes:
  - URL list (`.txt`)
  - Manifest (`.csv`) with download status

## Requirements

- Python 3.9+
- No third-party packages

## Quick Start

```bash
python3 scripts/scrape_images.py "https://example.com/gallery" \
  --include-js \
  --max-pages 3 \
  --out-dir scraped-images \
  --urls-file image_urls.txt \
  --csv-file image_manifest.csv
```

## Useful Modes

Only collect URLs (no downloads):

```bash
python3 scripts/scrape_images.py "https://example.com" \
  --include-js \
  --max-pages 5 \
  --no-download \
  --urls-file urls_only.txt \
  --csv-file urls_only_manifest.csv
```

Scrape one single page (fastest):

```bash
python3 scripts/scrape_images.py "https://example.com/page" --include-js --max-pages 1
```

Keep only certain image hosts (great for noisy pages):

```bash
python3 scripts/scrape_images.py "https://screamingeyeballs.bandcamp.com/..." \
  --include-js \
  --no-download \
  --include-domain f4.bcbits.com
```

Exclude known noise hosts:

```bash
python3 scripts/scrape_images.py "https://example.com" \
  --include-js \
  --exclude-domain js.stripe.com,fonts.gstatic.com
```

Strict verification mode (recommended on noisy JS-heavy sites):

```bash
python3 scripts/scrape_images.py "https://example.com" \
  --include-js \
  --verify-urls
```

Include embedded `data:image/...` assets (base64) and export them:

```bash
python3 scripts/scrape_images.py "https://example.com/page-with-iframe" \
  --max-pages 20 \
  --include-data-urls \
  --out-dir exported-images
```

## Flags

- `url` (required): starting page URL
- `--out-dir`: download directory (default: `scraped-images`)
- `--urls-file`: output TXT list (default: `image_urls.txt`)
- `--csv-file`: output CSV manifest (default: `image_manifest.csv`)
- `--max-pages`: number of same-site pages to crawl (default: `1`)
- `--include-js`: scan linked JS files for image URLs
- `--no-download`: skip downloads and only output URL list + CSV
- `--include-domain`: only keep images from selected hostnames (repeatable / comma-separated)
- `--exclude-domain`: remove images from selected hostnames (repeatable / comma-separated)
- `--verify-urls`: keep only URLs that return `200` and `image/*` (slower, but removes dead/false positives)
- `--include-data-urls`: include/export base64 `data:image/...` assets found in HTML attributes
- `--timeout`: request timeout seconds (default: `20`)
- `--user-agent`: custom UA string

## Notes

- Many site builders (GoDaddy, Squarespace-like setups, etc.) store gallery URLs inside JS bundles. Use `--include-js` for those.
- Downloaded files are deduplicated by URL and filename collisions are handled safely.
- Some sites only expose resized/compressed derivatives, not original full-resolution source files.
