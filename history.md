# History

决策记录，按时间顺序。只记做了什么决定、为什么，不记完整对话。

## 环境提案
- **Counterline（#219）：** 架构评审后确定三点：人机混合交互；承诺（commitment）作为一等对象；跨 App 的事件接口。之后补了 matcher 指标（ICR），处理了 `version.epoch` 问题，加了冒烟测试和两族 fixture。保留 `retention` 别名。四个依赖它的任务当时就改了依赖说明。用户确认环境需要 GUI，GUI 已写进提案。
- **Casefold（#222）：** 专业客户门户。按 ChatGPT 的意见收紧范围后提交，并补了与任务的对应关系。
- **骨架：** Counterline 骨架已在本地搭好。把它注册进 `apps.registry.json` 会让 `clock.test.cjs` 失败（那个测试要求恰好 7 个 App），所以撤回了注册。

## 任务提案
- **#95：** 根据 Haolun 的评审修了这些：
  - "memory in main"（我自己的错误）；
  - build-up 的定义和"任一数据源"的说法冲突，改成任一数据源中最早达到 45% 的小时；
  - E3 写了"没有固定期限"；
  - 时区规则会误判正确的 CDT 小时；
  - 写明 S3 的标题和 Flood Watch 不变。

  之后获批。
- **自查一轮：**
  - #133 的集成行过时，改为优先依赖 #219 和 #182；
  - 删掉了 #133 和 #129 里错误的反事实句子；
  - 各集成行加了 Notes；
  - #107 的提示注入覆盖到备用 session；
  - 置顶笔记的标题改为中性写法（"Conversation with X (date)"）。
- TianyuCodings 审了 6 个任务，回复已发出（`drafts/replies/replies-tianyu-1125.md`）。#102 获批。

## #102 实现
- **为什么不等 Casefold：** #222 还没批准，任务不能等它。所以门户按 Casefold 子集自建，记录和接口名保持一致，以后可以直接切换。
- **为什么自建 App 把文件字节存在自己的数据里：** `ctx.assets` 需要在 `runtime/registrations/` 注册，那是平台改动，要避开。
- 评分器经过两轮修复，共 10 个 bug，详见 `tasks/tax-packet/notes.md` 第 3 节。
- **为什么先问维护者再推送：** 4 个问题都是结构性的；任务 track 没有硬性期限；runner 没出来之前，推送只会给评审增加噪音。
- **GUI：** #102 的自建 App 先不做，等维护者答复。Counterline 的 GUI 可以先在本地做。
- **LLM judge：** 只考虑用在语言判断的点上，代码先算好事实；先问是否有共享配置。
