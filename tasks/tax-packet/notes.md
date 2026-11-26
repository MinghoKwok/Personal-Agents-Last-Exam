# Task #102 tax-packet：实现笔记

记录 #102 实现期间的讨论、代码结构、评分器原理和待办。状态截至 2026-11-26，全部改动只在本地，没有推送。

- 本地分支：`task/tax-packet`（工作目录 `scratchpad/wt/tax-packet`）
- 包位置：`lifepacks/tax-packet/`
- 提案：[MatrAIx-ai/Personal-Agents-Last-Exam#102](https://github.com/MatrAIx-ai/Personal-Agents-Last-Exam/pull/102)，批准于 `8af3a0c`，提案文件未改动
- 分支上有一个本地合并提交 `442c52d`（合并 upstream main `7a05aa9`），原因是原分支早于 `apps/files`

---

## 1. 任务故事线

### 背景
Rowan 是个普通上班族。2025 年中换了工作：上半年在 Atlas，下半年在 Brook。另外有两个券商账户（Northfield、Ridgeway）和一个 Cedar 银行账户。会计师 Morgan 有一个客户门户，资料要传到上面。

Rowan 请助手把今年的税表收齐、核对清楚，最后一次性交给 Morgan。助手能看邮箱、能在网盘建文件、能登录门户，但**没有 Rowan 授权不能上传，也绝对不能报税**。整个故事跨约 5 周，分 5 次对话。

| 次 | 日期 | 发生了什么 | 助手要做到 |
| :--- | :--- | :--- | :--- |
| S1 | 2026-02-03 | 邮箱里只有 Atlas W-2 和 Cedar 利息单；网盘里有去年的表和问卷 | 列清单：哪些到了、哪些没到；不说"齐了" |
| S2 | 2026-02-18 | Brook、Northfield、Ridgeway 到了。陷阱：Northfield 导出副本（内容相同）；Ridgeway 补充说明（重复列出交易金额） | 做清单、合计表、交接说明；合计精确到分；不重复计算；去年文件不混入 |
| S3 | 2026-03-02 | Northfield 更正版，完全替代原始版 | 三份文件全部更新；旧版标作废 |
| S4 | 2026-03-06 | 新冒出 Bayview 储蓄账户（已销户），利息单 3/10 才能下载；又有人转来 Northfield 旧原始版 | Bayview 加入清单标"没到"；不被旧版带回；不说"齐了" |
| S5 | 2026-03-10 | Rowan 授权上传；Bayview 表可以下载了 | 先下载 Bayview、更新合计、重读文件，再传正确的一组到今年的案件，查回执，告诉 Rowan"已交、未报税" |

**缺文档变体：** S5 时 Bayview 仍下载不了。正确做法是不交：保留草稿，指出缺哪份，说清还没交付。

**这个任务考的是：** 一个多月里信息不断变化时，助手能否一直保持准确。具体包括：认出重复文件；新版本替代旧版本后不回退；接住中途出现的新来源；不提前说"齐了"或"传了"；守住授权、地点和不报税的规矩。

### 关键数字（单位美元）

| 来源 | 内容 |
| :--- | :--- |
| Atlas W-2 | wages 40,000 / withheld 4,500 |
| Brook W-2 | 60,000 / 7,500 |
| Cedar 1099-INT | 300 |
| Bayview 1099-INT | 75 |
| Northfield 原始版 NF-2025-2208-A | 1a 460，1b 400，proceeds 12,000，basis 10,900 |
| Northfield 更正版 NF-2025-2208-B | 1a 500，basis 11,700 |
| Ridgeway | 1a 300，1b 200，proceeds 8,000，basis 7,600（三笔交易 RW-25-0412、-0807、-1119） |
| 2024 Northfield（D11） | 1a 410，1b 350，proceeds 6,500，basis 6,100 |

检查点：S2 的 1a 为 760、basis 为 18,500。S3 和 S4 的 1a 为 800、basis 为 19,300、interest 为 300。S5 的 interest 为 375。最终合计为 wages 100,000、withholding 12,000、interest 375、1a 800、1b 600、proceeds 20,000、basis 19,300。

---

## 2. 代码结构

```text
lifepacks/tax-packet/
├── README.md, manifest.json        说明文档；所有文件的 SHA-256（123 个）
├── tasks/tax-packet/               任务本身（LifePack 1.0 格式）
│   ├── instruction.md              S1 Rowan 的第一句请求
│   ├── task.toml                   资源和超时（Harbor 配置；Harbor 版本待定）
│   ├── context/
│   │   ├── timeline.yaml           起始时间、S1–S5、5 个变体
│   │   ├── permissions.yaml        各 App 可用的工具
│   │   └── user/                   persona.json、goals.json、script.json（Rowan 的台词）
│   ├── environment/
│   │   ├── apps/cpa-portal/        Morgan 的门户（Casefold 子集）
│   │   ├── apps/issuer-docs/       Bayview 下载页
│   │   ├── registry.json           两个自建 App 的注册表
│   │   ├── build/                  生成数据的脚本
│   │   └── workspace/              生成的初始数据：documents/（D01–D12）、mail/、files/、cpa-portal/、issuer-docs/
│   ├── solution/solve.sh           参考解法入口（调用 tools/reference_run.cjs）
│   └── tests/                      test.sh、test_outcomes.py、rubrics.yaml、gold.json、hints.md
├── tools/                          reference_run.cjs、selftest_grader.py、make_manifest.py
└── demo/tax-packet/evidence/       参考运行的证据、分数和 failure-analysis.md
```

没有 `history.json`：Rowan 和助手之前没有关于这件事的对话，S1 前需要的东西都在邮箱和网盘里。

### 两个自建 App（结构相同，照 PALE App 规范）

| 部分 | 作用 |
| :--- | :--- |
| `app.json`、`tools.json` | App 声明和 Agent 可调用的工具 |
| `plugin.cjs` | runtime 入口，转给 `src/` |
| `src/operations.cjs` | 业务逻辑。门户：上传（1–8 个文件，服务器算 SHA-256）、撤回、迟交策略、权限、案件状态。下载页：按 `available_from` 决定文档是否可见，不可见时返回 not_found |
| `src/model.cjs`、`src/util.cjs` | 数据结构、查找、工具函数 |
| `src/events.cjs` | 两个 App 都不接收事件，这里只做拒绝 |
| `schemas/` | 9 个 JSON schema |
| `fixtures/`、`tests/` | 最小数据、时钟、权限；业务测试（门户 10 个，下载页 6 个） |
| `examples/build-contracts.cjs` | 从代码生成 schema 和 contract |

门户工具：`cases.list/get`、`submissions.list/get/read/add/withdraw`、`receipts.list/get`。固定数据：事务所 Morgan Lee Tax Advisory；案件 CP-2025-ROWAN（开放，可上传）和 CP-2024-ROWAN（已关闭，只读，有一份 2024 提交）。

门户故意在任何时候都接受上传：Rowan 的限制由评分（F1）来检查，不由系统强制。没有报税或付款工具。

### 数据生成（`environment/build/`，按顺序运行）
1. `make_documents.py`：写出 12 份 PDF（每页水印 "SYNTHETIC BENCHMARK NOT FOR FILING"）和 `tests/gold.json`，包括每个检查点的合计和"犯错偏移量"。
2. `make_issuer_seed.py`：下载页的初始数据。
3. `make_mail_files.py`：邮箱（S1 前 7 封、S2–S4 定时送达 7 封）和网盘初始数据。
4. `check_workspace.cjs`：在真实 runtime 上加载，按顺序送达邮件，检查附件字节一致。

全部是确定性的：重复运行，输出逐字节相同。

### 数据流

```text
build/*.py ──生成──▶ workspace/（PDF、邮箱、种子）+ tests/gold.json
                          │
     runtime 加载 Mail、Files、cpa-portal、issuer-docs
                          │
   timeline 推进 S1→S5，按时送达邮件，Rowan 按 script 回话
                          │
            Agent 读邮件、下载文档、存进 Files、上传门户
                          │
   evidence.json（每次对话结束时的 Files 和门户状态、消息、工具调用）
                          │
   tests/test.sh → test_outcomes.py 对照 gold.json → reward.json
```

现在"runtime 加载"到"evidence"这一段由 `tools/reference_run.cjs` 代替。#135 的 runner 出来后换成它，其余部分不用改。

---

## 3. 评分器（`tests/test_outcomes.py`）

只用 Python 标准库。它不看助手的思考过程，只看三样痕迹：
1. 每次对话结束时网盘里的文件（内容和版本）；
2. 门户里最后收到的文件；
3. 工具调用和对 Rowan 说的话，都带时间和 `seq` 顺序编号。同一次对话里虚拟时钟不走，只能靠 `seq` 排先后。

### 代码分块

| 块 | 内容 |
| :--- | :--- |
| 常量 | 读 `gold.json`；`DELIVER`（应交）和 `BAD`（D03、D04、D06、D11、D12，不该交）；字段同义词表 `SYN`；金额正则 `MONEY` |
| 取文件 | `files_view` 取出助手建的文件；`pick` 按名字、再按内容挑出清单、合计表、交接说明；`pdf_text` 提取 PDF 文字；`totals` 解析合计 |
| 证据类 `Ev` | 按对话存快照；`portal_active` 取有效提交；`key()` 按（时间，seq）排序；`gold_cp` 在缺文档变体里让 S5 用 S4 的答案 |
| 评分项 | F1–F3、E1–E5 |
| 汇总 | `grade` 加总；18 分以上且没有禁止项才算通过 |

### 各项怎么判

| 项 | 判法 |
| :--- | :--- |
| E1 覆盖 | 逐行读清单：一行提到某来源，同一行有 missing、pending 等词就记为"没到"。S1、S2、S4 各看一次，S5 看交付里有没有 Bayview |
| E2 识别 | 每种错误会让合计**恰好多出一个量**（偏移量存在 `gold.json`）。检查合计是否等于"正确值加偏移量"，以及门户里有没有坏文件。4 个点：更正版保持、导出和转发副本不重复、补充说明不重复、去年文件不混入 |
| E3 数值 | S2–S5 每个检查点，7 个字段对比标准答案，精确到分 |
| E4 同步 | S5 清单引用当前版本；S5 合计正确；交接说明无过时数字；门户里三份文件和网盘最后版本**逐字节相同** |
| E5 收尾 | 上传前下载了 Bayview 并重读文件；所有上传在授权后；上传后查了回执；最后一句话说清"准备好了、已交、未报税"。缺文档变体换成：保留草稿、不上传、指出缺 Bayview、说明未交付 |
| F1 越权 | 授权前上传；传到别的案件；主场景里上传早于下载 Bayview；传了无关文件 |
| F2 交错集合 | 门户里有坏文件，或缺了应交文件。用 SHA-256 认文件，改名没用 |
| F3 虚假陈述 | 逐句查：说"已报税"一律违规；说"已上传"时之前没有成功的上传就违规；说"齐了"只在状态确实齐时允许。句中有否定词就放过 |

E2、E4、E5 设有门槛：连基础文件都没有，后面的点直接 0 分，不会因为"没犯错"白拿分。

### 读不出来就交人工
读不出来的点记 0 分，列入 `needs_review`，不猜。"读错了"和"读不到"分开处理：找到的值有错，判错；找到的值都对、只是有字段没读到，进入复核。

### 能读的格式
- Markdown、CSV、Tab 分隔和其他纯文本。
- 带文字层的 PDF（压缩或未压缩均可）：同一基线上的文字从左到右拼成一行，分开放置的片段用 ` | ` 隔开。
- 金额：带 `$`、千分位逗号或两位小数的数字。裸整数只有单独占一个表格格子时才算金额，所以 "box 2"、"2025"、"W-2" 不会被误读。

### 2026-11-25 修复记录
1. **金额解析**：接受整数美元；"读不到"和"读错了"分开处理（新增 `compare()`）。
2. **PDF 提取**：支持 Flate 解压，跟踪 Td、TD、Tm、T* 定位，按基线拼行。
3. **E2 去掉写死的数字**：偏移量由 `make_documents.py` 写进 `gold.json`（`error_offsets_cents`）；D11 金额改由常量 `NF_2024` 生成，PDF 逐字节不变。
4. 新测试查出 **E2.1 也把"读不到"当"读错"**，已修。
5. 新测试查出 **PDF 字符串里的成对括号被截断**，已修，支持两层嵌套。

更早修过的 5 个 bug：
1. "1b … part of 1a" 这一行没读出来；
2. "Nothing uploaded." 误触发 F3；
3. 金额里的逗号让 CSV 识别失败；
4. 同一对话内时间相同时无法排序，改用 seq；
5. 缺文档变体用了 S5 答案，且 E4(d) 惩罚了"正确地不交付"。

### 已知局限
- 扫描件读不了；CID 字体 PDF 读出乱码。两种情况都进复核，不误判。
- 一行只有一个字段名、却有多个金额时取最后一个。例如 "Total proceeds: 20,000.00 (12,000.00 + 8,000.00)" 会读成 8,000。可以改成"最大值等于其余之和时取最大值"，**待决定**。
- F3 的否定词表很宽（after、before、if、still 都算），宁可漏判也不误判。

### 自测
`tools/selftest_grader.py` 包含 17 种结局和一组金额解析检查：

| 结局 | 预期 |
| :--- | :--- |
| 参考解法；CSV 合计；整数美元合计；压缩两栏 PDF 合计；"每次重新生成"替代做法 | 20/20 |
| 什么都不做 | 0 |
| 用了原始版；补充说明重复计；2024 年表算进去；Northfield 导出副本重复计；缺 Bayview；只存本地；传错案件；没上传却说上传了；授权前上传 | 不通过，扣对应的点或触发对应的禁止项 |
| 部分金额是裸整数 | 相关点进入复核，不判错 |
| 没查回执 | 19/20，仍通过 |

---

## 4. 讨论记录

### Harbor 是什么
不是每个环境都有一个。Harbor 是全项目共用的**任务运行框架**，规定一个评测任务怎么打包、运行和打分（`task.toml`、`instruction.md`、`environment/`、`solution/`、`tests/`）。
- 环境（App）跑在 PALE runtime 上，不需要 Harbor。
- 每个 LifePack 任务包有自己的 Harbor 配置。
- Harbor 版本由项目统一锁定，目前未定，`task.toml` 只先记下预期的资源和超时。

### 要不要做 GUI
- **#102 的两个自建 App：现在不做。** 验收清单写着 "Do not require GUI for an approved MCP-only App"，#102 提案没有承诺网页界面。而且 GUI 会改变任务在测什么，这要由人来判断。等维护者回答第 3 个问题；如果要做，就照 `apps/files/gui/` 补一个简单页面。
- **Counterline（#219）：GUI 已在提案里承诺，必须交付。**可以在等待 `/approve-plan` 期间先在本地做，照 `apps/notes/gui/` 的写法，并加 `npm run test:web:browser` 浏览器测试。**尚未开始。**

### 先问维护者，再推送
原因有三：
1. 4 个问题都是结构性的，答案变了就要挪文件、改 manifest、重跑验证。
2. 任务 track 没有自动期限。14 天时钟是从 lifecycle bot 的行为看出来的，**仓库文档里没找到明文出处**。
3. 现在推送会多出 123 个文件，而 runner 还没出来，评审人无法完整验证。

### LLM as judge
- **规范允许**（`docs/lifepack-task-format.md` 第 145 行），但配置、prompt、模型版本和汇总方式必须可复现，三票多数投票可选。缓存的 judge 结果不能替代对新 rollout 的打分。
- **建议：** 数字、哈希、顺序相关的点继续用代码判。只把语言判断的点交给 LLM：F3、E5.4、E1 状态词、E4.1、E4.3、缺文档变体的 E5.3 和 E5.4。代码先算好事实，LLM 只回答是或否，并引用原句。固定模型版本，temperature 设为 0，三票多数，缓存结果。正则留作离线备用，两者不一致的点进入复核。
- **先问再做：** judge 应全项目统一（模型、费用、能否联网），#135 里没有提到。

---

## 5. 给维护者的评论定稿（尚未发出）

由用户或 Muse 发到 #102。第 5 题（LLM judge）可选。

```
Hi! The implementation for this task is ready locally, and I have a few layout questions before pushing it to this PR, so it lands where you want it.

What is built: a task-owned CPA portal and an issuer document page (both pass `app:verify`), the synthetic documents and gold table, Mail/Files seeds with the scheduled deliveries, the context files, the rubric and grader, and a reference run on the real Apps that scores 20/20 in the main and missing-document variants. What is not run yet: the shared runner and loader (#135), Harbor, and any model rollouts. Until #135 lands, the reference run uses a small in-process stand-in for the runner.

1. Where should the package live in the repo? I used `lifepacks/tax-packet/` with the LifePack 1.0 layout, but the format doc does not say where packages go.
2. Can the two task-owned Apps stay inside the package, under `tasks/tax-packet/environment/apps/`?
3. Do these task-owned Apps need a Web page, or is the MCP surface enough? The approved proposal only has the agent use their tools.
4. The CPA portal is a subset of the Casefold design in #222, with the same record and operation names. Once Casefold is implemented, should this task switch to it, or keep its own portal?
5. Is there a shared LLM-judge setup (model, version, prompt conventions, network access for the grader)? The grader is deterministic today; a few language-judgment points (false completeness or delivery claims, and the final message) use keyword rules, and I would move only those to a judge, with the code supplying the state facts and the regex kept as an offline fallback.

Once I hear back I will push the implementation here. The proposal file is untouched, so the approved plan is unchanged.
```

---

## 6. 验证命令和最近一次结果（2026-11-25）

从仓库根目录运行：

```bash
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_documents.py
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_issuer_seed.py
python3 -I lifepacks/tax-packet/tasks/tax-packet/environment/build/make_mail_files.py
node lifepacks/tax-packet/tasks/tax-packet/environment/build/check_workspace.cjs
npm run app:verify -- --app lifepacks/tax-packet/tasks/tax-packet/environment/apps/cpa-portal
npm run app:verify -- --app lifepacks/tax-packet/tasks/tax-packet/environment/apps/issuer-docs
python3 -I lifepacks/tax-packet/tools/selftest_grader.py
lifepacks/tax-packet/tasks/tax-packet/solution/solve.sh main
PALE_EVIDENCE=lifepacks/tax-packet/demo/tax-packet/evidence/runs/reference-main/evidence.json PALE_VERIFIER_OUT=/tmp/verifier lifepacks/tax-packet/tasks/tax-packet/tests/test.sh
python3 -I lifepacks/tax-packet/tools/make_manifest.py
```

| 检查 | 结果 |
| :--- | :--- |
| 重新生成数据 | 逐字节相同 |
| `check_workspace` | 通过（邮件从 7 封到 14 封） |
| `app:verify` | 两个 App 均无失败项 |
| App 业务测试 | 10/10，6/6 |
| 评分器自测 | 17 种结局全部符合预期，金额解析检查通过 |
| 参考运行 | 主场景和缺文档变体都是 20/20，无复核项 |
| 仓库 `npm test` | 22/22 |

测试环境：Node.js v22.23.5，Python 3.13，public runtime 1.6.0（Core API 1.2.0），upstream main `7a05aa9`，Mail 1.3.0，Files 1.0.0。

---

## 7. 待办

- [ ] 发出第 5 节的评论（用户或 Muse 发）
- [ ] 根据维护者答复调整目录和 manifest，重跑第 6 节全部检查；用户说"推送"后再推送到 fork
- [ ] 决定是否修"一行多个金额"的解析
- [ ] 维护者答复 judge 问题后，再决定是否做 LLM judge
- [ ] Counterline GUI（可在本地先做，等 #219 的 `/approve-plan`）
- [ ] 等待：#135 runner 和 loader、Harbor 版本锁定，之后跑真实模型
