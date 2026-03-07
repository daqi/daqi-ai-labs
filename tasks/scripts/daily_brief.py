from __future__ import annotations

import re
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DAILY_DIR = ROOT / "tasks" / "daily"
TODAY_ALIAS = DAILY_DIR / "today.md"
CHECKBOX_RE = re.compile(r"^- \[ \] (.+)$")


def task_file(day: date) -> Path:
    return DAILY_DIR / f"{day.isoformat()}.md"


def extract_unfinished_tasks(path: Path) -> list[str]:
    if not path.exists():
        return []

    tasks: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = CHECKBOX_RE.match(line.strip())
        if match:
            task = match.group(1).strip()
            if task and task not in tasks:
                tasks.append(task)
    return tasks


def build_content(today: date, carry_over: list[str]) -> str:
    yesterday = today - timedelta(days=1)
    lines = [
        f"# {today.isoformat()} 日清单",
        "",
        f"- 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"- 昨日日期：{yesterday.isoformat()}",
        "",
        "## 昨日待办",
    ]

    if carry_over:
        lines.extend([f"- [ ] {task}" for task in carry_over])
    else:
        lines.append("- [ ] 无未完成项，回看昨天是否已全部清空")

    lines.extend(
        [
            "",
            "## 本周主线",
            "- [ ] 本周最重要的单点突破是什么？",
            "",
            "## 今日主内容",
            "- [ ] 题目：",
            "- [ ] 钩子：",
            "- [ ] 最小发布动作：",
            "",
            "## 今日辅助内容",
            "- [ ] 题目：",
            "- [ ] 作用：补实验 / 补判断 / 补互动 / 补复盘",
            "- [ ] 最小发布动作：",
            "",
            "## 今日承接",
            "- [ ] 评论、私信、主页或成交入口推进 1 次",
            "",
            "## 今日复盘",
            "- [ ] 今天最重要的单点突破是什么？",
            "- [ ] 明天要延续什么？",
            "",
        ]
    )
    return "\n".join(lines)


def write_today_alias(content: str) -> None:
    TODAY_ALIAS.write_text(content, encoding="utf-8")


def maybe_notify(today_path: Path, carry_over: list[str]) -> None:
    title = "今日待办已生成"
    subtitle = today_path.name
    message = f"昨日延续 {len(carry_over)} 项，今天清单已就位。"
    script = (
        f'display notification "{message}" with title "{title}" subtitle "{subtitle}"'
    )
    subprocess.run(["osascript", "-e", script], check=False)


def main() -> None:
    DAILY_DIR.mkdir(parents=True, exist_ok=True)

    today = date.today()
    yesterday = today - timedelta(days=1)
    today_path = task_file(today)

    carry_over = extract_unfinished_tasks(task_file(yesterday))
    content = build_content(today, carry_over)

    if not today_path.exists():
        today_path.write_text(content, encoding="utf-8")
    else:
        existing = today_path.read_text(encoding="utf-8")
        if not existing.strip():
            today_path.write_text(content, encoding="utf-8")

    write_today_alias(today_path.read_text(encoding="utf-8"))
    maybe_notify(today_path, carry_over)
    print(today_path)


if __name__ == "__main__":
    main()
