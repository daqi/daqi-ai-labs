---
name: learning-sop
description: AI 原生深度学习工作流（Learning SOP），模拟 Benjamin Bloom 的 2 Sigma 个性化辅导效果。包含五个链式阶段：结构建立→费曼压缩→检索强化→迁移训练→元认知校准。带持久化记忆系统，跨 session 记录学习进度、知识水平、遗忘曲线复习计划。使用场景：(1) 用户想系统学习某个主题（"我想学 X"、"帮我深度学习 X"）(2) 用户想从指定阶段继续学习（"从第 3 阶段开始"、"phase=3"）(3) 用户想查看某主题的学习进度（"status"、"查看进度"）(4) 用户想恢复上次中断的学习（"resume"、"继续"）触发关键词：学习、深度学习、SOP、费曼、知识拓扑、检索强化、元认知、复习计划
---

# Learning SOP

五阶段 AI 原生深度学习工作流，链式执行，带跨 session 持久化记忆。

## 命令语法

```
/learning-sop topic="主题名" [slug="custom-slug"] [phase=N] [action=resume|status]
```

| 参数 | 说明 | 示例 |
|------|------|------|
| `topic` | 学习主题（必填） | `topic="奥派经济学主观价值理论"` |
| `slug` | 自定义目录名（可选，默认自动生成） | `slug="austrian-value"` |
| `phase` | 从指定阶段开始（1-5，默认从当前阶段继续） | `phase=3` |
| `action=status` | 只查看进度，不执行学习 | `action=status` |
| `action=resume` | 从上次中断处继续 | `action=resume` |

## 执行流程

### Step 1：初始化 Session

运行 `scripts/init_session.py` 获取 session 状态：

```bash
python3 .agents/skills/learning-sop/scripts/init_session.py \
  --topic "{topic}" [--slug "{slug}"] \
  --sessions-dir learning/sessions \
  --action init
```

- 若 session 不存在：自动创建 `learning/sessions/{slug}/` 目录和所有文件
- 若 session 存在：读取当前进度，输出 JSON 状态

若 `action=status`：打印进度摘要后终止，不进入学习流程。

### Step 2：确定起始阶段

优先级：
1. 用户指定 `phase=N` → 从 N 开始
2. `action=resume` or 无参数 → 从 `meta.md` 的 `current_phase` 继续
3. 全新 session → 从 Phase 1 开始

跳过阶段时，读取 `learning/sessions/{slug}/` 中对应 phase 文件获取历史上下文。

### Step 3：执行阶段（链式）

按顺序执行，每阶段结束后自动流转到下一阶段：

| 阶段 | 时长 | 参考文件 |
|------|------|---------|
| Phase 1：结构建立 | ~20 min | `references/phase1-structure.md` |
| Phase 2：费曼压缩 | ~25 min | `references/phase2-generation.md` |
| Phase 3：检索强化 | ~20 min | `references/phase3-retrieval.md` |
| Phase 4：迁移训练 | ~15 min | `references/phase4-transfer.md` |
| Phase 5：元认知校准 | ~10 min | `references/phase5-calibration.md` |

每个 phase 的 AI 角色、prompt 模板、追加格式见对应参考文件。

### Step 4：写入记忆

每个阶段结束后：
1. 追加摘要到对应 phase 文件（`phase{N}-*.md`），带时间戳 Session 块
2. 更新 `meta.md` 的 `completed_phases`、`current_phase`、`last_active`

Phase 5 完成后额外更新：`knowledge_level`、`next_review`、`total_sessions`，并在 `journal.md` 追加全流程摘要。

Session 文件结构和字段定义见 `references/session-schema.md`。

## 记忆文件位置

```
learning/sessions/{slug}/
├── meta.md               # 进度元数据（YAML frontmatter）
├── phase1-topology.md    # 知识拓扑历史
├── phase2-feynman.md     # 费曼摘要历史
├── phase3-quiz.md        # 出题记录历史
├── phase4-transfer.md    # 迁移案例历史
├── phase5-calibration.md # 元认知校准历史
└── journal.md            # 用户笔记 + AI 关键节点摘要
```

## 跳阶时的上下文加载规则

| 跳入阶段 | 需要读取的历史文件 |
|---------|----------------|
| Phase 2 | `phase1-topology.md`（获取盲区清单） |
| Phase 3 | `phase1-topology.md` + `phase2-feynman.md`（获取漏洞点） |
| Phase 4 | `phase1-topology.md` |
| Phase 5 | `phase3-quiz.md` + `phase2-feynman.md` + `phase4-transfer.md` |

## 注意事项

- Session 文件使用 Markdown，用户可手动编辑
- `journal.md` 是用户自由区，AI 只追加不覆盖
- `knowledge_level` 首次学习上限为 6（防止 Dunning-Kruger 效应）
- 同一 topic 可多次学习，记录全部追加保留
