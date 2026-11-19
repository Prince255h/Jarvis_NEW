"""Personal Productivity Suite for JARVIS (4.1 - 4.8)."""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QComboBox,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QCalendarWidget,
    QDateTimeEdit,
    QDateEdit,
    QSpinBox,
    QProgressBar,
    QMessageBox,
    QFileDialog,
    QFrame,
    QCheckBox,
    QGroupBox,
)
from PySide6.QtCore import Qt, QTimer, QDate, QDateTime, Signal

from core.productivity import (
    add_task,
    list_tasks,
    toggle_task,
    delete_task,
    add_reminder,
    list_reminders,
    delete_reminder,
    save_note,
    list_notes,
    delete_note,
    add_calendar_event,
    list_calendar_events,
    delete_calendar_event,
    export_calendar_ics,
    log_study_session,
    get_study_progress,
    build_daily_summary_text,
)
from core.scheduler import (
    ACTION_TYPES,
    SCHEDULE_TYPES,
    save_scheduled_task,
    list_scheduled_tasks,
    set_scheduled_task_enabled,
    delete_scheduled_task,
    list_scheduled_logs,
)
from tools.computer import is_potentially_dangerous_command
from interface.worker import JarvisWorker


class ProductivityPage(QWidget):
    """Unified Personal Productivity Workspace (Tasks, Reminders, Notes, Calendar, Pomodoro, Daily Summary)."""

    announce_signal = Signal(str)
    run_scheduled_now_signal = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ai_worker = None
        self._current_note_id = None
        self._editing_sched_id = None

        # Pomodoro state
        self._pomo_running = False
        self._pomo_mode = "Focus"
        self._pomo_remaining = 25 * 60
        self._pomo_total = 25 * 60
        self._pomo_timer = QTimer(self)
        self._pomo_timer.timeout.connect(self._tick_pomodoro)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("PERSONAL PRODUCTIVITY CENTER")
        title.setObjectName("page_title")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_tasks_tab(), "Tasks & To-Do")
        self.tabs.addTab(self._build_scheduler_tab(), "Scheduled Tasks")
        self.tabs.addTab(self._build_reminders_tab(), "Reminders & Alarms")
        self.tabs.addTab(self._build_notes_tab(), "Notes")
        self.tabs.addTab(self._build_calendar_tab(), "Calendar")
        self.tabs.addTab(self._build_pomodoro_tab(), "Study & Pomodoro")
        self.tabs.addTab(self._build_summary_tab(), "Daily Summary")
        layout.addWidget(self.tabs, 1)

        self.refresh_all()

    def refresh_all(self):
        self.refresh_tasks()
        self.refresh_scheduled_tasks()
        self.refresh_reminders()
        self.refresh_notes()
        self.refresh_calendar_events()
        self.refresh_study_progress()
        self.refresh_daily_summary()

    # ==========================================
    # 4.1 & 4.7 TASKS / TO-DO
    # ==========================================

    def _build_tasks_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QHBoxLayout()
        self.task_title_input = QLineEdit()
        self.task_title_input.setPlaceholderText("Add a new task or to-do item...")
        self.task_title_input.returnPressed.connect(self._add_task)

        self.task_priority = QComboBox()
        self.task_priority.addItems(["High", "Medium", "Low"])
        self.task_priority.setCurrentText("Medium")

        self.task_category = QComboBox()
        self.task_category.addItems(["General", "Work", "Study", "Coding", "Personal"])

        self.task_due = QDateEdit(QDate.currentDate())
        self.task_due.setCalendarPopup(True)
        self.task_due.setDisplayFormat("yyyy-MM-dd")

        add_btn = QPushButton("ADD TASK")
        add_btn.clicked.connect(self._add_task)

        form.addWidget(self.task_title_input, 3)
        form.addWidget(self.task_priority)
        form.addWidget(self.task_category)
        form.addWidget(self.task_due)
        form.addWidget(add_btn)
        layout.addLayout(form)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Filter:"))
        self.task_filter = QComboBox()
        self.task_filter.addItems(["All", "Today", "Pending", "Completed"])
        self.task_filter.currentTextChanged.connect(self.refresh_tasks)
        filter_row.addWidget(self.task_filter)
        filter_row.addStretch()

        toggle_btn = QPushButton("TOGGLE DONE")
        toggle_btn.clicked.connect(self._toggle_selected_task)
        del_btn = QPushButton("DELETE TASK")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_selected_task)
        filter_row.addWidget(toggle_btn)
        filter_row.addWidget(del_btn)
        layout.addLayout(filter_row)

        self.task_list = QListWidget()
        self.task_list.itemDoubleClicked.connect(lambda _: self._toggle_selected_task())
        layout.addWidget(self.task_list, 1)

        return tab

    def _add_task(self):
        title = self.task_title_input.text().strip()
        if not title:
            return
        add_task(
            title=title,
            priority=self.task_priority.currentText(),
            category=self.task_category.currentText(),
            due_date=self.task_due.date().toString("yyyy-MM-dd"),
        )
        self.task_title_input.clear()
        self.refresh_tasks()
        self.refresh_daily_summary()

    def refresh_tasks(self):
        mode = self.task_filter.currentText().lower()
        tasks = list_tasks(mode)
        self.task_list.clear()
        for tid, title, priority, cat, due, completed in tasks:
            mark = "✓" if completed else "○"
            item = QListWidgetItem(f"{mark}  [{priority}] {title}   —   {cat} | Due: {due}")
            item.setData(Qt.ItemDataRole.UserRole, (tid, bool(completed)))
            self.task_list.addItem(item)

    def _toggle_selected_task(self):
        item = self.task_list.currentItem()
        if not item:
            return
        tid, completed = item.data(Qt.ItemDataRole.UserRole)
        toggle_task(tid, not completed)
        self.refresh_tasks()
        self.refresh_daily_summary()

    def _delete_selected_task(self):
        item = self.task_list.currentItem()
        if not item:
            return
        tid, _ = item.data(Qt.ItemDataRole.UserRole)
        delete_task(tid)
        self.refresh_tasks()
        self.refresh_daily_summary()

    # ==========================================
    # CUSTOM SCHEDULED TASK AUTOMATION ENGINE
    # ==========================================

    def _build_scheduler_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(8)

        form_box = QGroupBox("CREATE / EDIT CUSTOM SCHEDULED TASK (RUNS AUTOMATICALLY AT SCHEDULED TIME)")
        fb = QVBoxLayout(form_box)
        fb.setSpacing(6)

        row1 = QHBoxLayout()
        self.sched_name_input = QLineEdit()
        self.sched_name_input.setPlaceholderText("Task Name (e.g. Morning AI Briefing, Auto-Organize Downloads)")
        self.sched_action_combo = QComboBox()
        for key, meta in ACTION_TYPES.items():
            self.sched_action_combo.addItem(meta["label"], key)
        self.sched_action_combo.currentIndexChanged.connect(self._update_sched_placeholder)
        row1.addWidget(self.sched_name_input, 2)
        row1.addWidget(self.sched_action_combo, 2)
        fb.addLayout(row1)

        row2 = QHBoxLayout()
        self.sched_payload_input = QLineEdit()
        row2.addWidget(self.sched_payload_input, 1)
        fb.addLayout(row2)

        row3 = QHBoxLayout()
        self.sched_type_combo = QComboBox()
        for key, label in SCHEDULE_TYPES.items():
            self.sched_type_combo.addItem(label, key)
        self.sched_type_combo.currentIndexChanged.connect(self._on_sched_type_changed)

        self.sched_interval_spin = QSpinBox()
        self.sched_interval_spin.setRange(1, 1440)
        self.sched_interval_spin.setValue(30)
        self.sched_interval_spin.setSuffix(" min")
        self.sched_interval_spin.setVisible(False)

        self.sched_dt_edit = QDateTimeEdit(QDateTime.currentDateTime().addSecs(300))
        self.sched_dt_edit.setCalendarPopup(True)
        self.sched_dt_edit.setDisplayFormat("yyyy-MM-dd HH:mm")

        self.sched_speak_chk = QCheckBox("Speak result")
        self.sched_speak_chk.setChecked(True)

        self.sched_save_btn = QPushButton("SCHEDULE TASK")
        self.sched_save_btn.setObjectName("primary_cta")
        self.sched_save_btn.clicked.connect(self._save_scheduled_task)

        new_btn = QPushButton("RESET FORM")
        new_btn.clicked.connect(self._reset_scheduler_form)

        row3.addWidget(QLabel("Repeat:"))
        row3.addWidget(self.sched_type_combo)
        row3.addWidget(self.sched_interval_spin)
        row3.addWidget(QLabel("Run At:"))
        row3.addWidget(self.sched_dt_edit)
        row3.addWidget(self.sched_speak_chk)
        row3.addWidget(self.sched_save_btn)
        row3.addWidget(new_btn)
        fb.addLayout(row3)

        layout.addWidget(form_box)

        # Scheduled task list + controls
        self.sched_list = QListWidget()
        self.sched_list.itemClicked.connect(self._preview_sched_output)
        self.sched_list.itemDoubleClicked.connect(self._edit_selected_sched)
        layout.addWidget(self.sched_list, 2)

        ctrl_row = QHBoxLayout()
        run_now_btn = QPushButton("▶ RUN NOW")
        run_now_btn.clicked.connect(self._run_selected_sched_now)
        toggle_btn = QPushButton("ENABLE / DISABLE")
        toggle_btn.clicked.connect(self._toggle_selected_sched)
        edit_btn = QPushButton("EDIT SELECTED")
        edit_btn.clicked.connect(self._edit_selected_sched)
        refresh_btn = QPushButton("REFRESH")
        refresh_btn.clicked.connect(self.refresh_scheduled_tasks)
        del_btn = QPushButton("DELETE")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_selected_sched)
        ctrl_row.addWidget(run_now_btn)
        ctrl_row.addWidget(toggle_btn)
        ctrl_row.addWidget(edit_btn)
        ctrl_row.addWidget(refresh_btn)
        ctrl_row.addStretch()
        ctrl_row.addWidget(del_btn)
        layout.addLayout(ctrl_row)

        self.sched_log_view = QTextEdit()
        self.sched_log_view.setReadOnly(True)
        self.sched_log_view.setMaximumHeight(145)
        self.sched_log_view.setPlaceholderText("Execution logs & output from scheduled tasks appear here...")
        layout.addWidget(self.sched_log_view, 1)

        self._update_sched_placeholder()
        return tab

    def _update_sched_placeholder(self):
        key = self.sched_action_combo.currentData() or "ai_prompt"
        self.sched_payload_input.setPlaceholderText(ACTION_TYPES[key]["placeholder"])

    def _on_sched_type_changed(self):
        stype = self.sched_type_combo.currentData()
        self.sched_interval_spin.setVisible(stype == "interval")

    def _reset_scheduler_form(self):
        self._editing_sched_id = None
        self.sched_name_input.clear()
        self.sched_payload_input.clear()
        self.sched_dt_edit.setDateTime(QDateTime.currentDateTime().addSecs(300))
        self.sched_save_btn.setText("SCHEDULE TASK")

    def _save_scheduled_task(self):
        name = self.sched_name_input.text().strip()
        atype = self.sched_action_combo.currentData()
        payload = self.sched_payload_input.text().strip()
        stype = self.sched_type_combo.currentData()
        interval = self.sched_interval_spin.value()
        run_at = self.sched_dt_edit.dateTime().toString("yyyy-MM-dd HH:mm")
        speak = self.sched_speak_chk.isChecked()

        if atype == "terminal_command":
            warn = (
                "\n\nWARNING: Potentially destructive command pattern detected!"
                if is_potentially_dangerous_command(payload)
                else ""
            )
            ans = QMessageBox.question(
                self,
                "Approve Scheduled Terminal Command",
                f"Approve scheduling this terminal command to run automatically?\n\n{payload}\n\nSchedule: {SCHEDULE_TYPES[stype]} @ {run_at}{warn}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return

        try:
            save_scheduled_task(
                name=name,
                action_type=atype,
                payload=payload,
                next_run_at=run_at,
                schedule_type=stype,
                interval_minutes=interval,
                enabled=True,
                speak_result=speak,
                task_id=self._editing_sched_id,
            )
            self._reset_scheduler_form()
            self.refresh_scheduled_tasks()
        except Exception as err:
            QMessageBox.warning(self, "Schedule Error", str(err))

    def refresh_scheduled_tasks(self):
        self.sched_list.clear()
        for t in list_scheduled_tasks():
            state = "ON " if t["enabled"] else "OFF"
            rep = f"Every {t['interval_minutes']}m" if t["schedule_type"] == "interval" else SCHEDULE_TYPES.get(t["schedule_type"], t["schedule_type"])
            item = QListWidgetItem(
                f"[{state}]  {t['name']}   |   {t['action_type']}   |   {rep}   |   Next: {t['next_run_at']}   |   Last: {t['last_status']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, t)
            self.sched_list.addItem(item)

        logs = list_scheduled_logs(limit=15)
        if logs:
            lines = [f"[{ran}] {tname} ({st}): {out[:220]}" for _, _, tname, ran, st, out in logs]
            self.sched_log_view.setPlainText("\n".join(lines))

    def _preview_sched_output(self, item):
        t = item.data(Qt.ItemDataRole.UserRole)
        if not t:
            return
        body = (
            f"TASK: {t['name']} (#{t['id']})\n"
            f"ACTION: {t['action_type']} -> {t['payload']}\n"
            f"NEXT RUN: {t['next_run_at']} ({t['schedule_type']})\n"
            f"LAST RUN: {t['last_run_at'] or 'Never'} [{t['last_status']}]\n"
            + ("-" * 45) + "\n"
            + (t["last_output"] or "(No execution output yet.)")
        )
        self.sched_log_view.setPlainText(body)

    def _edit_selected_sched(self, *_):
        item = self.sched_list.currentItem()
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        self._editing_sched_id = t["id"]
        self.sched_name_input.setText(t["name"])
        idx = self.sched_action_combo.findData(t["action_type"])
        if idx >= 0:
            self.sched_action_combo.setCurrentIndex(idx)
        self.sched_payload_input.setText(t["payload"])
        sidx = self.sched_type_combo.findData(t["schedule_type"])
        if sidx >= 0:
            self.sched_type_combo.setCurrentIndex(sidx)
        self.sched_interval_spin.setValue(int(t["interval_minutes"] or 30))
        dt = QDateTime.fromString(t["next_run_at"], "yyyy-MM-dd HH:mm")
        if dt.isValid():
            self.sched_dt_edit.setDateTime(dt)
        self.sched_speak_chk.setChecked(t["speak_result"])
        self.sched_save_btn.setText("UPDATE TASK")

    def _toggle_selected_sched(self):
        item = self.sched_list.currentItem()
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        set_scheduled_task_enabled(t["id"], not t["enabled"])
        self.refresh_scheduled_tasks()

    def _delete_selected_sched(self):
        item = self.sched_list.currentItem()
        if not item:
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        delete_scheduled_task(t["id"])
        if self._editing_sched_id == t["id"]:
            self._reset_scheduler_form()
        self.refresh_scheduled_tasks()

    def _run_selected_sched_now(self):
        item = self.sched_list.currentItem()
        if not item:
            QMessageBox.information(self, "No Selection", "Select a scheduled task to run.")
            return
        t = item.data(Qt.ItemDataRole.UserRole)
        self.sched_log_view.setPlainText(f"[Running scheduled task '{t['name']}' in background...]")
        self.run_scheduled_now_signal.emit(t)

    # ==========================================
    # 4.2 REMINDERS & ALARMS
    # ==========================================

    def _build_reminders_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QHBoxLayout()
        self.rem_title = QLineEdit()
        self.rem_title.setPlaceholderText("Reminder message (e.g., Stand up & stretch, Team meeting)...")

        self.rem_dt = QDateTimeEdit(QDateTime.currentDateTime().addSecs(300))
        self.rem_dt.setCalendarPopup(True)
        self.rem_dt.setDisplayFormat("yyyy-MM-dd HH:mm")

        add_btn = QPushButton("SET REMINDER")
        add_btn.clicked.connect(self._add_reminder)

        form.addWidget(self.rem_title, 3)
        form.addWidget(self.rem_dt, 1)
        form.addWidget(add_btn)
        layout.addLayout(form)

        self.rem_list = QListWidget()
        layout.addWidget(self.rem_list, 1)

        btn_row = QHBoxLayout()
        ref_btn = QPushButton("REFRESH")
        ref_btn.clicked.connect(self.refresh_reminders)
        del_btn = QPushButton("DELETE SELECTED")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_selected_reminder)
        btn_row.addStretch()
        btn_row.addWidget(ref_btn)
        btn_row.addWidget(del_btn)
        layout.addLayout(btn_row)

        return tab

    def _add_reminder(self):
        title = self.rem_title.text().strip()
        if not title:
            return
        dt_str = self.rem_dt.dateTime().toString("yyyy-MM-dd HH:mm")
        add_reminder(title, dt_str)
        self.rem_title.clear()
        self.refresh_reminders()
        self.refresh_daily_summary()

    def refresh_reminders(self):
        self.rem_list.clear()
        for rid, title, remind_at, notified in list_reminders(include_notified=True):
            status = "DONE" if notified else "ACTIVE"
            item = QListWidgetItem(f"[{status}]  {remind_at}  —  {title}")
            item.setData(Qt.ItemDataRole.UserRole, rid)
            self.rem_list.addItem(item)

    def _delete_selected_reminder(self):
        item = self.rem_list.currentItem()
        if not item:
            return
        delete_reminder(item.data(Qt.ItemDataRole.UserRole))
        self.refresh_reminders()
        self.refresh_daily_summary()

    # ==========================================
    # 4.3 NOTES & QUICK CAPTURE
    # ==========================================

    def _build_notes_tab(self):
        tab = QWidget()
        main = QHBoxLayout(tab)

        left = QVBoxLayout()
        self.note_search = QLineEdit()
        self.note_search.setPlaceholderText("Search notes or tags...")
        self.note_search.textChanged.connect(self.refresh_notes)

        self.note_list = QListWidget()
        self.note_list.itemClicked.connect(self._load_selected_note)

        left_btns = QHBoxLayout()
        new_btn = QPushButton("NEW NOTE")
        new_btn.clicked.connect(self._new_note)
        del_btn = QPushButton("DELETE")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_selected_note)
        left_btns.addWidget(new_btn)
        left_btns.addWidget(del_btn)

        left.addWidget(self.note_search)
        left.addWidget(self.note_list, 1)
        left.addLayout(left_btns)

        right = QVBoxLayout()
        self.note_title_input = QLineEdit()
        self.note_title_input.setPlaceholderText("Note title...")
        self.note_tags_input = QLineEdit()
        self.note_tags_input.setPlaceholderText("Tags (comma separated, e.g. study, ideas)")
        self.note_body_input = QTextEdit()
        self.note_body_input.setPlaceholderText("Quick capture notes, snippets, or thoughts...")

        save_btn = QPushButton("SAVE NOTE")
        save_btn.clicked.connect(self._save_note)

        right.addWidget(self.note_title_input)
        right.addWidget(self.note_tags_input)
        right.addWidget(self.note_body_input, 1)
        right.addWidget(save_btn)

        main.addLayout(left, 2)
        main.addLayout(right, 3)
        return tab

    def refresh_notes(self):
        q = self.note_search.text().strip()
        self.note_list.clear()
        for nid, title, content, tags, updated in list_notes(q):
            tag_label = f" [{tags}]" if tags else ""
            item = QListWidgetItem(f"{title}{tag_label}\n{updated}")
            item.setData(Qt.ItemDataRole.UserRole, (nid, title, content, tags))
            self.note_list.addItem(item)

    def _new_note(self):
        self._current_note_id = None
        self.note_title_input.clear()
        self.note_tags_input.clear()
        self.note_body_input.clear()
        self.note_title_input.setFocus()

    def _load_selected_note(self, item):
        nid, title, content, tags = item.data(Qt.ItemDataRole.UserRole)
        self._current_note_id = nid
        self.note_title_input.setText(title)
        self.note_tags_input.setText(tags)
        self.note_body_input.setPlainText(content)

    def _save_note(self):
        title = self.note_title_input.text().strip()
        body = self.note_body_input.toPlainText().strip()
        if not title and not body:
            return
        self._current_note_id = save_note(
            title or "Quick Note",
            body,
            self.note_tags_input.text().strip(),
            note_id=self._current_note_id,
        )
        self.refresh_notes()
        self.refresh_daily_summary()

    def _delete_selected_note(self):
        item = self.note_list.currentItem()
        if not item:
            return
        nid = item.data(Qt.ItemDataRole.UserRole)[0]
        delete_note(nid)
        if self._current_note_id == nid:
            self._new_note()
        self.refresh_notes()
        self.refresh_daily_summary()

    # ==========================================
    # 4.4 CALENDAR INTEGRATION
    # ==========================================

    def _build_calendar_tab(self):
        tab = QWidget()
        main = QHBoxLayout(tab)

        left = QVBoxLayout()
        self.calendar = QCalendarWidget()
        self.calendar.setGridVisible(True)
        self.calendar.selectionChanged.connect(self.refresh_calendar_events)
        left.addWidget(self.calendar)

        export_btn = QPushButton("EXPORT CALENDAR (.ICS)")
        export_btn.clicked.connect(self._export_ics)
        left.addWidget(export_btn)

        right = QVBoxLayout()
        self.cal_date_label = QLabel()
        self.cal_date_label.setObjectName("provider_status")

        form = QHBoxLayout()
        self.cal_time_input = QLineEdit()
        self.cal_time_input.setPlaceholderText("Time (e.g. 14:30)")
        self.cal_time_input.setMaximumWidth(115)
        self.cal_title_input = QLineEdit()
        self.cal_title_input.setPlaceholderText("Event title...")
        add_ev_btn = QPushButton("ADD EVENT")
        add_ev_btn.clicked.connect(self._add_calendar_event)
        form.addWidget(self.cal_time_input)
        form.addWidget(self.cal_title_input, 1)
        form.addWidget(add_ev_btn)

        self.cal_event_list = QListWidget()
        del_ev_btn = QPushButton("DELETE EVENT")
        del_ev_btn.setObjectName("danger_button")
        del_ev_btn.clicked.connect(self._delete_calendar_event)

        right.addWidget(self.cal_date_label)
        right.addLayout(form)
        right.addWidget(self.cal_event_list, 1)
        right.addWidget(del_ev_btn)

        main.addLayout(left, 3)
        main.addLayout(right, 2)
        return tab

    def refresh_calendar_events(self):
        d = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.cal_date_label.setText(f"Events for {d}")
        self.cal_event_list.clear()
        for eid, ev_date, ev_time, title, notes in list_calendar_events(d):
            prefix = f"{ev_time}  |  " if ev_time else ""
            item = QListWidgetItem(f"{prefix}{title}")
            item.setData(Qt.ItemDataRole.UserRole, eid)
            self.cal_event_list.addItem(item)

    def _add_calendar_event(self):
        title = self.cal_title_input.text().strip()
        if not title:
            return
        d = self.calendar.selectedDate().toString("yyyy-MM-dd")
        add_calendar_event(d, title, self.cal_time_input.text().strip())
        self.cal_title_input.clear()
        self.cal_time_input.clear()
        self.refresh_calendar_events()
        self.refresh_daily_summary()

    def _delete_calendar_event(self):
        item = self.cal_event_list.currentItem()
        if not item:
            return
        delete_calendar_event(item.data(Qt.ItemDataRole.UserRole))
        self.refresh_calendar_events()
        self.refresh_daily_summary()

    def _export_ics(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Calendar", "jarvis_calendar.ics", "iCalendar (*.ics)")
        if not path:
            return
        count = export_calendar_ics(path)
        QMessageBox.information(self, "Calendar Exported", f"Exported {count} event(s) to:\n{path}")

    # ==========================================
    # 4.5 & 4.6 STUDY TIMER / POMODORO & PROGRESS
    # ==========================================

    def _build_pomodoro_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        self.pomo_mode_label = QLabel("MODE: FOCUS SESSION")
        self.pomo_mode_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_mode_label.setObjectName("provider_status")

        self.pomo_time_label = QLabel("25:00")
        self.pomo_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pomo_time_label.setStyleSheet("font-size: 46px; font-weight: bold; padding: 10px;")

        topic_row = QHBoxLayout()
        self.study_topic_input = QLineEdit()
        self.study_topic_input.setPlaceholderText("What are you studying? (e.g. Python, Cybersecurity, Algorithms)")
        self.daily_goal_spin = QSpinBox()
        self.daily_goal_spin.setRange(15, 720)
        self.daily_goal_spin.setValue(120)
        self.daily_goal_spin.setSuffix(" min goal")
        self.daily_goal_spin.valueChanged.connect(self.refresh_study_progress)
        topic_row.addWidget(self.study_topic_input, 3)
        topic_row.addWidget(self.daily_goal_spin, 1)

        presets = QHBoxLayout()
        for label, mins, mode in [
            ("Focus 25m", 25, "Focus"),
            ("Deep Focus 50m", 50, "Focus"),
            ("Short Break 5m", 5, "Break"),
            ("Long Break 15m", 15, "Break"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, m=mins, md=mode: self._set_pomodoro(m, md))
            presets.addWidget(b)

        controls = QHBoxLayout()
        self.pomo_start_btn = QPushButton("START TIMER")
        self.pomo_start_btn.clicked.connect(self._toggle_pomodoro)
        reset_btn = QPushButton("RESET")
        reset_btn.clicked.connect(self._reset_pomodoro)
        log_btn = QPushButton("LOG SESSION NOW")
        log_btn.clicked.connect(self._log_manual_study)
        controls.addWidget(self.pomo_start_btn)
        controls.addWidget(reset_btn)
        controls.addWidget(log_btn)

        card_layout.addWidget(self.pomo_mode_label)
        card_layout.addWidget(self.pomo_time_label)
        card_layout.addLayout(topic_row)
        card_layout.addLayout(presets)
        card_layout.addLayout(controls)
        layout.addWidget(card)

        self.study_progress_label = QLabel("Daily Study Progress: 0 / 120 min")
        self.study_progress_bar = QProgressBar()
        self.study_log_list = QListWidget()

        layout.addWidget(self.study_progress_label)
        layout.addWidget(self.study_progress_bar)
        layout.addWidget(self.study_log_list, 1)

        return tab

    def _set_pomodoro(self, minutes, mode):
        self._pomo_timer.stop()
        self._pomo_running = False
        self._pomo_mode = mode
        self._pomo_total = minutes * 60
        self._pomo_remaining = self._pomo_total
        self.pomo_start_btn.setText("START TIMER")
        self.pomo_mode_label.setText(f"MODE: {mode.upper()} SESSION ({minutes} min)")
        self._update_pomo_display()

    def _toggle_pomodoro(self):
        if self._pomo_running:
            self._pomo_timer.stop()
            self._pomo_running = False
            self.pomo_start_btn.setText("RESUME TIMER")
        else:
            self._pomo_timer.start(1000)
            self._pomo_running = True
            self.pomo_start_btn.setText("PAUSE TIMER")

    def _reset_pomodoro(self):
        self._pomo_timer.stop()
        self._pomo_running = False
        self._pomo_remaining = self._pomo_total
        self.pomo_start_btn.setText("START TIMER")
        self._update_pomo_display()

    def _tick_pomodoro(self):
        self._pomo_remaining -= 1
        self._update_pomo_display()
        if self._pomo_remaining <= 0:
            self._pomo_timer.stop()
            self._pomo_running = False
            self.pomo_start_btn.setText("START TIMER")
            mins = max(1, self._pomo_total // 60)
            if self._pomo_mode == "Focus":
                topic = self.study_topic_input.text().strip() or "Focused Study"
                log_study_session(topic, mins)
                self.refresh_study_progress()
                self.refresh_daily_summary()
                self.announce_signal.emit(f"Focus session complete! Logged {mins} minutes of {topic}.")
            else:
                self.announce_signal.emit("Break finished! Ready for your next focus session.")
            QMessageBox.information(self, "Pomodoro Complete", f"{self._pomo_mode} session ({mins} min) completed!")
            self._pomo_remaining = self._pomo_total
            self._update_pomo_display()

    def _log_manual_study(self):
        mins = max(1, (self._pomo_total - self._pomo_remaining) // 60)
        if mins < 1:
            mins = max(1, self._pomo_total // 60)
        topic = self.study_topic_input.text().strip() or "Study Session"
        log_study_session(topic, mins)
        self.refresh_study_progress()
        self.refresh_daily_summary()

    def _update_pomo_display(self):
        m, s = divmod(max(0, self._pomo_remaining), 60)
        self.pomo_time_label.setText(f"{m:02d}:{s:02d}")

    def refresh_study_progress(self):
        prog = get_study_progress()
        goal = self.daily_goal_spin.value()
        today_min = prog["today_minutes"]
        pct = min(100, int((today_min / max(1, goal)) * 100))
        self.study_progress_label.setText(
            f"Daily Study Progress: {today_min} / {goal} min ({len(prog['today_sessions'])} sessions today | All-time: {prog['all_time_minutes']} min)"
        )
        self.study_progress_bar.setValue(pct)
        self.study_log_list.clear()
        for _, topic, mins, _, created in prog["today_sessions"]:
            self.study_log_list.addItem(f"{created}  —  {topic} ({mins} min)")

    # ==========================================
    # 4.8 DAILY SUMMARY
    # ==========================================

    def _build_summary_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btns = QHBoxLayout()
        refresh_btn = QPushButton("REFRESH SUMMARY")
        refresh_btn.clicked.connect(self.refresh_daily_summary)
        self.ai_brief_btn = QPushButton("GENERATE AI DAILY BRIEFING")
        self.ai_brief_btn.clicked.connect(self._generate_ai_briefing)
        btns.addWidget(refresh_btn)
        btns.addWidget(self.ai_brief_btn)
        btns.addStretch()

        self.summary_output = QTextEdit()
        self.summary_output.setReadOnly(True)

        layout.addLayout(btns)
        layout.addWidget(self.summary_output, 1)
        return tab

    def refresh_daily_summary(self):
        self.summary_output.setPlainText(build_daily_summary_text())

    def _generate_ai_briefing(self):
        if self._ai_worker is not None:
            return
        raw_summary = build_daily_summary_text()
        self.ai_brief_btn.setEnabled(False)
        self.summary_output.setPlainText(raw_summary + "\n\n[Generating JARVIS AI Strategic Briefing...]")
        self._ai_worker = JarvisWorker(
            message=(
                "Based on this user's daily productivity snapshot, give a crisp, encouraging "
                "strategic daily briefing with top 3 priorities and a suggested schedule:\n\n"
                + raw_summary
            ),
            task="assistant_prompt",
            personality_override="EXECUTIVE",
            style_override="Bullet Points",
            extra={"title": "AI DAILY BRIEFING", "prefix": raw_summary + "\n\n=== JARVIS AI BRIEFING ==="},
        )
        self._ai_worker.task_completed.connect(lambda _t, text: self.summary_output.setPlainText(text))
        self._ai_worker.error_occurred.connect(lambda err: self.summary_output.append(f"\n[AI Error] {err}"))
        self._ai_worker.finished.connect(self._on_ai_finished)
        self._ai_worker.start()

    def _on_ai_finished(self):
        w = self._ai_worker
        self._ai_worker = None
        self.ai_brief_btn.setEnabled(True)
        if w:
            w.deleteLater()

    def shutdown(self):
        self._pomo_timer.stop()
        if self._ai_worker and self._ai_worker.isRunning():
            self._ai_worker.quit()
            self._ai_worker.wait(1000)

