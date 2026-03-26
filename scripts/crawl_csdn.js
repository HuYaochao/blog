/**
 * crawl_csdn.js — CSDN 后台文章列表采集脚本
 *
 * 使用方法：
 *   1. 浏览器登录 CSDN，打开后台管理页：
 *      https://mp.csdn.net/mp_blog/manage/article
 *   2. 打开浏览器控制台（F12 → Console）
 *   3. 粘贴以下全部代码并回车
 *   4. 等待脚本自动翻完所有页
 *   5. 自动下载 csdn_articles.json 到浏览器下载目录
 *   6. 将文件移动到 blog/scripts/csdn_articles.json
 *
 * 注意：
 *   - 必须在已登录状态下运行
 *   - 不要在脚本运行期间切换页面
 *   - 如果中途失败，可重新运行（脚本会从第1页重新开始）
 */

(async function collectCSDN() {
  const allArticles = [];

  /** 提取当前页所有文章 */
  function extractPage() {
    const rows = document.querySelectorAll('.article-list-item-mp');
    return Array.from(rows).map(r => {
      const a     = r.querySelector('a[href*="articleId"]');
      const id    = a?.href?.match(/articleId=(\d+)/)?.[1];
      const title = r.querySelector('.list-item-title')?.textContent?.trim()
                 || a?.textContent?.trim() || '';
      const date  = r.innerText.match(/\d{4}-\d{2}-\d{2}/)?.[0] || '';
      const views = r.innerText.match(/阅读\s*([\d,]+)/)?.[1]?.replace(/,/g, '') || '';
      return {
        title,
        articleId: id,
        url: id ? `https://blog.csdn.net/hyc010110/article/details/${id}` : '',
        date,
        views,
        category: '',   // 后台列表页无分类，build.py 里可手动补或用 Haiku 生成
        tags: [],
        summary: ''
      };
    }).filter(a => a.title && a.articleId);
  }

  function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

  /** 获取分页器上所有页码按钮 */
  function getPageBtns() {
    return [...document.querySelectorAll('[class*="pager"] li')];
  }

  /** 获取总页数（取页码按钮里最大的数字） */
  function getTotalPages() {
    const nums = getPageBtns()
      .map(b => parseInt(b.textContent.trim()))
      .filter(n => !isNaN(n));
    return Math.max(...nums, 1);
  }

  // 回第 1 页
  const firstBtn = getPageBtns().find(b => b.textContent.trim() === '1');
  if (firstBtn) { firstBtn.click(); await sleep(1500); }

  const totalPages = getTotalPages();
  console.log(`📄 共 ${totalPages} 页，开始采集…`);

  for (let page = 1; page <= totalPages; page++) {
    // 找目标页码按钮（处理分页器省略号情况）
    const btn = getPageBtns().find(b => b.textContent.trim() === String(page));
    if (btn) {
      btn.click();
      await sleep(1500);
    } else {
      // 页码按钮被省略，用"下一页"按钮
      const next = document.querySelector('[class*="pager"] .btn-next');
      if (next) { next.click(); await sleep(1500); }
    }

    const pageData = extractPage();
    allArticles.push(...pageData);
    console.log(`  第 ${page}/${totalPages} 页 → ${pageData.length} 篇，累计 ${allArticles.length} 篇`);
  }

  // 下载 JSON
  const blob = new Blob([JSON.stringify(allArticles, null, 2)], { type: 'application/json' });
  const link = document.createElement('a');
  link.href     = URL.createObjectURL(blob);
  link.download = 'csdn_articles.json';
  link.click();

  console.log(`✅ 完成！共 ${allArticles.length} 篇，文件已下载。`);
  window.__csdnArticles = allArticles;  // 也存到全局变量方便检查
  return allArticles.length;
})();
