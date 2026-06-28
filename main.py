"""AUTO-MAIL entry point."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from config_store import SCHEDULE_DAY_LABELS, is_scheduled_day, join_list, normalize_schedule_days
from crewworks_sender import CrewWorksConfig, send_crewworks_mail
from email_sender import SmtpConfig, send_external_email
from mail_log import append_mail_log

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def scheduled_day_label(now: datetime) -> str:
    keys = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
    return SCHEDULE_DAY_LABELS[keys[now.weekday()]]


def matches_schedule(now: datetime, times: list[str], tolerance_minutes: int = 5) -> bool:
    if not times:
        return True
    current_minutes = now.hour * 60 + now.minute
    for time_str in times:
        hour, minute = map(int, time_str.split(":"))
        scheduled = hour * 60 + minute
        if abs(current_minutes - scheduled) <= tolerance_minutes:
            return True
    return False


def render_template(template: str, now: datetime) -> str:
    return template.format(date=now.strftime("%Y-%m-%d"), time=now.strftime("%H:%M"))


def _log_skip(now: datetime, message: str) -> None:
    append_mail_log(
        sent_at=now,
        sender="",
        recipients="",
        result="발송 안 함",
        error=message,
    )


def _log_send(
    *,
    now: datetime,
    sender: str,
    recipients: list[str],
    success: bool,
    error: str = "",
    dry_run: bool = False,
) -> None:
    if dry_run:
        result = "테스트"
    elif success:
        result = "성공"
    else:
        result = "실패"
    append_mail_log(
        sent_at=now,
        sender=sender,
        recipients=join_list(recipients),
        result=result,
        error=error if not success else "",
    )


def run(*, force: bool = False, skip_schedule: bool = False) -> int:
    load_dotenv(BASE_DIR / ".env")
    dry_run = not parse_bool(os.getenv("SEND_EMAIL"), default=False)
    now = datetime.now()
    config = load_config()
    schedule = config.get("schedule", {})

    if not is_scheduled_day(now, schedule) and not force:
        allowed = ", ".join(SCHEDULE_DAY_LABELS[day] for day in normalize_schedule_days(schedule))
        msg = f"오늘({scheduled_day_label(now)})은 발송 요일이 아닙니다. 설정 요일: {allowed}"
        print(msg)
        _log_skip(now, msg)
        return 0

    if not skip_schedule and not matches_schedule(now, schedule.get("times", [])) and not force:
        msg = f"현재 시간({now.strftime('%H:%M')})은 발송 시간이 아닙니다."
        print(msg)
        _log_skip(now, msg)
        return 0

    subject = render_template(config["mail"]["subject"], now)
    body = render_template(config["mail"]["body"], now)

    crewworks_cfg = config.get("crewworks", {})
    external_cfg = config.get("external", {})
    if not crewworks_cfg.get("enabled", False) and not external_cfg.get("enabled", False):
        msg = "발송 채널이 선택되지 않았습니다."
        print(msg)
        append_mail_log(
            sent_at=now,
            sender="",
            recipients="",
            result="발송 안 함",
            error=msg,
        )
        return 1

    if dry_run:
        print("[DRY-RUN] 실제 전송 없음 (SEND_EMAIL=False)")
        print("=" * 40)
    else:
        print("[LIVE] 실제 메일 전송 시작 (SEND_EMAIL=True)")

    results: list[str] = []
    failures: list[str] = []

    if crewworks_cfg.get("enabled", False):
        cw_config = None
        if not dry_run:
            cw_config = CrewWorksConfig(
                url=os.getenv("CREWWORKS_URL", "https://gw.yesyoungin.com/Main"),
                username=os.getenv("CREWWORKS_USERNAME", ""),
                password=os.getenv("CREWWORKS_PASSWORD", ""),
                otp=os.getenv("CREWWORKS_OTP", ""),
            )
        try:
            send_crewworks_mail(
                crewworks_cfg.get("recipients", []),
                subject,
                body,
                dry_run=dry_run,
                config=cw_config,
            )
            results.append("crewworks:ok")
            print("[CrewWorks 내부 메일] 성공")
            sender = cw_config.username if cw_config else os.getenv("CREWWORKS_USERNAME", "")
            _log_send(
                now=now,
                sender=sender,
                recipients=crewworks_cfg.get("recipients", []),
                success=True,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"[CrewWorks 내부 메일] 실패: {exc}")
            results.append(f"crewworks:error:{exc}")
            failures.append(f"CrewWorks: {exc}")
            sender = cw_config.username if cw_config else os.getenv("CREWWORKS_USERNAME", "")
            _log_send(
                now=now,
                sender=sender,
                recipients=crewworks_cfg.get("recipients", []),
                success=False,
                error=str(exc),
                dry_run=dry_run,
            )

    if external_cfg.get("enabled", False):
        smtp_config = None
        if not dry_run:
            smtp_config = SmtpConfig(
                host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
                port=int(os.getenv("SMTP_PORT", "587")),
                username=os.getenv("SMTP_USERNAME", ""),
                password=os.getenv("SMTP_PASSWORD", ""),
                from_address=os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", "")),
                use_tls=parse_bool(os.getenv("SMTP_USE_TLS"), default=True),
            )
        try:
            send_external_email(
                external_cfg.get("recipients", []),
                subject,
                body,
                dry_run=dry_run,
                smtp_config=smtp_config,
            )
            results.append("external:ok")
            print("[외부 이메일] 성공")
            sender = ""
            if smtp_config:
                sender = smtp_config.from_address
            elif dry_run:
                sender = os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", ""))
            _log_send(
                now=now,
                sender=sender,
                recipients=external_cfg.get("recipients", []),
                success=True,
                dry_run=dry_run,
            )
        except Exception as exc:
            print(f"[외부 이메일] 실패: {exc}")
            results.append(f"external:error:{exc}")
            failures.append(f"외부 메일: {exc}")
            sender = ""
            if smtp_config:
                sender = smtp_config.from_address
            elif dry_run:
                sender = os.getenv("SMTP_FROM", os.getenv("SMTP_USERNAME", ""))
            _log_send(
                now=now,
                sender=sender,
                recipients=external_cfg.get("recipients", []),
                success=False,
                error=str(exc),
                dry_run=dry_run,
            )

    if dry_run:
        print("=" * 40)

    mode = "DRY-RUN" if dry_run else "LIVE"
    successes = [r for r in results if r.endswith(":ok")]
    if failures and successes:
        print(f"일부 완료 ({mode}): 성공 {len(successes)}건, 실패 {len(failures)}건")
        for item in failures:
            print(f"  - 실패: {item}")
        return 0
    if failures:
        print(f"전체 실패 ({mode})")
        for item in failures:
            print(f"  - {item}")
        return 1

    print(f"완료 ({mode})")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="AUTO-MAIL")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-schedule", action="store_true")
    args = parser.parse_args()
    try:
        sys.exit(run(force=args.force, skip_schedule=args.skip_schedule))
    except Exception as exc:
        now = datetime.now()
        append_mail_log(
            sent_at=now,
            sender="",
            recipients="",
            result="실패",
            error=f"{type(exc).__name__}: {exc}",
        )
        raise


if __name__ == "__main__":
    main()
