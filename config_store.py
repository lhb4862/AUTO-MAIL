"""Load and save user settings for AUTO-MAIL."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from dotenv import dotenv_values, set_key

from mail_log import LOG_FILE, read_last_log_entry, read_recent_logs

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"

SCHEDULE_DAY_KEYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
SCHEDULE_DAY_LABELS = {
    "mon": "월",
    "tue": "화",
    "wed": "수",
    "thu": "목",
    "fri": "금",
    "sat": "토",
    "sun": "일",
}
WEEKDAY_KEYS = ("mon", "tue", "wed", "thu", "fri")
WEEKEND_KEYS = ("sat", "sun")
PYTHON_WEEKDAY_TO_KEY = SCHEDULE_DAY_KEYS

DEFAULT_CONFIG = {
    "schedule": {
        "times": ["09:00"],
        "days": list(WEEKDAY_KEYS),
    },
    "crewworks": {
        "enabled": True,
        "recipients": [],
    },
    "external": {
        "enabled": False,
        "recipients": [],
    },
    "mail": {
        "subject": "[{date}] 정기 안내",
        "body": "안녕하세요.\n\n{date} {time} 정기 메일입니다.\n\n감사합니다.",
    },
}

DEFAULT_ENV = {
    "SEND_EMAIL": "False",
    "CREWWORKS_URL": "https://gw.yesyoungin.com/Main",
    "CREWWORKS_USERNAME": "",
    "CREWWORKS_PASSWORD": "",
    "CREWWORKS_OTP": "",
    "SMTP_HOST": "smtp.gmail.com",
    "SMTP_PORT": "587",
    "SMTP_USERNAME": "",
    "SMTP_PASSWORD": "",
    "SMTP_FROM": "",
    "SMTP_USE_TLS": "True",
}


def _ensure_env_file() -> None:
    if not ENV_PATH.exists():
        if ENV_EXAMPLE_PATH.exists():
            ENV_PATH.write_text(ENV_EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            lines = [f"{key}={value}" for key, value in DEFAULT_ENV.items()]
            ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def normalize_schedule_days(schedule: dict) -> list[str]:
    raw = schedule.get("days")
    if isinstance(raw, list) and raw:
        return [day for day in raw if day in SCHEDULE_DAY_LABELS]
    if schedule.get("weekdays_only", True):
        return list(WEEKDAY_KEYS)
    return list(SCHEDULE_DAY_KEYS)


def is_scheduled_day(now: datetime, schedule: dict) -> bool:
    key = PYTHON_WEEKDAY_TO_KEY[now.weekday()]
    return key in normalize_schedule_days(schedule)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return json.loads(json.dumps(DEFAULT_CONFIG))
    with CONFIG_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    merged = json.loads(json.dumps(DEFAULT_CONFIG))
    merged.update({k: v for k, v in data.items() if isinstance(v, dict) and k in merged})
    for key in ("schedule", "crewworks", "external", "mail"):
        merged[key].update(data.get(key, {}))
    merged["schedule"]["days"] = normalize_schedule_days(merged["schedule"])
    merged["schedule"].pop("weekdays_only", None)
    return merged


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_env() -> dict[str, str]:
    _ensure_env_file()
    values = dotenv_values(ENV_PATH)
    merged = dict(DEFAULT_ENV)
    for key, value in values.items():
        if value is not None:
            merged[key] = value
    return merged


def save_env(values: dict[str, str]) -> None:
    _ensure_env_file()
    for key, value in values.items():
        set_key(str(ENV_PATH), key, value or "")


def parse_list(text: str) -> list[str]:
    items: list[str] = []
    for part in text.replace("\n", ",").split(","):
        cleaned = part.strip()
        if cleaned:
            items.append(cleaned)
    return items


def join_list(items: list[str]) -> str:
    return ", ".join(items)


def read_last_log_line() -> str:
    entry = read_last_log_entry()
    if not entry:
        return ""
    return (
        f"{entry.get('발송시간', '')} | {entry.get('보내는사람 메일', '')} | "
        f"{entry.get('받는사람', '')} | {entry.get('결과', '')} | {entry.get('오류내용', '')}"
    )


def _latest_run_entries() -> list[dict[str, str]]:
    entries = read_recent_logs(limit=10)
    if not entries:
        return []
    latest_time = entries[-1].get("발송시간", "")
    return [entry for entry in entries if entry.get("발송시간", "") == latest_time]


def _find_error_message(channel: str) -> str:
    for entry in reversed(_latest_run_entries()):
        if entry.get("결과") != "실패":
            continue
        sender = entry.get("보내는사람 메일", "")
        error = entry.get("오류내용", "").strip()
        if not error:
            continue
        if channel == "external" and "@" in sender:
            return error[:120] + ("..." if len(error) > 120 else "")
        if channel == "crewworks" and "@" not in sender:
            return error[:120] + ("..." if len(error) > 120 else "")
    for entry in reversed(read_recent_logs(limit=15)):
        if entry.get("결과") == "실패":
            error = entry.get("오류내용", "").strip()
            if error:
                return error[:120] + ("..." if len(error) > 120 else "")
    return ""


def parse_send_result(config: dict, *, exit_code: int) -> tuple[bool, str]:
    """Return (success, error_detail) after a live send."""
    entries = _latest_run_entries()
    details: list[str] = []

    crewworks = config.get("crewworks", {})
    external = config.get("external", {})

    if not crewworks.get("enabled") and not external.get("enabled"):
        return False, "발송 채널이 선택되지 않았습니다."

    if not entries:
        return False, "발송 기록이 없습니다."

    for entry in entries:
        if entry.get("결과") != "실패":
            continue
        error = entry.get("오류내용", "").strip() or "메일 발송 실패"
        details.append(error)

    if exit_code != 0 and not details:
        details.append("메일 발송 중 오류가 발생했습니다.")

    if details:
        return False, "\n".join(details)
    return True, ""


def format_run_result_message(config: dict, *, live: bool) -> str:
    mode = "실제 발송" if live else "테스트"
    entries = _latest_run_entries()
    lines = [f"{mode} 결과", ""]

    if not entries:
        return f"{mode}가 실행되었습니다."

    for entry in entries:
        lines.append(
            f"{entry.get('발송시간', '')} | 발신: {entry.get('보내는사람 메일', '') or '-'} | "
            f"수신: {entry.get('받는사람', '') or '-'} | 결과: {entry.get('결과', '')}"
        )
        error = entry.get("오류내용", "").strip()
        if error:
            lines.append(f"  오류: {error}")

    return "\n".join(lines)


def is_partial_success() -> bool:
    entries = _latest_run_entries()
    has_ok = any(entry.get("결과") in {"성공", "테스트"} for entry in entries)
    has_error = any(entry.get("결과") == "실패" for entry in entries)
    return has_ok and has_error
