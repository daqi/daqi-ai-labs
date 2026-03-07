# Session 存储结构

## 目录布局

```
learning/sessions/{slug}/
├── meta.md                    # 核心元数据，YAML frontmatter
├── journal.md                 # 用户自由笔记 + AI 每轮摘要
└── cycles/
    ├── cycle1/
    │   ├── diagnosis.md       # Step A：水平诊断结果（含遗忘衰减）
    │   ├── curriculum.md      # Step B：本轮生成的课程
    │   ├── quiz.md            # Step C：C2 作答记录
    │   └── assessment.md      # Step D：综合评估 + 循环决策
    ├── cycle2/
    │   └── [同上]
    └── ...
```

## meta.md frontmatter 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `topic` | string | 原始主题名称 |
| `slug` | string | URL 安全的目录名 |
| `started_at` | date | 首次学习日期 |
| `last_active` | date | 最后活跃日期（每轮结束后更新） |
| `current_cycle` | int | 当前/下一个待执行轮次（从 1 开始） |
| `knowledge_level` | int | 0-10，每轮 Step D 后更新 |
| `mode` | string | `learning`（学习中）或 `review`（复习模式） |
| `efactor` | float | SM-2 记忆稳定性，初始 2.5，复习后更新 |
| `next_review` | date | 下次复习日期（仅 mode=review 时有值） |
| `review_count` | int | 复习次数（区别于新轮学习） |
| `total_cycles_completed` | int | 已完成的学习循环总数 |

### meta.md 示例

```yaml
---
topic: "奥派经济学主观价值理论"
slug: "austrian-value"
started_at: "2026-03-04"
last_active: "2026-03-07"
current_cycle: 3
knowledge_level: 6
mode: learning
efactor: 2.5
next_review: ""
review_count: 0
total_cycles_completed: 2
---
```

## meta.md 更新时机

| 触发事件 | 更新字段 |
|---------|---------|
| 任意轮次 Step D 完成 | `last_active`、`knowledge_level`、`current_cycle` |
| 达标（level >= 8） | `mode=review`、`next_review`、`efactor` |
| 复习完成 | `review_count+1`、`last_active`、`next_review`、`efactor` |

## cycles/cycle{N}/ 文件内容格式

### diagnosis.md

```markdown
---
cycle: {N}
knowledge_level_before_decay: {level}
decay_delta: {0 / -0.5 / -1.0 / -1.5 / -2.0 / -2.5}
days_since_last: {days}
actual_level: {level after decay + calibration}
---

## 诊断结果

- 上轮水平：{last_level}/10
- 遗忘衰减：-{decay_delta}（间隔 {days} 天）
- 热身校准：{+0.5 / 0 / -0.5}
- 当前实际水平：{actual_level}/10

**已掌握概念**：[...]
**识别到的盲区**：[...]
**学习动机/背景**：[...]
```

### curriculum.md

```markdown
---
cycle: {N}
knowledge_level_at_generation: {level}
blind_spots_addressed:
  - {blind_spot_1}
  - {blind_spot_2}
generated_at: {timestamp}
---

# 第 {N} 轮课程：{topic}

[完整课程内容]
```

### quiz.md

```markdown
## 检索练习记录（Cycle {N}）

| # | 题目摘要 | 结果 | 备注 |
|---|---------|------|------|
| 1 | [摘要] | ✓ / △ / ✗ | [错误点] |

- 正确率：{X}%
- feynman_score：{score}/10
- transfer_score：{score}/10
```

### assessment.md

```markdown
## 第 {N} 轮学习评估

[综合评估内容]

- 知识水平：{old} → {new}
- 循环决策：[继续学习 / 进入复习模式]
- 下轮盲区：[...]
```

## journal.md 追加格式

每轮学习结束后，AI 在文件末尾追加（**不覆盖用户已有内容**）：

```markdown
## Cycle {N} 摘要（{YYYY-MM-DD}）
- 攻克盲区：{blind_spots}
- 水平变化：{old} → {new}
- 关键突破：{一句话}

---
```

## slug 命名规则

- 全小写英文字母
- 空格替换为 `-`
- 去除特殊字符和中文
- 示例：`"奥派经济学主观价值理论"` → `austrian-value`（用户可自定义）
