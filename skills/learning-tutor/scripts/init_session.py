#!/usr/bin/env python3
"""Session bootstrapper for the learning-tutor skill.

Usage:
    python3 skills/learning-tutor/scripts/init_session.py \
        --topic "主题" [--slug "slug"] \
        --sessions-dir learning/tutor-sessions \
        --action init|status|start-session \
        [--mode diagnose|teach|drill|remediate|review]

The script creates the topic-level tutor session directory and, when asked,
creates a new sessionN scaffold with plan/transcript/evidence/assessment files.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path


DEFAULT_SESSIONS_DIR = "learning/tutor-sessions"
VALID_MODES = {"diagnose", "teach", "drill", "remediate", "review"}

META_TEMPLATE = """\
---
topic: "{topic}"
slug: "{slug}"
started_at: "{timestamp}"
last_active: "{timestamp}"
current_mode: diagnose
current_focus:
  concept_ids: []
  skill_ids: []
overall_mastery: 0.0
active_session: 0
review_state:
  efactor: 2.5
  next_review: ""
  review_count: 0
---
"""

JOURNAL_TEMPLATE = """\
# Tutor Journal · {topic}

<!-- 用户自由记录区 + AI 在每次 session 结束后追加摘要（只追加，不覆盖） -->
"""

DOMAIN_MODEL_TEMPLATE = """\
concepts: []
relations: []
skills: []
"""

LEARNER_MODEL_TEMPLATE = """\
learner_profile:
  motivation: ""
  application_context: ""
  target_depth: intro
  self_calibration_bias: balanced

concept_mastery: []
"""

MISCONCEPTIONS_TEMPLATE = """\
misconceptions: []
"""

TUTOR_PREFERENCES_TEMPLATE = """\
tutor_preferences:
  preferred_explanation_style: []
  preferred_pacing: medium
  max_probe_rounds_before_hint: 2
  notes: []
"""

PLAN_TEMPLATE = """\
## Session Plan

- mode: {mode}
- focus concepts:
  - 
- target skill:
  - 
- exit criteria:
  - 
"""

TRANSCRIPT_TEMPLATE = """\
## Session Transcript Summary

<!-- 按回合追加摘要，不要逐字粘贴完整对话 -->
"""

EVIDENCE_TEMPLATE = """\
evidence: []
"""

ASSESSMENT_TEMPLATE = """\
## Session Assessment

- mode: {mode}
- focus:
  - 
- mastery change: 0.0 -> 0.0
- resolved misconceptions: []
- active misconceptions: []
- next recommended action: 
- next recommended mode: 
"""


def now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "topic"


def parse_frontmatter(text: str) -> dict:
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}

    lines = match.group(1).splitlines()
    data = {}
    current_key = None

    for raw_line in lines:
        if not raw_line.strip():
            continue
        if raw_line.startswith("  ") and current_key:
            nested = data.get(current_key)
            if not isinstance(nested, dict):
                nested = {}
                data[current_key] = nested
            nested_line = raw_line.strip()
            if ":" in nested_line:
                key, _, val = nested_line.partition(":")
                nested[key.strip()] = parse_scalar(val.strip())
            continue
        if ":" in raw_line:
            key, _, val = raw_line.partition(":")
            current_key = key.strip()
            stripped = val.strip()
            data[current_key] = {} if stripped == "" else parse_scalar(stripped)
    return data


def render_meta(meta: dict) -> str:
    current_focus = meta.get("current_focus", {}) or {}
    review_state = meta.get("review_state", {}) or {}

    return "\n".join(
        [
            "---",
            f'topic: "{meta.get("topic", "")}"',
            f'slug: "{meta.get("slug", "")}"',
            f'started_at: "{meta.get("started_at", "")}"',
            f'last_active: "{meta.get("last_active", "")}"',
            f'current_mode: {meta.get("current_mode", "diagnose")}',
            "current_focus:",
            f'  concept_ids: {json.dumps(current_focus.get("concept_ids", []), ensure_ascii=False)}',
            f'  skill_ids: {json.dumps(current_focus.get("skill_ids", []), ensure_ascii=False)}',
            f'overall_mastery: {meta.get("overall_mastery", 0.0)}',
            f'active_session: {meta.get("active_session", 0)}',
            "review_state:",
            f'  efactor: {review_state.get("efactor", 2.5)}',
            f'  next_review: "{review_state.get("next_review", "")}"',
            f'  review_count: {review_state.get("review_count", 0)}',
            "---",
            "",
        ]
    )


def parse_scalar(value: str):
    if value == "":
        return ""
    if value == "[]":
        return []
    if (value.startswith("[") and value.endswith("]")) or (value.startswith("{") and value.endswith("}")):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in {"true", "false"}:
        return value == "true"
    if value.replace(".", "", 1).lstrip("-").isdigit():
        return float(value) if "." in value else int(value)
    return value


def write_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def ensure_topic_session(slug: str, topic: str, sessions_dir: Path) -> Path:
    session_root = sessions_dir / slug
    session_root.mkdir(parents=True, exist_ok=True)

    timestamp = now_iso()
    write_if_missing(session_root / "meta.md", META_TEMPLATE.format(topic=topic, slug=slug, timestamp=timestamp))
    write_if_missing(session_root / "journal.md", JOURNAL_TEMPLATE.format(topic=topic))
    write_if_missing(session_root / "domain-model.md", DOMAIN_MODEL_TEMPLATE)
    write_if_missing(session_root / "learner-model.md", LEARNER_MODEL_TEMPLATE)
    write_if_missing(session_root / "misconceptions.md", MISCONCEPTIONS_TEMPLATE)
    write_if_missing(session_root / "tutor-preferences.md", TUTOR_PREFERENCES_TEMPLATE)
    (session_root / "sessions").mkdir(exist_ok=True)
    return session_root


def next_session_number(session_root: Path) -> int:
    sessions_dir = session_root / "sessions"
    max_number = 0
    for child in sessions_dir.iterdir():
        if child.is_dir() and child.name.startswith("session"):
            suffix = child.name.replace("session", "", 1)
            if suffix.isdigit():
                max_number = max(max_number, int(suffix))
    return max_number + 1


def update_meta(session_root: Path, *, mode: str | None = None, active_session: int | None = None) -> dict:
    meta_path = session_root / "meta.md"
    text = meta_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)
    fm["topic"] = fm.get("topic", session_root.name)
    fm["slug"] = fm.get("slug", session_root.name)
    fm["started_at"] = fm.get("started_at", now_iso())
    fm["last_active"] = now_iso()
    fm["current_mode"] = mode or fm.get("current_mode", "diagnose")
    fm["active_session"] = active_session if active_session is not None else fm.get("active_session", 0)
    fm["overall_mastery"] = fm.get("overall_mastery", 0.0)
    fm["current_focus"] = fm.get("current_focus", {}) or {"concept_ids": [], "skill_ids": []}
    fm["review_state"] = fm.get("review_state", {}) or {"efactor": 2.5, "next_review": "", "review_count": 0}

    new_text = render_meta(fm)
    meta_path.write_text(new_text, encoding="utf-8")
    return parse_frontmatter(new_text)


def create_session_scaffold(session_root: Path, mode: str) -> Path:
    session_number = next_session_number(session_root)
    session_dir = session_root / "sessions" / f"session{session_number}"
    session_dir.mkdir(parents=True, exist_ok=False)
    (session_dir / "plan.md").write_text(PLAN_TEMPLATE.format(mode=mode), encoding="utf-8")
    (session_dir / "transcript.md").write_text(TRANSCRIPT_TEMPLATE, encoding="utf-8")
    (session_dir / "evidence.md").write_text(EVIDENCE_TEMPLATE, encoding="utf-8")
    (session_dir / "assessment.md").write_text(ASSESSMENT_TEMPLATE.format(mode=mode), encoding="utf-8")
    update_meta(session_root, mode=mode, active_session=session_number)
    return session_dir


def read_status(session_root: Path) -> dict:
    meta_path = session_root / "meta.md"
    fm = parse_frontmatter(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    sessions_dir = session_root / "sessions"
    session_count = 0
    if sessions_dir.exists():
        session_count = sum(1 for child in sessions_dir.iterdir() if child.is_dir() and child.name.startswith("session"))

    return {
        "exists": meta_path.exists(),
        "topic": fm.get("topic", session_root.name),
        "slug": fm.get("slug", session_root.name),
        "session_dir": str(session_root),
        "current_mode": fm.get("current_mode", "diagnose"),
        "overall_mastery": fm.get("overall_mastery", 0.0),
        "active_session": fm.get("active_session", 0),
        "session_count": session_count,
        "last_active": fm.get("last_active", ""),
        "review_state": fm.get("review_state", {}),
    }


def print_status_summary(status: dict) -> None:
    if not status.get("exists"):
        print("Tutor session not found.")
        return

    print(f"\n{'=' * 50}")
    print(f"  主题：{status['topic']}")
    print(f"  Slug：{status['slug']}")
    print(f"  当前模式：{status['current_mode']}")
    print(f"  总体掌握度：{status['overall_mastery']}/10")
    print(f"  当前会话：Session {status['active_session']}")
    print(f"  已创建会话数：{status['session_count']}")
    print(f"  最后活跃：{status['last_active']}")
    print(f"{'=' * 50}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Learning Tutor session manager")
    parser.add_argument("slug", nargs="?", help="Session slug")
    parser.add_argument("--topic", help="Topic name")
    parser.add_argument("--slug", dest="slug_opt", help="Explicit slug override")
    parser.add_argument("--sessions-dir", default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--action", choices=["init", "status", "start-session"], default="init")
    parser.add_argument("--mode", default="diagnose", help="Tutor mode for start-session")
    args = parser.parse_args()

    if args.slug_opt:
        slug = args.slug_opt
        topic = args.topic or slug
    elif args.slug:
        slug = args.slug
        topic = args.topic or slug
    elif args.topic:
        slug = slugify(args.topic)
        topic = args.topic
    else:
        parser.error("Provide slug positional arg, --slug, or --topic")

    mode = args.mode.strip()
    if mode not in VALID_MODES:
        parser.error(f"Invalid --mode '{mode}'. Choose from: {', '.join(sorted(VALID_MODES))}")

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.is_absolute():
        sessions_dir = Path.cwd() / sessions_dir

    session_root = ensure_topic_session(slug, topic, sessions_dir)

    if args.action == "start-session":
        session_dir = create_session_scaffold(session_root, mode)
        result = read_status(session_root)
        result["created_session"] = session_dir.name
    else:
        result = read_status(session_root)

    if args.action == "status":
        print_status_summary(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()