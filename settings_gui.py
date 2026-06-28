"""AUTO-MAIL settings window (double-click launcher)."""

from __future__ import annotations

import copy
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, scrolledtext, ttk

from config_store import (
    BASE_DIR,
    SCHEDULE_DAY_KEYS,
    SCHEDULE_DAY_LABELS,
    WEEKDAY_KEYS,
    WEEKEND_KEYS,
    join_list,
    load_config,
    load_env,
    normalize_schedule_days,
    parse_list,
    save_config,
    save_env,
)

WINDOW_TITLE = "AUTO-MAIL 설정"
_SUBPROCESS_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

CHANNEL_EXTERNAL = "external"
CHANNEL_CREWWORKS = "crewworks"
CHANNEL_LABELS = {
    CHANNEL_EXTERNAL: "외부 메일 (SMTP)",
    CHANNEL_CREWWORKS: "사내 메일 (CrewWorks)",
}

APP_BG = "#f1f5f9"
FOOTER_BG = "#e2e8f0"
FOOTER_HEIGHT = 72

PICKER_BG = "#2563eb"
PICKER_FG = "#ffffff"

BTN_REMOVE_BG = "#fee2e2"
BTN_REMOVE_ACTIVE = "#fecaca"
BTN_ADD_BG = "#dcfce7"
BTN_ADD_ACTIVE = "#bbf7d0"


class TimePickerDialog(tk.Toplevel):
    PERIODS = ("오전", "오후")

    @staticmethod
    def parse_24h(time_str: str) -> tuple[str, int, int]:
        hour_str, minute_str = time_str.strip().split(":", 1)
        hour = int(hour_str)
        minute = int(minute_str)
        if hour == 0:
            return "오전", 12, minute
        if hour < 12:
            return "오전", hour, minute
        if hour == 12:
            return "오후", 12, minute
        return "오후", hour - 12, minute

    @staticmethod
    def format_24h(period: str, hour12: int, minute: int) -> str:
        if period == "오전":
            hour24 = 0 if hour12 == 12 else hour12
        else:
            hour24 = 12 if hour12 == 12 else hour12 + 12
        return f"{hour24:02d}:{minute:02d}"

    @staticmethod
    def format_display(time_24: str) -> str:
        period, hour12, minute = TimePickerDialog.parse_24h(time_24)
        return f"{period} {hour12}:{minute:02d}"

    def __init__(self, parent: tk.Misc, *, initial: str = "09:00") -> None:
        super().__init__(parent)
        self._picker_parent = parent
        if hasattr(parent, "_unbind_main_mousewheel"):
            parent._unbind_main_mousewheel()

        self.title("발송 시간 선택")
        self.resizable(False, False)
        self.transient(parent)
        self.result: str | None = None

        period, hour12, minute = self.parse_24h(initial)

        body = ttk.Frame(self, padding=(16, 12, 16, 8))
        body.pack(fill=tk.BOTH, expand=True)

        lists_wrap = ttk.Frame(body)
        lists_wrap.pack()

        self.lb_period = self._make_listbox(lists_wrap, self.PERIODS, 6, padx=(0, 4))
        self.lb_hour = self._make_listbox(lists_wrap, [str(h) for h in range(1, 13)], 4, padx=(0, 4))
        self.lb_minute = self._make_listbox(lists_wrap, [f"{m:02d}" for m in range(60)], 4)

        self._select_value(self.lb_period, period)
        self._select_value(self.lb_hour, str(hour12))
        self._select_value(self.lb_minute, f"{minute:02d}")

        footer = ttk.Frame(body, padding=(0, 10, 0, 0))
        footer.pack(fill=tk.X)
        ttk.Button(footer, text="✓", width=4, command=self._confirm).pack(side=tk.LEFT, expand=True)
        ttk.Button(footer, text="✕", width=4, command=self._cancel).pack(side=tk.RIGHT, expand=True)

        self.bind("<Return>", lambda _e: self._confirm())
        self.bind("<Escape>", lambda _e: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self.bind("<Destroy>", self._on_destroy, add=True)

        for widget in (self, body, lists_wrap, footer):
            widget.bind("<MouseWheel>", self._block_wheel_propagation, add=True)

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{px}+{py}")

        self.grab_set()
        parent.wait_window(self)

    @staticmethod
    def _block_wheel_propagation(_event: tk.Event) -> str:
        return "break"

    def _on_destroy(self, event: tk.Event) -> None:
        if event.widget is not self:
            return
        parent = self._picker_parent
        if parent.winfo_exists() and hasattr(parent, "_bind_main_mousewheel"):
            parent._bind_main_mousewheel()

    def _make_listbox(
        self,
        parent: tk.Misc,
        values: tuple[str, ...] | list[str],
        width: int,
        *,
        padx: tuple[int, int] = (0, 0),
    ) -> tk.Listbox:
        column = tk.Frame(parent)
        column.pack(side=tk.LEFT, padx=padx)

        listbox = tk.Listbox(
            column,
            height=7,
            width=width,
            exportselection=False,
            activestyle="none",
            selectbackground=PICKER_BG,
            selectforeground=PICKER_FG,
            font=("Segoe UI", 10),
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
        )
        scrollbar = tk.Scrollbar(
            column,
            orient=tk.VERTICAL,
            width=10,
            command=listbox.yview,
            bd=0,
            highlightthickness=0,
        )
        listbox.configure(yscrollcommand=scrollbar.set)
        listbox.pack(side=tk.LEFT)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        for value in values:
            listbox.insert(tk.END, value)

        def on_wheel(event: tk.Event, lb: tk.Listbox = listbox) -> str:
            lb.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        for widget in (column, listbox, scrollbar):
            widget.bind("<MouseWheel>", on_wheel)

        listbox.bind(
            "<ButtonRelease-1>",
            lambda _e, lb=listbox: lb.selection_clear(0, tk.END)
            or lb.selection_set(lb.nearest(lb.winfo_pointery() - lb.winfo_rooty())),
        )
        return listbox

    def _finish(self) -> None:
        self.grab_release()
        self.destroy()

    def _select_value(self, listbox: tk.Listbox, value: str) -> None:
        values = listbox.get(0, tk.END)
        if value in values:
            index = values.index(value)
            listbox.selection_set(index)
            listbox.see(index)

    def _get_selection(self) -> str:
        period = self.lb_period.get(self.lb_period.curselection()[0])
        hour12 = int(self.lb_hour.get(self.lb_hour.curselection()[0]))
        minute = int(self.lb_minute.get(self.lb_minute.curselection()[0]))
        return self.format_24h(period, hour12, minute)

    def _confirm(self) -> None:
        if not self.lb_period.curselection() or not self.lb_hour.curselection() or not self.lb_minute.curselection():
            messagebox.showwarning(WINDOW_TITLE, "시간을 선택해 주세요.", parent=self)
            return
        self.result = self._get_selection()
        self._finish()

    def _cancel(self) -> None:
        self._finish()


class SettingsApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(WINDOW_TITLE)
        self.configure(bg=APP_BG)
        self.geometry("780x820")
        self.minsize(620, 520)
        self.resizable(True, True)

        self.config_data = load_config()
        self.env_data = load_env()
        self.config_data = copy.deepcopy(self.config_data)
        self.env_data = copy.deepcopy(self.env_data)
        self.var_channel = tk.StringVar(value=CHANNEL_EXTERNAL)
        self.schedule_times: list[str] = []

        self._main_mousewheel_handler = None

        self.main_container = ttk.Frame(self)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        self._build_footer()
        self._build_ui()

        self._load_fields()
        self._on_channel_change()
        self._center_window()
        self.protocol("WM_DELETE_WINDOW", self.handle_close)

    def _center_window(self) -> None:
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2 - 20)
        self.geometry(f"{width}x{height}+{x}+{y}")

    def _close_window(self) -> None:
        self._unbind_main_mousewheel()
        self.destroy()

    def _bind_main_mousewheel(self) -> None:
        if self._main_mousewheel_handler:
            self.bind_all("<MouseWheel>", self._main_mousewheel_handler)

    def _unbind_main_mousewheel(self) -> None:
        self.unbind_all("<MouseWheel>")

    def _build_ui(self) -> None:
        self.content_area = tk.Frame(self.main_container, bg=APP_BG)
        self.content_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)
        self.content_area.bind("<Configure>", self._adjust_body_height)

        canvas = tk.Canvas(self.content_area, bg=APP_BG, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(self.content_area, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        root = ttk.Frame(canvas, padding=12)
        self._scroll_window = canvas.create_window((0, 0), window=root, anchor=tk.NW)
        self._content_canvas = canvas

        def on_root_configure(_event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(self._scroll_window, width=event.width)

        root.bind("<Configure>", on_root_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event: tk.Event) -> None:
            if not canvas.winfo_exists():
                return
            canvas.yview_scroll(int(-event.delta / 120), "units")

        self._main_mousewheel_handler = on_mousewheel
        self._bind_main_mousewheel()

        root.columnconfigure(1, weight=1)

        ttk.Label(root, text="메일 종류").grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        self.combo_channel = ttk.Combobox(
            root,
            textvariable=self.var_channel,
            values=list(CHANNEL_LABELS.values()),
            state="readonly",
            width=28,
        )
        self.combo_channel.grid(row=0, column=1, sticky=tk.W, pady=(0, 8))
        self.combo_channel.bind("<<ComboboxSelected>>", self._on_channel_change)

        schedule_frame = ttk.LabelFrame(root, text="발송 일정", padding=10)
        schedule_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        schedule_frame.columnconfigure(1, weight=1)

        ttk.Label(
            schedule_frame,
            text="＋ 버튼으로 발송 시간을 추가하세요. 항목을 클릭하면 시간을 변경할 수 있습니다.",
        ).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 6))

        ttk.Label(schedule_frame, text="발송 시간").grid(row=1, column=0, sticky=tk.NW, pady=4)

        times_column = ttk.Frame(schedule_frame)
        times_column.grid(row=1, column=1, sticky=tk.W, pady=4)

        self.times_list_frame = ttk.Frame(times_column)
        self.times_list_frame.pack(anchor=tk.W)

        ttk.Label(schedule_frame, text="발송 요일").grid(row=2, column=0, sticky=tk.NW, pady=4)

        days_wrap = ttk.Frame(schedule_frame)
        days_wrap.grid(row=2, column=1, sticky=tk.W, pady=4)

        self.day_vars: dict[str, tk.BooleanVar] = {}
        for index, key in enumerate(SCHEDULE_DAY_KEYS):
            var = tk.BooleanVar(value=key in WEEKDAY_KEYS)
            self.day_vars[key] = var
            ttk.Checkbutton(days_wrap, text=SCHEDULE_DAY_LABELS[key], variable=var).grid(
                row=0, column=index, padx=(0, 6)
            )

        preset_wrap = ttk.Frame(schedule_frame)
        preset_wrap.grid(row=3, column=1, sticky=tk.W, pady=(0, 4))
        ttk.Button(preset_wrap, text="평일", width=6, command=lambda: self._set_day_preset(WEEKDAY_KEYS)).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(preset_wrap, text="주말", width=6, command=lambda: self._set_day_preset(WEEKEND_KEYS)).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(preset_wrap, text="매일", width=6, command=lambda: self._set_day_preset(SCHEDULE_DAY_KEYS)).pack(
            side=tk.LEFT
        )

        self.channel_frame = ttk.LabelFrame(root, text="연결 설정", padding=10)
        self.channel_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        self.channel_frame.columnconfigure(1, weight=1)

        self.frame_external = ttk.Frame(self.channel_frame)
        self.frame_crewworks = ttk.Frame(self.channel_frame)

        self.entry_smtp_from = self._label_entry(self.frame_external, 0, "보내는 사람 (From)")
        self.entry_smtp_username = self._label_entry(self.frame_external, 1, "SMTP 계정")
        self.entry_smtp_password = self._password_entry(self.frame_external, 2, "SMTP 비밀번호")
        self.entry_smtp_host = self._label_entry(self.frame_external, 3, "SMTP 서버")
        self.entry_smtp_port = self._label_entry(self.frame_external, 4, "SMTP 포트")
        self.frame_external.columnconfigure(1, weight=1)

        self.entry_cw_username = self._label_entry(self.frame_crewworks, 0, "보내는 사람 (로그인 ID)")
        self.entry_cw_password = self._password_entry(self.frame_crewworks, 1, "비밀번호")
        self.entry_cw_otp = self._label_entry(self.frame_crewworks, 2, "OTP (선택)")
        self.frame_crewworks.columnconfigure(1, weight=1)

        self.compose_frame = ttk.LabelFrame(root, text="메일 작성", padding=10)
        self.compose_frame.grid(row=3, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4))
        self.compose_frame.columnconfigure(1, weight=1)
        compose_frame = self.compose_frame

        self.lbl_recipients = ttk.Label(compose_frame, text="받는 사람")
        self.lbl_recipients.grid(row=0, column=0, sticky=tk.NW, pady=4)
        self.text_recipients = scrolledtext.ScrolledText(compose_frame, height=2, width=50)
        self.text_recipients.grid(row=0, column=1, sticky=tk.EW, pady=4)

        ttk.Label(compose_frame, text="제목").grid(row=1, column=0, sticky=tk.W, pady=4)
        self.entry_subject = ttk.Entry(compose_frame, width=60)
        self.entry_subject.grid(row=1, column=1, sticky=tk.EW, pady=4)
        ttk.Label(
            compose_frame,
            text="{date}, {time} 사용 가능",
            font=("", 8),
        ).grid(row=2, column=1, sticky=tk.W)

        ttk.Label(compose_frame, text="본문").grid(row=3, column=0, sticky=tk.NW, pady=4)
        self.text_body = scrolledtext.ScrolledText(compose_frame, height=4, width=60)
        self.text_body.grid(row=3, column=1, sticky=tk.EW, pady=4)

    def _adjust_body_height(self, _event: tk.Event | None = None) -> None:
        if not hasattr(self, "text_body") or not hasattr(self, "content_area"):
            return
        try:
            area_height = self.content_area.winfo_height()
            if area_height <= 1:
                return
            fixed_height = 310
            body_pixels = area_height - fixed_height
            lines = max(3, min(18, body_pixels // 22))
            current = int(self.text_body.cget("height"))
            if lines != current:
                self.text_body.configure(height=lines)
                if hasattr(self, "_content_canvas"):
                    self._content_canvas.update_idletasks()
                    self._content_canvas.configure(scrollregion=self._content_canvas.bbox("all"))
        except tk.TclError:
            return

    def _label_entry(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        show: str | None = None,
    ) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        entry = ttk.Entry(parent, width=52, show=show)
        entry.grid(row=row, column=1, sticky=tk.EW, pady=4)
        return entry

    def _password_entry(self, parent: ttk.Frame, row: int, label: str) -> ttk.Entry:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        wrap = ttk.Frame(parent)
        wrap.grid(row=row, column=1, sticky=tk.EW, pady=4)
        wrap.columnconfigure(0, weight=1)

        entry = ttk.Entry(wrap, show="*", width=48)
        entry.grid(row=0, column=0, sticky=tk.EW)

        visible = tk.BooleanVar(value=False)

        def toggle() -> None:
            if visible.get():
                entry.configure(show="*")
                toggle_btn.configure(text="표시")
                visible.set(False)
            else:
                entry.configure(show="")
                toggle_btn.configure(text="숨김")
                visible.set(True)

        toggle_btn = ttk.Button(wrap, text="표시", width=5, command=toggle)
        toggle_btn.grid(row=0, column=1, padx=(4, 0))
        return entry

    def _build_footer(self) -> None:
        self.footer = tk.Frame(self.main_container, bg=FOOTER_BG, height=FOOTER_HEIGHT)
        self.footer.pack(side=tk.BOTTOM, fill=tk.X)
        self.footer.pack_propagate(False)

        ttk.Separator(self.footer, orient=tk.HORIZONTAL).pack(fill=tk.X)

        btn_wrap = ttk.Frame(self.footer, padding=(12, 10))
        btn_wrap.pack(fill=tk.BOTH, expand=True)

        ttk.Button(btn_wrap, text="닫기", command=self.handle_close).pack(side=tk.RIGHT, padx=4)
        ttk.Button(btn_wrap, text="저장", command=self.handle_save).pack(side=tk.RIGHT, padx=4)

    def _make_time_action_button(self, parent: tk.Misc, text: str, bg: str, active_bg: str, command) -> tk.Button:
        return tk.Button(
            parent,
            text=text,
            width=3,
            bg=bg,
            fg="SystemButtonText",
            activebackground=active_bg,
            activeforeground="SystemButtonText",
            relief=tk.FLAT,
            bd=0,
            highlightthickness=1,
            highlightbackground="#d9d9d9",
            highlightcolor="#d9d9d9",
            font=tkfont.nametofont("TkDefaultFont"),
            command=command,
        )

    def _place_time_row_actions(self, row: ttk.Frame, *, index: int | None = None, show_add: bool = False) -> None:
        if index is not None:
            self._make_time_action_button(
                row,
                "-",
                BTN_REMOVE_BG,
                BTN_REMOVE_ACTIVE,
                command=lambda idx=index: self._remove_schedule_time(idx),
            ).pack(side=tk.LEFT, padx=(6, 4))

        if show_add:
            self._make_time_action_button(
                row,
                "+",
                BTN_ADD_BG,
                BTN_ADD_ACTIVE,
                command=self._add_schedule_time,
            ).pack(side=tk.LEFT)
        elif index is not None:
            ttk.Label(row, width=3).pack(side=tk.LEFT)

    def _schedule_time_sort_key(self, time_str: str) -> tuple[int, int]:
        hour_str, minute_str = time_str.strip().split(":", 1)
        return int(hour_str), int(minute_str)

    def _sort_schedule_times(self) -> None:
        self.schedule_times.sort(key=self._schedule_time_sort_key)

    def _refresh_times_ui(self) -> None:
        self._sort_schedule_times()
        for child in self.times_list_frame.winfo_children():
            child.destroy()

        if not self.schedule_times:
            row = ttk.Frame(self.times_list_frame)
            row.pack(anchor=tk.W, pady=2)
            ttk.Label(row, text="등록된 발송 시간이 없습니다.", foreground="#64748b").pack(side=tk.LEFT)
            self._place_time_row_actions(row, show_add=True)
            return

        for index, time_value in enumerate(self.schedule_times):
            row = ttk.Frame(self.times_list_frame)
            row.pack(anchor=tk.W, pady=2)

            ttk.Button(
                row,
                text=TimePickerDialog.format_display(time_value),
                command=lambda idx=index: self._edit_schedule_time(idx),
            ).pack(side=tk.LEFT)

            self._place_time_row_actions(row, index=index, show_add=index == 0)

    def _add_schedule_time(self) -> None:
        initial = self.schedule_times[-1] if self.schedule_times else "09:00"
        dialog = TimePickerDialog(self, initial=initial)
        if not dialog.result:
            return
        if dialog.result in self.schedule_times:
            messagebox.showinfo(WINDOW_TITLE, "이미 추가된 발송 시간입니다.")
            return
        self.schedule_times.append(dialog.result)
        self._sort_schedule_times()
        self._refresh_times_ui()

    def _edit_schedule_time(self, index: int) -> None:
        dialog = TimePickerDialog(self, initial=self.schedule_times[index])
        if not dialog.result:
            return
        if dialog.result in self.schedule_times and self.schedule_times[index] != dialog.result:
            messagebox.showinfo(WINDOW_TITLE, "이미 추가된 발송 시간입니다.")
            return
        self.schedule_times[index] = dialog.result
        self._sort_schedule_times()
        self._refresh_times_ui()

    def _remove_schedule_time(self, index: int) -> None:
        del self.schedule_times[index]
        self._refresh_times_ui()

    def _channel_key(self) -> str:
        label = self.var_channel.get()
        for key, text in CHANNEL_LABELS.items():
            if text == label:
                return key
        return CHANNEL_EXTERNAL

    def _set_channel_key(self, key: str) -> None:
        self.var_channel.set(CHANNEL_LABELS.get(key, CHANNEL_LABELS[CHANNEL_EXTERNAL]))

    def _set_day_preset(self, keys: tuple[str, ...]) -> None:
        selected = set(keys)
        for key, var in self.day_vars.items():
            var.set(key in selected)

    def _selected_days(self) -> list[str]:
        return [key for key in SCHEDULE_DAY_KEYS if self.day_vars[key].get()]

    def _show_recipients(self, recipients: list[str]) -> None:
        self.text_recipients.delete("1.0", tk.END)
        self.text_recipients.insert("1.0", join_list(recipients))

    def _on_channel_change(self, _event: object | None = None) -> None:
        new_channel = self._channel_key()

        if _event is not None and hasattr(self, "_last_channel"):
            recipients = parse_list(self.text_recipients.get("1.0", tk.END))
            if self._last_channel == CHANNEL_CREWWORKS:
                self.config_data.setdefault("crewworks", {})["recipients"] = recipients
            else:
                self.config_data.setdefault("external", {})["recipients"] = recipients

            if new_channel == CHANNEL_CREWWORKS:
                show = self.config_data.get("crewworks", {}).get("recipients", [])
            else:
                show = self.config_data.get("external", {}).get("recipients", [])
            self._show_recipients(show)

        self._last_channel = new_channel
        self.frame_external.grid_remove()
        self.frame_crewworks.grid_remove()

        if new_channel == CHANNEL_CREWWORKS:
            self.channel_frame.configure(text="사내 메일 (CrewWorks) 연결")
            self.frame_crewworks.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
            self.lbl_recipients.configure(text="받는 사람 (사용자 ID, 쉼표 구분)")
        else:
            self.channel_frame.configure(text="외부 메일 (SMTP) 연결")
            self.frame_external.grid(row=0, column=0, columnspan=2, sticky=tk.EW)
            self.lbl_recipients.configure(text="받는 사람 (이메일, 쉼표 구분)")

    def _load_fields(self) -> None:
        schedule = self.config_data["schedule"]
        crewworks = self.config_data["crewworks"]
        external = self.config_data["external"]
        mail = self.config_data["mail"]

        self.schedule_times = list(schedule.get("times", []))
        self._sort_schedule_times()
        self._refresh_times_ui()
        selected_days = set(normalize_schedule_days(schedule))
        for key, var in self.day_vars.items():
            var.set(key in selected_days)

        if crewworks.get("enabled") and not external.get("enabled"):
            active = CHANNEL_CREWWORKS
        else:
            active = CHANNEL_EXTERNAL
        self._set_channel_key(active)

        recipients = (
            crewworks.get("recipients", [])
            if active == CHANNEL_CREWWORKS
            else external.get("recipients", [])
        )
        self.text_recipients.insert("1.0", join_list(recipients))

        self.entry_cw_username.insert(0, self.env_data.get("CREWWORKS_USERNAME", ""))
        self.entry_cw_password.insert(0, self.env_data.get("CREWWORKS_PASSWORD", ""))
        self.entry_cw_otp.insert(0, self.env_data.get("CREWWORKS_OTP", ""))

        self.entry_smtp_from.insert(0, self.env_data.get("SMTP_FROM", ""))
        self.entry_smtp_username.insert(0, self.env_data.get("SMTP_USERNAME", ""))
        self.entry_smtp_password.insert(0, self.env_data.get("SMTP_PASSWORD", ""))
        self.entry_smtp_host.insert(0, self.env_data.get("SMTP_HOST", "smtp.gmail.com"))
        self.entry_smtp_port.insert(0, self.env_data.get("SMTP_PORT", "587"))

        self.entry_subject.insert(0, mail.get("subject", ""))
        self.text_body.insert("1.0", mail.get("body", ""))

    def _collect_config(self) -> dict:
        channel = self._channel_key()
        recipients = parse_list(self.text_recipients.get("1.0", tk.END))
        crewworks = self.config_data.get("crewworks", {})
        external = self.config_data.get("external", {})

        if channel == CHANNEL_CREWWORKS:
            crewworks_enabled = True
            external_enabled = False
            crewworks_recipients = recipients
            external_recipients = external.get("recipients", [])
        else:
            crewworks_enabled = False
            external_enabled = True
            crewworks_recipients = crewworks.get("recipients", [])
            external_recipients = recipients

        return {
            "schedule": {
                "times": list(self.schedule_times),
                "days": self._selected_days(),
            },
            "crewworks": {
                "enabled": crewworks_enabled,
                "recipients": crewworks_recipients,
            },
            "external": {
                "enabled": external_enabled,
                "recipients": external_recipients,
            },
            "mail": {
                "subject": self.entry_subject.get().strip(),
                "body": self.text_body.get("1.0", tk.END).rstrip("\n"),
            },
        }

    def _collect_env(self) -> dict[str, str]:
        return {
            "SEND_EMAIL": "True",
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

    def _normalize_config(self, config: dict) -> dict:
        data = copy.deepcopy(config)
        schedule = data.setdefault("schedule", {})
        schedule["days"] = normalize_schedule_days(schedule)
        schedule["times"] = sorted(schedule.get("times", []))
        mail = data.setdefault("mail", {})
        body = mail.get("body", "")
        if isinstance(body, str):
            mail["body"] = body.rstrip("\n")
        return data

    def _is_dirty(self) -> bool:
        current_config = self._normalize_config(self._collect_config())
        saved_config = self._normalize_config(self.config_data)
        if current_config != saved_config:
            return True

        current_env = self._collect_env()
        for key, value in current_env.items():
            if key == "SEND_EMAIL":
                continue
            if self.env_data.get(key) != value:
                return True
        return False

    def _register_scheduler(self) -> tuple[bool, str]:
        script = BASE_DIR / "setup_scheduler.ps1"
        if not script.exists():
            return False, f"오류 코드: 2\n\n스케줄러 스크립트를 찾을 수 없습니다:\n{script}"

        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script),
                ],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )
        except subprocess.TimeoutExpired:
            return False, "오류 코드: 시간 초과\n\n자동 발송 등록이 60초 안에 끝나지 않았습니다."
        except Exception as exc:
            errno = getattr(exc, "errno", None)
            if errno is not None:
                return False, f"오류 코드: {errno}\n\n{exc}"
            return False, f"오류: {type(exc).__name__}\n\n{exc}"

        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "알 수 없는 오류").strip()
            return False, f"오류 코드: {result.returncode}\n\n{detail}"

        missing = self._missing_scheduler_tasks(self.schedule_times)
        if missing:
            return False, (
                "오류 코드: 작업 미등록\n\n"
                f"다음 자동 발송 작업이 등록되지 않았습니다:\n"
                + "\n".join(f"- AUTO-MAIL-{time.replace(':', '-')}" for time in missing)
            )
        return True, ""

    def _missing_scheduler_tasks(self, times: list[str]) -> list[str]:
        if not times:
            return []
        try:
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-NoProfile",
                    "-Command",
                    "Get-ScheduledTask -TaskName 'AUTO-MAIL-*' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty TaskName",
                ],
                cwd=BASE_DIR,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
                creationflags=_SUBPROCESS_FLAGS,
            )
        except Exception:
            return list(times)

        registered = {
            line.strip()
            for line in (result.stdout or "").splitlines()
            if line.strip().startswith("AUTO-MAIL-")
        }
        missing: list[str] = []
        for time_value in times:
            task_name = f"AUTO-MAIL-{time_value.replace(':', '-')}"
            if task_name not in registered:
                missing.append(time_value)
        return missing

    def _persist_settings(self) -> tuple[bool, bool]:
        if not self._selected_days():
            messagebox.showwarning(WINDOW_TITLE, "발송 요일을 하나 이상 선택해 주세요.")
            return False, False
        config = self._collect_config()
        env = self._collect_env()
        try:
            save_config(config)
            save_env(env)
        except OSError as exc:
            errno = getattr(exc, "errno", None)
            code = f"오류 코드: {errno}" if errno is not None else f"오류: {type(exc).__name__}"
            messagebox.showerror(
                WINDOW_TITLE,
                f"설정 파일 저장에 실패했습니다.\n\n{code}\n{exc}",
            )
            return False, False
        except Exception as exc:
            messagebox.showerror(
                WINDOW_TITLE,
                f"설정 파일 저장에 실패했습니다.\n\n오류: {type(exc).__name__}\n{exc}",
            )
            return False, False

        self.config_data = copy.deepcopy(config)
        self.env_data = copy.deepcopy(env)

        ok, error = self._register_scheduler()
        if not ok:
            messagebox.showerror(
                WINDOW_TITLE,
                "설정은 저장했지만 자동 발송 등록에 실패했습니다.\n\n"
                f"{error}\n\n"
                "PowerShell에서 setup_scheduler.ps1을 직접 실행해 주세요.",
            )
            return True, False
        return True, True

    def handle_save(self) -> None:
        if not self._is_dirty():
            return
        if messagebox.askyesno(WINDOW_TITLE, "변경된 내용을 저장하시겠습니까?"):
            saved, scheduler_ok = self._persist_settings()
            if saved and scheduler_ok:
                messagebox.showinfo(
                    WINDOW_TITLE,
                    "설정을 저장했습니다.\n"
                    "설정한 요일·시간에 자동으로 메일이 발송됩니다.\n"
                    "(PC가 켜져 있어야 합니다.)",
                )

    def handle_close(self) -> None:
        if not self._is_dirty():
            self._close_window()
            return
        if messagebox.askyesno(WINDOW_TITLE, "변경사항을 저장하지 않고 닫으시겠습니까?"):
            self._close_window()

    def save_settings(self, *, show_message: bool = True) -> None:
        saved, scheduler_ok = self._persist_settings()
        if not saved:
            return
        if show_message and scheduler_ok:
            messagebox.showinfo(
                WINDOW_TITLE,
                "설정을 저장했습니다.\n"
                "설정한 요일·시간에 자동으로 메일이 발송됩니다.\n"
                "(PC가 켜져 있어야 합니다.)",
            )


def main() -> None:
    app = SettingsApp()
    app.mainloop()


if __name__ == "__main__":
    main()
