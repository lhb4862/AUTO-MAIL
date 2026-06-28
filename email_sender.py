"""External SMTP email sender."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: str
    password: str
    from_address: str
    use_tls: bool = True


def _print_dry_run(recipients: Iterable[str], subject: str, body: str) -> None:
    print("[외부 이메일]")
    print(f"  수신자: {', '.join(recipients)}")
    print(f"  제목:   {subject}")
    print(f"  본문:   {body}")


def send_external_email(
    recipients: list[str],
    subject: str,
    body: str,
    *,
    dry_run: bool,
    smtp_config: SmtpConfig | None = None,
) -> bool:
    if not recipients:
        print("[외부 이메일] 수신자가 없어 건너뜁니다.")
        return True

    if dry_run:
        _print_dry_run(recipients, subject, body)
        return True

    if smtp_config is None:
        raise ValueError("smtp_config is required for live send.")

    message = MIMEMultipart()
    message["From"] = smtp_config.from_address
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain", "utf-8"))

    if smtp_config.use_tls:
        server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30)
        server.starttls()
    else:
        server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, timeout=30)

    try:
        if smtp_config.username:
            server.login(smtp_config.username, smtp_config.password)
        server.sendmail(smtp_config.from_address, recipients, message.as_string())
    finally:
        server.quit()

    print(f"[외부 이메일] 전송 완료: {', '.join(recipients)}")
    return True