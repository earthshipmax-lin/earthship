# Matt Pocock 资料与设计取舍

阅读日期：2026-11-09（Asia/Shanghai）。实际通过 GitHub raw 读取下列原始资料；GitHub API 在当前网络策略下返回 403，因此未据此声称完整调查其全部作品。这里是归纳和应用，不是 Matt 对本项目的背书。

1. [Skills For Real Engineers](https://github.com/mattpocock/skills/blob/main/README.md)：强调小而可组合、可修改的 skills，清晰需求、共享术语和快速反馈。应用：一个核心 skill + 独立同步器 + 可恢复文档，不引入庞大编排框架。
2. [handoff](https://github.com/mattpocock/skills/blob/main/skills/productivity/handoff/SKILL.md)：交接摘要、引用现有 artifacts、脱敏、建议下一阶段技能。原版手动触发并写临时目录；本项目因持续备份需求，改为仓库内持久化、检查点触发和 GitHub 核验。不能误称原版已有自动云备份功能。
3. [writing-for-agents](https://github.com/mattpocock/skills/blob/main/skills/productivity/writing-for-agents/SKILL.md)：明确 context pointers 的触发分支、渐进披露、可检查的完成标准。应用：精简 AGENTS.md 指向 SKILL.md，恢复与事件格式单独存放，以远端包含提交为完成标准。
4. [retro](https://github.com/mattpocock/skills/blob/main/skills/engineering/retro/SKILL.md)：从实际证据改进导航、检查、规范和信息访问；机械错误更适合确定性检查。应用：经验记录附证据、候选/已验证状态，脚本改进需要回归测试。
5. [domain-modeling](https://github.com/mattpocock/skills/blob/main/skills/engineering/domain-modeling/SKILL.md)：术语和重要决策及时落盘，避免长期依赖会话记忆。应用：固定事件分类，在需求和决策出现时记录；复杂领域出现时才创建专用词汇表或 ADR。

本项目额外增加的工程措施：独立 append-only 备份分支、未提交文本快照、断网本地队列、跨会话路径隔离、非强制推送、远端提交验证、SHA-256 清单、凭据启发式排除。这些是针对本次需求的设计，不应归因于上述作者。
