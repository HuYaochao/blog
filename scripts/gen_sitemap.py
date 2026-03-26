"""
gen_sitemap.py — 生成 sitemap.xml

用法:
    python scripts/gen_sitemap.py

输出:
    blog/sitemap.xml

配置:
    修改下方 BASE_URL 为你的 GitHub Pages 地址
"""

import json
import os
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

# ── 配置 ──────────────────────────────────────────────
BASE_URL = "https://huyaochao.github.io/blog"  # GitHub Pages URL（结尾不带 /）
OUTPUT   = os.path.join(os.path.dirname(__file__), "..", "sitemap.xml")
DATA     = os.path.join(os.path.dirname(__file__), "..", "posts.json")
# ──────────────────────────────────────────────────────

TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")


def make_url(loc: str, lastmod: str = "", changefreq: str = "monthly", priority: str = "0.5") -> ET.Element:
    url = ET.Element("url")
    ET.SubElement(url, "loc").text = loc
    ET.SubElement(url, "lastmod").text = lastmod or TODAY
    ET.SubElement(url, "changefreq").text = changefreq
    ET.SubElement(url, "priority").text = priority
    return url


def main():
    with open(DATA, encoding="utf-8") as f:
        posts = json.load(f)

    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    # 首页
    urlset.append(make_url(
        loc=f"{BASE_URL}/",
        lastmod=TODAY,
        changefreq="daily",
        priority="1.0"
    ))

    # 每篇文章的本地阅读页
    for post in posts:
        pid = post.get("id", "")
        if not pid:
            continue

        # 确定跳转平台（优先 csdn，次 zhihu，次 wechat）
        platforms = post.get("platforms", {})
        platform = "csdn" if platforms.get("csdn") else \
                   "zhihu" if platforms.get("zhihu") else \
                   "wechat" if platforms.get("wechat") else "csdn"

        loc = f"{BASE_URL}/post.html?id={pid}&platform={platform}"
        lastmod = post.get("date") or TODAY

        # 按阅读量设置 priority
        views = post.get("views") or 0
        if views >= 500:
            priority = "0.9"
        elif views >= 100:
            priority = "0.7"
        elif views >= 20:
            priority = "0.6"
        else:
            priority = "0.5"

        urlset.append(make_url(loc=loc, lastmod=lastmod, priority=priority))

    # 格式化输出
    ET.indent(urlset, space="  ")
    tree = ET.ElementTree(urlset)

    out_path = os.path.abspath(OUTPUT)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        tree.write(f, encoding="unicode", xml_declaration=False)

    print(f"[OK] sitemap.xml -> {len(posts) + 1} URLs")
    print(f"     path: {out_path}")


if __name__ == "__main__":
    main()
