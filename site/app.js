const $ = (id) => document.getElementById(id);
let snapshot = null;
let busy = false;
let toastTimer;
const LOCAL_KEY = 'node-helper-snapshot-v1';
const names = { github: 'GitHub', gitlab: 'GitLab' };
function compactTime(value, seconds = false) {
  if (!value || Number.isNaN(Date.parse(value))) return '未获取';
  const options = { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false };
  if (seconds) options.second = '2-digit';
  const parts = Object.fromEntries(new Intl.DateTimeFormat('zh-CN', options).formatToParts(new Date(value)).map(part => [part.type, part.value]));
  return `${parts.month}-${parts.day} ${parts.hour}:${parts.minute}${seconds ? `:${parts.second}` : ''}`;
}
function element(tag, className, text) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  if (text !== undefined) el.textContent = text; // Never render source Markdown as HTML.
  return el;
}
function notify(text) {
  $('toast').textContent = text;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 2600);
}
async function copy(text) {
  if (!text) return;
  try {
    await navigator.clipboard.writeText(text);
    notify('已复制，可粘贴到客户端');
  } catch {
    $('copy-text').value = text;
    $('manual-copy').showModal();
    $('copy-text').focus();
    $('copy-text').select();
  }
}
function copyButton(label, className, text) {
  const button = element('button', className, label);
  button.type = 'button';
  button.addEventListener('click', () => copy(text));
  return button;
}
function linkIcon() {
  const namespace = 'http://www.w3.org/2000/svg';
  const svg = document.createElementNS(namespace, 'svg');
  svg.setAttribute('viewBox', '0 0 20 21.6166');
  svg.setAttribute('aria-hidden', 'true');
  for (const pathData of [
    'M12.4812 8.32937C12.328 8.16386 12.1648 8.01466 11.9965 7.87632L11.9962 7.87662C11.823 7.6966 11.5879 7.58573 11.3286 7.58573C10.7965 7.58573 10.3652 8.05192 10.3652 8.62698C10.3652 8.88143 10.4498 9.1145 10.5901 9.29536C10.6576 9.38236 10.7378 9.45726 10.8278 9.51656C10.9186 9.59752 11.0078 9.67725 11.0912 9.76736L11.1706 9.85323C12.1691 10.9311 11.871 12.788 10.8725 13.8672L6.6118 18.4709C5.61335 19.5487 3.99009 19.5487 2.99158 18.4709L2.91152 18.3843C1.91299 17.3051 1.91299 15.5494 2.91152 14.4729L4.79388 12.4391C5.03539 12.2319 5.19044 11.9121 5.19044 11.553C5.19044 10.9284 4.72196 10.4221 4.14406 10.4221C3.92599 10.4221 3.72356 10.4943 3.55594 10.6176L3.53422 10.6343C3.46013 10.6919 3.39313 10.7594 3.33527 10.8355L1.3791 12.8139C-0.4597 14.8027 -0.4597 18.0553 1.3791 20.0413L1.45852 20.1271C3.29732 22.1131 6.30548 22.1131 8.14428 20.1271L12.4037 15.5221C14.24 13.5348 14.3957 10.3999 12.5595 8.41385L12.4812 8.32937Z',
    'M18.6211 1.57638L18.5416 1.49054C16.7029 -0.496847 13.6947 -0.496847 11.8559 1.49054L7.59646 6.09553C5.75766 8.08292 5.65639 10.9528 7.49519 12.9415L7.57335 13.0247C7.65686 13.1149 7.74353 13.2 7.83201 13.2816C7.89606 13.3589 7.9713 13.4251 8.05493 13.4774C8.19044 13.5616 8.3449 13.6093 8.50973 13.6093C9.01204 13.6093 9.41923 13.1692 9.41923 12.6263C9.41923 12.4731 9.38676 12.328 9.32887 12.1988C9.20863 11.907 8.98356 11.7293 8.82788 11.561L8.7497 11.4779C7.75124 10.3988 8.1304 8.83098 9.12885 7.75184L13.3908 3.14816C14.3868 2.06897 16.0106 2.06897 17.0091 3.14816L17.0886 3.23263C18.0871 4.31185 18.0871 6.06825 17.0886 7.14607L15.2124 9.17524C14.9572 9.37963 14.7917 9.70748 14.7917 10.0771C14.7917 10.6967 15.2564 11.1989 15.8296 11.1989C16.0291 11.1989 16.2154 11.138 16.3736 11.0325L16.4062 11.0099C16.4958 10.9451 16.5755 10.8654 16.6424 10.7744L18.6197 8.80238C20.4599 6.81502 20.4599 3.56374 18.6211 1.57638Z'
  ]) {
    const path = document.createElementNS(namespace, 'path');
    path.setAttribute('d', pathData);
    path.setAttribute('fill', '#514BEA');
    svg.append(path);
  }
  return svg;
}
function nodeCard(node) {
  const card = element('section', 'node');
  const top = element('div', 'node-summary');
  const icon = element('span', 'node-icon');
  icon.append(linkIcon());
  const main = element('div', 'node-main');
  const title = element('h3', '', node.name);
  title.append(element('span', 'protocol', node.protocol.toUpperCase()));
  const button = copyButton('复制', 'node-copy', node.import_url);
  button.setAttribute('aria-label', `复制${node.name}一键导入链接`);
  const address = node.fields.find(f => /address|地址/i.test(f.label))?.value || '展开查看节点信息';
  main.append(title, element('p', 'address', address));
  top.append(icon, main, button);
  card.append(top);
  const details = element('details');
  details.addEventListener('toggle', () => card.classList.toggle('is-open', details.open));
  details.append(element('summary', '', '参数与导入链接'));
  const table = element('table');
  table.setAttribute('aria-label', `${node.name}参数`);
  const body = element('tbody');
  for (const field of node.fields) {
    const row = element('tr');
    row.append(element('td', '', field.label), element('td', '', field.value || '—'));
    body.append(row);
  }
  table.append(body);
  const link = element('textarea');
  link.value = node.import_url;
  link.readOnly = true;
  link.setAttribute('aria-label', `${node.name}导入链接`);
  const info = `${node.name}（${node.protocol}）\n${node.fields.map(f => `${f.label}: ${f.value}`).join('\n')}\n\n${node.import_url}`;
  details.append(table, link, copyButton('复制完整信息', 'info-copy', info));
  if (node.notes) details.append(element('p', 'note', node.notes));
  card.append(details);
  return card;
}
function sourceCard(source) {
  const card = element('article', 'source');
  const header = element('div', 'source-header');
  const name = element('div', 'source-name');
  const info = element('div');
  const origin = element('a', 'source-origin');
  // Only known origins are made clickable.
  const url = new URL(source.url);
  if (url.protocol === 'https:' && ['github.com', 'gitlab.com'].includes(url.hostname)) origin.href = url.href;
  origin.target = '_blank'; origin.rel = 'noopener noreferrer';
  origin.setAttribute('aria-label', `打开 ${source.name} 原始页面`);
  origin.append(element('h2', '', source.name));
  info.append(origin);
  const logo = element('img', 'source-logo');
  logo.classList.add(`source-logo-${source.id}`);
  logo.src = `./icons/${source.id}.svg`;
  logo.alt = '';
  name.append(logo, info);
  const label = source.stale ? '上次成功数据' : source.status === 'ok' ? '获取正常' : source.status === 'partial' ? '部分获取' : '获取失败';
  const pillClass = source.status === 'ok' && !source.stale ? 'pill' : source.status === 'error' && !source.stale ? 'pill error' : 'pill warn';
  header.append(name, element('span', pillClass, label));
  const times = element('dl', 'times');
  const authorTime = source.author_updated?.iso ? (source.author_updated.precision === 'day' ? `${source.author_updated.iso.slice(5, 10)}（仅日期）` : compactTime(source.author_updated.iso)) : (source.author_updated?.raw || '正文未提供');
  const entries = [['网页最后编辑', compactTime(source.page_edited_at, true)], ['作者更新时间', authorTime]];
  if (source.stale) entries.push(['上次成功获取', compactTime(source.last_success_at)]);
  for (const [label, value] of entries) {
    const group = element('div');
    group.append(element('dt', '', label), element('dd', '', value));
    times.append(group);
  }
  if (source.author_updated?.raw) times.title = `作者原文：${source.author_updated.raw}`;
  card.append(header, times);
  if (source.author_updated?.raw && !source.author_updated?.iso) card.append(element('p', 'source-warning', `作者原文：${source.author_updated.raw}`));
  for (const warning of [...(source.warnings || []), ...(source.error ? [source.error] : [])]) card.append(element('p', 'source-warning', warning));
  if (!source.nodes.length) card.append(element('p', 'empty', '尚无可用节点。下一次后台检测会继续尝试。'));
  for (const node of source.nodes) card.append(nodeCard(node));
  return card;
}
function valid(data) {
  return data?.schema_version === 1 && Array.isArray(data.sources) && data.sources.length === 2 && data.latest && data.comparison && data.sources.every(s => names[s.id] && Array.isArray(s.nodes) && s.nodes.every(n => Array.isArray(n.fields) && typeof n.import_url === 'string' && typeof n.protocol === 'string'));
}
function render(data, cached = false) {
  snapshot = data;
  $('checked').textContent = `北京时间 ${compactTime(data.checked_at)}`;
  $('health').textContent = '30分钟自动检测';
  const age = Date.now() - Date.parse(data.checked_at);
  const alerts = [];
  if (cached) alerts.push('暂时无法读取在线结果，正在显示本机缓存。');
  // Scheduled GitHub Actions can be delayed for several hours during busy periods.
  const staleAfterMinutes = Math.max(12 * 60, Number(data.interval_minutes || 30) * 24);
  if (age > staleAfterMinutes * 60 * 1000) alerts.push('后台检测已超过12小时未更新，请检查 GitHub Actions 是否正常运行。');
  if (data.sources.some(s => s.stale)) alerts.push('部分来源本次获取失败，卡片保留上次成功数据。');
  $('notice').textContent = alerts.join(' ');
  $('notice').hidden = !alerts.length;
  const comparison = data.comparison;
  const suffix = comparison.includes_stale ? '（含旧数据）' : '';
  $('comparison').textContent = ({ same: '两站节点一致', different: '两站节点不一致', unknown: '暂时无法比对' }[comparison.status] || '暂时无法比对') + suffix;
  $('comparison-icon').textContent = comparison.status === 'same' ? '✓' : comparison.status === 'different' ? '!' : '?';
  $('summary-card').dataset.state = comparison.status;
  const source = data.sources.find(s => s.id === data.latest.source_id);
  $('selection').textContent = source ? `当前为你选择的是 ${source.name} 的节点${data.latest.stale ? '（上次成功数据）' : ''}` : '暂时没有可用节点';
  for (const [id, number] of [['copy-1', 1], ['copy-2', 2]]) $(id).disabled = !source?.nodes.some(node => node.id === number);
  // Keep disclosure state when the background read refreshes cards.
  const opened = new Set([...document.querySelectorAll('.source')].flatMap((card, i) => [...card.querySelectorAll('details')].flatMap((d, j) => d.open ? [`${i}:${j}`] : [])));
  const displayOrder = { gitlab: 0, github: 1 };
  const visibleSources = [...data.sources].sort((a, b) => displayOrder[a.id] - displayOrder[b.id]);
  $('sources').replaceChildren(...visibleSources.map(sourceCard));
  document.querySelectorAll('.source').forEach((sourceCardElement, i) => sourceCardElement.querySelectorAll('details').forEach((details, j) => {
    details.open = opened.has(`${i}:${j}`);
    details.closest('.node')?.classList.toggle('is-open', details.open);
  }));
}
async function refresh(manual = false) {
  if (busy) return;
  busy = true;
  setRefreshing(true);
  try {
    if (location.protocol === 'file:') {
      if (!valid(window.__NODE_DATA__)) throw new Error('本地预览数据不存在');
      render(window.__NODE_DATA__);
      if (manual) notify('已读取项目内的预览数据');
      return;
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    let data;
    try {
      const response = await fetch(`./data.json?t=${Date.now()}`, { cache: 'no-store', signal: controller.signal });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      data = await response.json();
    } finally { clearTimeout(timer); }
    if (!valid(data)) throw new Error('数据格式不正确');
    // A briefly lagging CDN must not replace a newer local snapshot.
    if (snapshot && Date.parse(snapshot.checked_at) > Date.parse(data.checked_at)) data = snapshot;
    render(data);
    try { localStorage.setItem(LOCAL_KEY, JSON.stringify(data)); } catch { /* Private mode / quota: online still works. */ }
    if (manual) notify('已读取后台最新检测结果');
  } catch {
    if (snapshot) render(snapshot, true);
    else {
      $('notice').hidden = false;
      $('notice').textContent = '暂时无法加载节点数据。首次使用请联网，并确认 GitHub Actions 已完成部署。';
      $('checked').textContent = '暂无检测结果';
      $('health').textContent = '等待后台数据';
      $('selection').textContent = '获取成功后即可复制节点。';
      $('comparison').textContent = '暂无数据';
      $('comparison-icon').textContent = '?';
      $('summary-card').dataset.state = 'unknown';
      $('sources').replaceChildren(element('p', 'empty', '点击“刷新结果”重试。'));
    }
    if (manual) notify(snapshot ? '读取失败，已保留缓存' : '读取失败，请稍后重试');
  } finally {
    busy = false; setRefreshing(false);
  }
}
function setRefreshing(active) {
  $('refresh').disabled = active;
  $('refresh').classList.toggle('is-loading', active);
  $('refresh').setAttribute('aria-busy', String(active));
}
for (const [id, number] of [['copy-1', 1], ['copy-2', 2]]) {
  $(id).addEventListener('click', () => {
    const source = snapshot?.sources.find(s => s.id === snapshot.latest.source_id);
    copy(source?.nodes.find(n => n.id === number)?.import_url);
  });
}
$('refresh').addEventListener('click', () => refresh(true));
$('close-copy').addEventListener('click', () => $('manual-copy').close());
const backToTop = $('back-to-top');
function updateBackToTop() { backToTop.classList.toggle('is-visible', window.scrollY > 560); }
backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }));
window.addEventListener('scroll', updateBackToTop, { passive: true });
updateBackToTop();
try { const saved = JSON.parse(localStorage.getItem(LOCAL_KEY)); if (valid(saved)) render(saved, true); } catch { /* Ignore invalid local cache. */ }
if (!snapshot && valid(window.__NODE_DATA__)) render(window.__NODE_DATA__);
refresh();
setInterval(() => { if (!document.hidden) refresh(); }, 5 * 60 * 1000);
document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
window.addEventListener('online', () => refresh());
if (location.protocol !== 'file:' && 'serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(() => {});
