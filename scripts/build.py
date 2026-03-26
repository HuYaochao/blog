# -*- coding: utf-8 -*-
"""
build.py -- csdn_articles.json -> MD backup files + posts.json
Usage:
    python scripts/build.py
Output:
    posts/csdn_XXXXXX.md   per-article frontmatter backup
    posts.json             data file read by index.html
"""

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ---- paths ---------------------------------------------------------------
ROOT        = Path(__file__).parent.parent          # blog/
SCRIPTS     = ROOT / "scripts"
POSTS_DIR   = ROOT / "posts"
OUTPUT_JSON = ROOT / "posts.json"

CSDN_JSON   = SCRIPTS / "csdn_articles.json"
ZHIHU_JSON  = SCRIPTS / "zhihu_articles.json"   # placeholder
WECHAT_JSON = SCRIPTS / "wechat_articles.json"  # placeholder

CSDN_USER   = "hyc010110"


# ---- helpers -------------------------------------------------------------
def slugify(title: str, article_id: str) -> str:
    safe = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', title)[:40].strip('_')
    return f"csdn_{article_id}"


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_md(article: dict, platform: str):
    """Generate MD file with frontmatter (body left empty)."""
    aid = article.get("articleId") or article.get("id") or ""
    if not aid:
        # For zhihu/wechat without a numeric ID, derive one from the URL
        url = article.get("url", "")
        import hashlib
        aid = hashlib.md5(url.encode()).hexdigest()[:10] if url else "unknown"
    filename = f"{platform}_{aid}.md"
    filepath = POSTS_DIR / filename

    # Skip if exists (preserve any manual edits)
    if filepath.exists():
        return False

    platforms_block = {}
    if platform == "csdn":
        platforms_block["csdn"] = article.get("url", "")
    elif platform == "zhihu":
        platforms_block["zhihu"] = article.get("url", "")
    elif platform == "wechat":
        platforms_block["wechat"] = article.get("url", "")

    title    = article.get("title", "").replace('"', '\\"')
    date     = article.get("date", "")
    views    = article.get("views", "")
    category = article.get("category", "")
    tags_raw = article.get("tags", [])
    tags_str = json.dumps(tags_raw, ensure_ascii=False) if tags_raw else "[]"
    summary  = article.get("summary", "")

    fm = f"""---
title: "{title}"
date: "{date}"
category: "{category}"
tags: {tags_str}
summary: "{summary}"
views: "{views}"
platforms:
  csdn: "{platforms_block.get('csdn', '')}"
  zhihu: "{platforms_block.get('zhihu', '')}"
  wechat: "{platforms_block.get('wechat', '')}"
---

<!-- article body (optional) - use fetch_content.py to auto-fill -->
"""
    filepath.write_text(fm, encoding="utf-8")
    return True


def build_posts_json(articles: list) -> list:
    """
    Build posts.json data structure.
    Deduplication strategy:
      - Same title across platforms → merge into one entry (union of platform URLs)
      - Same CSDN articleId         → keep first occurrence
    """
    # Pass 1: group by normalised title
    from collections import defaultdict
    by_title = defaultdict(list)
    for a in articles:
        title = (a.get("title") or "").strip()
        if title:
            by_title[title].append(a)

    posts = []
    seen_csdn_ids = set()

    for title, group in by_title.items():
        # Sort group: csdn first (has articleId), then zhihu, wechat
        group.sort(key=lambda x: {"csdn": 0, "zhihu": 1, "wechat": 2}.get(x.get("_src", ""), 3))

        base = group[0]
        aid = base.get("articleId") or base.get("id") or ""

        # Skip duplicate CSDN articles (same articleId)
        if base.get("_src") == "csdn" and aid:
            if aid in seen_csdn_ids:
                continue
            seen_csdn_ids.add(aid)

        # Merge platform URLs from all entries with this title
        platforms = {"csdn": "", "zhihu": "", "wechat": ""}
        for a in group:
            src = a.get("_src", "")
            if src in platforms and not platforms[src]:
                platforms[src] = a.get("url", "")

        # Pick best metadata (first non-empty wins)
        def first(*keys):
            for a in group:
                for k in keys:
                    v = a.get(k, "")
                    if v:
                        return v
            return ""

        posts.append({
            "id":       aid or title[:40],
            "title":    title,
            "date":     first("date"),
            "category": first("category"),
            "tags":     next((a.get("tags") for a in group if a.get("tags")), []),
            "summary":  first("summary"),
            "views":    first("views"),
            "platforms": platforms,
        })

    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


# ---- main ----------------------------------------------------------------
def main():
    POSTS_DIR.mkdir(exist_ok=True)

    csdn_raw   = load_json(CSDN_JSON)
    zhihu_raw  = load_json(ZHIHU_JSON)
    wechat_raw = load_json(WECHAT_JSON)

    for a in csdn_raw:   a["_src"] = "csdn"
    for a in zhihu_raw:  a["_src"] = "zhihu"
    for a in wechat_raw: a["_src"] = "wechat"

    print(f"[IN] Input: CSDN {len(csdn_raw)} | Zhihu {len(zhihu_raw)} | WeChat {len(wechat_raw)}")

    new_md = 0
    for a in csdn_raw:   new_md += write_md(a, "csdn")
    for a in zhihu_raw:  new_md += write_md(a, "zhihu")
    for a in wechat_raw: new_md += write_md(a, "wechat")
    print(f"[MD] New MD files: {new_md} (existing skipped)")

    posts = build_posts_json(csdn_raw + zhihu_raw + wechat_raw)
    OUTPUT_JSON.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[OK] posts.json -> {len(posts)} articles")
    print(f"     path: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
