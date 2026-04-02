# Render Capture CLI

Capture screenshots from JavaScript-rendered/app-style pages where normal image URL scraping is not enough.

Script: `scripts/capture_rendered_page.py`

## Install

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Quick Start

Viewport screenshot:

```bash
python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
  --out ptable-viewport.png \
  --wait-ms 2500
```

Full-page screenshot:

```bash
python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
  --out ptable-full.png \
  --full-page \
  --wait-ms 2500
```

Specific element screenshot (CSS selector):

```bash
python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
  --out ptable-element.png \
  --selector "#Table" \
  --wait-ms 2500
```

## Flags

- `url`: page URL to open
- `--out`: output PNG path
- `--full-page`: capture full scroll area
- `--selector`: capture one element instead of whole page
- `--wait-ms`: extra wait after load for dynamic rendering
- `--timeout-ms`: navigation/selector timeout
- `--width`: viewport width
- `--height`: viewport height
- `--user-agent`: optional custom user agent
- `--headed`: show browser window (default is headless)

