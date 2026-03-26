# -*- coding: utf-8 -*-
"""
fetch_content.py -- Fetch CSDN article body and write into posts/*.md

Usage:
    python scripts/fetch_content.py              # fetch 10 articles (default)
    python scripts/fetch_content.py --limit 50   # fetch up to 50
    python scripts/fetch_content.py --limit 0    # fetch ALL missing
    python scripts/fetch_content.py --delay 3    # slower, less likely to be blocked
    python scripts/fetch_content.py --file csdn_140000000.md  # one specific file

After running, re-run build.py to refresh posts.json summaries (if you add
gen_meta.py later).

Dependencies: requests, beautifulsoup4, markdownify  (all in requirements)
"""

import argparse
import re
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import markdownify

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- paths ---------------------------------------------------------------
ROOT      = Path(__file__).parent.parent
POSTS_DIR = ROOT / "posts"

# ---- HTTP headers (mimic a real browser) --------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://blog.csdn.net/",
}


# ---- frontmatter helpers ------------------------------------------------
_FM_CSDN_RE  = re.compile(r'^\s+csdn:\s+"([^"]*)"', re.MULTILINE)
_FM_END_RE   = re.compile(r'^---\s*$', re.MULTILINE)
_PLACEHOLDER = re.compile(r'<!--.*?-->', re.DOTALL)


def extract_csdn_url(md_text: str) -> str:
    """Pull the csdn URL out of the frontmatter."""
    m = _FM_CSDN_RE.search(md_text)
    return m.group(1) if m else ""


def has_body(md_text: str) -> bool:
    """Return True if the file already has real content after the frontmatter."""
    # find end of second ---
    matches = list(_FM_END_RE.finditer(md_text))
    if len(matches) < 2:
        return False
    body = md_text[matches[1].end():].strip()
    # strip placeholder comment
    body = _PLACEHOLDER.sub("", body).strip()
    return len(body) > 20   # at least some real text


def inject_body(md_text: str, body_md: str) -> str:
    """Replace the placeholder comment with actual content."""
    if _PLACEHOLDER.search(md_text):
        # Use lambda to prevent re from interpreting backslashes in body_md
        # (articles may contain \u, \n, \t etc. in code snippets)
        return _PLACEHOLDER.sub(lambda m: body_md, md_text, count=1)
    # fallback: just append
    return md_text.rstrip() + "\n\n" + body_md


# ---- CSDN fetcher -------------------------------------------------------
def fetch_csdn_body(url: str) -> tuple[str | None, str | None]:
    """
    Fetch a CSDN article page, extract content div, convert to Markdown.
    Returns (markdown_text, error_msg).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        return None, f"request error: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try several known CSDN content containers (changes over time)
    content_div = (
        soup.find("div", id="content_views") or
        soup.find("div", class_="markdown_views") or
        soup.find("div", class_="htmledit_views") or
        soup.find("div", id="article_content")
    )

    if not content_div:
        return None, "content div not found (page structure may have changed)"

    # Remove noisy elements: toolbar, copyright footer, ads
    for sel in ["#toolsBox", ".article-copyright", ".hide-article-box",
                ".recommend-box", ".insert-baidu-box"]:
        for el in content_div.select(sel):
            el.decompose()

    md = markdownify.markdownify(
        str(content_div),
        heading_style="ATX",
        bullets="-",
        strip=["script", "style"],
    ).strip()

    if len(md) < 50:
        return None, f"content too short ({len(md)} chars) — possibly paywalled or 404"

    return md, None


# ---- main ---------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Fetch CSDN article bodies into posts/*.md")
    parser.add_argument("--limit",  type=int,   default=10,
                        help="Max articles to fetch (0 = all, default 10)")
    parser.add_argument("--delay",  type=float, default=2.5,
                        help="Delay between requests in seconds (default 2.5)")
    parser.add_argument("--file",   type=str,   default=None,
                        help="Fetch a single MD file by name, e.g. csdn_140000000.md")
    parser.add_argument("--force",  action="store_true",
                        help="Re-fetch even if body already exists")
    args = parser.parse_args()

    # Collect target files
    if args.file:
        candidates = [POSTS_DIR / args.file]
    else:
        candidates = sorted(POSTS_DIR.glob("csdn_*.md"))

    to_fetch = []
    for path in candidates:
        if not path.exists():
            print(f"[WARN] not found: {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        url  = extract_csdn_url(text)
        if not url:
            continue
        if not args.force and has_body(text):
            continue
        to_fetch.append((path, url, text))

    total = len(to_fetch)
    if args.limit and args.limit > 0:
        to_fetch = to_fetch[:args.limit]

    print(f"[IN] {total} articles need content — fetching {len(to_fetch)}")
    if total > len(to_fetch):
        print(f"     (run with --limit 0 to fetch all {total})")

    ok = skip = fail = 0
    for i, (path, url, original_text) in enumerate(to_fetch, 1):
        label = f"[{i:03d}/{len(to_fetch)}] {path.name}"
        print(f"{label} ...", end=" ", flush=True)

        md_body, err = fetch_csdn_body(url)
        if err:
            print(f"FAIL ({err})")
            fail += 1
        else:
            new_text = inject_body(original_text, md_body)
            path.write_text(new_text, encoding="utf-8")
            chars = len(md_body)
            print(f"OK  ({chars:,} chars)")
            ok += 1

        if i < len(to_fetch):
            time.sleep(args.delay)

    print(f"\n[OK] Done: {ok} fetched, {fail} failed, {skip} skipped")
    if fail > 0:
        print("     Tip: CSDN may rate-limit. Try --delay 5 or run again later.")


if __name__ == "__main__":
    main()
