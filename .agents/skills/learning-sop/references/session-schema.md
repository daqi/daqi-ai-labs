# Session 存储结构

## 目录布局

```
learning/sessions/{slug}/
├── meta.md               # 核心元数据，YAML frontmatter + 可选备注
├── phase1-topology.md    # Phase 1：知识拓扑输出（追加式）
├── phase2-feynman.md     # Phase 2：费曼对话摘要（追加式）
├── phase3-quiz.md        # Phase 3：出题/答题/得分记录（追加式）
├── phase4-transfer.md    # Phase 4：迁移训练案例（追加式）
├── phase5-calibration.md # Phase 5：元认知校准记录（追加式）
└── journal.md            # 用户自由笔记 + AI 关键节点摘要
```

## meta.md frontmatter 字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `topic` | string | 原始主题名称 |
| `slug` | string | URL 安全的目录名 |
| `started_at` | date | 首次学习日期 |
| `last_active` | date | 最后活跃日期（每次 phase 结束后更新） |
| `completed_phases` | int[] | 已完成的阶段编号列表 |
| `current_phase` | int | 当前/下一个待执行阶段（1-5） |
| `total_sessions` | int | 累计学习次数（每次全流程 +1，单阶段也 +1） |
| `knowledge_level` | int | 0-10，Phase 5 校准后更新 |
| `next_review` | date | 基于遗忘曲线推算的下次复习日期 |
| `review_count` | int | 复习次数（区别于首次学习） |

## Phase 文件追加格式

每次执行该阶段后，AI 在对应文件末尾追加一个 Session 块，**不覆盖历史记录**：

```markdown
## Session {N} · {YYYY-MM-DD}

{本次学习的摘要内容}

---
```

### phase1-topology.md 追加内容

```markdown
## Session 1 · 2026-03-02

### 核心命题
...

### 依赖前提
...

### 关键争议
...

### 盲区清单
- [ ] 初学者易混淆点 1
- [ ] 初学者易混淆点 2

---
```

### phase2-feynman.md 追加内容（摘要，非完整对话）

```markdown
## Session 1 · 2026-03-02

**能流畅解释的部分**: ...
**暴露的漏洞**: 在解释反例时逻辑断裂，无法区分主观价值与相对价值
**追问路径**: 核心命题 → 举例 → 反例构造（卡住）→ 重新定义边界
**建议强化点**: 反例构造能力，参见 phase3 迁移题

---
```

### phase3-quiz.md 追加内容

```markdown
## Session 1 · 2026-03-02

| # | 题型 | 题目摘要 | 得分 | 错误点 |
|---|------|---------|------|--------|
| 1 | 概念题 | 核心主张是什么 | 8/10 | 忽略边际效用 |
| 2 | 应用题 | 解释拍卖定价 | 7/10 | — |
| 3 | 迁移题 | 映射到 NFT 泡沫 | 5/10 | 未能脱离原框架 |

**本次正确率**: 67%
**预测保持曲线**: 3天后降至约 40%（Ebbinghaus）
**推荐下次复习**: 2026-03-05

---
```

### phase4-transfer.md 追加内容

```markdown
## Session 1 · 2026-03-02

**映射目标**: AI 产品定价
**核心映射**: 主观价值 → 用户感知效用；边际效用递减 → 功能疲劳
**迁移质量**: 能识别同构关系，但未能推导出新见解
**迁移深度评估**: 浅层映射（概念对应），未达深层迁移（规律复用）

---
```

### phase5-calibration.md 追加内容

```markdown
## Session 1 · 2026-03-02

**自评分**: 4/10
**能否教别人**: 否，核心推导链尚不清晰
**最不确定点**: 价格信号传递机制与主观价值的关系
**认知错觉概率**: 中等（约60%） — 用户对术语熟悉但推导逻辑模糊
**更新 knowledge_level**: 4
**更新 next_review**: 2026-03-05（3天后，正确率<70% 触发短间隔）

---
```

## meta.md 更新时机

| 触发事件 | 更新字段 |
|---------|---------|
| 任意 phase 完成 | `last_active`, `completed_phases`, `current_phase` |
| Phase 5 完成 | `knowledge_level`, `next_review`, `total_sessions` |
| 用户明确复习 | `review_count` +1 |

## slug 命名规则

- 全小写英文
- 空格替换为 `-`
- 去除特殊字符
- 示例：`"奥派经济学主观价值理论"` → `austrian-subjective-value`（用户可自定义）
