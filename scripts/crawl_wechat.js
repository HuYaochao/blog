/**
 * crawl_wechat.js — 微信公众号文章列表抓取
 *
 * 使用方法：
 *   1. 登录微信公众号后台，打开已发布文章列表页：
 *      https://mp.weixin.qq.com/cgi-bin/appmsgpublish?sub=list&begin=0&count=10
 *      （token 会自动从 URL 携带，不需要手动加）
 *   2. 确保页面全部加载
 *   3. F12 → Console，粘贴下面代码并回车
 *   4. 自动翻页完成后，下载 wechat_articles.json
 *   5. 把文件放到 blog/scripts/wechat_articles.json
 *
 * 注意：token 不会保存到 JSON 文件里，只用于当前会话请求
 */

(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const results = [];
  const seenTitles = new Set();

  function getToken() {
    return new URLSearchParams(location.search).get('token') || '';
  }

  // 自动获取 fakeid（公众号账号ID）
  function getFakeid() {
    // 方式1: window 全局变量
    if (window.wx && window.wx.fakeid) return window.wx.fakeid;
    if (window.__wxjs_environment) return '';
    // 方式2: 页面 script 标签
    for (const s of document.querySelectorAll('script')) {
      const m = s.textContent.match(/fakeid['":\s=]+['"]([a-zA-Z0-9_\-]+)['"]/);
      if (m) return m[1];
    }
    // 方式3: URL 参数
    const p = new URLSearchParams(location.search);
    return p.get('fakeid') || '';
  }

  // 去除 token/scene 等追踪参数
  function stripToken(url) {
    try {
      const u = new URL(url);
      ['token','lang','scene','subscene','pass_ticket','wx_header'].forEach(k => u.searchParams.delete(k));
      return u.toString();
    } catch { return url; }
  }

  function formatTs(ts) {
    const d = new Date(ts * 1000);
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }

  // 通过 JSON API 获取文章列表（比 DOM 稳定）
  async function fetchPage(begin, count = 10) {
    const token = getToken();
    const fakeid = getFakeid();
    const apiUrl = `/cgi-bin/appmsg?action=list_ex&begin=${begin}&count=${count}&fakeid=${fakeid}&type=9&query=&token=${token}&lang=zh_CN&f=json&ajax=1`;
    try {
      const res = await fetch(apiUrl, { credentials: 'include' });
      const data = await res.json();
      console.log(`[API begin=${begin}] ret=${data.base_resp?.ret}, count=${data.app_msg_list?.length}`);
      if (data && data.app_msg_list && data.app_msg_list.length > 0) {
        return data.app_msg_list.map(item => ({
          title:     item.title || '',
          articleId: String(item.aid || item.appmsgid || ''),
          url:       stripToken(item.link || ''),
          date:      item.update_time ? formatTs(item.update_time) : '',
          views:     item.read_num != null ? String(item.read_num) : '',
          summary:   item.digest || '',
          platform:  'wechat',
        }));
      }
      if (data.base_resp && data.base_resp.ret !== 0) {
        console.warn('[微信] API 返回错误 ret=' + data.base_resp.ret + '，尝试 DOM 回退');
      }
    } catch (e) {
      console.warn('[微信] JSON API 失败，降级到 DOM 抓取:', e.message);
    }
    return null;
  }

  // DOM 回退（当 API 失败时）
  function extractDOM() {
    const items = [];
    const rows = document.querySelectorAll('.weui-desktop-list-item, tr[data-id], .article-list-item');
    rows.forEach(row => {
      const titleEl = row.querySelector('a[href*="mp.weixin.qq.com/s"]') ||
                      row.querySelector('.article-title a') ||
                      row.querySelector('a[target="_blank"]');
      if (!titleEl) return;
      const title = (titleEl.textContent || '').trim();
      if (!title || seenTitles.has(title)) return;
      const url = stripToken(titleEl.href || '');
      const rowText = row.innerText || '';
      let date = '';
      const dm = rowText.match(/(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})/);
      if (dm) date = `${dm[1]}-${String(dm[2]).padStart(2,'0')}-${String(dm[3]).padStart(2,'0')}`;
      let views = '';
      const vm = rowText.match(/([\d,]+)\s*次?阅读/);
      if (vm) views = vm[1].replace(/,/g, '');
      items.push({ title, articleId: '', url, date, views, summary: '', platform: 'wechat' });
    });
    return items;
  }

  async function gotoPage(begin) {
    const token = getToken();
    history.pushState({}, '', `/cgi-bin/appmsgpublish?sub=list&begin=${begin}&count=10&token=${token}&lang=zh_CN`);
    await sleep(1500);
  }

  console.log('[微信] 开始抓取... fakeid=' + getFakeid());

  let begin = 0;
  let emptyCount = 0;

  while (true) {
    await gotoPage(begin);
    await sleep(1800);

    let items = await fetchPage(begin, 10);
    if (!items) items = extractDOM();

    const newItems = items.filter(a => {
      if (!a.title || seenTitles.has(a.title)) return false;
      seenTitles.add(a.title);
      return true;
    });

    results.push(...newItems);
    console.log(`[begin=${begin}] 新增 ${newItems.length} 篇，累计 ${results.length} 篇`);

    if (newItems.length === 0) {
      emptyCount++;
      if (emptyCount >= 2) { console.log('[微信] 连续两页为空，停止'); break; }
    } else {
      emptyCount = 0;
    }

    if (items.length < 10) { console.log('[微信] 最后一页，停止'); break; }
    begin += 10;
    await sleep(1500);
  }

  console.log(`[微信] 完成！共 ${results.length} 篇`);

  const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
  const a = Object.assign(document.createElement('a'), {
    href: URL.createObjectURL(blob),
    download: 'wechat_articles.json'
  });
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
})();
