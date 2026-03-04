#!/usr/bin/env python3
"""
init_session.py — Learning SOP session manager (adaptive cycle version)

Usage:
    python3 init_session.py --topic "主题名" [--slug "slug"] \
        --sessions-dir learning/sessions --action init|status

Output (JSON to stdout):
{
  "exists": bool,
  "slug": str,
  "topic": str,
  "session_dir": str,
  "current_cycle": int,
  "knowledge_level": int,
  "mode": str,
  "efactor": float,
  "next_review": str,
  "review_count": int,
  "total_cycles_completed": int,
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

META_TEMPLATE = """\
---
topic: "{topic}"
slug: "{slug}"
started_at: "{today}"
last_active: "{today}"
current_cycle: 1
knowledge_level: 0
mode: learning
efactor: 2.5
next_review: ""
review_count: 0
total_cycles_completed: 0
---
"""

JOURNAL_TEMPLATE = """\
# 学习日志 · {topic}

<!-- 用户自由记录区 + AI 在每轮结束后追加摘要（只追加，不覆盖） -->
"""


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
            if val.startswith("[") and val.endswith("]"):
                inner = val[1:-1].strip()
                fm[key] = [int(x.strip()) for x in inner.split(",") if x.strip()] if inner else []
            elif val.replace(".", "", 1).lstrip("-").isdigit():
                fm[key] = float(val) if "." in val else int(val)
            else:
                fm[key] = val.strip('"')
    return fm


def init_session(slug: str, topic: str, sessions_dir: Path) -> dict:
    """Create session dir and files if not exist. Return status dict."""
    session_dir = sessions_dir / slug
    exists_before = session_dir.exists()

    if not exists_before:
        session_dir.mkdir(parents=True, exist_ok=True)
        today = date.today().isoformat()
        meta_content = META_TEMPLATE.format(topic=topic, slug=slug, today=today)
        (session_dir / "meta.md").write_text(meta_content, encoding="utf-8")
        (session_dir / "journal.md").write_text(
            JOURNAL_TEMPLATE.format(topic=topic), encoding="utf-8"
        )
        # cycles/ dir will be created on demand by the AI when writing cycle files

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

    # Detect how many cycles exist on disk
    cycles_dir = session_dir / "cycles"
    completed_cycles = 0
    if cycles_dir.exists():
        completed_cycles = sum(
            1 for d in cycles_dir.iterdir()
            if d.is_dir() and (d / "assessment.md").exists()
        )

    return {
        "exists": True,
        "slug": slug,
        "topic": fm.get("topic", slug),
        "session_dir": str(session_dir),
        "current_cycle": fm.get("current_cycle", 1),
        "knowledge_level": fm.get("knowledge_level", 0),
        "mode": fm.get("mode", "learning"),
        "efactor": fm.get("efactor", 2.5),
        "next_review": fm.get("next_review", ""),
        "review_count": fm.get("review_count", 0),
        "total_cycles_completed": fm.get("total_cycles_completed", completed_cycles),
        "last_active": fm.get("last_active", ""),
    }


def print_status_summary(status: dict):
    """Print a human-readable status summary."""
    if not status.get("exists"):
        print(f"Session '{status['slug']}' not found.")
        return

    mode = status.get("mode", "learning")
    print(f"\n{'='*50}")
    print(f"  主题：{status['topic']}")
    print(f"  Slug：{status['slug']}")
    print(f"  知识水平：{status['knowledge_level']}/10")
    print(f"  当前轮次：Cycle {status['current_cycle']}")
    print(f"  已完成轮次：{status['total_cycles_completed']}")
    print(f"  模式：{'学习中' if mode == 'learning' else '复习维护'}")
    if mode == "review":
        print(f"  E-Factor：{status['efactor']}")
        print(f"  下次复习：{status['next_review'] or '未设定'}")
        print(f"  已复习次数：{status['review_count']}")
    print(f"  最后活跃：{status['last_active']}")
    print(f"{'='*50}\n")


def slugify(text: str) -> str:
    """Convert topic string to a URL-safe slug."""
    slug = text.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = slug.strip("-")
    return slug or "topic"


def main():
    parser = argparse.ArgumentParser(description="Learning SOP session manager")
    parser.add_argument("slug", nargs="?", help="Session slug (positional, optional)")
    parser.add_argument("--topic", help="Topic name (auto-generates slug if not given)")
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

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.is_absolute():
        sessions_dir = Path.cwd() / sessions_dir

    if args.action == "init":
        result = init_session(slug, topic, sessions_dir)
    else:
        result = read_status(slug, sessions_dir)

    if args.action == "status":
        print_status_summary(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
