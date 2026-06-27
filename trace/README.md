# 开发交互轨迹 (Claude Code)

本目录保存本项目使用 **Claude Code** 开发的完整交互轨迹,对应任务要求的"完整保留开发过程中的完整交互轨迹"。

- `session-*.jsonl` —— Claude Code 会话记录(原始位置:`~/.claude/projects/`)。
  每行是一条 JSON 事件(用户消息 / 模型回复 / 工具调用与结果),完整记录了从环境探活、
  逐模块实现、到调试迭代(见 `docs/DESIGN.md` 第 5 节"迭代过程")的全过程。

> 查看建议:用支持 JSONL 的工具逐行读取,或 `cat session-*.jsonl | jq -c '{type,role}'` 速览结构。
