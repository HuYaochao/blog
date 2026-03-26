# 小胡说技书 — 博客聚合站

个人博客内容整理发布站，聚合 CSDN / 知乎 / 微信公众号三平台文章，托管于 GitHub Pages。

---

## 目录结构

```
blog/
├── index.html          主页（纯静态，读取 posts.json 渲染）
├── posts.json          文章数据（由 build.py 生成，不要手动编辑）
├── logo.jpg            站点 Logo（直接替换此文件即可更换）
├── css/
│   ├── base.css        CSS 变量 & reset
│   ├── dark.css        深色模式
│   ├── sidebar.css     侧栏
│   ├── topbar.css      顶栏 & 搜索
│   └── cards.css       文章卡片 & 分页
├── posts/              MD 备份（每篇文章一个文件，含 frontmatter）
└── scripts/
    ├── crawl_csdn.js   CSDN 爬取脚本（浏览器控制台运行）
    ├── build.py        数据构建脚本（本地 Python 运行）
    ├── csdn_articles.json    CSDN 原始数据（爬取后放这里）
    ├── zhihu_articles.json   知乎原始数据（预留）
    └── wechat_articles.json  公众号原始数据（预留）
```

---

## 日常更新流程

### 第一步：重新爬取 CSDN（有新文章时）

1. 浏览器登录 CSDN，打开后台管理页：
   `https://mp.csdn.net/mp_blog/manage/article`
2. 按 `F12` 打开控制台（Console 标签）
3. 打开 `scripts/crawl_csdn.js`，全选复制，粘贴到控制台回车
4. 等待约 35 秒（自动翻 23 页），完成后自动下载 `csdn_articles.json`
5. 将下载的文件移动到 `blog/scripts/csdn_articles.json`（覆盖旧文件）

### 本地预览

直接双击打开 index.html **不行**（浏览器的 file:// 安全限制会阻止 fetch）。
需要起一个本地 HTTP 服务器：

```bash
cd D:\dev\project\blog
python -m http.server 8080
```

然后浏览器打开 http://localhost:8080 即可。

---

## 第二步：重新构建数据

```bash
cd D:\dev\project\blog
python scripts/build.py
```

输出：
- `posts/csdn_XXXXXX.md` — 新文章的 MD 备份（已存在的不覆盖）
- `posts.json` — 更新后的聚合数据

### 第三步：提交到 GitHub

```bash
git add .
git commit -m "update: 同步 CSDN 文章 $(date +%Y-%m-%d)"
git push
```

---

## 第三步（可选）：抓取文章正文

```bash
# 默认抓 10 篇测试
python scripts/fetch_content.py

# 抓全部（300 篇，约 15 分钟）
python scripts/fetch_content.py --limit 0

# 常用参数
#   --limit N     最多抓 N 篇（0=全部）
#   --delay N     请求间隔秒数（默认 2.5，越大越安全）
#   --file xxx.md 只抓某一篇
#   --force       重新抓已有正文的文章
```

正文直接写入 `posts/csdn_XXXXXX.md` 的 frontmatter 之后。
如果出现大量 FAIL 可加大 `--delay`，或分批跑（每次 `--limit 50`）。

依赖：`pip install markdownify`（其他库已自带）

---

## 知乎文章爬取

脚本：`scripts/crawl_zhihu.js`

1. 登录知乎，打开：https://www.zhihu.com/creator/manage/creation/article
2. 等页面加载完毕
3. F12 → Console，粘贴 `crawl_zhihu.js` 内容并回车
4. 脚本自动翻页，完成后下载 `zhihu_articles.json`
5. 将文件放到 `blog/scripts/zhihu_articles.json`，重新运行 `build.py`

---

## 微信公众号文章爬取

脚本：`scripts/crawl_wechat.js`

1. 登录微信公众号后台，打开：
   https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=10
   （token 会由浏览器自动携带，**不要**手动加到脚本里）
2. F12 → Console，粘贴 `crawl_wechat.js` 内容并回车
3. 完成后下载 `wechat_articles.json`（token 已自动从所有 URL 中清除）
4. 将文件放到 `blog/scripts/wechat_articles.json`，重新运行 `build.py`

---

## 后续计划（待完成）

### 摘要 & 分类自动生成（用 Haiku 省 token）

脚本：`scripts/gen_meta.py`（待写）

思路：扫描 `posts/` 下 summary 为空的 MD 文件，
      调用 Claude Haiku API，批量生成摘要和分类，
      写回 frontmatter，再跑 build.py 重建 posts.json。

```python
# 预计调用方式
python scripts/gen_meta.py --model haiku --limit 50
```

### 知乎爬取

脚本：`scripts/crawl_zhihu.js`（待写）
数据：`scripts/zhihu_articles.json`

### 微信公众号爬取

脚本：`scripts/crawl_wechat.js`（待写）
数据：`scripts/wechat_articles.json`

---

## 数据格式说明

### csdn_articles.json（爬虫输出）

```json
[
  {
    "title": "文章标题",
    "articleId": "123456789",
    "url": "https://blog.csdn.net/hyc010110/article/details/123456789",
    "date": "2025-11-20",
    "views": "1234",
    "category": "",
    "tags": [],
    "summary": ""
  }
]
```

### posts.json（build.py 输出，网页读取）

```json
[
  {
    "id": "123456789",
    "title": "文章标题",
    "date": "2025-11-20",
    "category": "Python",
    "tags": ["爬虫", "自动化"],
    "summary": "一句话摘要",
    "views": "1234",
    "platforms": {
      "csdn": "https://blog.csdn.net/...",
      "zhihu": "",
      "wechat": ""
    }
  }
]
```

### posts/csdn_XXXXXX.md（MD 备份）

```markdown
---
title: "文章标题"
date: "2025-11-20"
category: ""
tags: []
summary: ""
views: "1234"
platforms:
  csdn: "https://blog.csdn.net/..."
  zhihu: ""
  wechat: ""
---

<!-- 正文备份（可选填充）-->
```

---

## 技术栈

- 前端：纯静态 HTML + CSS（纸张风格，参考 papyrai-ui）
- 托管：GitHub Pages
- 数据：`posts.json`（静态文件，无后端）
- 爬取：浏览器控制台 JS 脚本（需登录态）
- 构建：Python 3（无额外依赖，仅标准库）
- 浏览量统计：localStorage（本地累加，后续可换 busuanzi）
