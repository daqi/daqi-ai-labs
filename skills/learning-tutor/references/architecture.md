# Learning Tutor 整体架构设计

## 定位

Learning Tutor 不是 Learning Loop 的重命名版，也不是在原有学习 SOP 上继续堆步骤。它是一个以“实时个性化教学”为核心的独立 skill。

它解决的问题不是“如何组织一轮学习流程”，而是“如何在每一个教学回合里判断学习者当前状态，并动态决定下一步该讲、该问、该提示、该纠错，还是该切换策略”。

一句话定义：

Learning Tutor = 面向单个学习者的自适应 AI 导师引擎。

---

## 与 Learning Loop 的边界分工

建议长期采用双轨：

| Skill | 角色 | 最适合的场景 |
|------|------|-------------|
| `learning-loop` | 流程型学习 SOP | 用户想系统学习一个主题，接受按轮推进 |
| `learning-tutor` | 导师型教学引擎 | 用户希望像真人老师一样被带着学、被追问、被纠错 |

Learning Tutor 不以“轮次”作为第一抽象，而以“学习状态”和“教学动作”作为第一抽象。

这意味着：

1. 它可以复用 Learning Loop 的记忆思想，但不应继承其固定 Step A/B/C/D 心智。
2. 它应该优先强调 tutor 行为，而不是课程生产。
3. 它的核心价值来自实时调度，而不是长文课程本身。

---

## 产品目标

Learning Tutor 的目标有四个：

1. 快速识别学习者当前真实水平，而不是只看自评。
2. 在互动中识别错误类型和稳定误解，而不是只收集盲区。
3. 根据不同错误触发不同教学动作，而不是统一“再讲一遍”。
4. 沉淀长期学习者模型，让 tutor 越教越懂这个人。

---

## 核心原则

### 1. 以学习者模型为中心

系统不是围绕课程运转，而是围绕“这个人现在处在什么状态”运转。

### 2. 以回合级干预为核心

最重要的不是生成内容，而是决定每个回答之后下一拍怎么教。

### 3. 以证据而不是印象做评估

评估最小单位是一次回答暴露的证据，而不是轮次结束时的总体感觉。

### 4. 以误解修复而不是内容覆盖为目标

真正的 tutor 不是尽可能多讲，而是优先修掉最关键的认知错误。

### 5. 以长期个性化为增强方向

同一个 tutor，多教几次后，必须越来越像“认识这个学习者”。

---

## 顶层架构

```text
用户请求
  -> Session Bootstrap
  -> Tutor Orchestrator
      -> Learner Model
      -> Domain Model
      -> Intervention Engine
      -> Assessment Engine
      -> Review Planner
  -> Session Memory
  -> 用户输出
```

---

## 六大模块

## 1. Session Bootstrap

职责：

1. 识别当前是新主题、继续学习、专项纠偏，还是复习模式。
2. 初始化或加载本 topic 的 session。
3. 判断是否已有历史 learner model、misconceptions、review state。
4. 给 Tutor Orchestrator 提供初始上下文。

输入：

1. 用户主题。
2. 用户目标。
3. 现有 session 文件。

输出：

1. 当前 session 状态。
2. 当前推荐 tutor mode。
3. 当前优先处理的 concept 或 misconception。

---

## 2. Tutor Orchestrator

职责：

1. 充当整个 skill 的主调度器。
2. 判断当前处于哪个教学状态。
3. 在不同状态间切换。
4. 调用对应模块生成下一条 tutor 行为。

它本质上是一个状态机，而不是线性工作流。

### 推荐状态机

```text
INIT
  -> BASELINE_CHECK
  -> GOAL_LOCK
  -> CONCEPT_SELECTION
  -> TEACH_OR_PROBE
  -> UNDERSTANDING_CHECK
  -> PRACTICE
  -> TRANSFER
  -> ASSESS
  -> NEXT_DECISION

NEXT_DECISION:
  - continue
  - remediate
  - switch_concept
  - schedule_review
  - close_session
```

说明：

1. `TEACH_OR_PROBE` 表示先判断当前更适合讲解还是更适合发问。
2. `UNDERSTANDING_CHECK` 不通过时，可回到 `TEACH_OR_PROBE`。
3. `TRANSFER` 失败时，可直接进入 `remediate`，不必强行结束整轮。

---

## 3. Learner Model

这是 Learning Tutor 的核心资产。

它不是简单记录一个 `knowledge_level`，而是记录“这个人怎么学、学到哪、常错什么”。

### 三层结构

#### 全局层

记录：

1. 学习动机。
2. 应用场景。
3. 目标深度。
4. 自评偏差。
5. 偏好的讲解方式。

#### 概念层

记录：

1. 各 concept 的掌握度。
2. 各 concept 的最近证据。
3. 常见错误类型。
4. 是否存在稳定误解。

#### 行为层

记录：

1. 是不是容易高估自己。
2. 遇到难题会不会卡住。
3. 更适合先类比还是先定义。
4. 追问多少轮后需要提示。

### 建议字段

```yaml
learner_profile:
  motivation: "为什么要学"
  application_context: "工作/考试/个人理解"
  target_depth: intro | practical | deep
  self_calibration_bias: overconfident | balanced | underconfident
  preferred_explanation_style:
    - analogy
    - example-first
  struggle_patterns:
    - abstract-jump
    - formula-anxiety

concept_mastery:
  - concept_id: concept-a
    mastery: 4.5
    confidence: 6
    common_error_types:
      - boundary-failure
      - transfer-failure

tutor_preferences:
  max_probe_rounds_before_hint: 2
  preferred_pacing: slow | medium | fast
```

---

## 4. Domain Model

Learning Tutor 不能把主题只当一句字符串来处理，必须把主题拆成“可诊断、可教学、可评估”的最小单元。

### 推荐拆法

每个主题拆成三类节点：

1. `concept`：概念本体。
2. `relation`：概念之间的因果、依赖、边界、对比。
3. `skill`：解释、比较、应用、迁移、批判等能力。

### 示例

```yaml
concepts:
  - id: subjective-value
    label: 主观价值
    prerequisites: []

relations:
  - id: value-price-relation
    label: 价值与价格的关系
    depends_on:
      - subjective-value

skills:
  - id: explain-subjective-value
    label: 用人话解释主观价值
    depends_on:
      - subjective-value

  - id: apply-value-price-relation
    label: 在市场案例中分析价值与价格关系
    depends_on:
      - subjective-value
      - value-price-relation
```

### 这层的作用

1. 知道当前该教哪个点。
2. 知道某个点卡住时缺的是前置还是迁移。
3. 知道复习时先抽查哪个点最划算。

---

## 5. Intervention Engine

这是 Learning Tutor 最关键的差异化模块。

### 作用

根据学习者回答，判断错误类型，并选择下一步教学动作。

### 错误类型体系

建议使用以下统一 taxonomy：

| error_type | 含义 | 典型表现 |
|-----------|------|---------|
| `concept-confusion` | 概念混淆 | 把 A 说成 B |
| `definition-gap` | 定义缺口 | 知道感觉，不知道关键条件 |
| `boundary-failure` | 边界失真 | 换极端情况就崩 |
| `causal-break` | 因果链断裂 | 只能背结论，解释不出因果 |
| `retrieval-failure` | 提取失败 | 学过但一时想不起来 |
| `transfer-failure` | 迁移失败 | 熟题会，新场景不会 |
| `expression-failure` | 表达失败 | 似懂非懂，说不清 |
| `overconfidence-risk` | 认知高估 | 自评分明显高于表现 |

### 教学动作库

| action | 用途 |
|-------|------|
| `probe` | 继续追问，查清楚到底会不会 |
| `hint` | 给低强度提示，帮用户提取已有知识 |
| `contrast` | 用相邻概念对比澄清混淆 |
| `counterexample` | 用反例击穿错误解释 |
| `reframe` | 换一种讲法或比喻 |
| `simplify` | 降低任务颗粒度 |
| `escalate` | 连续表现稳定时提升难度 |
| `remediate` | 对稳定误解进入纠偏模式 |

### 基本决策规则

1. 回答方向对但细节空，优先 `probe` 或 `hint`。
2. 概念经常混，优先 `contrast`。
3. 因果链错了，优先 `counterexample`。
4. 连续两轮回答失败，优先 `simplify`。
5. 连续两轮稳定正确，触发 `escalate`。
6. 同一误解多次出现，触发 `remediate`。

---

## 6. Assessment Engine

Assessment Engine 不只在 session 末尾打分，而是在互动中不断写入 evidence。

### 评估对象

1. 概念理解。
2. 关系理解。
3. 检索能力。
4. 迁移能力。
5. 元认知准确度。

### 最小证据结构

```yaml
evidence:
  - timestamp: 2026-03-11T10:00:00
    concept_id: concept-a
    skill_id: explain-concept-a
    prompt_type: explain
    observed_error_type: definition-gap
    intervention: hint
    outcome: improved
    confidence_shift: +1
    mastery_delta: +0.5
```

### 评估输出

Assessment Engine 应产出三类结果：

1. 当前会话表现摘要。
2. concept 级 mastery 更新。
3. 下一步建议动作。

---

## 7. Review Planner

Learning Tutor 不只做复习排期，还要做复习内容排序。

### 复习优先级

$$
priority = forgetting\_risk + misconception\_severity + transfer\_weakness
$$

### 含义

1. `forgetting_risk`：多久没碰 + 历史遗忘速度。
2. `misconception_severity`：误解是否高频复发。
3. `transfer_weakness`：是否只能做熟题。

这样复习时，优先打最脆弱的知识点，而不是平均分配时间。

---

## 推荐工作模式

Learning Tutor 建议至少支持 5 种 tutor mode：

| mode | 作用 | 典型触发 |
|------|------|---------|
| `diagnose` | 初始摸底 | 新主题、首次进入 |
| `teach` | 概念讲解与澄清 | 用户对核心概念陌生 |
| `drill` | 检索和巩固 | 概念基本会，但提取不稳 |
| `remediate` | 纠偏误解 | 稳定错误反复出现 |
| `review` | 复习维护 | 已掌握后进入保持模式 |

mode 不由用户手动指定，而由系统根据表现动态切换。

---

## 会话协议

Learning Tutor 更适合“回合式协议”，而不是固定大步骤协议。

### 一个标准 tutor 回合应包含

1. 当前聚焦点：现在在学哪个 concept 或 skill。
2. 当前动作：现在是在问、讲、提示、纠偏还是迁移。
3. 用户回应。
4. 系统分类：识别错误类型或正确类型。
5. 下一个教学动作。
6. 证据落盘。

### 标准循环

```text
选择焦点
  -> 发起教学动作
  -> 收集用户回答
  -> 分类错误/表现
  -> 选择下一动作
  -> 写 evidence
  -> 判断是否切换 concept 或 mode
```

---

## 文件结构建议

建议独立使用自己的 session 空间，而不是直接复用 learning-loop 的目录，以避免协议互相污染。

```text
learning/tutor-sessions/{slug}/
├── meta.md
├── journal.md
├── domain-model.md
├── learner-model.md
├── misconceptions.md
├── tutor-preferences.md
└── sessions/
    ├── session1/
    │   ├── plan.md
    │   ├── transcript.md
    │   ├── evidence.md
    │   └── assessment.md
    └── ...
```

### 设计理由

1. Learning Loop 以 cycle 为核心，因此使用 `cycles/`。
2. Learning Tutor 以 tutor session 为核心，因此更适合 `sessions/`。
3. 这样能天然区分“流程学习记录”和“导师互动记录”。

---

## 核心文件说明

### `meta.md`

记录全局状态：

```yaml
topic: "主题"
slug: "topic-slug"
started_at: "2026-03-11"
last_active: "2026-03-11"
current_mode: diagnose
current_focus:
  concept_ids:
    - concept-a
overall_mastery: 3.5
review_state:
  efactor: 2.5
  next_review: ""
  review_count: 0
```

### `domain-model.md`

记录该主题的概念图谱、关系和技能节点。

### `learner-model.md`

记录学习者对各 concept 的掌握度、信心、常见错误。

### `misconceptions.md`

记录稳定误解及其修复状态。

### `tutor-preferences.md`

记录长期有效的教学偏好。

### `sessions/sessionN/plan.md`

定义本次 session 的目标、焦点和退出条件。

### `sessions/sessionN/transcript.md`

记录关键回合摘要，而不是机械记录全文。

### `sessions/sessionN/evidence.md`

记录本次 session 中的关键证据。

### `sessions/sessionN/assessment.md`

输出本次 session 的掌握更新、误解变化和下次建议。

---

## 新 skill 的命令心智

Learning Tutor 不建议继续沿用 `cycle=N` 这种强流程参数，而建议采用更贴近 tutor 行为的参数。

示例：

```text
/learning-tutor topic="主题" [action=start|resume|review|focus] [focus="concept-id"]
```

### 参数建议

| 参数 | 作用 |
|------|------|
| `topic` | 学习主题 |
| `action=start` | 启动新主题 tutor session |
| `action=resume` | 继续上次 tutor session |
| `action=review` | 进入复习模式 |
| `action=focus` | 针对某个 concept 做专项纠偏 |
| `focus` | 指定 concept 或 skill |

这个设计更符合 tutor 心智，因为用户真正关心的是“继续教我”“复习一下”“我就卡在这个点”，不是“从第几轮开始”。

---

## 最小可实施版本

如果现在就要开工，不要一次把所有层都做满。建议按 MVP 路线走。

### MVP-1

先实现三件事：

1. Learner Model。
2. Error Type + Intervention Engine。
3. Evidence Logging。

做到这一步，Learning Tutor 就已经和 Learning Loop 拉开本质差异。

### MVP-2

再补：

1. Domain Model。
2. Misconception Registry。
3. Review Planner。

### MVP-3

最后补：

1. Tutor preference adaptation。
2. concept 级复习排序。
3. 更细的 mode 切换规则。

---

## 成功标准

Learning Tutor 设计是否成功，可以看 5 个信号：

1. 课程文字减少了，但单次互动更深了。
2. 用户更容易说出“我错在这里”，而不是“我大概懂了”。
3. 同一误解能被系统持续追踪，而不是每次重新发现。
4. 下次继续时，tutor 明显更像认识这个人，而不是重新开场。
5. 复习时系统优先抽查脆弱点，而不是随机复习。

---

## 与后续文件的关系

这份架构文档是 `learning-tutor` 的顶层蓝图。基于它，后续至少应继续补三类文件：

1. `SKILL.md`：定义 skill 触发、边界、交互协议、默认执行方式。
2. `references/session-schema.md`：定义 session 文件结构和字段。
3. `references/tutor-loop.md`：定义回合级 tutor 行为规则。

推荐实现顺序：

1. 先写 `SKILL.md`，把产品边界锁死。
2. 再写 `session-schema.md`，把记忆层协议锁死。
3. 最后写 `tutor-loop.md`，把回合级行为锁死。