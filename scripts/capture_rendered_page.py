#!/usr/bin/env python3
"""Capture screenshots from JS-rendered/app-style webpages using Playwright.

Examples:
  python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
    --out ptable-viewport.png --wait-ms 2500

  python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
    --out ptable-full.png --full-page --wait-ms 2500

  python3 scripts/capture_rendered_page.py "https://ptable.com/#Properties" \
    --out ptable-table-only.png --selector "#Table" --wait-ms 2500
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Capture screenshots from app-rendered webpages.")
    parser.add_argument("url", help="URL to open in Chromium")
    parser.add_argument("--out", default="rendered-capture.png", help="Output PNG file path")
    parser.add_argument("--full-page", action="store_true", help="Capture the full scrollable page")
    parser.add_argument("--selector", help="Capture only this CSS selector instead of the whole page")
    parser.add_argument("--wait-ms", type=int, default=2000, help="Additional wait after load (default: 2000)")
    parser.add_argument("--timeout-ms", type=int, default=60000, help="Navigation timeout in ms (default: 60000)")
    parser.add_argument("--width", type=int, default=1440, help="Viewport width (default: 1440)")
    parser.add_argument("--height", type=int, default=900, help="Viewport height (default: 900)")
    parser.add_argument("--user-agent", default="", help="Optional custom user agent")
    parser.add_argument("--headed", action="store_true", help="Run with visible browser window")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        print("Playwright is required.", file=sys.stderr)
        print("Install with:", file=sys.stderr)
        print("  python3 -m pip install playwright", file=sys.stderr)
        print("  python3 -m playwright install chromium", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    if out_path.parent and str(out_path.parent) != ".":
        out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=(not args.headed))
            context_kwargs: dict[str, object] = {
                "viewport": {"width": args.width, "height": args.height},
            }
            if args.user_agent:
                context_kwargs["user_agent"] = args.user_agent
            context = browser.new_context(**context_kwargs)
            page = context.new_page()
            page.goto(args.url, wait_until="networkidle", timeout=args.timeout_ms)
            if args.wait_ms > 0:
                page.wait_for_timeout(args.wait_ms)

            if args.selector:
                locator = page.locator(args.selector).first
                locator.wait_for(state="visible", timeout=args.timeout_ms)
                locator.screenshot(path=str(out_path))
            else:
                page.screenshot(path=str(out_path), full_page=args.full_page)

            context.close()
            browser.close()
    except Exception as exc:
        message = str(exc)
        if "Executable doesn't exist" in message or "browserType.launch" in message:
            print("Chromium browser for Playwright is not installed.", file=sys.stderr)
            print("Run:", file=sys.stderr)
            print("  python3 -m playwright install chromium", file=sys.stderr)
            return 3
        print(f"Capture failed: {message}", file=sys.stderr)
        return 1

    print(f"Saved screenshot: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

