"""Memory & Conversation History Center for JARVIS (1.6, 1.7, 1.8, 3.9)."""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QMessageBox,
    QTabWidget,
    QComboBox,
    QTextEdit,
)
from PySide6.QtCore import Qt, Signal

from core.memory import (
    search_messages,
    delete_message,
    clear_all_memory,
    list_sessions,
    delete_session,
    get_long_term_memories,
    add_long_term_memory,
    delete_long_term_memory,
    clear_long_term_memory,
)
from core.brain import start_new_chat
from interface.worker import JarvisWorker


class MemoryManager(QWidget):
    """Unified Conversation History (3.9), Message Search (1.8), Summaries (1.6), and Long-Term Memory (1.7)."""

    session_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("JARVIS Memory & History Center")
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("MEMORY & CONVERSATION HISTORY")
        title.setObjectName("page_title")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_sessions_tab(), "Conversation History")
        self.tabs.addTab(self._build_search_tab(), "Search Messages")
        self.tabs.addTab(self._build_ltm_tab(), "Long-Term Memory")
        layout.addWidget(self.tabs, 1)

        self.refresh()

    # ==========================================
    # TAB 1: CONVERSATION HISTORY & SUMMARIES (3.9, 1.6)
    # ==========================================

    def _build_sessions_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.session_list = QListWidget()
        self.session_list.itemClicked.connect(self._preview_session_summary)
        self.session_list.itemDoubleClicked.connect(self._open_selected_session)

        self.session_summary_box = QTextEdit()
        self.session_summary_box.setReadOnly(True)
        self.session_summary_box.setMaximumHeight(130)
        self.session_summary_box.setPlaceholderText("Select a conversation to view its summary, or click 'SUMMARIZE SESSION'...")

        btns = QHBoxLayout()
        open_btn = QPushButton("OPEN IN CHAT")
        open_btn.clicked.connect(self._open_selected_session)
        self.sum_btn = QPushButton("SUMMARIZE SESSION")
        self.sum_btn.clicked.connect(self._summarize_selected_session)
        del_btn = QPushButton("DELETE SESSION")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_selected_session)
        btns.addWidget(open_btn)
        btns.addWidget(self.sum_btn)
        btns.addStretch()
        btns.addWidget(del_btn)

        layout.addWidget(self.session_list, 2)
        layout.addWidget(self.session_summary_box, 1)
        layout.addLayout(btns)
        return tab

    def refresh_sessions(self):
        self.session_list.clear()
        for sid, title, summary, updated_at, msg_count in list_sessions():
            has_sum = " [Summarized]" if summary else ""
            item = QListWidgetItem(f"{title}{has_sum}\n{msg_count} messages  |  Updated: {updated_at}")
            item.setData(Qt.ItemDataRole.UserRole, (sid, summary))
            self.session_list.addItem(item)

    def _preview_session_summary(self, item):
        _, summary = item.data(Qt.ItemDataRole.UserRole)
        self.session_summary_box.setPlainText(summary or "(No summary generated for this session yet.)")

    def _open_selected_session(self, *_):
        item = self.session_list.currentItem()
        if not item:
            return
        sid, _ = item.data(Qt.ItemDataRole.UserRole)
        self.session_selected.emit(sid)

    def _summarize_selected_session(self):
        if self._worker is not None:
            return
        item = self.session_list.currentItem()
        if not item:
            return
        sid, _ = item.data(Qt.ItemDataRole.UserRole)
        self.sum_btn.setEnabled(False)
        self.session_summary_box.setPlainText("[Generating AI conversation summary...]")
        self._worker = JarvisWorker(task="summarize", extra={"session_id": sid})
        self._worker.task_completed.connect(self._on_summary_done)
        self._worker.error_occurred.connect(lambda err: self.session_summary_box.setPlainText(f"[Error] {err}"))
        self._worker.finished.connect(self._cleanup_worker)
        self._worker.start()

    def _on_summary_done(self, _title, summary):
        self.session_summary_box.setPlainText(summary)
        self.refresh_sessions()

    def _cleanup_worker(self):
        w = self._worker
        self._worker = None
        self.sum_btn.setEnabled(True)
        if w:
            w.deleteLater()

    def _delete_selected_session(self):
        item = self.session_list.currentItem()
        if not item:
            return
        sid, _ = item.data(Qt.ItemDataRole.UserRole)
        ans = QMessageBox.question(
            self, "Delete Session", "Delete this entire conversation session?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            delete_session(sid)
            self.refresh()

    # ==========================================
    # TAB 2: SEARCH PREVIOUS CONVERSATIONS (1.8)
    # ==========================================

    def _build_search_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search saved conversations...")
        self.search_input.textChanged.connect(self.refresh_messages)

        self.message_list = QListWidget()

        buttons = QHBoxLayout()
        self.delete_button = QPushButton("DELETE SELECTED")
        self.delete_button.clicked.connect(self.delete_selected)
        self.clear_button = QPushButton("CLEAR ALL MEMORY")
        self.clear_button.setObjectName("danger_button")
        self.clear_button.clicked.connect(self.clear_all)
        self.refresh_button = QPushButton("REFRESH")
        self.refresh_button.clicked.connect(self.refresh)

        buttons.addWidget(self.delete_button)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.refresh_button)

        layout.addWidget(self.search_input)
        layout.addWidget(self.message_list, 1)
        layout.addLayout(buttons)
        return tab

    def refresh_messages(self):
        query = self.search_input.text().strip()
        messages = search_messages(query)
        self.message_list.clear()
        for message_id, role, message, timestamp in messages:
            preview = (message or "").replace("\n", " ")[:140]
            item = QListWidgetItem(f"{(role or 'unknown').upper()} | {timestamp}\n{preview}")
            item.setData(Qt.ItemDataRole.UserRole, message_id)
            self.message_list.addItem(item)

    def delete_selected(self):
        item = self.message_list.currentItem()
        if item is None:
            QMessageBox.information(self, "No selection", "Please select a message first.")
            return
        message_id = item.data(Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(
            self, "Confirm deletion", "Are you sure you want to delete this message?"
        )
        if answer == QMessageBox.StandardButton.Yes:
            delete_message(message_id)
            self.refresh()

    def clear_all(self):
        answer = QMessageBox.question(
            self, "Clear all memory",
            "This will permanently delete all saved conversations. Continue?"
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            clear_all_memory()
            start_new_chat()
            self.refresh()
            QMessageBox.information(self, "Memory cleared", "All saved conversations have been deleted.")
        except Exception as error:
            QMessageBox.critical(self, "Error", str(error))

    # ==========================================
    # TAB 3: LONG-TERM MEMORY (1.7)
    # ==========================================

    def _build_ltm_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form = QHBoxLayout()
        self.ltm_category = QComboBox()
        self.ltm_category.addItems(["profile", "preference", "project", "study", "general"])
        self.ltm_fact_input = QLineEdit()
        self.ltm_fact_input.setPlaceholderText("Add a persistent fact JARVIS should always remember...")
        self.ltm_fact_input.returnPressed.connect(self._add_ltm)
        add_btn = QPushButton("REMEMBER")
        add_btn.clicked.connect(self._add_ltm)
        form.addWidget(self.ltm_category)
        form.addWidget(self.ltm_fact_input, 3)
        form.addWidget(add_btn)

        self.ltm_list = QListWidget()

        btns = QHBoxLayout()
        del_btn = QPushButton("FORGET SELECTED")
        del_btn.clicked.connect(self._delete_ltm)
        clear_btn = QPushButton("CLEAR LONG-TERM MEMORY")
        clear_btn.setObjectName("danger_button")
        clear_btn.clicked.connect(self._clear_ltm)
        btns.addWidget(del_btn)
        btns.addStretch()
        btns.addWidget(clear_btn)

        layout.addLayout(form)
        layout.addWidget(self.ltm_list, 1)
        layout.addLayout(btns)
        return tab

    def refresh_ltm(self):
        self.ltm_list.clear()
        for mid, cat, fact, created in get_long_term_memories():
            item = QListWidgetItem(f"[{cat.upper()}]  {fact}   ({created})")
            item.setData(Qt.ItemDataRole.UserRole, mid)
            self.ltm_list.addItem(item)

    def _add_ltm(self):
        fact = self.ltm_fact_input.text().strip()
        if not fact:
            return
        add_long_term_memory(fact, category=self.ltm_category.currentText())
        self.ltm_fact_input.clear()
        self.refresh_ltm()

    def _delete_ltm(self):
        item = self.ltm_list.currentItem()
        if not item:
            return
        delete_long_term_memory(item.data(Qt.ItemDataRole.UserRole))
        self.refresh_ltm()

    def _clear_ltm(self):
        ans = QMessageBox.question(
            self, "Clear Long-Term Memory", "Delete all long-term remembered facts?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans == QMessageBox.StandardButton.Yes:
            clear_long_term_memory()
            self.refresh_ltm()

    def refresh(self):
        self.refresh_sessions()
        self.refresh_messages()
        self.refresh_ltm()

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)
