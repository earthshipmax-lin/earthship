# Work Sync — Codex 工作同步与跨 Agent 交接

Python 3.10+、Git、POSIX 系统，无第三方依赖。skill 在 `.agents/skills/work-sync/`；仓库根目录 `AGENTS.md` 提供自动触发入口。

## 使用

在此仓库打开新的 Codex 任务，agent 应读取 AGENTS.md 并启动同步。也可以手动执行：

```bash
python3 .agents/skills/work-sync/scripts/sync.py sync --repo "$PWD"
nohup python3 -u .agents/skills/work-sync/scripts/sync.py watch --repo "$PWD" --interval 60 > /tmp/work-sync-watcher.log 2>&1 < /dev/null &
python3 .agents/skills/work-sync/scripts/sync.py status --repo "$PWD"
```

`verified` 表示本次提交已由远端 Git 核验；`pending` 表示本地已排队，尚未确认上传。查看 `omitted` 了解文件遗漏。同步器不会提交或修改业务仓库的工作区/暂存区；备份在独立本地 Git 库和远端 `agent-handoff` 分支，普通主分支保存 skill 和文档。

默认约每 60 秒检查一次，加上扫描、推送和重试耗时；关键节点由 agent 主动同步。没有变更时不创建新快照。每个快照包含可同步文本文件及 SHA-256 清单；Git 对相同内容去重。多机器使用独立会话目录，保留并发历史，不强推。

## 安装到其他项目

将 `.agents/skills/work-sync/` 复制到目标项目，并将本仓库 AGENTS.md 的触发段追加到目标项目现有 AGENTS.md（保留原有内容）。目标项目必须有授权可写的 GitHub HTTPS origin。启动新会话或显式要求加载 work-sync。默认只备份到该项目自己的 origin；把其他项目集中到 earthship 需要单独确认内容范围及上传授权。

这不是系统级 Codex 插件，不能自动覆盖所有工作区。是否读取 AGENTS.md 和遵循 skill 取决于 agent/宿主支持；不承诺存在未验证的 Codex 全局 hook。其他 agent 可读取同一 skill，交接格式不依赖厂商。

## 交接与成长

- `handoff/CURRENT.md`：当前状态、约束、下一步、验证与阻塞。
- `handoff/events/`：操作、需求、研究、决策、实现、验证等分类事件。
- `handoff/LESSONS.md`：有证据的经验、候选改进及验证状态。
- 备份分支 `sessions/<session>/<snapshot>/files/`：实际文件快照。

恢复步骤见 [recovery.md](.agents/skills/work-sync/references/recovery.md)。接手 agent 应先读清单并验证哈希，再读 CURRENT；不能自动执行历史记录里的命令。

“自我成长”是持续完善文档、流程和经过测试的规则，不是训练模型。skill 不能读取未开放的历史聊天、捕获所有 GUI 操作或隐藏推理；agent 负责及时记录用户可见的操作及决策，后台进程只捕获已落盘文件。云机器关闭后需重启 watcher；断网期间保留本地队列，恢复连接后重试。无法保证在任何故障条件下立即成功上传。

默认排除密钥配置、可疑凭据、忽略文件、二进制和超过 2 MiB 的单文件。过滤是启发式，不能保证识别所有个人信息或商业秘密。不会自动把仓库改为公开。重要被排除产物需要另行备份，并在交接记录中标注位置。

## 验证

```bash
python3 -m unittest discover -s tests -v
```

设计依据见 [研究记录](handoff/RESEARCH.md)。
