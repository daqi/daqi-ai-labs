# Learning Tutor Session Schema

## 目录结构

Learning Tutor 使用独立的 session 空间：

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

设计原则：

1. topic 级长期记忆和单次 tutor session 记录分开。
2. 记录“这个人如何学习”，不只记录“这个主题讲了什么”。
3. 每次会话都要能独立复盘，也要能汇入长期 learner model。

---

## 初始化脚本

优先使用 `skills/learning-tutor/scripts/init_session.py` 进行 session 初始化和状态读取。

### 初始化 topic session

```bash
python3 skills/learning-tutor/scripts/init_session.py \
  --topic "主题" [--slug "topic-slug"] \
  --sessions-dir learning/tutor-sessions \
  --action init
```

### 创建新的 tutor session

```bash
python3 skills/learning-tutor/scripts/init_session.py \
  --topic "主题" [--slug "topic-slug"] \
  --sessions-dir learning/tutor-sessions \
  --action start-session \
  --mode teach
```

### 查看状态

```bash
python3 skills/learning-tutor/scripts/init_session.py \
  --topic "主题" [--slug "topic-slug"] \
  --sessions-dir learning/tutor-sessions \
  --action status
```

脚本职责：

1. 保证 topic 级目录存在。
2. 在缺失时创建顶层文件。
3. 按需创建新的 `sessionN/` 目录和四个基础文件。
4. 返回当前状态摘要，供 tutor 调度使用。

### 更新回合和会话状态

```bash
python3 skills/learning-tutor/scripts/update_session.py \
  --topic "主题" [--slug "topic-slug"] \
  --sessions-dir learning/tutor-sessions \
  --action append-round|finalize-session \
  --payload-file /tmp/learning-tutor-payload.json
```

脚本职责：

1. 追加 `transcript.md` 回合摘要。
2. 追加 `evidence.md` 证据条目。
3. 写入 `assessment.md` 会话总结。
4. 更新 `learner-model.md`、`misconceptions.md` 和 `journal.md`。
5. 更新 `meta.md` 中的 mode、focus、overall mastery、review state。

### Payload 模板

优先复用以下模板，而不是临时手写字段名：

1. `assets/payload-templates/append-round.json`
2. `assets/payload-templates/finalize-session.json`

使用方式：

1. 复制模板到临时文件。
2. 只替换本次 session 相关字段。
3. 再把该文件传给 `update_session.py --payload-file`。

---

## 顶层文件

### `meta.md`

记录全局状态和调度所需最小信息。

建议 frontmatter：

```yaml
---
topic: "主题"
slug: "topic-slug"
started_at: "2026-03-11"
last_active: "2026-03-11T10:00:00"
current_mode: diagnose
current_focus:
  concept_ids:
    - concept-a
  skill_ids: []
overall_mastery: 3.5
active_session: 1
review_state:
  efactor: 2.5
  next_review: ""
  review_count: 0
---
```

字段说明：

| 字段 | 说明 |
|------|------|
| `topic` | 用户原始主题 |
| `slug` | 目录名 |
| `started_at` | 首次开始时间 |
| `last_active` | 最近活跃时间 |
| `current_mode` | 当前 tutor mode |
| `current_focus` | 当前聚焦的 concept 和 skill |
| `overall_mastery` | 主题总体掌握度，0-10 可用小数 |
| `active_session` | 当前或最近一次 session 编号 |
| `review_state` | 复习状态与排期 |

### `journal.md`

追加式日志，记录每次 session 的摘要，不覆盖用户内容。

推荐格式：

```markdown
## Session 3 摘要（2026-03-11）
- 当前模式：remediate
- 当前焦点：concept-a
- 关键进展：用户已经区分 A 和 B
- 残留问题：边界条件仍不稳
- 下次建议：用新场景做一次迁移检测
```

### `domain-model.md`

记录主题知识图谱。用于回答：当前 topic 由哪些 concept、relation、skill 组成。

建议格式：

```yaml
concepts:
  - id: concept-a
    label: 核心概念 A
    prerequisites: []
    related_relations:
      - relation-a-b

relations:
  - id: relation-a-b
    label: A 与 B 的关系
    depends_on:
      - concept-a
      - concept-b

skills:
  - id: explain-a
    label: 用人话解释 A
    depends_on:
      - concept-a
```

### `learner-model.md`

记录学习者在各 concept 上的掌握情况。

如果由脚本维护，允许写成“Markdown 说明 + JSON code block”的机器可写格式；手工调整时优先修改 JSON 块。

建议格式：

```yaml
learner_profile:
  motivation: "为什么学"
  application_context: "要用在哪"
  target_depth: intro | practical | deep
  self_calibration_bias: overconfident | balanced | underconfident

concept_mastery:
  - concept_id: concept-a
    mastery: 4.5
    confidence: 6
    last_touched_at: 2026-03-11T10:00:00
    evidence_count: 3
    common_error_types:
      - concept-confusion
      - transfer-failure
    misconception_ids:
      - m-001
```

### `misconceptions.md`

记录稳定误解及其修复状态。

如果由脚本维护，允许写成“Markdown 说明 + JSON code block”的机器可写格式；手工调整时优先修改 JSON 块。

建议格式：

```yaml
misconceptions:
  - id: m-001
    statement: "把 A 理解成 B"
    concept_ids:
      - concept-a
    first_seen_session: 1
    last_seen_session: 3
    severity: high
    status: active
    recommended_actions:
      - contrast
      - counterexample
```

状态建议：

1. `active`：当前仍在复发。
2. `watch`：近期未复发，但仍需抽查。
3. `resolved`：连续多次未复发，可降级。

### `tutor-preferences.md`

记录长期有效的教学偏好。

建议格式：

```yaml
tutor_preferences:
  preferred_explanation_style:
    - analogy
    - example-first
  preferred_pacing: medium
  max_probe_rounds_before_hint: 2
  notes:
    - "先追问两轮再提示效果最好"
    - "遇到抽象概念时先用真实案例"
```

---

## 单次 Session 文件

每个 tutor session 在 `sessions/sessionN/` 下有 4 个文件。

### `plan.md`

记录本次会话目标、焦点和退出条件。

模板建议：

```markdown
## Session Plan

- mode: teach
- focus concepts:
  - concept-a
- target skill:
  - explain-a
- exit criteria:
  - 用户能用自己的话准确解释 A
  - 用户能区分 A 与 B
```

### `transcript.md`

记录关键回合摘要，而不是逐字全文。

模板建议：

```markdown
## Round 1
- action: probe
- prompt_summary: 让用户解释 concept-a
- user_response_summary: 能说出表层定义，但把 A 和 B 混了
- next_action: contrast
```

### `evidence.md`

记录最小证据单元。

模板建议：

```yaml
evidence:
  - timestamp: 2026-03-11T10:00:00
    concept_id: concept-a
    skill_id: explain-a
    prompt_type: explain
    observed_error_type: concept-confusion
    intervention: contrast
    outcome: improved
    confidence_shift: +1
    mastery_delta: +0.5
```

字段说明：

| 字段 | 说明 |
|------|------|
| `prompt_type` | 本次动作类型，如 explain / probe / practice / transfer |
| `observed_error_type` | 识别到的错误类型 |
| `intervention` | 使用的教学动作 |
| `outcome` | improved / unchanged / unresolved |
| `confidence_shift` | 学习者自信变化 |
| `mastery_delta` | 本次证据带来的掌握度变化 |

### `assessment.md`

记录本次会话总结。

模板建议：

```markdown
## Session Assessment

- mode: remediate
- focus: concept-a
- mastery change: 3.5 -> 4.5
- resolved misconceptions:
  - m-001
- active misconceptions:
  - m-002
- next recommended action: transfer-check
- next recommended mode: drill
```

---

## 更新时机

### 会话开始前

更新：

1. `meta.md` 的 `current_mode`、`current_focus`、`active_session`
2. 新建 `sessionN/plan.md`

### 每个关键回合后

更新：

1. `sessionN/transcript.md`
2. `sessionN/evidence.md`

### 会话结束后

更新：

1. `sessionN/assessment.md`
2. `learner-model.md`
3. `misconceptions.md`
4. `meta.md`
5. `journal.md`

---

## 命名规则

- `slug` 尽量短、可读、可复用。
- session 使用连续编号：`session1`、`session2`、`session3`。
- 不要覆盖历史 session，只追加新的 session 目录。

---

## 设计约束

1. 一次会话只追少量焦点，不做全主题铺开。
2. 所有掌握度变化都尽量有 evidence 来源。
3. 稳定误解必须单独记录，不能藏在普通总结里。
4. transcript 用摘要，不用逐字堆砌对话。