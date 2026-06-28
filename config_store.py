"""Load and save user settings for AUTO-MAIL."""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import dotenv_values, set_key

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
ENV_PATH = BASE_DIR / ".env"
ENV_EXAMPLE_PATH = BASE_DIR / ".env.example"
LOG_FILE = BASE_DIR / "logs" / "mail_log.txt"

DEFAULT_CONFIG = {
    "schedule": {
        "times": ["09:00"],
        "weekdays_only": False,
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
    if not LOG_FILE.exists():
        return ""
    lines = LOG_FILE.read_text(encoding="utf-8").strip().splitlines()
    return lines[-1] if lines else ""


def _find_error_message(channel: str) -> str:
    if not LOG_FILE.exists():
        return ""
    for line in reversed(LOG_FILE.read_text(encoding="utf-8").splitlines()[-15:]):
        marker = f"ERROR {channel}:"
        if marker in line:
            msg = line.split(marker, 1)[1].strip()
            if len(msg) > 120:
                return msg[:120] + "..."
            return msg
    return ""


def format_run_result_message(config: dict, *, live: bool) -> str:
    log_line = read_last_log_line()
    mode = "실제 발송" if live else "테스트"
    lines = [f"{mode} 결과", ""]

    if not log_line:
        return f"{mode}가 실행되었습니다."

    if "subject='" in log_line:
        subject = log_line.split("subject='", 1)[1].split("'", 1)[0]
        lines.append(f"제목: {subject}")
        lines.append("")

    if "DRY-RUN" in log_line:
        lines.append("(실제 전송 없음 — 콘솔 출력만)")
        lines.append("")

    crewworks = config.get("crewworks", {})
    external = config.get("external", {})

    if crewworks.get("enabled"):
        recipients = join_list(crewworks.get("recipients", []))
        if "crewworks:ok" in log_line:
            lines.append("CrewWorks 내부 메일: 성공")
            if recipients:
                lines.append(f"  수신자: {recipients}")
        elif "crewworks:error" in log_line:
            lines.append("CrewWorks 내부 메일: 실패")
            err = _find_error_message("crewworks")
            if err:
                lines.append(f"  사유: {err}")

    if external.get("enabled"):
        recipients = join_list(external.get("recipients", []))
        if "external:ok" in log_line:
            lines.append("외부 이메일: 성공")
            if recipients:
                lines.append(f"  수신자: {recipients}")
            sender = load_env().get("SMTP_FROM") or load_env().get("SMTP_USERNAME", "")
            if sender:
                lines.append(f"  발신: {sender}")
        elif "external:error" in log_line:
            lines.append("외부 이메일: 실패")
            err = _find_error_message("external")
            if err:
                lines.append(f"  사유: {err}")

    return "\n".join(lines)


def is_partial_success() -> bool:
    log_line = read_last_log_line()
    has_ok = ":ok" in log_line
    has_error = ":error" in log_line
    return has_ok and has_error
