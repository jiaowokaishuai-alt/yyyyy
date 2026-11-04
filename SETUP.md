---
title: 闲鱼比价监控 · GitHub Actions 部署说明
summary: 在公共 GitHub 仓库跑闲鱼价格监控（每 30 分钟单轮抓取，命中推通知）的最短步骤：上传包内文件、设置 XIANYU_STATE_B64 与 OPENAI_API_KEY 等 Secrets、手动跑一次并看日志确认登录态有效。模型用 DeepSeek deepseek-flash（官方页面核实：对应 DeepSeek-V4.1-Flash，具备原生多模态图片理解）；公共仓库连续 60 天无活动会停用定时任务，cron 在高峰时段可能延迟或跳过。全程 0 成本，只有模型 API 按量计费。
---

闲鱼比价监控 · GitHub Actions 部署说明

这套包的作用：让 GitHub 的免费服务器每 30 分钟替你跑一轮闲鱼搜索，命中符合条件（蓝宝石 NITRO+ 氮动 RX 9070 XT 16G，标价 ≤ 6900）的商品就推通知给你。跑完即退出，不需要 7×24 常驻机器，也不需要付费服务器。

包里有什么

.github/workflows/goofish-monitor.yml 定时工作流（每 30 分钟 + 手动触发）
.github/workflows/keepalive.yml 保活（每月自动提交一次，防止定时任务被停用）
config.json 任务配置模板（两组搜索词 + 价格上限 6900）
prompts/nitro_9070xt_criteria.txt AI 判定标准（拒掉脉动/极地/合金脉动/超白金/超白金极光等非氮动 SKU）
run-once.sh 单轮抓取入口（跑完即退出，带登录态缺失检查）
tools/write_env.py 生成 .env（密钥来自 Secrets，不回显）
tools/decode_state.py 把 base64 登录态还原成 state/acc_1.json
tools/run_summary.py 把本轮结果写进 GitHub 运行摘要
requirements-runtime.txt 依赖清单（上游项目原版）
.env.template 本地手跑时的参考模板

工作流会在运行时自动克隆上游项目 Usagi-org/ai-goofish-monitor，你不需要把整个项目拷进仓库。

第一步：建仓库、传文件

1. 登录 GitHub，右上角 + → New repository。
2. Visibility 选 Public（必须是公共仓库，公共仓库的 Actions 免费且不限量；私有仓库只有每月约 2000 分钟，按每 30 分钟一轮根本不够）。
3. 仓库名随便填，例如 goofish-monitor，勾选 Add a README file，然后 Create。
4. 进入仓库，点 Add file → Upload files，把本包解压后的所有文件和文件夹整体拖进去（.github 文件夹要一起拖，它是定时任务的关键）。
5. 提交后确认仓库首页能看到 .github、config.json、run-once.sh 等文件。

第二步：填 Secrets

1. 仓库页 → Settings → Secrets and variables → Actions → New repository secret。
2. 加 XIANYU_STATE_B64：值是闲鱼登录态的 base64（见第三步）。
3. 加 OPENAI_API_KEY：填你的 DeepSeek key（值只存在 Secrets 里，不回显、不打印）。
4. 想要命中时收到推送，再加下面任意一个（见第七步该填哪个）：
   WX_BOT_URL 企业微信机器人地址
   BARK_URL iOS Bark 地址
   PUSHPLUS_TOKEN PushPlus 的 token
   WEBHOOK_URL 自建 webhook 地址
5. 一个都不加也能跑，只是命中后不会推送，只能去 Actions 运行摘要里看结果。

第三步：把闲鱼登录态转成 base64（在你的 Windows 电脑上做）

1. 用 Chrome 登录 goofish.com，用 Cookie-Editor 之类的扩展导出闲鱼域名的登录态 JSON，存成 state.json。
2. 打开 PowerShell，执行下面这一行，base64 会直接进剪贴板：
   [Convert]::ToBase64String([IO.File]::ReadAllBytes("$env:USERPROFILE\Downloads\state.json")) | Set-Clipboard
   路径按你实际保存位置改。
3. 打开 XIANYU_STATE_B64 的值框，Ctrl+V 粘贴，保存。
4. 不想转 base64 也行：直接把导出的 JSON 原文粘进去，脚本同样认得（会自动区分）。
5. 登录态会过期（一般几天到几周），过期后重做这一步、更新同一个 Secret 即可。

第四步：手动跑一次

1. 仓库页 → Actions → 左侧选 goofish-monitor。
2. 右侧 Run workflow → 保持默认（debug_limit 填 3 可以先小规模试，task_name 留空）→ Run workflow。
3. 等 3～10 分钟，点进这次运行看日志。

第五步：怎么确认登录态有效

1. 看运行摘要（这次运行页最下面的 Summary）：出现「本轮新入库：N 条」说明搜索成功。
2. 摘要里出现「登录态提示：日志里出现登录失效或风控相关字样」就是登录态失效或被风控拦截，重新导出登录态并更新 Secret。工作流也会给出一条黄色警告。
3. 日志里出现「缺少闲鱼登录态文件」说明 Secret 没填或值不对。
4. 日志里出现「未找到可用的登录状态文件」是项目自身的报错，含义同上。
5. 判定为符合条件的商品会出现在摘要的「命中商品」表格里（标题、标价、链接）。

第六步：之后的自动运行

1. 设置好后不用管：每 30 分钟一轮，每轮只分析新出现的商品（结果库会记住已处理过的链接）。
2. 每轮命中 1～3 条是正常节奏；同一条链接不会重复推送。
3. 结果库靠 GitHub 缓存跨轮次保留，缓存约一周不用会被自动清理，清掉后只是会重新分析一遍当前在售的商品。

第七步：通知渠道填哪个最省事

1. 最省事：WX_BOT_URL（企业微信群机器人）。在企业微信群里点群机器人 → 添加 → 复制 webhook 地址，粘进 Secret 就能收到微信消息推送。
2. 有 iPhone 可以用 BARK_URL，装上 Bark App 复制那条 https://api.day.app/你的key 就行。
3. PUSHPLUS_TOKEN 也行，但要先去 pushplus.plus 注册拿 token。
4. WEBHOOK_URL 留给爱折腾的：要自己有个能收 POST 的地址，还需要配 WEBHOOK_METHOD / WEBHOOK_BODY 等。

第八步：两个必须知道的时间坑

1. 公共仓库连续 60 天没有任何提交活动，GitHub 会自动停用定时工作流。包里的 keepalive.yml 每月 1 日自动提交一次空变更，正好把这条规则挡住；如果你把它删了，就要自己偶尔改一下文件提交一次。
2. GitHub 的 cron 在整点等高峰时段会排队，可能延迟十几分钟甚至直接跳过某一轮。少跑一轮不影响结果，下一轮会把新商品补上。

费用

1. 公共仓库的 Actions 用标准 runner（4 核 16G）免费且不限量，不用绑卡。
2. 唯一花钱的是模型 API：每轮对少量新商品调用 deepseek-flash，按 token 计费，量很小；不开源节流也不要紧，但 API 余额用完会静默跳过 AI 分析（摘要里就不会有命中）。

关于模型的核实结论

1. DeepSeek 官方 API 文档写明：base_url 用 https://api.deepseek.com，模型名用 deepseek-flash（现已升级为 DeepSeek-V4.1-Flash-1017，调用方式不变）。
2. 官方发布说明写明 DeepSeek-V4.1-Flash 具备原生多模态视觉理解，所以包里默认让 AI 连图片一起分析（config.json 里 analyze_images 为 true）。
3. 如果实测出现图片相关的 400 报错，把 config.json 里两个任务的 analyze_images 都改成 false，就会走纯文本判定（判定标准文件不用改）。

本地想手动跑一次（可选）

1. cd 到上游项目目录，把本包的 config.json、prompts、run-once.sh 放到项目根目录。
2. python -m pip install -r requirements-runtime.txt
3. python -m playwright install chromium
4. 复制 .env.template 成 .env，填好 OPENAI_API_KEY 和通知渠道。
5. 把登录态 JSON 放到 state/acc_1.json。
6. 项目根目录执行：STATE_FILE=state/acc_1.json bash run-once.sh --app .
