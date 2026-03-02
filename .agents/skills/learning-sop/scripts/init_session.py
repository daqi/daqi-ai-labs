#!/usr/bin/env python3
"""
init_session.py — Learning SOP session manager

Usage:
    python3 init_session.py <slug> [--sessions-dir <path>] [--action <init|status>]

Actions:
    init    Create session folder if not exists; print status JSON
    status  Read and print session status JSON (error if not exists)

Output (JSON to stdout):
{
  "exists": bool,
  "slug": str,
  "topic": str,
  "session_dir": str,
  "current_phase": int,
  "completed_phases": [int],
  "knowledge_level": int,
  "next_review": str,
  "total_sessions": int,
  "last_active": str
}
"""

import argparse
import json
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path


DEFAULT_SESSIONS_DIR = "learning/sessions"

PHASE_FILES = [
    "phase1-topology.md",
    "phase2-feynman.md",
    "phase3-quiz.md",
    "phase4-transfer.md",
    "phase5-calibration.md",
    "journal.md",
]

META_TEMPLATE = """\
---
topic: "{topic}"
slug: "{slug}"
started_at: "{today}"
last_active: "{today}"
completed_phases: []
current_phase: 1
total_sessions: 0
knowledge_level: 0
next_review: ""
review_count: 0
---
"""

PHASE_TEMPLATES = {
    "phase1-topology.md": """\
# 知识拓扑 · {topic}

<!-- Phase 1 每次学习后由 AI 追加一个 Session 块 -->
""",
    "phase2-feynman.md": """\
# 费曼压缩记录 · {topic}

<!-- Phase 2 每次学习后由 AI 追加摘要：暴露的漏洞 + 追问路径 -->
""",
    "phase3-quiz.md": """\
# 检索强化记录 · {topic}

<!-- Phase 3 每次学习后由 AI 追加：题目/答案/得分/错误分析/下次复习时间 -->
""",
    "phase4-transfer.md": """\
# 跨域迁移记录 · {topic}

<!-- Phase 4 每次学习后由 AI 追加：映射目标领域 + 迁移案例摘要 -->
""",
    "phase5-calibration.md": """\
# 元认知校准记录 · {topic}

<!-- Phase 5 每次学习后由 AI 追加：自评分/能否教别人/最不确定点/认知错觉概率 -->
""",
    "journal.md": """\
# 学习日志 · {topic}

<!-- 用户自由记录 + AI 在每次完整流程结束后追加关键节点摘要 -->
""",
}


def parse_frontmatter(text: str) -> dict:
    """Parse YAML-like frontmatter from markdown."""
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    fm = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip()
            # parse lists like [1, 2]
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [int(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
            elif val.isdigit():
                fm[key] = int(val)
            else:
                fm[key] = val.strip('"')
    return fm


def init_session(slug: str, topic: str, sessions_dir: Path) -> dict:
    """Create session dir and files if not exist. Return status dict."""
    session_dir = sessions_dir / slug
    exists_before = session_dir.exists()

    if not exists_before:
        session_dir.mkdir(parents=True, exist_ok=True)
        # Write meta.md
        today = date.today().isoformat()
        meta_content = META_TEMPLATE.format(topic=topic, slug=slug, today=today)
        (session_dir / "meta.md").write_text(meta_content, encoding="utf-8")
        # Write phase files
        for fname, template in PHASE_TEMPLATES.items():
            (session_dir / fname).write_text(template.format(topic=topic), encoding="utf-8")

    return read_status(slug, sessions_dir)


def read_status(slug: str, sessions_dir: Path) -> dict:
    """Read session meta.md and return status dict."""
    session_dir = sessions_dir / slug
    meta_path = session_dir / "meta.md"

    if not meta_path.exists():
        return {
            "exists": False,
            "slug": slug,
            "session_dir": str(session_dir),
            "error": "Session not found. Run with --action init to create.",
        }

    text = meta_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(text)

    return {
        "exists": True,
        "slug": slug,
        "topic": fm.get("topic", slug),
        "session_dir": str(session_dir),
        "current_phase": fm.get("current_phase", 1),
        "completed_phases": fm.get("completed_phases", []),
        "knowledge_level": fm.get("knowledge_level", 0),
        "next_review": fm.get("next_review", ""),
        "total_sessions": fm.get("total_sessions", 0),
        "last_active": fm.get("last_active", ""),
        "review_count": fm.get("review_count", 0),
    }


def slugify(text: str) -> str:
    """Convert topic string to a URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "topic"


def main():
    parser = argparse.ArgumentParser(description="Learning SOP session manager")
    parser.add_argument("slug", nargs="?", help="Session slug (or omit and use --topic/--slug)")
    parser.add_argument("--topic", help="Topic name (auto-generates slug if slug not given)")
    parser.add_argument("--slug", dest="slug_opt", help="Explicit slug override")
    parser.add_argument("--sessions-dir", default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--action", choices=["init", "status"], default="init")
    args = parser.parse_args()

    # Resolve slug and topic
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

    # Resolve sessions directory relative to cwd or absolute
    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.is_absolute():
        sessions_dir = Path.cwd() / sessions_dir

    if args.action == "init":
        result = init_session(slug, topic, sessions_dir)
    else:
        result = read_status(slug, sessions_dir)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
