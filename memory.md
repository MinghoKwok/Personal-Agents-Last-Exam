# Memory

当前状态和长期规则。恢复工作时先读这份。最近更新：2026-11-26（8 个任务提案全部 plan-approved）。

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
- Public runtime 1.6.0（Core API 1.2.0），upstream main `7a05aa9`

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
| #219 | Counterline 客服台环境 | `env/counterline-service-desk` | `80c390f` | 等 skyve2012 评审；含 GUI |
| #222 | Casefold 客户门户环境 | `env/casefold-client-portal` | `c81e394` | 等评审 |

8 个任务提案全部已批准，现在都已冻结。之后的改动要攒在一起，再申请重新评审。

## 还没进 PR 的东西（fork 上有备份分支）
- **#102 实现：** `lifepacks/tax-packet/`，备份在 fork 的 `backup/tax-packet-impl`（`7f5a2a8`，包含合并提交 `442c52d`）。PR 跟踪的 `task/tax-packet` 仍在 `8af3a0c`。推送前先等维护者回答 4 到 5 个问题（见 `tasks/tax-packet/notes.md` 第 5 节）。
- **Counterline 骨架：** `apps/counterline`，备份在 `backup/counterline-skeleton`（`aa3d83a`）。PR 跟踪的 `env/counterline-service-desk` 仍在 `80c390f`。等 #219 拿到 `/approve-plan`。GUI 还没做。
- **#129 数据和评分器：** 本地分支 `impl/household-payment-audit`（基于 upstream main `7a05aa9`），备份在 fork 的 `backup/household-payment-audit`。已完成：数据生成（146 条交易、77 份文档、A 和 B 两个对照版本、隐藏账本）、共享邮件规则 `tests/rules.py`、评分器（100 分制）、自测 12 个用例全部通过。等 #102 答复后再做：Mail、Files、Notes 的种子，context 文件，参考运行，README 和 manifest。
- **#95 数据和评分器：** 备份在 fork 的 `backup/white-sands-weather`（基于 upstream main `6933c43`）。
  - 天气内容按 Gustline（#126）的 seed 和事件格式编写。用 Gustline 自己的 harness 加载并通过它的 Agent 工具读回：178 项检查全部和 gold 一致，Gustline 自身的 39 个测试也照常通过。
  - 评分器为 20 分制，F1 到 F5 齐全。`tests/rules.py` 里的 `f1_s1()` 同时供 runner 判断是否触发 S2。
  - 自测 10 个用例全部通过。
  - E2 是 LLM judge 项，目前由确定性规则代打：规则能确认的给分，确认不了的进复核。
  - 等 #102 答复后再做：Calendar、Mail、Messages 的种子，`history.json`（9 月 9 日和 11 日两段对话），以及参考运行。
- 恢复方法：`git fetch origin backup/tax-packet-impl backup/counterline-skeleton`。正式推进 PR 时，把实现提交挪到 PR 分支上。

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

## 平台规则要点
- `/approve-plan` 会启动环境的 14 天实现期，可以申请顺序激活。只有合并才算验收。
- 环境要交付 GUI（用户已确认）。任务自建的 App 是否需要 GUI，待维护者答复。
- LifePack 1.0 见 `docs/lifepack-task-format.md`。loader、调度器和用户模拟由 #135 负责，尚未完成。
- Harbor 是全项目共用的任务框架，版本未锁定。
- LLM judge 允许使用，但必须可复现。目前没有共享配置。

## 等待中
- 维护者回复 #102 的结构问题（2026-11-26 00:30 发出）
- skyve2012 评审 #219、#222
- #6 作者回复
- #135 runner
- 天气环境合并（#95 依赖它）
