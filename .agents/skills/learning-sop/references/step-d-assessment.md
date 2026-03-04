# Step D：测评 & 循环决策

## AI 角色

客观的学习评估师，综合 C1/C2/C3 表现给出本轮评估，并决定下一步行动（继续循环或进入 SM-2 复习模式）。

---

## 综合评分

读取本轮三个子阶段得分：
- `feynman_score`（0-10）：来自 C1
- `quiz_accuracy`（0-1）：来自 C2 正确率
- `transfer_score`（0-10）：来自 C3

综合掌握度：
```
comprehensive_score = feynman_score * 0.4 + quiz_accuracy * 10 * 0.3 + transfer_score * 0.3
```

知识水平更新规则：
```
delta = round((comprehensive_score - 5) / 2)
delta = max(-1, min(+2, delta))          # 单轮增幅上限 +2，降幅上限 -1
new_level = max(0, min(10, old_level + delta))
```

---

## 输出评估报告

保存到 `cycles/cycle{N}/assessment.md`：

```markdown
## 第 {cycle} 轮学习评估

### 本轮表现

| 环节 | 得分 | 说明 |
|------|------|------|
| 费曼测试 | {feynman_score}/10 | {一句话评语} |
| 检索练习 | {quiz_accuracy*100:.0f}% | {X}/{total} 题正确 |
| 迁移应用 | {transfer_score}/10 | {一句话评语} |
| **综合掌握度** | **{comprehensive_score:.1f}/10** | |

### 知识水平变化
{old_level} → **{new_level}** /10

### 本轮真正理解的内容
- {concept_1}：从模糊 → 清晰
- {concept_2}：{...}

### 下一轮仍需攻克的盲区
- {remaining_blind_spot_1}：{说明}
- {remaining_blind_spot_2}：{说明}
```

---

## 循环决策

### 未达标（`new_level < 8`）→ 进入下一轮

```
你的掌握度还有提升空间，进入第 {cycle+1} 轮！

下轮课程将：
- 聚焦仍不清晰的 [{remaining_blind_spots}]
- 难度调整为 {next_level_name} 级
- 用新的例子和视角重新切入

准备好了告诉我，开始第 {cycle+1} 轮的诊断。
```

更新 `meta.md`：`current_cycle = N+1`，`knowledge_level = new_level`

---

### 达标（`new_level >= 8`）→ 进入 SM-2 复习模式

```
🎉 核心掌握达成！「{topic}」掌握度已达 {new_level}/10，进入复习维护模式。
```

计算并展示个性化复习计划（见下方 SM-2 算法），更新 `meta.md`：`mode = review`

---

## SM-2 动态复习间隔算法

### 核心参数

```
E-Factor（记忆稳定性）：初始值 2.5，范围 [1.3, 5.0]
Interval（复习间隔天数）
```

### 首次进入复习模式的间隔

```
第 1 次复习：今天 + 1 天（固定）
第 2 次复习：今天 + 4 天（固定）
第 3 次及以后：上次间隔 × E-Factor（取整）
```

### 每次复习后更新 E-Factor

复习时执行 C2 检索练习，将正确率换算为 q 值（0-5）：

```
q = round(quiz_accuracy * 5)
```

| q 值 | 描述 | E-Factor 更新 | 间隔处理 |
|------|------|--------------|---------|
| 5 | 完全记得，秒答 | `EF = EF + 0.1` | 正常递增 |
| 4 | 记得，略费力 | `EF = EF`（不变） | 正常递增 |
| 3 | 模糊，需提示 | `EF = EF - 0.14` | 正常递增 |
| 2 | 大部分忘记 | `EF = EF - 0.30` | 重置 interval=1 |
| 1 | 几乎全忘 | `EF = EF - 0.50` | 重置 interval=1 |
| 0 | 完全不记得 | `EF = EF - 0.50` | **触发完整循环重学** |

```
EF = max(1.3, min(5.0, EF))
```

### 复习计划输出示例

```markdown
## 你的个性化复习计划

当前记忆稳定性（E-Factor）：2.5

| 次数 | 预计日期 | 间隔 |
|------|---------|------|
| 第1次 | {today+1} | 1 天 |
| 第2次 | {today+5} | 4 天 |
| 第3次 | {today+15} | 10 天（≈4×2.5） |
| 第4次 | {today+40} | 25 天 |
| 第5次 | {today+103} | 63 天 |

> 以上为预估，每次复习后根据实际记忆状态自动调整。
> 若某次复习 q=0，间隔重置，同时触发完整循环重学。
```

---

## 复习模式触发条件

用户运行 `/learning-sop topic="..." action=resume` 时：

1. 读取 `meta.md` 中的 `next_review` 日期和 `mode`
2. 若 `mode=review` 且今天 ≥ `next_review`：只执行 **C2 检索练习 + Step D**，约 15 分钟
3. 若今天 < `next_review`：提示"下次复习还有 {N} 天，可提前复习或等到计划日期"

---

## 写入记忆

每轮结束后：

**`meta.md` 更新字段**：

```yaml
current_cycle: {N+1 或保持N（已达标）}
knowledge_level: {new_level}
mode: {learning | review}
efactor: {EF，首次学习保持 2.5，复习后更新}
next_review: {日期 或 null}
review_count: {复习次数，复习时 +1}
last_active: {timestamp}
```

**`journal.md` 追加**：

```markdown
## Cycle {N} 摘要（{date}）
- 攻克盲区：{blind_spots}
- 水平变化：{old} → {new}
- 关键突破：{一句话描述本轮最重要的理解进展}
```
