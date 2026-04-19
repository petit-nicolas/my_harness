# wiki/feedback — Runner → Builder 反馈队列

Wiki Feedback Loop 的物理落点。由 Harness Runner 在教学过程中追加 ticket，由 Cursor Builder 在 build-time 审核处理。

## 设计意图

- **Runner 永远不写 wiki**，但学生反馈、教学观测、quiz 数据信号都不应该丢
- 通过 append-only 队列把这些信号传给 Builder
- Builder 由 `feedback_reviewer`（Cursor 自己充当）辅助决策，调用 `wiki_write` 修订
- 完整数据流与协议见 `.cursor/rules/physics-project.mdc` 的 Feedback Loop 章节

## 子目录（V3.6 子任务建立）

```
feedback/
├── README.md          本文件
├── inbox/             待处理（Harness Runner 通过 feedback_submit 写入）
│   └── 2026-04-19T10-32-15-mechanics-newton-second-law-a3f2.md
├── processed/         已接受并完成 wiki 修订
└── rejected/          已拒绝（含 reviewer 理由）
```

## Ticket 命名

`<ISO timestamp>-<target slug>-<short hash>.md`

- `timestamp`：精确到秒，避免冲突
- `target slug`：wiki 页面 id 转 slug（`mechanics/newton-second-law` → `mechanics-newton-second-law`）
- `short hash`：4 位随机，防同秒并发

## Ticket frontmatter（runner 提交时写入）

```yaml
---
ticket_id: 2026-04-19T10-32-15-a3f2
target: mechanics/newton-second-law      # wiki 页 id；new_concept 类可填 proposed/<slug>
kind: error | gap | unclear | outdated | new_concept
submitted_by: harness-runner | harness-hook | student-direct
submitted_at: 2026-04-19T10:32:15
session_id: <harness session id>
evidence: |
  学生原话 / 系统观测信号 / 上下文片段
suggestion: |                              # 可空
  runner 的修订建议
status: pending                            # pending → accepted | rejected | needs_more_info
---
```

## Builder 处理后追加字段

**accepted**：

```yaml
processed_at: 2026-04-19T15:44:02
commit_summary: 在 mechanics/newton-second-law 增加近似适用条件的醒目提示框
processed_by: cursor + feedback_reviewer
```

**rejected**：

```yaml
rejected_at: 2026-04-19T15:50:11
reject_reason: 学生表述与 wiki 一致，理解偏差源自学生未读完整段落
processed_by: cursor + feedback_reviewer
```

**needs_more_info**：

```yaml
notes: 需要原 session 的完整问答上下文；下次同 target 反馈到达时合并查看
```

## 写权限隔离（V3.6 通过 src.security 落地）

| 路径 | Builder | Runner |
|------|:-------:|:------:|
| `inbox/` | rwx | **仅 O_CREAT \| O_EXCL** |
| `processed/` | rwx | 不可写 |
| `rejected/` | rwx | 不可写 |

Runner 的 `feedback_submit` 实现层走 `src.security` 的 file policy，硬阻断非法写入；不依赖 prompt 约束。

## 防洪流策略

- runner submit 前去重：同 target + 近 1 小时 + 同 kind 不重复
- inbox 容量 100 条；满时 runner 提示"反馈队列已满，请通知管理员"，**不阻塞教学**
- builder 批量处理时主动归并同 target 多条 ticket（在 frontmatter 加 `merged_into`）

## 当前状态

**仅本 README**（治理层）。子目录与业务实现由 V3.6 子任务建立。
