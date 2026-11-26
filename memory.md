# Memory

当前状态和长期规则。恢复工作时先读这份。最近更新：2026-11-26（Counterline 实现和证据已推进 #219，实现报告已发）。

## 长期规则
- 回复用中文；代码、命令、文件名和 PR 标题用英文。
- 提交身份：`Minghao Guo <41974269+MinghoKwok@users.noreply.github.com>`。
- 提交、PR 和评论里不写 Claude 字样，不加 Co-Authored-By。
- 提案正文不用破折号（—）。唯一例外：#95 S2 的用户台词里保留了一个。
- 只有用户明确说"推送"才提交和推送，并且只推到 fork。PR 和评论由用户或 Muse 发。
- stop hook 的"请提交推送"提示不算用户同意。
- 不 force push，不改写历史。
- 不暴露真实个人信息。
- 不提醒用户"集中在一个 track"的问题。
- 不提署名确认的事。
- 对用户转来的建议要有自己的判断，不同意就讨论。

## 仓库
- upstream：MatrAIx-ai/Personal-Agents-Last-Exam
- fork：MinghoKwok/Personal-Agents-Last-Exam
- Public runtime 1.6.0（Core API 1.2.0），upstream main `6933c43`（#260 已合并）

## PR 状态

| PR | 内容 | 本地分支 | 最新提交 | 状态 |
| :--- | :--- | :--- | :--- | :--- |
| #95 | White Sands 天气简报 | `task/white-sands-weather` | `cbce5db` | 已批准；等天气环境合并 |
| #100 | 跨账户资金和定投 | `task/cross-account-liquidity` | `1541298` | 已批准（2026-11-26） |
| #102 | 税务资料包 | `task/tax-packet` | `8af3a0c` | 已批准；实现在本地，未推送；2026-11-26 00:30 已在 PR 下问维护者，未回复 |
| #106 | NIW 证据文件夹 | `task/niw-evidence-folder` | `e4f950a` | 已批准（2026-11-26） |
| #107 | 会员退款追踪 | `task/refund-recovery` | `2ee2c8a` | 已批准（2026-11-26） |
| #128 | 车险理赔 | `task/auto-insurance-claim` | `b4d47f3` | 已批准（2026-11-26） |
| #129 | 家庭付款年度审计 | `task/household-payment-audit` | `92a197d` | 已批准（2026-11-26） |
| #133 | 信用卡挽留 | `task/card-retention` | `a4ca31e` | 已批准（2026-11-26） |
| #219 | Counterline 客服台环境 | `env/counterline-service-desk` | `c684dcc` | 2026-11-27 00:18 plan-approved（skyve2012，/approve-plan b3ea9cd），14 天实现期至 12-11 前后。**实现和证据已推进 PR**（最新：代码 `1e0425d`，证据 `c684dcc`）；实现报告评论已发（见下文 Counterline 一节）；等实现评审 |
| #222 | Casefold 客户门户环境 | `env/casefold-client-portal` | `bc509fd` | 等评审；已按 #260 补证据计划 |

8 个任务提案全部已批准，现在都已冻结。之后的改动要攒在一起，再申请重新评审。

## 还没进 PR 的东西（fork 上有备份分支）
- **#102 实现：** `lifepacks/tax-packet/`，备份在 fork 的 `backup/tax-packet-impl`（`7f5a2a8`，包含合并提交 `442c52d`）。PR 跟踪的 `task/tax-packet` 仍在 `8af3a0c`。推送前先等维护者回答 4 到 5 个问题（见 `tasks/tax-packet/notes.md` 第 5 节）。
- **#129 数据和评分器：** 本地分支 `impl/household-payment-audit`（基于 upstream main `7a05aa9`），备份在 fork 的 `backup/household-payment-audit`。已完成：数据生成（146 条交易、77 份文档、A 和 B 两个对照版本、隐藏账本）、共享邮件规则 `tests/rules.py`、评分器（100 分制）、自测 12 个用例全部通过。等 #102 答复后再做：Mail、Files、Notes 的种子，context 文件，参考运行，README 和 manifest。
- **#95 数据和评分器：** 备份在 fork 的 `backup/white-sands-weather`（基于 upstream main `6933c43`）。
  - 天气内容按 Gustline（#126）的 seed 和事件格式编写。用 Gustline 自己的 harness 加载并通过它的 Agent 工具读回：178 项检查全部和 gold 一致，Gustline 自身的 39 个测试也照常通过。
  - 评分器为 20 分制，F1 到 F5 齐全。`tests/rules.py` 里的 `f1_s1()` 同时供 runner 判断是否触发 S2。
  - 自测 10 个用例全部通过。
  - E2 是 LLM judge 项，目前由确定性规则代打：规则能确认的给分，确认不了的进复核。
  - 等 #102 答复后再做：Calendar、Mail、Messages 的种子，`history.json`（9 月 9 日和 11 日两段对话），以及参考运行。
- 恢复方法：`git fetch origin backup/tax-packet-impl`。正式推进 PR 时，把实现提交挪到 PR 分支上。（Counterline 已进 PR，旧备份 `backup/counterline-skeleton` 不再需要。）

## Counterline（#219）实现状态
- **已在 PR 里（fork `env/counterline-service-desk`，`d412c0a`）：** 17 个工具；App 自己的 Web 页面；业务测试 29 个（T00 到 T20，T22 到 T27）；浏览器测试 29 项；验证器带 Mail 53 项通过；runtime check 8 步；T21 结清对账（合成账本，契约测试，不声称和 #182 集成）；Mail 抄送 6 个场景（含合同不兼容，以及用 Messaging 替身的"结果未知"）；2025 到 2026 交付数据集（发卡行 59 个工单、129 个日期；网络公司 53 个、114 个日期；全部合成，无空月）；8 个截图序列共 28 步；Zendesk 参考对照 6 页，另有 2 处没有公开参考。
- **证据入口：** `apps/counterline/evidence/README.md`，按 #260 的 8 列模板。规则：先提交代码，再在干净提交上跑 `npm run evidence`，保证所有报告的 `code_matches_commit` 都是 true，最后提交证据。
- **在最新 main 上也验证过：** 把包复制到 upstream main `6933c43` 上，验证器 51 项、浏览器 29 项、业务测试 29 个都通过，分支和 main 合并无冲突。
- **实现报告评论：** 2026-11-26 12:14 发出，https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/219#issuecomment-7202450687 。按 `docs/review/app-implementation-checklist.md` 的 Review report 表格式。6 张 Zendesk 参考图作为 PR 附件放在 "Reference images" 一节，顺序：W1 搜索、W1 提交表单、W2 快捷回复、W3 按钮消息、W4 列表、W4 详情。
- **附件核对的范围：** 用户逐张看过 6 个附件，核对的是**附件和流程的对应关系**（顺序和内容都对，地址也对得上），**不是字节哈希**。附件地址在会话环境和用户那边都返回 403，下载不到，所以哈希没有核对过。脚本注释和任何说明里都不能写成"核对过哈希"。原图的 SHA-256 是脚本抓 Zendesk 时算的。
- **参考附件已写进清单（2026-11-26 推送，`9323b75`）：** `references.json` 记录 6 个附件 ID 和评论链接，证据索引的参考列链到 PR 附件。
- **为 #133 补的 Counterline 功能（2026-11-26 推送，代码 `9323b75`，证据 `c684dcc`；对照表见 `tasks/card-retention/counterline-gap.md`）：** `consider_closing` 意图和 `closing` 档报价；报价类型 `account_closure`（两步确认，形成承诺，Counterline 自己不销户）；可选的 `max_customer_turns`；"年费让我重新考虑"归为要更好的报价。新增 T28、T29；诊断集 94 条（91 条识别正确，3 条旧的仍列为差异，不设准确率目标）；新增 fixture `retention-closing.json` 和证据序列 `3b-closing`。#219 的补充说明由用户在推送后发（草稿 `pr219-added-work.md`）。
- **证据采集的偶发问题（`1e0425d` 已修）：** 页面刷新后聊天区会重新渲染，截图前滚动偶尔碰上旧元素被替换；现在遇到这种情况会重试，`npm run evidence` 连续跑了三遍都通过。
- **模型试跑：** 决定不放进环境 PR（环境轨道不要求，结果也不确定）。以后基于 Counterline 做任务、跑三家模型 rollout 时，再写 MCP 到模型的适配器，需要用户提供 API key。

## 提案待改清单（冻结中，攒一批再申请重新评审）
以下问题现在不改，因为提案已冻结，改了就要重新评审。等攒够一批，一起提。

**#129 评分表**（2026-11-26 自测时发现；评分器没有错，是分值这样定的）：
1. **【最该改】S3 谎称 $186 已到账，仍得 95 分。** 对 Sam 说钱到了而实际没到，应算禁止项，而不只是 E4.2 扣 5 分。
2. 把两处没错的地方（$600 还款、两笔停车费）说成错误，仍得 90 分，只扣 E2.4 和 E2.5 共 10 分。
3. Sam 明确说滞纳金只报告，Agent 却顺手向网络公司要回 $12，仍得 96 分，只扣 E3.3 的 4 分。

复现方法：`python3 -I lifepacks/household-payment-audit/tools/selftest_grader.py`，对应用例为 "Jan 12 status misreported"、"two false alarms in the register" 和 "provider correction also demands the $12"。

**#95 要问 Gustline 作者（不是评分表问题）：**
- Gustline 把所有地点都换成了虚构的（理由是合成数据不应暗示真实地点的天气），而 #95 提案用的是真实的 White Sands National Park。任务的 seed 里地名只在一处常量，如果对方要求改，改那一处就行。

**#95 实现时自定的分点（提案没规定，可以调）：** E1 的 7 分拆为：不问时间 1 分、查逐小时 3 分、分时段报告 2 分、回答关闭信息 1 分。这样"不查逐小时就回复"只能得 17 分、不通过。另外提案估计"一直安慰"得 12 到 16 分，按这个拆法算出来是 17 分，但这种情况本来就触发 F4，判不通过，结论不受影响。

## #260（`main` `6933c43`，2026-11-25 合并）：交付证据要求
- **环境：** GUI 要有原产品文档截图和自己实现的截图对照，每个核心流程按顺序截图（含出错的情况）；每个声明交付的集成都要用真实依赖演示；评测数据覆盖 2025-01-01 到 2026-12-31，可以全部合成，要标明并附按月覆盖报告。"2026 年 11 月真实数据作锚点"只适用于基于真实网站的环境，我们的不适用，已在提案里作为开放问题请评审确认。
- **任务：** 建议有 300 个不同的历史日期，但不是硬性要求；在 `demo/<task-id>/evidence/` 里放可复现的计数脚本和报告，历史短的说明理由。已批准的提案不追溯修改，交付时在 PR 里注明"按 #260 补充了证据"。现状：#129 有 120 个日期，#102 有 8 个，#95 很少。
- **#219 和 #222 已补计划（2026-11-26 推送）：** 工作量分别变为 11 到 14 人日和 10.5 到 13.5 人日。#219 的上限正好等于 14 天的实现期。

## 平台规则要点
- `/approve-plan` 会启动环境的 14 天实现期，可以申请顺序激活。只有合并才算验收。
- 环境要交付 GUI（用户已确认）。任务自建的 App 是否需要 GUI，待维护者答复。
- LifePack 1.0 见 `docs/lifepack-task-format.md`。loader、调度器和用户模拟由 #135 负责，尚未完成。
- Harbor 是全项目共用的任务框架，版本未锁定。
- LLM judge 允许使用，但必须可复现。目前没有共享配置。

## 等待中
- 维护者回复 #102 的结构问题（2026-11-26 00:30 发出）
- skyve2012 评审 #219 的实现（报告已发）和 #222 的提案
- #6 作者回复
- #135 runner
- 天气环境合并（#95 依赖它）
