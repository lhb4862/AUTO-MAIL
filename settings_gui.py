"""AUTO-MAIL settings window (double-click launcher)."""

from __future__ import annotations

import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from config_store import (
    format_run_result_message,
    is_partial_success,
    join_list,
    load_config,
    load_env,
    parse_list,
    save_config,
    save_env,
)

WINDOW_TITLE = "AUTO-MAIL 설정"


class SettingsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.geometry("720x680")
        self.minsize(640, 600)

        self.config_data = load_config()
        self.env_data = load_env()

        self._build_ui()
        self._load_fields()

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.tab_schedule = ttk.Frame(notebook, padding=12)
        self.tab_crewworks = ttk.Frame(notebook, padding=12)
        self.tab_external = ttk.Frame(notebook, padding=12)
        self.tab_mail = ttk.Frame(notebook, padding=12)

        notebook.add(self.tab_schedule, text="발송 시간")
        notebook.add(self.tab_crewworks, text="CrewWorks")
        notebook.add(self.tab_external, text="외부 메일")
        notebook.add(self.tab_mail, text="메일 내용")

        self._build_schedule_tab()
        self._build_crewworks_tab()
        self._build_external_tab()
        self._build_mail_tab()
        self._build_buttons()

    def _label_entry(self, parent: ttk.Frame, row: int, label: str, show: str | None = None) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        entry = ttk.Entry(parent, width=52, show=show)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=4)
        parent.columnconfigure(1, weight=1)
        return entry

    def _build_schedule_tab(self) -> None:
        ttk.Label(
            self.tab_schedule,
            text="발송 시간은 쉼표로 구분합니다. 예: 09:00, 18:00",
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

        self.entry_times = self._label_entry(self.tab_schedule, 1, "발송 시간")
        self.var_weekdays_only = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.tab_schedule,
            text="평일만 발송 (체크 해제 시 주말 포함)",
            variable=self.var_weekdays_only,
        ).grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=8)

        self.var_send_email = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.tab_schedule,
            text="실제 메일 전송 (체크 해제 시 테스트 모드: 콘솔 출력만)",
            variable=self.var_send_email,
        ).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=4)

    def _build_crewworks_tab(self) -> None:
        self.var_crewworks_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.tab_crewworks,
            text="CrewWorks 내부 메일 사용",
            variable=self.var_crewworks_enabled,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

        ttk.Label(self.tab_crewworks, text="받는 사람 (ID, 쉼표 구분)").grid(row=1, column=0, sticky=tk.NW, pady=4)
        self.text_crewworks_recipients = scrolledtext.ScrolledText(self.tab_crewworks, height=3, width=50)
        self.text_crewworks_recipients.grid(row=1, column=1, sticky=tk.EW, pady=4)

        self.entry_cw_username = self._label_entry(self.tab_crewworks, 2, "로그인 ID")
        self.entry_cw_password = self._label_entry(self.tab_crewworks, 3, "비밀번호", show="*")
        self.entry_cw_otp = self._label_entry(self.tab_crewworks, 4, "OTP (선택)")

        self.tab_crewworks.columnconfigure(1, weight=1)

    def _build_external_tab(self) -> None:
        self.var_external_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.tab_external,
            text="외부 SMTP 메일 사용",
            variable=self.var_external_enabled,
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 8))

        ttk.Label(self.tab_external, text="받는 사람 (이메일, 쉼표 구분)").grid(row=1, column=0, sticky=tk.NW, pady=4)
        self.text_external_recipients = scrolledtext.ScrolledText(self.tab_external, height=3, width=50)
        self.text_external_recipients.grid(row=1, column=1, sticky=tk.EW, pady=4)

        self.entry_smtp_from = self._label_entry(self.tab_external, 2, "보내는 사람 (From)")
        self.entry_smtp_username = self._label_entry(self.tab_external, 3, "SMTP 계정")
        self.entry_smtp_password = self._label_entry(self.tab_external, 4, "SMTP 비밀번호", show="*")
        self.entry_smtp_host = self._label_entry(self.tab_external, 5, "SMTP 서버")
        self.entry_smtp_port = self._label_entry(self.tab_external, 6, "SMTP 포트")

        self.tab_external.columnconfigure(1, weight=1)

    def _build_mail_tab(self) -> None:
        ttk.Label(self.tab_mail, text="제목 ({date}, {time} 사용 가능)").grid(row=0, column=0, sticky=tk.W, pady=4)
        self.entry_subject = ttk.Entry(self.tab_mail, width=60)
        self.entry_subject.grid(row=0, column=1, sticky=tk.EW, pady=4)

        ttk.Label(self.tab_mail, text="본문").grid(row=1, column=0, sticky=tk.NW, pady=4)
        self.text_body = scrolledtext.ScrolledText(self.tab_mail, height=16, width=60)
        self.text_body.grid(row=1, column=1, sticky=tk.NSEW, pady=4)

        self.tab_mail.columnconfigure(1, weight=1)
        self.tab_mail.rowconfigure(1, weight=1)

    def _build_buttons(self) -> None:
        frame = ttk.Frame(self, padding=(10, 0, 10, 10))
        frame.pack(fill=tk.X)

        ttk.Button(frame, text="저장", command=self.save_settings).pack(side=tk.LEFT, padx=4)
        ttk.Button(frame, text="테스트 실행", command=self.run_test).pack(side=tk.LEFT, padx=4)
        ttk.Button(frame, text="실제 발송", command=self.run_live).pack(side=tk.LEFT, padx=4)
        ttk.Button(frame, text="닫기", command=self.destroy).pack(side=tk.RIGHT, padx=4)

    def _load_fields(self) -> None:
        schedule = self.config_data["schedule"]
        crewworks = self.config_data["crewworks"]
        external = self.config_data["external"]
        mail = self.config_data["mail"]

        self.entry_times.insert(0, join_list(schedule.get("times", [])))
        self.var_weekdays_only.set(schedule.get("weekdays_only", True))
        self.var_send_email.set(self.env_data.get("SEND_EMAIL", "False").lower() == "true")

        self.var_crewworks_enabled.set(crewworks.get("enabled", True))
        self.text_crewworks_recipients.insert("1.0", join_list(crewworks.get("recipients", [])))
        self.entry_cw_username.insert(0, self.env_data.get("CREWWORKS_USERNAME", ""))
        self.entry_cw_password.insert(0, self.env_data.get("CREWWORKS_PASSWORD", ""))
        self.entry_cw_otp.insert(0, self.env_data.get("CREWWORKS_OTP", ""))

        self.var_external_enabled.set(external.get("enabled", False))
        self.text_external_recipients.insert("1.0", join_list(external.get("recipients", [])))
        self.entry_smtp_from.insert(0, self.env_data.get("SMTP_FROM", ""))
        self.entry_smtp_username.insert(0, self.env_data.get("SMTP_USERNAME", ""))
        self.entry_smtp_password.insert(0, self.env_data.get("SMTP_PASSWORD", ""))
        self.entry_smtp_host.insert(0, self.env_data.get("SMTP_HOST", "smtp.gmail.com"))
        self.entry_smtp_port.insert(0, self.env_data.get("SMTP_PORT", "587"))

        self.entry_subject.insert(0, mail.get("subject", ""))
        self.text_body.insert("1.0", mail.get("body", ""))

    def _collect_config(self) -> dict:
        return {
            "schedule": {
                "times": parse_list(self.entry_times.get()),
                "weekdays_only": self.var_weekdays_only.get(),
            },
            "crewworks": {
                "enabled": self.var_crewworks_enabled.get(),
                "recipients": parse_list(self.text_crewworks_recipients.get("1.0", tk.END)),
            },
            "external": {
                "enabled": self.var_external_enabled.get(),
                "recipients": parse_list(self.text_external_recipients.get("1.0", tk.END)),
            },
            "mail": {
                "subject": self.entry_subject.get().strip(),
                "body": self.text_body.get("1.0", tk.END).rstrip("\n"),
            },
        }

    def _collect_env(self, *, send_email: bool | None = None) -> dict[str, str]:
        live = self.var_send_email.get() if send_email is None else send_email
        return {
            "SEND_EMAIL": "True" if live else "False",
            "CREWWORKS_URL": self.env_data.get("CREWWORKS_URL", "https://gw.yesyoungin.com/Main"),
            "CREWWORKS_USERNAME": self.entry_cw_username.get().strip(),
            "CREWWORKS_PASSWORD": self.entry_cw_password.get(),
            "CREWWORKS_OTP": self.entry_cw_otp.get().strip(),
            "SMTP_HOST": self.entry_smtp_host.get().strip() or "smtp.gmail.com",
            "SMTP_PORT": self.entry_smtp_port.get().strip() or "587",
            "SMTP_USERNAME": self.entry_smtp_username.get().strip(),
            "SMTP_PASSWORD": self.entry_smtp_password.get(),
            "SMTP_FROM": self.entry_smtp_from.get().strip(),
            "SMTP_USE_TLS": self.env_data.get("SMTP_USE_TLS", "True"),
        }

    def save_settings(self, *, send_email: bool | None = None, show_message: bool = True) -> None:
        config = self._collect_config()
        env = self._collect_env(send_email=send_email)
        save_config(config)
        save_env(env)
        self.config_data = config
        self.env_data = env
        if send_email is not None:
            self.var_send_email.set(send_email)
        if show_message:
            messagebox.showinfo(WINDOW_TITLE, "설정을 저장했습니다.")

    def _run_main(self, *, live: bool) -> None:
        self.save_settings(send_email=live, show_message=False)
        if live and not messagebox.askyesno(WINDOW_TITLE, "지금 실제로 메일을 보내시겠습니까?"):
            return

        try:
            env = os.environ.copy()
            env["PYTHONUTF8"] = "1"
            env["PYTHONIOENCODING"] = "utf-8"
            config = self._collect_config()
            result = subprocess.run(
                [sys.executable, "main.py", "--force"],
                cwd=str(__import__("config_store").BASE_DIR),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
            )
            message = format_run_result_message(config, live=live)
            if result.returncode == 0 and is_partial_success():
                messagebox.showwarning(WINDOW_TITLE, message)
            elif result.returncode == 0:
                messagebox.showinfo(WINDOW_TITLE, message)
            else:
                messagebox.showerror(WINDOW_TITLE, message)
        except Exception as exc:
            messagebox.showerror(WINDOW_TITLE, f"실행 오류: {exc}")

    def run_test(self) -> None:
        self._run_main(live=False)

    def run_live(self) -> None:
        self._run_main(live=True)


def main() -> None:
    app = SettingsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
