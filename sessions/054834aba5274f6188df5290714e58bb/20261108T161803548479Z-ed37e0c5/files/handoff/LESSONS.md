# 经验与改进

## 2026-11-09：区分交接上下文和文件备份（validated）
- 观察：后台程序只能看见落盘文件，无法直接访问托管 Codex 的全部对话。
- 规则：agent 在关键操作后记录事件并维护 CURRENT；watcher 负责文件快照。
- 证据：skill 的 Capture 流程及同步器 collect 接口。
- 限制：依赖 agent 遵循指令，不能宣传为全量聊天自动导出。

## 2026-11-09：用实际远端证明送达（validated）
- 观察：本地 commit、进程存活和推送日志均不能单独证明远端持有备份。
- 规则：先落盘，再推送；用 ls-remote 或祖先关系核验。
- 证据：tests/test_sync.py 的 outage、remote recovery 和 independent sessions 用例全部通过。
- 改进候选：未来若有明确审计或全量导出需求，接入宿主官方支持的事件/转录接口；当前未验证这些接口存在。
