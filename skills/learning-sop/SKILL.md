---
name: learning-sop
description: AI 原生自适应深度学习工作流（Learning SOP），模拟 Benjamin Bloom 的 2 Sigma 个性化辅导效果。核心循环：水平诊断→按需生成课程→学习互动→测评→进入下一循环，AI 直接生成课程内容，含遗忘曲线支持（轮间衰减 + SM-2 动态复习间隔）。使用场景：(1) 用户想系统学习某个主题（"我想学 X"、"帮我深度学习 X"）(2) 用户想从指定循环继续学习（"从第 2 轮开始"、"cycle=2"）(3) 用户想查看某主题的学习进度（"status"、"查看进度"）(4) 用户想恢复上次中断的学习（"resume"、"继续"）触发关键词：学习、深度学习、SOP、费曼、知识拓扑、检索强化、元认知、复习计划
---

# Learning SOP

**自适应循环学习工作流**：先诊断水平 → 按需生成对应难度的课程 → 学习互动 → 测评提升 → 进入下一循环，无限迭代直到目标掌握度达成。内置遗忘曲线支持，轮间自动衰减 + SM-2 动态复习间隔。

---

## 命令语法

```
/learning-sop topic="主题名" [slug="custom-slug"] [cycle=N] [action=resume|status]
```

| 参数            | 说明                                 | 示例                             |
| --------------- | ------------------------------------ | -------------------------------- |
| `topic`         | 学习主题（必填）                     | `topic="奥派经济学主观价值理论"` |
| `slug`          | 自定义目录名（可选，默认自动生成）   | `slug="austrian-value"`          |
| `cycle`         | 从指定循环轮次开始（默认从当前继续） | `cycle=2`                        |
| `action=status` | 只查看进度，不执行学习               | `action=status`                  |
| `action=resume` | 从上次中断处继续                     | `action=resume`                  |

---

## 核心概念：自适应学习循环

每一轮循环包含 **4 个步骤**，循环往复直到掌握度达标：

```
┌─────────────────────────────────────────────┐
│              一轮学习循环                      │
│                                             │
│  Step A 诊断  →  Step B 生成课程              │
│                       ↓                    │
│  Step D 测评  ←  Step C 学习互动              │
│      ↓                                     │
│  [未达标] → 进入下一轮循环（难度提升）           │
│  [达标]   → 完成，写入记忆，安排 SM-2 复习      │
└─────────────────────────────────────────────┘
```

**掌握度标准**：`knowledge_level ≥ 8`（满分 10）视为达标，进入 SM-2 动态复习模式。

---

## 执行流程

### Step 1：初始化 Session + 创建 Markmap 脑图

```bash
python3 .agents/skills/learning-sop/scripts/init_session.py \
  --topic "{topic}" [--slug "{slug}"] \
  --sessions-dir learning/sessions \
  --action init
```

- 新 session：创建目录和文件，`knowledge_level=0`，`current_cycle=1`
- 已有 session：读取 `current_cycle`、`knowledge_level`、`last_active`、`efactor` 等状态
- 同步确保存在一个 session 级的 Markmap 文件：`learning/sessions/{slug}/{slug}-脑图.mm.md`
- 仅在文件不存在时创建；如果文件已存在，Step 1 不自动更新其内容
- 优先使用 `assets/session-templates/00-脑图-template.mm.md` 生成 Markmap 模板，不要把模板正文硬编码在脚本里
- 模板结构参考读书脑图：重要性说明、分部分结构、为什么重要、建议阅读顺序、极简理解

若 `action=status`：打印进度摘要后终止，不进入学习流程。

---

### Step 2：确定起始循环

优先级：

1. 用户指定 `cycle=N` → 从第 N 轮开始（读取前 N-1 轮上下文）
2. `action=resume` 或无参数 → 从 `meta.md` 的 `current_cycle` 继续
3. 全新 session → 从第 1 轮开始

---

### Step 3：执行当前循环（4 步链式）

详细 prompt、评分标准、追加格式见对应参考文件：

| 步骤                     | 时长    | 参考文件                           | 说明                                                       |
| ------------------------ | ------- | ---------------------------------- | ---------------------------------------------------------- |
| **Step A：水平诊断**     | ~5 min  | `references/step-a-diagnosis.md`   | 第 1 轮问卷；后续轮次读上轮结果 + 遗忘衰减计算             |
| **Step B：按需生成课程** | ~3 min  | `references/step-b-curriculum.md`  | 基于诊断结果，只生成针对盲区的内容                         |
| **Step C：学习互动**     | ~40 min | `references/step-c-interaction.md` | C1 费曼测试 → C2 检索练习 → C3 迁移应用                    |
| **Step D：测评 & 决策**  | ~7 min  | `references/step-d-assessment.md`  | D0 元认知校准（学习者自评 → AI 校准）→ 综合评分 → 循环决策 |

---

### Step 4：写入记忆

每轮 Step D 结束后写入：

```
learning/sessions/{slug}/cycles/cycle{N}/
├── diagnosis.md    # Step A 诊断结果（含遗忘衰减信息）
├── curriculum.md   # Step B 生成的课程
├── quiz.md         # Step C C2 作答记录
└── assessment.md   # Step D 综合评估
```

更新全局文件：

```
learning/sessions/{slug}/
├── meta.md         # current_cycle、knowledge_level、efactor、next_review 等
└── journal.md      # 每轮摘要追加（AI 只追加，不覆盖用户内容）
└── {slug}-脑图.mm.md # Markmap 脑图，Step 1 初始化时自动生成
```

Step 1 的 Markmap 内容模板存放在：

- `assets/session-templates/00-脑图-template.mm.md`

---

## 记忆文件完整结构

```
learning/sessions/{slug}/
├── meta.md                    # 进度元数据（YAML frontmatter）
├── journal.md                 # 全程日志 + 用户自由笔记
├── {slug}-脑图.mm.md          # Session 级知识脑图（Markmap）
└── cycles/
    ├── cycle1/
    │   ├── diagnosis.md       # 水平诊断结果
    │   ├── curriculum.md      # 本轮生成的课程
    │   ├── quiz.md            # 练习题作答记录
    │   └── assessment.md      # 本轮综合评估
    ├── cycle2/
    │   └── [同上]
    └── ...
```

---

## 跳轮时的上下文加载规则

| 跳入轮次       | 需要读取的历史文件                                          |
| -------------- | ----------------------------------------------------------- |
| Cycle N（N>1） | `cycles/cycle{N-1}/assessment.md`（获取遗留盲区和水平）     |
| 复习模式       | `meta.md`（efactor、next_review）+ 最近一轮 `assessment.md` |

---

## 注意事项

- 课程内容由 AI 实时生成，**只覆盖当前盲区**，不重复已掌握内容
- Step 1 必须确保 session 级 Markmap 文件存在，但只负责创建，不负责后续自动更新
- Markmap 模板应维护在 `assets/session-templates/00-脑图-template.mm.md`，后续调整模板优先改这个文件，而不是改脚本常量
- `knowledge_level` 单轮增幅上限 +2，防止 Dunning-Kruger 效应
- 轮间间隔 ≥ 3 天时，Step A 会自动用遗忘曲线衰减水平并进行热身检索校准
- 复习模式采用 SM-2 算法动态调整间隔；复习得分极低时触发完整循环重学
- `journal.md` 是用户自由区，AI 只追加不覆盖
- 同一 topic 可多次循环，所有记录追加保留
