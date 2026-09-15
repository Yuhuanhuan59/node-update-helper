# 节点更新助手

一个手机优先的静态 PWA：集中查看 GitHub / GitLab 两个公开 Wiki 的节点1、节点2，一键复制链接或完整参数，自动比较两站内容。后台使用 Python 标准库抓取，GitHub Actions 每30分钟生成 `site/data.json`，GitHub Pages 发布网页。无需服务器、数据库、API Key 或付费中转服务。

## 立即部署到 GitHub Pages

1. 创建一个 **Public（公开）** GitHub 仓库，例如 `node-update-helper`，默认分支用 `main`。
2. 上传本项目**目录内的全部文件**到仓库根目录。根目录应直接看到 `README.md`、`site/`、`scripts/`、`tests/` 和 `.github/`，不要把整个项目再包一层，也不要只上传 ZIP。
3. 打开仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**。
4. 打开 **Actions → Update nodes and deploy Pages → Run workflow**，选择默认分支并运行。首次上传时，如果任务因为尚未开启 Pages 而失败，完成第3步后重新运行即可。
5. 等 `build` 和 `deploy` 成功，点击任务内的 `github-pages` 地址，或在 Settings → Pages 中打开站点。通常为 `https://你的用户名.github.io/node-update-helper/`。

以后默认在北京时间每小时的00分、30分自动检测。新提交前端或脚本后也会自动发布。无需手动修改仓库名、基础路径或填入 Token。

### 上传方式

**Git 命令上传**（在本项目根目录执行；替换示例用户名和仓库名）：

```bash
git init -b main
git add .
git commit -m "Add node update helper"
git remote add origin https://github.com/YOUR_USERNAME/node-update-helper.git
git push -u origin main
```

如果使用 GitHub 网页上传，特别注意 `.github` 是隐藏目录。macOS Finder 用 `Command + Shift + .` 显示隐藏文件。如果上传时遗漏它，可在仓库里用 **Add file → Create new file**，文件名填 `.github/workflows/update-and-deploy.yml`，将本项目同名文件的完整内容粘贴进去。没有该文件就不会有自动任务。

工作流支持 `main` 和 `master` 的推送，且只在仓库默认分支执行。若自定义默认分支名称，请修改工作流的 `push.branches`。定时任务也只从默认分支运行。

## 使用方式

- **复制节点1 / 复制节点2**：两个按钮分别复制选中来源的单个节点导入链接，每次只复制一个节点。
- **来源卡片 → 参数与导入链接**：展开参数表、原始链接和说明；可复制完整信息。
- **刷新结果**：重新读取已发布的 `data.json`，不直接触发抓取。需要立即抓取时，到自己的 Actions 页面手动运行工作流。
- 在前台打开的网页每5分钟读取一次后台结果；切回网页或恢复网络时也会读取。
- 支持 PWA 的浏览器可从浏览器菜单安装；iPhone 可在 Safari 分享菜单中选择“添加到主屏幕”。离线前至少在线打开过一次。

## 时间与最新来源选择

每个来源保留三类时间，前端统一以**北京时间（UTC+8）**显示：

| 字段 | 含义与来源 |
| --- | --- |
| 网页最后编辑 `page_edited_at` | GitHub Wiki 标题区的 `relative-time[datetime]`；GitLab 对应 Wiki 历史页 `#versions` 下的最新提交时间。不是仓库整体更新时间，也不是 HTTP 缓存时间。 |
| 作者更新时间 `author_updated` | 仅解析正文“更新时间”标签所在行，保留原文、解析值和精度。当前来源的中文时间按北京时间解释；只有日期时标明“仅日期”。 |
| 最后检测 `checked_at` | 脚本此次实际检测时间，来源级别和整个快照分别保存。`last_success_at` 是该来源最后成功读取完整节点的时间。 |

选择规则：

1. 优先选本次成功取得完整节点的来源（含“节点成功、编辑时间失败”的部分成功来源）。失败来源的缓存仍可在卡片单独复制。
2. 两站都有作者时间时，比较作者时间；否则，如果两站都有网页编辑时间，统一比较网页编辑时间。不会混用两种时间直接比较。
3. 节点内容一致时任一来源都可使用。内容不同且时间相同或无法比较时，明确显示“先后待确认”；排序相同时稳定选 GitHub（若可用），不声称已确认最新。只有日期的作者时间按整日区间判断；与另一来源时间重叠时也标记先后待确认。
4. 只有一个本次成功来源时使用该来源，并提示无法确认另一来源是否更新。
5. 两站均失败时，在已有缓存中按上述时间规则选取；按钮改为“复制上次成功节点”。首次运行又没有缓存时禁用复制。

“最新”指发布内容的先后，不表示节点连通性经过测试。正文注明仅“更新节点2”时，本工具保留这一原文；它是页面级作者时间，不伪造每个节点各自的更新时间。

## 抓取与容错

来源：

- [GitHub Wiki 原页面](https://github.com/Alvin9999-newpac/fanqiang/wiki/v2ray%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7)
- [GitLab Wiki 原页面](https://gitlab.com/zhifan999/fq/-/wikis/v2ray%E5%85%8D%E8%B4%B9%E8%B4%A6%E5%8F%B7)

GitHub 使用官方域名的 Wiki 原始 Markdown；GitLab 使用公开 Wiki API。两个来源并行、独立抓取，单次请求超时20秒，最多尝试3次，限制响应大小。前端只请求同站静态 JSON，没有跨域抓取问题。

节点解析按 `节点1/节点2` 的粗体标题或 Markdown 标题分段，再寻找该节点的“一键导入链接”子标题和参数表。支持当前 VMess / AnyTLS，以及若干常见导入链接协议；不绑定 IP、域名、端口、UUID 或密码。VMess 会检查其 Base64 JSON 中的必需字段。

两个节点都完整才更新该来源。若缺少标题、表格或链接，或出现多个无法确定的链接，会将该来源判为失败并保留上次完整快照，避免把截断页面当成新数据。只有编辑时间获取失败时，保留本次新节点并将编辑时间显示为“未获取”；不会拿旧编辑时间冒充新内容的时间。

比对同时包含节点参数表与导入配置。忽略标签空白、URI 查询参数顺序、VMess JSON 格式与备注 `ps`、其他 URI 的显示名称 `#fragment`；保留连接地址、凭证、TLS 等参数。它是保守比对，不把不同参数名或不同编码形式的所有等价配置强行判为一致。以后作者大幅改变结构时，页面会显示解析失败，需要相应更新解析器。

### 跨运行保留数据

每次工作流从 Actions cache 恢复上次快照，再读取自己已经发布的 Pages `data.json`，选择检测时间较新的快照作为恢复基线。本次抓取失败的来源从基线保留数据。生成后的 JSON 被缓存并随网页部署，**不需要 `contents: write`，不会每半小时向代码仓库提交一次**。

Actions 缓存不是永久存储；缓存被回收时仍可从上一版 Pages 恢复。首次部署前，或缓存被清除且已发布站点也无法访问时，只能使用随项目附带的初始快照；如果该文件也不存在，就显示空状态。初始 `site/data.json` 是项目交付时的一次真实检测，正式运行后会自动替换。

### PWA 缓存

Service worker 仅缓存页面外壳，使用网络优先策略，`data.json` 不进入 service worker 缓存。前端自己保存带检测时间的最后有效快照，网络失败时明确标注“本机缓存”。后台检测超过90分钟时提示检查 Actions；来源失败保留的内容始终标注旧数据。所有资源使用相对路径，适用于 `/仓库名/` 子路径。

## 本地运行与测试

需要 Python 3.10+；没有第三方 Python 依赖，`requirements.txt` 仅作说明。

```bash
# 运行离线单元测试（不会请求真实站点）
python3 -m unittest discover -s tests -v

# 实际抓取两个来源，生成 site/data.json
python3 scripts/fetch_nodes.py

# 开启完整本地预览
python3 -m http.server 8000 --directory site
```

打开 `http://localhost:8000/`。也可以直接双击 `site/index.html`：页面会读取项目内随最后一次抓取生成的 `data.js`，因此来源卡片可以正常显示。直接双击属于静态预览，刷新按钮只会重新读取这份项目内数据；要读取最新后台结果、使用剪贴板和离线安装，请使用本地 HTTP 服务或已部署的 HTTPS 页面。Windows 如无 `python3` 命令，可换成 `py -3`。

可指定输出和恢复地址：

```bash
python3 scripts/fetch_nodes.py --output site/data.json \
  --previous-url https://YOUR_USERNAME.github.io/node-update-helper/data.json
```

可用 Node.js 额外检查前端语法（运行项目本身不需要 Node.js）：

```bash
node --check site/app.js
node --check site/sw.js
```

测试覆盖结构解析、CRLF/标题变化、动态地址和协议、非法和缺失链接、缺失参数表、编辑时间作用域、作者时间解析、语义比较、单站失败、元数据失败、两站失败、跨运行数据恢复以及最新来源选择。交付验证见 [TESTING.md](TESTING.md)。

## 文件结构

```text
.github/workflows/update-and-deploy.yml  定时检测、测试、恢复、发布
scripts/fetch_nodes.py                   抓取、解析、比较与容错
tests/test_fetch_nodes.py                无网络依赖的测试
site/index.html                         手机优先界面
site/styles.css                         固定750px视觉样式
site/app.js                             渲染、复制与本机缓存
site/data.json                          检测结果（自动生成）
site/data.js                            直接双击 HTML 时使用的同步预览数据
site/manifest.webmanifest                PWA 安装配置
site/sw.js                              离线页面缓存
site/icons/                             SVG 与 PNG 图标
requirements.txt                        无第三方依赖说明
README.md
TESTING.md
```

`data.json` 顶层包括 `schema_version`、`checked_at`、`interval_minutes`、`sources`、`comparison` 和 `latest`。每个来源的 `status` 为 `ok`、`partial` 或 `error`；`stale` 表示节点来自此前快照；`warnings` 和 `error` 保存失败原因。最新选中来源在 `latest.source_id` 中，两站逐节点比较在 `comparison.nodes` 中。

## 免费运行的边界与常见问题

- **使用公开仓库和标准 `ubuntu-latest` runner。** GitHub Free 支持公开仓库 Pages；公开仓库的标准 GitHub 托管 Actions runner 免费。参见 [Pages 官方说明](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) 和 [Actions 计费说明](https://docs.github.com/en/actions/concepts/billing-and-usage)。不包含自定义域名的购买费用，也不要求购买域名。
- **半小时是计划频率，非准点保证。** GitHub 高负载时定时任务可能延迟或被丢弃；公开仓库连续60天没有活动时，定时任务会自动停用。需要到 Actions 页面重新启用，或按 GitHub 提示更新定时配置。项目不制造自动提交来规避此限制。参见 [GitHub schedule 说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)。
- **Pages 报404 / `configure-pages` 失败：** 先按部署步骤选择 Pages 的 GitHub Actions 发布方式，再重新运行；确认 `.github/workflows` 已上传，并查看仓库是否禁用了 Actions 或 Pages。
- **部署权限失败：** 检查仓库/组织策略是否允许 Actions 部署 Pages，以及 `github-pages` 环境是否允许默认分支。工作流已声明 `pages: write`、`id-token: write`，无需个人访问令牌。
- **网页刷新后内容不变：** 查看“后台最后检测”和各站编辑时间。刷新网页只读结果；来源本来未更新、定时任务延迟或已停用时，内容自然不变。
- **本机抓取失败而 Actions 正常：** 本机网络可能无法访问来源；GitHub runner 和手机访问 Pages 的网络环境相互独立。本工具不保证 GitHub Pages 或原站在任何地区都可访问。
- **一键复制不可用：** 使用 HTTPS / localhost；浏览器拒绝剪贴板权限时会显示手动复制窗口。顶部两个复制按钮每次分别复制节点1或节点2。
- **两站均失败但 workflow 仍是绿色：** 这是为了继续发布失败状态及旧数据。Actions 运行摘要会显示每站状态，全失败时另有 warning；绿色只代表部署流程完成，不代表来源成功。

本项目只展示原作者公开发布的节点参数及链接，不提供节点服务器。页面不加载原站广告或脚本，来源文本按纯文本显示。源数据与原作者内容的权利归各自权利人；代码授权不覆盖第三方内容。

接口参考：[GitLab Wiki API](https://docs.gitlab.com/api/wikis/)。
