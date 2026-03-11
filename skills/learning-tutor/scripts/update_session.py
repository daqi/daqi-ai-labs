#!/usr/bin/env python3
"""Update round-level and session-level records for the learning-tutor skill.

Usage:
    python3 skills/learning-tutor/scripts/update_session.py \
        --topic "主题" [--slug "slug"] \
        --sessions-dir learning/tutor-sessions \
        --action append-round|finalize-session \
        --payload-file /tmp/payload.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from init_session import (
    DEFAULT_SESSIONS_DIR,
    VALID_MODES,
    ensure_topic_session,
    now_iso,
    parse_frontmatter,
    render_meta,
    slugify,
)


DEFAULT_LEARNER_MODEL = {
    "learner_profile": {
        "motivation": "",
        "application_context": "",
        "target_depth": "intro",
        "self_calibration_bias": "balanced",
    },
    "concept_mastery": [],
}

DEFAULT_MISCONCEPTIONS = {"misconceptions": []}
DEFAULT_TUTOR_PREFERENCES = {
    "tutor_preferences": {
        "preferred_explanation_style": [],
        "preferred_pacing": "medium",
        "max_probe_rounds_before_hint": 2,
        "notes": [],
    }
}


def load_payload(args) -> dict:
    if args.payload_file:
        return json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
    if args.payload:
        return json.loads(args.payload)
    raise SystemExit("Provide --payload-file or --payload")


def resolve_session_root(args) -> tuple[str, str, Path]:
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
        raise SystemExit("Provide slug positional arg, --slug, or --topic")

    sessions_dir = Path(args.sessions_dir)
    if not sessions_dir.is_absolute():
        sessions_dir = Path.cwd() / sessions_dir
    session_root = ensure_topic_session(slug, topic, sessions_dir)
    return slug, topic, session_root


def read_meta(session_root: Path) -> dict:
    meta_path = session_root / "meta.md"
    return parse_frontmatter(meta_path.read_text(encoding="utf-8"))


def write_meta(session_root: Path, meta: dict) -> None:
    meta_path = session_root / "meta.md"
    meta.setdefault("topic", session_root.name)
    meta.setdefault("slug", session_root.name)
    meta.setdefault("started_at", now_iso())
    meta.setdefault("current_mode", "diagnose")
    meta.setdefault("current_focus", {"concept_ids": [], "skill_ids": []})
    meta.setdefault("overall_mastery", 0.0)
    meta.setdefault("active_session", 0)
    meta.setdefault("review_state", {"efactor": 2.5, "next_review": "", "review_count": 0})
    meta["last_active"] = now_iso()
    meta_path.write_text(render_meta(meta), encoding="utf-8")


def resolve_session_dir(session_root: Path, session_number: int | None) -> tuple[int, Path]:
    meta = read_meta(session_root)
    number = session_number or meta.get("active_session", 0)
    if not number:
        raise SystemExit("No active session found. Run init_session.py with --action start-session first.")
    session_dir = session_root / "sessions" / f"session{number}"
    if not session_dir.exists():
        raise SystemExit(f"Session directory not found: {session_dir}")
    return number, session_dir


def next_round_number(transcript_path: Path) -> int:
    if not transcript_path.exists():
        return 1
    text = transcript_path.read_text(encoding="utf-8")
    matches = re.findall(r"^## Round (\d+)", text, re.MULTILINE)
    return (max(int(item) for item in matches) + 1) if matches else 1


def append_markdown_block(path: Path, block: str) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    content = existing.rstrip() + "\n\n" + block.strip() + "\n"
    path.write_text(content, encoding="utf-8")


def append_evidence_yaml(path: Path, entry: dict) -> None:
    lines = [
        f'  - timestamp: "{entry.get("timestamp", now_iso())}"',
        f'    concept_id: "{entry.get("concept_id", "")}"',
        f'    skill_id: "{entry.get("skill_id", "")}"',
        f'    prompt_type: "{entry.get("prompt_type", "")}"',
        f'    observed_error_type: "{entry.get("observed_error_type", "")}"',
        f'    intervention: "{entry.get("intervention", "")}"',
        f'    outcome: "{entry.get("outcome", "")}"',
        f'    confidence_shift: {entry.get("confidence_shift", 0)}',
        f'    mastery_delta: {entry.get("mastery_delta", 0)}',
    ]
    if path.exists():
        text = path.read_text(encoding="utf-8").strip()
    else:
        text = "evidence: []"

    if text == "evidence: []":
        text = "evidence:\n"
    if not text.endswith("\n"):
        text += "\n"
    text += "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")


def load_json_block(path: Path, default: dict) -> dict:
    if not path.exists():
        return json.loads(json.dumps(default, ensure_ascii=False))
    text = path.read_text(encoding="utf-8")
    match = re.search(r"```json\n(.*?)\n```", text, re.DOTALL)
    if not match:
        return json.loads(json.dumps(default, ensure_ascii=False))
    return json.loads(match.group(1))


def write_json_block_markdown(path: Path, title: str, description: str, data: dict) -> None:
    content = "\n".join(
        [
            f"# {title}",
            "",
            description,
            "",
            "```json",
            json.dumps(data, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def merge_concept_updates(existing: list[dict], updates: list[dict]) -> list[dict]:
    by_id = {item.get("concept_id"): item for item in existing if item.get("concept_id")}
    for update in updates:
        concept_id = update.get("concept_id")
        if not concept_id:
            continue
        current = by_id.get(concept_id, {"concept_id": concept_id, "evidence_count": 0})
        current.update({k: v for k, v in update.items() if k != "evidence_count_delta"})
        current["last_touched_at"] = now_iso()
        current["evidence_count"] = current.get("evidence_count", 0) + update.get("evidence_count_delta", 0)
        by_id[concept_id] = current
    return list(by_id.values())


def merge_misconception_updates(existing: list[dict], updates: list[dict], session_number: int) -> list[dict]:
    by_id = {item.get("id"): item for item in existing if item.get("id")}
    for update in updates:
        item_id = update.get("id")
        if not item_id:
            continue
        current = by_id.get(item_id, {"id": item_id, "first_seen_session": session_number})
        current.update(update)
        current.setdefault("first_seen_session", session_number)
        current["last_seen_session"] = update.get("last_seen_session", session_number)
        by_id[item_id] = current
    return list(by_id.values())


def append_round(session_root: Path, payload: dict) -> dict:
    session_number, session_dir = resolve_session_dir(session_root, payload.get("session"))
    transcript_path = session_dir / "transcript.md"
    evidence_path = session_dir / "evidence.md"

    round_number = payload.get("round_number") or next_round_number(transcript_path)
    transcript = payload.get("transcript", {})
    evidence = payload.get("evidence", {})
    focus = payload.get("focus", {})
    mode = payload.get("mode")

    block = "\n".join(
        [
            f"## Round {round_number}",
            f'- action: {transcript.get("action", evidence.get("intervention", ""))}',
            f'- prompt_summary: {transcript.get("prompt_summary", "")}',
            f'- user_response_summary: {transcript.get("user_response_summary", "")}',
            f'- next_action: {transcript.get("next_action", "")}',
        ]
    )
    append_markdown_block(transcript_path, block)

    evidence_entry = {
        "timestamp": evidence.get("timestamp", now_iso()),
        "concept_id": evidence.get("concept_id", ""),
        "skill_id": evidence.get("skill_id", ""),
        "prompt_type": evidence.get("prompt_type", ""),
        "observed_error_type": evidence.get("observed_error_type", ""),
        "intervention": evidence.get("intervention", transcript.get("action", "")),
        "outcome": evidence.get("outcome", ""),
        "confidence_shift": evidence.get("confidence_shift", 0),
        "mastery_delta": evidence.get("mastery_delta", 0),
    }
    append_evidence_yaml(evidence_path, evidence_entry)

    meta = read_meta(session_root)
    if mode:
        meta["current_mode"] = mode
    if focus:
        meta["current_focus"] = {
            "concept_ids": focus.get("concept_ids", meta.get("current_focus", {}).get("concept_ids", [])),
            "skill_ids": focus.get("skill_ids", meta.get("current_focus", {}).get("skill_ids", [])),
        }
    meta["active_session"] = session_number
    write_meta(session_root, meta)

    return {
        "session": session_number,
        "round_number": round_number,
        "transcript_path": str(transcript_path),
        "evidence_path": str(evidence_path),
    }


def finalize_session(session_root: Path, payload: dict) -> dict:
    session_number, session_dir = resolve_session_dir(session_root, payload.get("session"))
    assessment = payload.get("assessment", {})
    journal = payload.get("journal", {})
    focus = payload.get("focus", {})
    mode = payload.get("mode", "diagnose")

    if mode not in VALID_MODES:
        raise SystemExit(f"Invalid mode '{mode}' in payload")

    assessment_text = "\n".join(
        [
            "## Session Assessment",
            "",
            f'- mode: {mode}',
            f'- focus: {", ".join(focus.get("concept_ids", [])) or assessment.get("focus", "")}',
            f'- mastery change: {assessment.get("mastery_from", 0.0)} -> {assessment.get("mastery_to", 0.0)}',
            "- resolved misconceptions:",
            *[f'  - {item}' for item in assessment.get("resolved_misconceptions", [])],
            "- active misconceptions:",
            *[f'  - {item}' for item in assessment.get("active_misconceptions", [])],
            f'- next recommended action: {assessment.get("next_recommended_action", "")}',
            f'- next recommended mode: {assessment.get("next_recommended_mode", "")}',
            *[f'- summary: {line}' for line in assessment.get("summary_lines", [])],
            "",
        ]
    )
    (session_dir / "assessment.md").write_text(assessment_text, encoding="utf-8")

    journal_block = "\n".join(
        [
            f"## Session {session_number} 摘要（{now_iso().split('T')[0]}）",
            f'- 当前模式：{mode}',
            f'- 当前焦点：{", ".join(focus.get("concept_ids", []))}',
            f'- 关键进展：{journal.get("key_progress", "")}',
            f'- 残留问题：{journal.get("remaining_issue", "")}',
            f'- 下次建议：{journal.get("next_step", assessment.get("next_recommended_action", ""))}',
        ]
    )
    append_markdown_block(session_root / "journal.md", journal_block)

    learner_model = load_json_block(session_root / "learner-model.md", DEFAULT_LEARNER_MODEL)
    if payload.get("learner_profile"):
        learner_model["learner_profile"].update(payload["learner_profile"])
    learner_model["concept_mastery"] = merge_concept_updates(
        learner_model.get("concept_mastery", []),
        payload.get("concept_updates", []),
    )
    write_json_block_markdown(
        session_root / "learner-model.md",
        "Learner Model",
        "机器可写的学习者模型状态。手工调整时，优先修改下方 JSON。",
        learner_model,
    )

    misconceptions = load_json_block(session_root / "misconceptions.md", DEFAULT_MISCONCEPTIONS)
    misconceptions["misconceptions"] = merge_misconception_updates(
        misconceptions.get("misconceptions", []),
        payload.get("misconception_updates", []),
        session_number,
    )
    write_json_block_markdown(
        session_root / "misconceptions.md",
        "Misconceptions",
        "机器可写的稳定误解状态。手工调整时，优先修改下方 JSON。",
        misconceptions,
    )

    if payload.get("tutor_preferences"):
        tutor_preferences = load_json_block(session_root / "tutor-preferences.md", DEFAULT_TUTOR_PREFERENCES)
        tutor_preferences["tutor_preferences"].update(payload["tutor_preferences"])
        write_json_block_markdown(
            session_root / "tutor-preferences.md",
            "Tutor Preferences",
            "机器可写的教学偏好状态。手工调整时，优先修改下方 JSON。",
            tutor_preferences,
        )

    meta = read_meta(session_root)
    meta["current_mode"] = assessment.get("next_recommended_mode") or mode
    meta["current_focus"] = {
        "concept_ids": focus.get("concept_ids", []),
        "skill_ids": focus.get("skill_ids", []),
    }
    meta["active_session"] = session_number
    meta["overall_mastery"] = payload.get("overall_mastery", assessment.get("mastery_to", meta.get("overall_mastery", 0.0)))
    if payload.get("review_state"):
        meta["review_state"] = payload["review_state"]
    write_meta(session_root, meta)

    return {
        "session": session_number,
        "assessment_path": str(session_dir / "assessment.md"),
        "journal_path": str(session_root / "journal.md"),
        "learner_model_path": str(session_root / "learner-model.md"),
        "misconceptions_path": str(session_root / "misconceptions.md"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Learning Tutor session updater")
    parser.add_argument("slug", nargs="?", help="Session slug")
    parser.add_argument("--topic", help="Topic name")
    parser.add_argument("--slug", dest="slug_opt", help="Explicit slug override")
    parser.add_argument("--sessions-dir", default=DEFAULT_SESSIONS_DIR)
    parser.add_argument("--action", choices=["append-round", "finalize-session"], required=True)
    parser.add_argument("--payload-file", help="Path to JSON payload")
    parser.add_argument("--payload", help="Inline JSON payload")
    args = parser.parse_args()

    _, _, session_root = resolve_session_root(args)
    payload = load_payload(args)

    if args.action == "append-round":
        result = append_round(session_root, payload)
    else:
        result = finalize_session(session_root, payload)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()