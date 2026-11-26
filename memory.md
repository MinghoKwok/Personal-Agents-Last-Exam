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

## 只在本地、没推送的东西
- **#102 实现：** `lifepacks/tax-packet/` 位于 `task/tax-packet` 分支，带本地合并提交 `442c52d`。推送前先等维护者回答 4 到 5 个问题（见 `tasks/tax-packet/notes.md` 第 5 节）。
- **Counterline 骨架：** `apps/counterline`，等 #219 拿到 `/approve-plan`。GUI 还没做。
- 注意：容器回收后，本地内容会丢失。

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
