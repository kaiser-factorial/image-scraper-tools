#!/usr/bin/env python3
"""Scrape image URLs from a webpage (and optional internal pages) and download them.

Features:
- Extracts image URLs from HTML attributes (`src`, `srcset`, `data-*`) and inline `style` URLs
- Optionally follows internal links up to a page limit
- Optionally fetches linked JavaScript files to find embedded image URLs (useful for site builders)
- Downloads images with collision-safe names
- Writes URL manifest and CSV metadata

No third-party dependencies required.
"""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import html
import re
import sys
import zlib
from collections import deque
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlparse, urlsplit, urlunsplit
from urllib.request import Request, urlopen

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".svg", ".tif", ".tiff", ".avif"}
TEXT_TYPES = ("text/html", "application/xhtml+xml", "application/javascript", "text/javascript")


def strip_url_fragment(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


def normalize_candidate_url(raw: str, base_url: str) -> str | None:
    raw = html.unescape(raw)
    raw = raw.replace("\\/", "/").strip().strip('"\'')
    raw = raw.rstrip("\\")
    if not raw:
        return None
    if raw.startswith("data:"):
        return None
    if raw.startswith("//"):
        raw = "https:" + raw
    try:
        abs_url = urljoin(base_url, raw)
    except Exception:
        return None
    abs_url = strip_url_fragment(abs_url).replace("\\", "")
    abs_url = abs_url.replace(" ", "%20")
    # Some builders append transform suffixes like '/:/' after the image path.
    abs_url = re.sub(r"/:/.*$", "", abs_url)
    try:
        parsed = urlparse(abs_url)
    except Exception:
        return None
    if parsed.scheme not in {"http", "https"}:
        return None
    return abs_url


def is_likely_image_url(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


def is_data_image_url(url: str) -> bool:
    return url.lower().startswith("data:image/")


def ext_from_data_image_url(url: str) -> str:
    m = re.match(r"^data:image/([a-zA-Z0-9.+-]+);base64,", url, flags=re.IGNORECASE)
    subtype = (m.group(1).lower() if m else "bin").split("+")[0]
    if subtype == "jpeg":
        return "jpg"
    return subtype


def decode_data_image_url(url: str) -> bytes | None:
    m = re.match(r"^data:image/[a-zA-Z0-9.+-]+;base64,(.+)$", url, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    payload = re.sub(r"\s+", "", m.group(1))
    try:
        return base64.b64decode(payload, validate=True)
    except Exception:
        return None


class LinkImageParser(HTMLParser):
    def __init__(self, base_url: str, include_data_urls: bool = False):
        super().__init__()
        self.base_url = base_url
        self.include_data_urls = include_data_urls
        self.links: set[str] = set()
        self.frame_links: set[str] = set()
        self.script_links: set[str] = set()
        self.image_urls: set[str] = set()

    def _maybe_add_image_candidate(self, raw_value: str) -> None:
        raw_value = html.unescape(raw_value or "").strip().strip('"\'')
        if not raw_value:
            return
        if is_data_image_url(raw_value):
            if self.include_data_urls:
                self.image_urls.add(raw_value)
            return
        u = normalize_candidate_url(raw_value, self.base_url)
        if u and is_likely_image_url(u):
            self.image_urls.add(u)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_map = {k.lower(): (v or "") for k, v in attrs}

        for link_attr in ("href",):
            if link_attr in attrs_map and tag == "a":
                u = normalize_candidate_url(attrs_map[link_attr], self.base_url)
                if u:
                    self.links.add(u)

        if tag == "script" and "src" in attrs_map:
            u = normalize_candidate_url(attrs_map["src"], self.base_url)
            if u:
                self.script_links.add(u)

        if tag in {"iframe", "frame", "embed"} and "src" in attrs_map:
            u = normalize_candidate_url(attrs_map["src"], self.base_url)
            if u:
                self.frame_links.add(u)
        if tag == "object" and "data" in attrs_map:
            u = normalize_candidate_url(attrs_map["data"], self.base_url)
            if u:
                self.frame_links.add(u)

        # Common direct image-bearing attributes
        for attr in ("src", "data-src", "data-original", "data-image", "poster"):
            if attr in attrs_map:
                self._maybe_add_image_candidate(attrs_map[attr])

        # srcset can contain many urls with descriptors ("url 1x, url 2x")
        if "srcset" in attrs_map:
            for candidate in attrs_map["srcset"].split(","):
                first = candidate.strip().split(" ")[0]
                self._maybe_add_image_candidate(first)

        # Scan every data-* attr as fallback
        for k, v in attrs_map.items():
            if k.startswith("data-"):
                self._maybe_add_image_candidate(v)

        # Inline styles often contain background-image URLs
        style = attrs_map.get("style", "")
        for match in re.findall(r"url\(([^)]+)\)", style, flags=re.IGNORECASE):
            self._maybe_add_image_candidate(match)


def fetch_text(url: str, timeout: float, user_agent: str) -> tuple[str, str] | None:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            if content_type and not any(content_type.startswith(tt) for tt in TEXT_TYPES):
                return None
            raw = response.read()
    except Exception:
        return None

    # Some servers still return compressed payloads without transparent decoding.
    # Detect by magic/header and decompress when possible.
    try:
        if raw.startswith(b"\x1f\x8b"):
            raw = gzip.decompress(raw)
        elif raw.startswith(b"\x78\x9c") or raw.startswith(b"\x78\x01") or raw.startswith(b"\x78\xda"):
            raw = zlib.decompress(raw)
    except Exception:
        pass

    # best effort decode
    for enc in ("utf-8", "latin-1"):
        try:
            return raw.decode(enc, errors="replace"), content_type
        except Exception:
            continue
    return None


def fetch_head_or_get(url: str, timeout: float, user_agent: str) -> tuple[int, str] | None:
    headers = {"User-Agent": user_agent, "Accept-Encoding": "identity"}
    for method in ("HEAD", "GET"):
        request = Request(url, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                status = int(getattr(response, "status", 0) or 0)
                ctype = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
                return status, ctype
        except Exception:
            continue
    return None


def is_verified_image_url(url: str, timeout: float, user_agent: str) -> bool:
    result = fetch_head_or_get(url, timeout=timeout, user_agent=user_agent)
    if not result:
        return False
    status, ctype = result
    if status != 200:
        return False
    return ctype.startswith("image/")


def extract_image_urls_from_js(js_text: str, base_url: str) -> set[str]:
    # Grab quoted URL-looking tokens then normalize.
    # Works well on minified bundles used by many site builders.
    js_text = js_text.replace("\\/", "/")
    tokens = re.findall(r"(?:https?:)?//[^\"'\s)]+|/[\w%./-]+\.(?:jpg|jpeg|png|webp|gif|bmp|svg|tif|tiff|avif)", js_text, flags=re.IGNORECASE)
    out: set[str] = set()
    for token in tokens:
        u = normalize_candidate_url(token, base_url)
        if u and is_likely_image_url(u):
            out.add(u)
    return out


def same_site(url: str, root: str) -> bool:
    a = urlparse(url).netloc.lower()
    b = urlparse(root).netloc.lower()
    return a == b


def normalize_domains(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    for item in values:
        for part in item.split(","):
            d = part.strip().lower()
            if d:
                out.append(d)
    return out


def host_matches_domain(host: str, domain: str) -> bool:
    return host == domain or host.endswith("." + domain)


def url_passes_domain_filters(url: str, include_domains: list[str], exclude_domains: list[str]) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except Exception:
        return False
    if not host:
        return False
    if include_domains and not any(host_matches_domain(host, d) for d in include_domains):
        return False
    if exclude_domains and any(host_matches_domain(host, d) for d in exclude_domains):
        return False
    return True


def safe_name_from_url(url: str) -> str:
    parsed = urlparse(url)
    candidate = Path(parsed.path).name or "image"
    candidate = html.unescape(candidate)
    if not Path(candidate).suffix:
        candidate = candidate + ".img"
    return re.sub(r"[^A-Za-z0-9._-]+", "_", candidate)


def unique_path(dest_dir: Path, filename: str, url: str) -> Path:
    base = Path(filename)
    stem, suffix = base.stem, base.suffix
    target = dest_dir / filename
    if not target.exists():
        return target
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return dest_dir / f"{stem}_{digest}{suffix}"


def download_binary(url: str, out_path: Path, timeout: float, user_agent: str) -> bool:
    request = Request(url, headers={"User-Agent": user_agent, "Accept-Encoding": "identity"})
    try:
        with urlopen(request, timeout=timeout) as response:
            data = response.read()
            if not data:
                return False
            out_path.write_bytes(data)
            return True
    except Exception:
        return False


def scrape(
    start_url: str,
    max_pages: int,
    include_js: bool,
    include_data_urls: bool,
    timeout: float,
    user_agent: str,
) -> tuple[set[str], set[str], set[str]]:
    visited_pages: set[str] = set()
    visited_js: set[str] = set()
    image_urls: set[str] = set()

    queue: deque[str] = deque([start_url])

    while queue and len(visited_pages) < max_pages:
        url = queue.popleft()
        if url in visited_pages:
            continue
        visited_pages.add(url)

        fetched = fetch_text(url, timeout=timeout, user_agent=user_agent)
        if not fetched:
            continue
        html_text, _ = fetched

        parser = LinkImageParser(base_url=url, include_data_urls=include_data_urls)
        try:
            parser.feed(html_text)
        except Exception:
            pass

        image_urls.update(parser.image_urls)

        if include_js:
            for script_url in parser.script_links:
                if script_url in visited_js:
                    continue
                visited_js.add(script_url)
                js_fetched = fetch_text(script_url, timeout=timeout, user_agent=user_agent)
                if not js_fetched:
                    continue
                js_text, _ = js_fetched
                image_urls.update(extract_image_urls_from_js(js_text, base_url=script_url))

        for link in parser.frame_links:
            if same_site(link, start_url) and link not in visited_pages:
                queue.appendleft(link)

        for link in parser.links:
            if same_site(link, start_url) and link not in visited_pages:
                queue.append(link)

    return image_urls, visited_pages, visited_js


def write_outputs(
    image_urls: Iterable[str],
    out_txt: Path,
    out_csv: Path,
    dest_dir: Path,
    download: bool,
    timeout: float,
    user_agent: str,
) -> tuple[int, int]:
    urls_sorted = sorted(set(image_urls))
    out_txt.write_text("\n".join(urls_sorted) + ("\n" if urls_sorted else ""), encoding="utf-8")

    downloaded = 0
    rows: list[tuple[str, str, str, str]] = []
    for url in urls_sorted:
        if is_data_image_url(url):
            digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
            name = f"data_image_{digest}.{ext_from_data_image_url(url)}"
        else:
            name = safe_name_from_url(url)
        status = "not_downloaded"
        saved_to = ""
        if download:
            out_path = unique_path(dest_dir, name, url)
            if is_data_image_url(url):
                payload = decode_data_image_url(url)
                ok = bool(payload)
                if ok and payload is not None:
                    out_path.write_bytes(payload)
            else:
                ok = download_binary(url, out_path, timeout=timeout, user_agent=user_agent)
            if ok:
                downloaded += 1
                status = "downloaded"
                saved_to = str(out_path)
            else:
                status = "failed"
        rows.append((name, url, status, saved_to))

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "url", "status", "saved_to"])
        writer.writerows(rows)

    return len(urls_sorted), downloaded


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scrape images from a webpage and optionally download them.")
    p.add_argument("url", help="Starting page URL")
    p.add_argument("--out-dir", default="scraped-images", help="Directory to save downloaded images")
    p.add_argument("--urls-file", default="image_urls.txt", help="Output text file for deduped image URLs")
    p.add_argument("--csv-file", default="image_manifest.csv", help="Output CSV file")
    p.add_argument("--max-pages", type=int, default=1, help="How many same-site pages to crawl (default: 1)")
    p.add_argument("--include-js", action="store_true", help="Also scan linked JavaScript files for image URLs")
    p.add_argument("--no-download", action="store_true", help="Only collect URLs; do not download files")
    p.add_argument(
        "--include-data-urls",
        action="store_true",
        help="Include embedded data:image URLs and export them when downloading",
    )
    p.add_argument(
        "--include-domain",
        action="append",
        default=[],
        help="Only keep images from these hostnames (repeat flag or pass comma-separated values)",
    )
    p.add_argument(
        "--exclude-domain",
        action="append",
        default=[],
        help="Exclude images from these hostnames (repeat flag or pass comma-separated values)",
    )
    p.add_argument(
        "--verify-urls",
        action="store_true",
        help="Keep only URLs that return HTTP 200 with image/* content type (slower, more accurate)",
    )
    p.add_argument("--timeout", type=float, default=20.0, help="Request timeout in seconds")
    p.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (compatible; image-scraper/1.0)",
        help="HTTP user-agent",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    start_url = strip_url_fragment(args.url)
    include_domains = normalize_domains(args.include_domain)
    exclude_domains = normalize_domains(args.exclude_domain)

    if args.max_pages < 1:
        print("--max-pages must be >= 1", file=sys.stderr)
        return 2

    out_dir = Path(args.out_dir)
    if not args.no_download:
        out_dir.mkdir(parents=True, exist_ok=True)

    image_urls, visited_pages, visited_js = scrape(
        start_url=start_url,
        max_pages=args.max_pages,
        include_js=args.include_js,
        include_data_urls=args.include_data_urls,
        timeout=args.timeout,
        user_agent=args.user_agent,
    )
    remote_urls = {u for u in image_urls if not is_data_image_url(u)}
    data_urls = {u for u in image_urls if is_data_image_url(u)}
    remote_urls = {
        u for u in remote_urls if url_passes_domain_filters(u, include_domains=include_domains, exclude_domains=exclude_domains)
    }
    if args.verify_urls:
        remote_urls = {u for u in remote_urls if is_verified_image_url(u, timeout=args.timeout, user_agent=args.user_agent)}
    image_urls = remote_urls | data_urls

    total, downloaded = write_outputs(
        image_urls=image_urls,
        out_txt=Path(args.urls_file),
        out_csv=Path(args.csv_file),
        dest_dir=out_dir,
        download=(not args.no_download),
        timeout=args.timeout,
        user_agent=args.user_agent,
    )

    print(f"Visited pages: {len(visited_pages)}")
    print(f"Visited JS files: {len(visited_js)}")
    print(f"Image URLs found: {total}")
    if args.no_download:
        print("Download skipped (--no-download)")
    else:
        print(f"Downloaded: {downloaded}")
        print(f"Output directory: {out_dir}")
    print(f"URLs file: {args.urls_file}")
    print(f"CSV file: {args.csv_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
