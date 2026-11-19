"""Desktop Automation (2.1 - 2.9) & Advanced Intelligence Tools (7.2 - 7.8) Page for JARVIS."""

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
    QSlider,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QApplication,
)
from PySide6.QtCore import Qt, Signal

from tools.computer import (
    APP_ALIASES,
    SITE_SHORTCUTS,
    open_application,
    open_website,
    search_google,
    search_youtube,
    create_folder,
    create_file,
    plan_folder_organization,
    execute_folder_organization,
    volume_up,
    volume_down,
    volume_mute_toggle,
    set_volume_percent,
    capture_screenshot_qapp,
    is_potentially_dangerous_command,
    run_approved_command,
)
from tools.documents import extract_document_text
from tools.plugins import plugin_manager
from tools.rag import list_indexed_files, clear_rag_index
from core.memory import (
    save_custom_command,
    get_custom_commands,
    delete_custom_command,
)
from interface.worker import JarvisWorker


class AutomationToolsPage(QWidget):
    """Desktop Automation, Document/PDF Reader, Web/YouTube Tools, Plugins & Custom Commands."""

    commands_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._loaded_doc = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("DESKTOP AUTOMATION & ADVANCED TOOLS")
        title.setObjectName("page_title")
        layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_desktop_tab(), "Desktop Control")
        self.tabs.addTab(self._build_files_docs_tab(), "Files, PDF & Docs")
        self.tabs.addTab(self._build_rag_tab(), "Knowledge Base (RAG)")
        self.tabs.addTab(self._build_clipboard_tab(), "Smart Clipboard")
        self.tabs.addTab(self._build_web_yt_tab(), "Web & YouTube AI")
        self.tabs.addTab(self._build_plugins_commands_tab(), "Plugins & Commands")
        layout.addWidget(self.tabs, 1)

        self._clip_history = []
        self._install_clipboard_watcher()
        self.refresh_rag_files()
        self.refresh_plugins()
        self.refresh_custom_commands()

    # ==========================================
    # TAB 1: DESKTOP CONTROL (2.1, 2.2, 2.3, 2.7, 2.8, 2.9)
    # ==========================================

    def _build_desktop_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # 2.1 Open Applications & 2.2 Websites
        launch_box = QGroupBox("Launch Apps, Websites & Searches (2.1 - 2.3)")
        lb_layout = QVBoxLayout(launch_box)

        app_row = QHBoxLayout()
        self.app_combo = QComboBox()
        self.app_combo.setEditable(True)
        self.app_combo.addItems(sorted(APP_ALIASES.keys()))
        open_app_btn = QPushButton("OPEN APP")
        open_app_btn.clicked.connect(self._open_app)
        app_row.addWidget(QLabel("Application:"))
        app_row.addWidget(self.app_combo, 2)
        app_row.addWidget(open_app_btn, 1)

        site_row = QHBoxLayout()
        self.site_combo = QComboBox()
        self.site_combo.setEditable(True)
        self.site_combo.addItems(sorted(SITE_SHORTCUTS.keys()))
        open_site_btn = QPushButton("OPEN WEBSITE")
        open_site_btn.clicked.connect(self._open_site)
        site_row.addWidget(QLabel("Website/URL:"))
        site_row.addWidget(self.site_combo, 2)
        site_row.addWidget(open_site_btn, 1)

        search_row = QHBoxLayout()
        self.quick_search_input = QLineEdit()
        self.quick_search_input.setPlaceholderText("Enter search query for Google or YouTube...")
        g_btn = QPushButton("SEARCH GOOGLE")
        g_btn.clicked.connect(self._search_google)
        yt_btn = QPushButton("SEARCH YOUTUBE")
        yt_btn.clicked.connect(self._search_youtube)
        search_row.addWidget(self.quick_search_input, 3)
        search_row.addWidget(g_btn, 1)
        search_row.addWidget(yt_btn, 1)

        lb_layout.addLayout(app_row)
        lb_layout.addLayout(site_row)
        lb_layout.addLayout(search_row)
        layout.addWidget(launch_box)

        # 2.7 Volume & 2.8 Screenshot
        sys_box = QGroupBox("System Volume & Screenshot with Permission (2.7 - 2.8)")
        sb_layout = QHBoxLayout(sys_box)

        vol_down_btn = QPushButton("VOL -")
        vol_down_btn.clicked.connect(lambda: self._log_desktop(volume_down()))
        vol_mute_btn = QPushButton("MUTE / UNMUTE")
        vol_mute_btn.clicked.connect(lambda: self._log_desktop(volume_mute_toggle()))
        vol_up_btn = QPushButton("VOL +")
        vol_up_btn.clicked.connect(lambda: self._log_desktop(volume_up()))

        self.vol_slider = QSlider(Qt.Orientation.Horizontal)
        self.vol_slider.setRange(0, 100)
        self.vol_slider.setValue(50)
        set_vol_btn = QPushButton("SET VOL %")
        set_vol_btn.clicked.connect(lambda: self._log_desktop(set_volume_percent(self.vol_slider.value())))

        shot_btn = QPushButton("TAKE SCREENSHOT")
        shot_btn.clicked.connect(self._take_screenshot)

        sb_layout.addWidget(vol_down_btn)
        sb_layout.addWidget(vol_mute_btn)
        sb_layout.addWidget(vol_up_btn)
        sb_layout.addWidget(self.vol_slider, 2)
        sb_layout.addWidget(set_vol_btn)
        sb_layout.addWidget(shot_btn)
        layout.addWidget(sys_box)

        # WhatsApp Web in Google Chrome Automation
        wa_box = QGroupBox("WhatsApp Web Chrome Automation (Messaging & Calling)")
        wa_layout = QVBoxLayout(wa_box)

        wa_top_row = QHBoxLayout()
        self.wa_contact_input = QLineEdit()
        self.wa_contact_input.setPlaceholderText("Contact Name (e.g. Alex, Mom) or Phone (+91...)")
        wa_open_btn = QPushButton("OPEN WHATSAPP WEB")
        wa_open_btn.clicked.connect(self._open_whatsapp_web_ui)
        wa_top_row.addWidget(QLabel("Target Contact:"))
        wa_top_row.addWidget(self.wa_contact_input, 3)
        wa_top_row.addWidget(wa_open_btn, 1)

        wa_msg_row = QHBoxLayout()
        self.wa_msg_input = QLineEdit()
        self.wa_msg_input.setPlaceholderText("Enter message to search, type & send via Chrome...")
        self.wa_msg_input.returnPressed.connect(self._send_whatsapp_ui)
        wa_send_btn = QPushButton("SEND VIA CHROME")
        wa_send_btn.clicked.connect(self._send_whatsapp_ui)
        wa_call_btn = QPushButton("CALL CONTACT")
        wa_call_btn.clicked.connect(self._call_whatsapp_ui)

        wa_msg_row.addWidget(self.wa_msg_input, 3)
        wa_msg_row.addWidget(wa_send_btn, 1)
        wa_msg_row.addWidget(wa_call_btn, 1)

        wa_layout.addLayout(wa_top_row)
        wa_layout.addLayout(wa_msg_row)
        layout.addWidget(wa_box)

        # 2.9 Approved Terminal Commands
        term_box = QGroupBox("Approved Terminal Command Executor (2.9)")
        tb_layout = QVBoxLayout(term_box)
        cmd_row = QHBoxLayout()
        self.cmd_input = QLineEdit()
        self.cmd_input.setPlaceholderText("Enter terminal command (always asks explicit confirmation before executing)...")
        self.cmd_input.returnPressed.connect(self._run_terminal_command)
        run_cmd_btn = QPushButton("REQUEST & RUN")
        run_cmd_btn.clicked.connect(self._run_terminal_command)
        cmd_row.addWidget(self.cmd_input, 4)
        cmd_row.addWidget(run_cmd_btn, 1)
        tb_layout.addLayout(cmd_row)

        self.desktop_output = QTextEdit()
        self.desktop_output.setReadOnly(True)
        self.desktop_output.setPlaceholderText("Automation & command execution results appear here...")
        tb_layout.addWidget(self.desktop_output, 1)
        layout.addWidget(term_box, 1)

        return tab

    def _log_desktop(self, text: str):
        self.desktop_output.append(str(text))

    def _open_app(self):
        try:
            self._log_desktop(open_application(self.app_combo.currentText()))
        except Exception as err:
            self._log_desktop(f"[ERROR] {err}")

    def _open_site(self):
        try:
            self._log_desktop(open_website(self.site_combo.currentText()))
        except Exception as err:
            self._log_desktop(f"[ERROR] {err}")

    def _search_google(self):
        try:
            self._log_desktop(search_google(self.quick_search_input.text()))
        except Exception as err:
            self._log_desktop(f"[ERROR] {err}")

    def _search_youtube(self):
        try:
            self._log_desktop(search_youtube(self.quick_search_input.text()))
        except Exception as err:
            self._log_desktop(f"[ERROR] {err}")

    def _open_whatsapp_web_ui(self):
        from tools.whatsapp import open_whatsapp_web
        try:
            self._log_desktop(open_whatsapp_web())
        except Exception as err:
            self._log_desktop(f"[WHATSAPP ERROR] {err}")

    def _send_whatsapp_ui(self):
        from tools.whatsapp import send_whatsapp_message
        contact = self.wa_contact_input.text().strip()
        msg = self.wa_msg_input.text().strip()
        if not contact:
            QMessageBox.warning(self, "WhatsApp Automation", "Please specify a contact name or phone number.")
            return
        try:
            res = send_whatsapp_message(contact=contact, message=msg, auto_send=True)
            self._log_desktop(res)
            self.wa_msg_input.clear()
        except Exception as err:
            self._log_desktop(f"[WHATSAPP ERROR] {err}")

    def _call_whatsapp_ui(self):
        from tools.whatsapp import call_whatsapp_contact
        contact = self.wa_contact_input.text().strip()
        if not contact:
            QMessageBox.warning(self, "WhatsApp Automation", "Please specify a contact name or phone number.")
            return
        try:
            res = call_whatsapp_contact(contact=contact, call_type="voice")
            self._log_desktop(res)
        except Exception as err:
            self._log_desktop(f"[WHATSAPP ERROR] {err}")

    def _take_screenshot(self):
        ans = QMessageBox.question(
            self,
            "Screenshot Permission",
            "JARVIS requests permission to capture a screenshot of your primary screen and save it to data/screenshots/. Allow?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            self._log_desktop("Screenshot cancelled by user.")
            return
        try:
            path = capture_screenshot_qapp(QApplication.instance())
            self._log_desktop(f"Screenshot saved: {path}")
        except Exception as err:
            self._log_desktop(f"[Screenshot Error] {err}")

    def _run_terminal_command(self):
        if self._worker is not None:
            self._log_desktop("[Busy] Wait for the current background task to finish.")
            return
        cmd = self.cmd_input.text().strip()
        if not cmd:
            return
        warning = ""
        if is_potentially_dangerous_command(cmd):
            warning = "\n\nWARNING: This command matches a potentially destructive pattern!"

        ans = QMessageBox.question(
            self,
            "Approve Terminal Command",
            f"Do you approve executing the following command?\n\n{cmd}{warning}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ans != QMessageBox.StandardButton.Yes:
            self._log_desktop(f"Cancelled command: {cmd}")
            return

        self._log_desktop(f"[Executing] $ {cmd} ...")
        self._worker = JarvisWorker(message=cmd, task="run_command")
        self._worker.task_completed.connect(lambda _t, out: self._log_desktop(out))
        self._worker.error_occurred.connect(lambda err: self._log_desktop(f"[Command Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ==========================================
    # TAB 2: FILES, FOLDER ORGANIZER, PDF & DOCS (2.4, 2.5, 7.2, 7.3)
    # ==========================================

    def _build_files_docs_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(10)

        # 2.4 Create File/Folder
        create_box = QGroupBox("Create Files & Folders (2.4)")
        cb = QVBoxLayout(create_box)
        row1 = QHBoxLayout()
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("Relative path (inside workspace_files/) or full path (e.g. notes/plan.txt or my_project)")
        mk_dir_btn = QPushButton("CREATE FOLDER")
        mk_dir_btn.clicked.connect(self._create_folder)
        mk_file_btn = QPushButton("CREATE FILE")
        mk_file_btn.clicked.connect(self._create_file)
        row1.addWidget(self.path_input, 3)
        row1.addWidget(mk_dir_btn)
        row1.addWidget(mk_file_btn)

        self.file_content_input = QLineEdit()
        self.file_content_input.setPlaceholderText("Optional initial content for created file...")
        cb.addLayout(row1)
        cb.addWidget(self.file_content_input)
        layout.addWidget(create_box)

        # 2.5 Organize Folder
        org_box = QGroupBox("Smart Folder Organizer (2.5)")
        ob = QHBoxLayout(org_box)
        self.org_folder_input = QLineEdit()
        self.org_folder_input.setPlaceholderText("Select a folder to organize into Documents / Images / Code / Archives...")
        browse_org_btn = QPushButton("BROWSE")
        browse_org_btn.clicked.connect(self._browse_org_folder)
        org_btn = QPushButton("PREVIEW & ORGANIZE")
        org_btn.clicked.connect(self._organize_folder)
        ob.addWidget(self.org_folder_input, 3)
        ob.addWidget(browse_org_btn)
        ob.addWidget(org_btn)
        layout.addWidget(org_box)

        # 7.2 & 7.3 PDF & Document Reader + AI Summarizer
        doc_box = QGroupBox("PDF & Document Reader / AI Summarizer (7.2 - 7.3)")
        db = QVBoxLayout(doc_box)
        drow = QHBoxLayout()
        open_doc_btn = QPushButton("LOAD PDF / DOCX / TEXT")
        open_doc_btn.clicked.connect(self._load_document)
        self.doc_question = QLineEdit()
        self.doc_question.setPlaceholderText("Ask a question about the loaded document (leave blank to summarize)...")
        self.doc_ai_btn = QPushButton("SUMMARIZE / ANALYZE")
        self.doc_ai_btn.clicked.connect(self._analyze_document)
        drow.addWidget(open_doc_btn)
        drow.addWidget(self.doc_question, 3)
        drow.addWidget(self.doc_ai_btn)
        db.addLayout(drow)

        self.doc_output = QTextEdit()
        self.doc_output.setReadOnly(True)
        self.doc_output.setPlaceholderText("Extracted PDF/DOCX/file text and AI summaries appear here...")
        db.addWidget(self.doc_output, 1)
        layout.addWidget(doc_box, 1)

        return tab

    def _create_folder(self):
        try:
            msg = create_folder(self.path_input.text())
            self.doc_output.setPlainText(msg)
        except Exception as err:
            self.doc_output.setPlainText(f"[Error] {err}")

    def _create_file(self):
        try:
            msg = create_file(self.path_input.text(), self.file_content_input.text())
            self.doc_output.setPlainText(msg)
        except Exception as err:
            self.doc_output.setPlainText(f"[Error] {err}")

    def _browse_org_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to Organize")
        if folder:
            self.org_folder_input.setText(folder)

    def _organize_folder(self):
        folder = self.org_folder_input.text().strip()
        if not folder:
            return
        try:
            moves = plan_folder_organization(folder)
            if not moves:
                self.doc_output.setPlainText("No loose files found in that folder to organize.")
                return
            preview = "\n".join(f"  {src.name}  ->  {dst.parent.name}/{dst.name}" for src, dst in moves[:20])
            if len(moves) > 20:
                preview += f"\n  ...and {len(moves) - 20} more files."
            ans = QMessageBox.question(
                self,
                "Confirm Folder Organization",
                f"Move {len(moves)} file(s) into categorized subfolders?\n\n{preview}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans == QMessageBox.StandardButton.Yes:
                res = execute_folder_organization(folder)
                self.doc_output.setPlainText(res)
        except Exception as err:
            self.doc_output.setPlainText(f"[Organize Error] {err}")

    def _load_document(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Document", "", "Documents (*.pdf *.docx *.txt *.md *.csv *.json *.py *.log);;All Files (*)"
        )
        if not path:
            return
        try:
            meta = extract_document_text(path)
            self._loaded_doc = meta
            pages_info = f" | Pages: {meta['pages']}" if meta["pages"] else ""
            header = f"Loaded: {meta['name']} ({meta['word_count']} words{pages_info})\n" + ("=" * 50) + "\n\n"
            self.doc_output.setPlainText(header + meta["text"][:10000])
        except Exception as err:
            self.doc_output.setPlainText(f"[Document Read Error] {err}")

    def _analyze_document(self):
        if self._worker is not None:
            return
        if not self._loaded_doc:
            self.doc_output.setPlainText("Please load a PDF, DOCX, or text file first.")
            return
        question = self.doc_question.text().strip() or (
            "Summarize this document clearly with: 1) Executive Summary, 2) Key Points, 3) Actionable Insights."
        )
        self.doc_ai_btn.setEnabled(False)
        self.doc_output.setPlainText(f"[JARVIS analyzing {self._loaded_doc['name']}...]")
        self._worker = JarvisWorker(
            message=question,
            task="assistant_prompt",
            document_context=self._loaded_doc["text"],
            extra={"title": f"Document Analysis: {self._loaded_doc['name']}"},
        )
        self._worker.task_completed.connect(lambda _t, body: self.doc_output.setPlainText(body))
        self._worker.error_occurred.connect(lambda err: self.doc_output.setPlainText(f"[ERROR] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ==========================================
    # TAB 3: WEB SEARCH & YOUTUBE SUMMARIZER (7.4, 7.5)
    # ==========================================

    def _build_web_yt_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        web_row = QHBoxLayout()
        self.web_query_input = QLineEdit()
        self.web_query_input.setPlaceholderText("Search the web and get an AI-grounded answer with sources...")
        self.web_query_input.returnPressed.connect(self._run_web_search)
        self.web_btn = QPushButton("WEB SEARCH")
        self.web_btn.clicked.connect(self._run_web_search)
        web_row.addWidget(self.web_query_input, 4)
        web_row.addWidget(self.web_btn, 1)

        yt_row = QHBoxLayout()
        self.yt_url_input = QLineEdit()
        self.yt_url_input.setPlaceholderText("Paste a YouTube video URL (or video ID) to summarize...")
        self.yt_url_input.returnPressed.connect(self._run_youtube_summary)
        self.yt_btn = QPushButton("SUMMARIZE YOUTUBE")
        self.yt_btn.clicked.connect(self._run_youtube_summary)
        yt_row.addWidget(self.yt_url_input, 4)
        yt_row.addWidget(self.yt_btn, 1)

        self.web_yt_output = QTextEdit()
        self.web_yt_output.setReadOnly(True)
        self.web_yt_output.setPlaceholderText("Web search results and YouTube video summaries appear here...")

        layout.addLayout(web_row)
        layout.addLayout(yt_row)
        layout.addWidget(self.web_yt_output, 1)
        return tab

    def _run_web_search(self):
        if self._worker is not None:
            return
        q = self.web_query_input.text().strip()
        if not q:
            return
        self.web_btn.setEnabled(False)
        self.web_yt_output.setPlainText(f"[Searching the web for: {q}...]")
        self._worker = JarvisWorker(
            message=q,
            task="web_search",
            extra={"synthesize": False},
        )
        self._worker.task_completed.connect(lambda _t, text: self.web_yt_output.setPlainText(text))
        self._worker.error_occurred.connect(lambda err: self.web_yt_output.setPlainText(f"[ERROR] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _run_youtube_summary(self):
        if self._worker is not None:
            return
        url = self.yt_url_input.text().strip()
        if not url:
            return
        self.yt_btn.setEnabled(False)
        self.web_yt_output.setPlainText(f"[Fetching YouTube video & generating AI summary...]")
        self._worker = JarvisWorker(
            message=url,
            task="youtube_summary",
            extra={"stream_to_chat": False},
        )
        self._worker.task_completed.connect(lambda title, text: self.web_yt_output.setPlainText(f"{title}\n\n{text}"))
        self._worker.error_occurred.connect(lambda err: self.web_yt_output.setPlainText(f"[ERROR] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ==========================================
    # TAB 4: PLUGINS & CUSTOM COMMANDS (7.7, 7.8)
    # ==========================================

    def _build_plugins_commands_tab(self):
        tab = QWidget()
        main = QHBoxLayout(tab)

        # Left: Plugins (7.7)
        p_box = QGroupBox("Plugin / Tool System (plugins/*.py) (7.7)")
        pl = QVBoxLayout(p_box)
        self.plugin_list = QListWidget()
        p_run_row = QHBoxLayout()
        self.plugin_arg_input = QLineEdit()
        self.plugin_arg_input.setPlaceholderText("Arguments for selected plugin tool...")
        run_p_btn = QPushButton("RUN PLUGIN")
        run_p_btn.clicked.connect(self._run_selected_plugin)
        reload_p_btn = QPushButton("RELOAD")
        reload_p_btn.clicked.connect(self._reload_plugins)
        p_run_row.addWidget(self.plugin_arg_input, 2)
        p_run_row.addWidget(run_p_btn)
        p_run_row.addWidget(reload_p_btn)

        self.plugin_output = QTextEdit()
        self.plugin_output.setReadOnly(True)
        self.plugin_output.setMaximumHeight(130)

        pl.addWidget(self.plugin_list, 1)
        pl.addLayout(p_run_row)
        pl.addWidget(self.plugin_output)

        # Right: Custom Commands (7.8)
        c_box = QGroupBox("Custom Chat Commands (/name) (7.8)")
        cl = QVBoxLayout(c_box)
        self.cmd_name_input = QLineEdit()
        self.cmd_name_input.setPlaceholderText("Command name (e.g. standup, docs, news)")
        self.cmd_type_combo = QComboBox()
        self.cmd_type_combo.addItems(["prompt", "url", "app"])
        self.cmd_payload_input = QLineEdit()
        self.cmd_payload_input.setPlaceholderText("Payload (AI prompt template with {args}, URL, or app name)")
        self.cmd_desc_input = QLineEdit()
        self.cmd_desc_input.setPlaceholderText("Short description")

        c_btns = QHBoxLayout()
        save_c_btn = QPushButton("SAVE COMMAND")
        save_c_btn.clicked.connect(self._save_custom_command)
        del_c_btn = QPushButton("DELETE SELECTED")
        del_c_btn.setObjectName("danger_button")
        del_c_btn.clicked.connect(self._delete_custom_command)
        c_btns.addWidget(save_c_btn)
        c_btns.addWidget(del_c_btn)

        self.custom_cmd_list = QListWidget()

        cl.addWidget(self.cmd_name_input)
        cl.addWidget(self.cmd_type_combo)
        cl.addWidget(self.cmd_payload_input)
        cl.addWidget(self.cmd_desc_input)
        cl.addLayout(c_btns)
        cl.addWidget(self.custom_cmd_list, 1)

        main.addWidget(p_box, 1)
        main.addWidget(c_box, 1)
        return tab

    def refresh_plugins(self):
        self.plugin_list.clear()
        for tool in plugin_manager.list_tools():
            item = QListWidgetItem(f"{tool['name']} ({tool['module']})\n  {tool['description']}  |  {tool['usage']}")
            item.setData(Qt.ItemDataRole.UserRole, tool["name"])
            self.plugin_list.addItem(item)

    def _reload_plugins(self):
        plugin_manager.reload()
        self.refresh_plugins()
        self.plugin_output.setPlainText(f"Reloaded {len(plugin_manager.list_tools())} plugin tool(s).")

    def _run_selected_plugin(self):
        item = self.plugin_list.currentItem()
        if not item:
            self.plugin_output.setPlainText("Select a plugin tool first.")
            return
        name = item.data(Qt.ItemDataRole.UserRole)
        try:
            out = plugin_manager.run_tool(name, self.plugin_arg_input.text())
            self.plugin_output.setPlainText(out)
        except Exception as err:
            self.plugin_output.setPlainText(f"[Plugin Error] {err}")

    def refresh_custom_commands(self):
        self.custom_cmd_list.clear()
        for cid, name, action_type, payload, desc in get_custom_commands():
            item = QListWidgetItem(f"/{name} [{action_type}] — {desc or payload[:60]}")
            item.setData(Qt.ItemDataRole.UserRole, cid)
            self.custom_cmd_list.addItem(item)

    def _save_custom_command(self):
        try:
            save_custom_command(
                self.cmd_name_input.text(),
                self.cmd_type_combo.currentText(),
                self.cmd_payload_input.text(),
                self.cmd_desc_input.text(),
            )
            self.cmd_name_input.clear()
            self.cmd_payload_input.clear()
            self.cmd_desc_input.clear()
            self.refresh_custom_commands()
            self.commands_changed.emit()
        except Exception as err:
            QMessageBox.warning(self, "Command Error", str(err))

    def _delete_custom_command(self):
        item = self.custom_cmd_list.currentItem()
        if not item:
            return
        delete_custom_command(item.data(Qt.ItemDataRole.UserRole))
        self.refresh_custom_commands()
        self.commands_changed.emit()

    # ==========================================
    # KNOWLEDGE BASE / FOLDER RAG (Chat With Your Folder)
    # ==========================================

    def _build_rag_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        idx_row = QHBoxLayout()
        self.rag_folder_input = QLineEdit()
        self.rag_folder_input.setPlaceholderText("Choose a folder of PDFs, notes, or code to index locally...")
        browse_btn = QPushButton("BROWSE")
        browse_btn.clicked.connect(self._browse_rag_folder)
        self.rag_index_btn = QPushButton("INDEX FOLDER")
        self.rag_index_btn.clicked.connect(self._index_rag_folder)
        clear_btn = QPushButton("CLEAR INDEX")
        clear_btn.setObjectName("danger_button")
        clear_btn.clicked.connect(self._clear_rag_index)
        idx_row.addWidget(self.rag_folder_input, 3)
        idx_row.addWidget(browse_btn)
        idx_row.addWidget(self.rag_index_btn)
        idx_row.addWidget(clear_btn)
        layout.addLayout(idx_row)

        self.rag_files_list = QListWidget()
        self.rag_files_list.setMaximumHeight(130)
        layout.addWidget(self.rag_files_list)

        q_row = QHBoxLayout()
        self.rag_query_input = QLineEdit()
        self.rag_query_input.setPlaceholderText("Ask a question across ALL your indexed files (or use /kb <question> in chat)...")
        self.rag_query_input.returnPressed.connect(self._ask_rag)
        self.rag_ask_btn = QPushButton("ASK KNOWLEDGE BASE")
        self.rag_ask_btn.clicked.connect(self._ask_rag)
        q_row.addWidget(self.rag_query_input, 3)
        q_row.addWidget(self.rag_ask_btn, 1)
        layout.addLayout(q_row)

        self.rag_output = QTextEdit()
        self.rag_output.setReadOnly(True)
        self.rag_output.setPlaceholderText("Cited answers from your local indexed folder appear here...")
        layout.addWidget(self.rag_output, 1)
        return tab

    def _browse_rag_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose Folder to Index")
        if folder:
            self.rag_folder_input.setText(folder)

    def _index_rag_folder(self):
        if self._worker is not None:
            return
        folder = self.rag_folder_input.text().strip()
        if not folder:
            return
        self.rag_index_btn.setEnabled(False)
        self.rag_output.setPlainText(f"[Indexing folder: {folder}...]")
        self._worker = JarvisWorker(message=folder, task="rag_index")
        self._worker.task_completed.connect(self._on_rag_indexed)
        self._worker.error_occurred.connect(lambda err: self.rag_output.setPlainText(f"[Index Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_rag_indexed(self, _title, summary):
        self.rag_output.setPlainText(summary)
        self.refresh_rag_files()

    def refresh_rag_files(self):
        self.rag_files_list.clear()
        for fname, fpath, chunks, ts in list_indexed_files():
            self.rag_files_list.addItem(f"{fname}  ({chunks} chunks)  —  {fpath}")

    def _clear_rag_index(self):
        clear_rag_index()
        self.refresh_rag_files()
        self.rag_output.setPlainText("Local knowledge base index cleared.")

    def _ask_rag(self):
        if self._worker is not None:
            return
        q = self.rag_query_input.text().strip()
        if not q:
            return
        self.rag_ask_btn.setEnabled(False)
        self.rag_output.setPlainText(f"[Searching local knowledge base for: {q}...]")
        self._worker = JarvisWorker(message=q, task="rag_ask", extra={"stream_to_chat": False})
        self._worker.task_completed.connect(lambda _t, ans: self.rag_output.setPlainText(ans))
        self._worker.error_occurred.connect(lambda err: self.rag_output.setPlainText(f"[RAG Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ==========================================
    # SMART CLIPBOARD HISTORY + AI ACTIONS
    # ==========================================

    def _build_clipboard_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        info = QLabel("Live clipboard history (auto-captured). Select any snippet for one-click AI actions:")
        info.setObjectName("subtitle")
        layout.addWidget(info)

        self.clip_list = QListWidget()
        self.clip_list.setMaximumHeight(160)
        layout.addWidget(self.clip_list)

        act_row = QHBoxLayout()
        for label, prompt_prefix in [
            ("EXPLAIN", "Explain this clearly:"),
            ("FIX GRAMMAR", "Fix grammar, spelling, and polish this text cleanly:"),
            ("SUMMARIZE", "Summarize this concisely into key bullet points:"),
            ("TRANSLATE EN", "Translate this text into natural English:"),
            ("ANALYZE CODE", "Analyze this code snippet for bugs, purpose, and improvements:"),
        ]:
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, p=prompt_prefix, lb=label: self._run_clipboard_ai(p, lb))
            act_row.addWidget(b)
        copy_back = QPushButton("COPY OUTPUT")
        copy_back.clicked.connect(lambda: QApplication.clipboard().setText(self.clip_output.toPlainText()))
        act_row.addWidget(copy_back)
        layout.addLayout(act_row)

        self.clip_output = QTextEdit()
        self.clip_output.setReadOnly(True)
        self.clip_output.setPlaceholderText("AI clipboard action results appear here...")
        layout.addWidget(self.clip_output, 1)
        return tab

    def _install_clipboard_watcher(self):
        cb = QApplication.clipboard()
        if cb is not None:
            cb.dataChanged.connect(self._on_clipboard_changed)
            initial = (cb.text() or "").strip()
            if initial:
                self._record_clip(initial)

    def _on_clipboard_changed(self):
        cb = QApplication.clipboard()
        if cb is None:
            return
        text = (cb.text() or "").strip()
        if text:
            self._record_clip(text)

    def _record_clip(self, text: str):
        if self._clip_history and self._clip_history[0] == text:
            return
        if text in self._clip_history:
            self._clip_history.remove(text)
        self._clip_history.insert(0, text)
        self._clip_history = self._clip_history[:25]
        self.clip_list.clear()
        for snippet in self._clip_history:
            preview = " ".join(snippet.split())[:110]
            item = QListWidgetItem(preview)
            item.setData(Qt.ItemDataRole.UserRole, snippet)
            self.clip_list.addItem(item)

    def _run_clipboard_ai(self, instruction: str, title: str):
        if self._worker is not None:
            return
        item = self.clip_list.currentItem()
        text = item.data(Qt.ItemDataRole.UserRole) if item else (QApplication.clipboard().text() or "").strip()
        if not text:
            self.clip_output.setPlainText("Clipboard is empty. Copy some text first.")
            return
        self.clip_output.setPlainText(f"[Running AI Clipboard Action: {title}...]")
        self._worker = JarvisWorker(
            message=f"{instruction}\n\n{text[:10000]}",
            task="assistant_prompt",
            extra={"title": f"Clipboard: {title}"},
        )
        self._worker.task_completed.connect(lambda _t, body: self.clip_output.setPlainText(body))
        self._worker.error_occurred.connect(lambda err: self.clip_output.setPlainText(f"[Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_worker_done(self):
        w = self._worker
        self._worker = None
        self.doc_ai_btn.setEnabled(True)
        self.web_btn.setEnabled(True)
        self.yt_btn.setEnabled(True)
        self.rag_index_btn.setEnabled(True)
        self.rag_ask_btn.setEnabled(True)
        if w:
            w.deleteLater()

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)

