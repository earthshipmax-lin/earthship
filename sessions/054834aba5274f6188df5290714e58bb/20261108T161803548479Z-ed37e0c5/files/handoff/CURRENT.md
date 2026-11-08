# 当前工作

## 目标与授权
用户需要 Codex 工作自动持续同步至 GitHub、分类总结、可持续改进，并方便其他 agent 接手。用户已确认使用 earthshipmax-lin/earthship。允许上传本项目的 skill 和经过筛选的工作记录；当前保留仓库原有可见性。

## 已完成
- 查阅 Matt Pocock 的 skills README、handoff、writing-for-agents、retro 和 domain-modeling。
- 编写 work-sync skill、AGENTS.md 触发入口、Python 同步器、交接规范与恢复说明。
- 六个集成测试通过：远端恢复/哈希/无变更、敏感文件排除、断网补传、多会话并发、删除语义、状态目录保护。

## 正在进行
首次实际 GitHub 推送、远端独立恢复检查和 watcher 启动。结果见后续 events 和同步器状态。

## 下一步
1. 核实 main 分支含 skill、agent-handoff 分支含快照。
2. 新 agent 从 AGENTS.md 加载 skill；读取最新备份的 manifest、CURRENT 和 LESSONS。
3. 在新的项目中部署时，复制 skill 并追加触发说明，明确该项目的上传目标及权限。

## 约束与限制
Python 3.10+、Git、POSIX。没有第三方依赖。后台进程随机器停止；每次会话启动需重启。只同步已落盘、未被排除的小型文本；不是所有聊天和 GUI 操作的无损备份。未上传队列位于项目父目录 .handoff-state；公网故障下无法保证即时上传。运行 sync 获取新鲜远端验证，status 只是上次结果。
