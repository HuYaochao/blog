/**
 * crawl_zhihu.js — 知乎专栏文章爬取
 *
 * 使用方法：
 *   1. 登录知乎，打开创作中心文章列表：
 *      https://www.zhihu.com/creator/manage/creation/article
 *   2. 等页面完全加载
 *   3. F12 → Console，粘贴以下代码并回车
 *   4. 脚本自动翻页抓取所有文章，完成后自动下载 zhihu_articles.json
 *   5. 将文件放到 blog/scripts/zhihu_articles.json
 */

(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [];
  const seenTitles = new Set();

  function extractPage() {
    const items = [];
    // 文章卡片：标题链接匹配 /p/数字
    const links = document.querySelectorAll('a[href*="/p/"]');
    links.forEach(a => {
      const href = a.href || '';
      const match = href.match(/zhihu\.com\/p\/(\d+)/);
      if (!match) return;

      const articleId = match[1];
      const title = (a.textContent || a.innerText || '').trim();
      if (!title || title.length < 2) return;
      if (seenTitles.has(title)) return;
      seenTitles.add(title);

      // 向上找父容器，提取日期和阅读量
      let container = a;
      for (let i = 0; i < 8; i++) {
        container = container.parentElement;
        if (!container) break;
      }

      let date = '';
      let views = '';

      if (container) {
        const text = container.innerText || '';

        // 日期：匹配 YYYY-MM-DD 或 YYYY/MM/DD
        const dateMatch = text.match(/(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
        if (dateMatch) {
          date = `${dateMatch[1]}-${String(dateMatch[2]).padStart(2,'0')}-${String(dateMatch[3]).padStart(2,'0')}`;
        }

        // 阅读量：匹配"1234 次阅读"或"1.2万 阅读"
        const viewMatch = text.match(/([\d\.]+\s*[万千]?)\s*次?阅读/);
        if (viewMatch) {
          let v = viewMatch[1].trim();
          if (v.includes('万')) views = String(Math.round(parseFloat(v) * 10000));
          else if (v.includes('千')) views = String(Math.round(parseFloat(v) * 1000));
          else views = v.replace(/\D/g, '');
        }
      }

      items.push({
        title,
        articleId,
        url: `https://zhuanlan.zhihu.com/p/${articleId}`,
        date,
        views,
        category: '',
        tags: [],
        summary: '',
      });
    });
    return items;
  }

  function findNextBtn() {
    // 查找"下一页"按钮
    const btns = [...document.querySelectorAll('button, a')];
    return btns.find(b => {
      const t = (b.textContent || '').trim();
      return t === '下一页' || t === '›' || t === '>' || t === '下一页';
    });
  }

  let page = 1;
  console.log('[知乎] 开始抓取...');

  while (true) {
    await sleep(1200);
    const items = extractPage();
    results.push(...items);
    console.log(`[第${page}页] 新增 ${items.length} 篇，累计 ${results.length} 篇`);

    const nextBtn = findNextBtn();
    if (!nextBtn || nextBtn.disabled || nextBtn.getAttribute('aria-disabled') === 'true') {
      console.log('[知乎] 已到最后一页');
      break;
    }
    nextBtn.click();
    page++;
    await sleep(2000);
  }

  // 去重（按标题）
  const unique = [];
  const titles = new Set();
  for (const a of results) {
    if (!titles.has(a.title)) { titles.add(a.title); unique.push(a); }
  }

  console.log(`[知乎] 完成！共 ${unique.length} 篇（去重后）`);

  // 下载
  const blob = new Blob([JSON.stringify(unique, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'zhihu_articles.json';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
})();
