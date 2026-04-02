#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

TMP_DIR="$ROOT_DIR/.smoke_tmp"
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo "[1/3] Running scraper smoke test..."
python3 scripts/scrape_images.py \
  "https://www.wikipedia.org/" \
  --max-pages 1 \
  --no-download \
  --verify-urls \
  --urls-file "$TMP_DIR/smoke_urls.txt" \
  --csv-file "$TMP_DIR/smoke_manifest.csv" >/dev/null

if [[ ! -s "$TMP_DIR/smoke_urls.txt" ]]; then
  echo "FAIL: scraper produced no URLs"
  exit 1
fi

if [[ ! -s "$TMP_DIR/smoke_manifest.csv" ]]; then
  echo "FAIL: scraper produced no manifest"
  exit 1
fi

URL_COUNT="$(wc -l < "$TMP_DIR/smoke_urls.txt" | tr -d ' ')"
echo "PASS: scraper returned $URL_COUNT URL(s)"

echo "[2/3] Checking render-capture prerequisites..."
if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
  PY_BIN="$ROOT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY_BIN="python3"
else
  echo "FAIL: no Python interpreter found"
  exit 1
fi

if "$PY_BIN" - <<'PY' >/dev/null 2>&1
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec("playwright") else 1)
PY
then
  HAS_PLAYWRIGHT=1
else
  HAS_PLAYWRIGHT=0
fi

echo "[3/3] Running render-capture smoke test..."
if [[ "$HAS_PLAYWRIGHT" -eq 1 ]]; then
  "$PY_BIN" scripts/capture_rendered_page.py \
    "https://example.com/" \
    --out "$TMP_DIR/smoke_render.png" \
    --wait-ms 1000 >/dev/null

  if [[ ! -s "$TMP_DIR/smoke_render.png" ]]; then
    echo "FAIL: render capture did not produce an image"
    exit 1
  fi
  echo "PASS: render capture produced smoke_render.png"
else
  echo "SKIP: Playwright not installed in selected Python environment"
fi

echo "Smoke test completed successfully."
