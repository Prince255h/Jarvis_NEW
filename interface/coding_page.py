"""Coding Assistant Workspace for JARVIS (5.1 - 5.8)."""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QPlainTextEdit,
    QTextEdit,
    QFileDialog,
    QApplication,
    QSplitter,
)
from PySide6.QtCore import Qt

from tools.cybersec import (
    check_python_syntax,
    get_git_repo_summary,
    scan_code_security_local,
)
from interface.worker import JarvisWorker


CODING_MODES = {
    "5.1 Explain Code": "Explain the following {lang} code clearly: purpose, control flow, key functions, and time/space complexity.",
    "5.2 Debug Code": "Debug the following {lang} code. Identify all bugs, logic errors, or edge-case issues, explain root causes, and provide the corrected code.",
    "5.3 Generate Code": "Generate clean, well-structured, production-ready {lang} code with brief usage examples for the following specification:",
    "5.4 Review Code Quality": "Perform a thorough code quality review of this {lang} code covering readability, modularity, performance, error handling, and best practices.",
    "5.5 Explain Terminal Error": "Analyze the following terminal error / stack trace, explain the root cause in plain language, and give exact step-by-step fixes:",
    "5.6 Git & GitHub Assistant": "Provide clear Git / GitHub commands, workflow steps, and best practices for the following request (never suggest destructive force actions without warnings):",
    "5.7 Linux Command Helper": "Explain or provide safe Linux shell commands for the following request, breaking down every flag clearly:",
    "5.8 Analyze Code Security": "Perform a thorough defensive application security (SAST) audit on this {lang} code. List vulnerabilities with severity, root cause, and secure remediated code:",
}


class CodingAssistantPage(QWidget):
    """Dedicated Coding Assistant covering features 5.1 through 5.8."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("CODING ASSISTANT STUDIO")
        title.setObjectName("page_title")
        layout.addWidget(title)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(list(CODING_MODES.keys()))
        controls.addWidget(self.mode_combo, 2)

        controls.addWidget(QLabel("Language:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Python", "JavaScript / TypeScript", "C / C++", "Java", "Go", "Rust", "SQL", "Bash / Linux", "PowerShell", "HTML / CSS"])
        controls.addWidget(self.lang_combo, 1)

        load_btn = QPushButton("LOAD FILE")
        load_btn.clicked.connect(self._load_file)
        git_btn = QPushButton("GIT STATUS")
        git_btn.clicked.connect(self._run_git_status)
        self.run_btn = QPushButton("RUN ASSISTANT")
        self.run_btn.clicked.connect(self._run_assistant)

        controls.addWidget(load_btn)
        controls.addWidget(git_btn)
        controls.addWidget(self.run_btn)
        layout.addLayout(controls)

        splitter = QSplitter(Qt.Orientation.Vertical)

        self.input_editor = QPlainTextEdit()
        self.input_editor.setPlaceholderText(
            "Paste code, terminal stack trace, Git/Linux question, or coding prompt here..."
        )

        self.output_view = QTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setPlaceholderText("JARVIS Coding Assistant analysis & generated code will appear here...")

        splitter.addWidget(self.input_editor)
        splitter.addWidget(self.output_view)
        splitter.setSizes([260, 340])
        layout.addWidget(splitter, 1)

        bottom = QHBoxLayout()
        syntax_btn = QPushButton("LOCAL PYTHON SYNTAX CHECK")
        syntax_btn.clicked.connect(self._quick_syntax_check)
        sec_btn = QPushButton("LOCAL SECURITY PRE-SCAN")
        sec_btn.clicked.connect(self._quick_security_scan)
        copy_btn = QPushButton("COPY OUTPUT")
        copy_btn.clicked.connect(self._copy_output)
        clear_btn = QPushButton("CLEAR")
        clear_btn.clicked.connect(self._clear)
        bottom.addWidget(syntax_btn)
        bottom.addWidget(sec_btn)
        bottom.addStretch()
        bottom.addWidget(copy_btn)
        bottom.addWidget(clear_btn)
        layout.addLayout(bottom)

    def _load_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Source Code File", "", "Code Files (*.py *.js *.ts *.java *.cpp *.c *.go *.rs *.sql *.sh *.ps1 *.html *.css *.txt);;All Files (*)"
        )
        if not path:
            return
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        self.input_editor.setPlainText(text[:20000])

    def _run_git_status(self):
        summary = get_git_repo_summary()
        self.output_view.setPlainText(summary)

    def _quick_syntax_check(self):
        self.output_view.setPlainText(check_python_syntax(self.input_editor.toPlainText()))

    def _quick_security_scan(self):
        self.output_view.setPlainText(scan_code_security_local(self.input_editor.toPlainText()))

    def _run_assistant(self):
        if self._worker is not None:
            return
        user_text = self.input_editor.toPlainText().strip()
        if not user_text:
            self.output_view.setPlainText("Please enter code, an error message, or a coding request above.")
            return

        mode = self.mode_combo.currentText()
        lang = self.lang_combo.currentText()
        instruction = CODING_MODES[mode].format(lang=lang)

        prefix = ""
        if mode.startswith("5.2") and lang == "Python":
            prefix = check_python_syntax(user_text)
        elif mode.startswith("5.8"):
            prefix = scan_code_security_local(user_text)

        prompt = f"{instruction}\n\n```{lang.lower()}\n{user_text}\n```"

        self.run_btn.setEnabled(False)
        self.output_view.setPlainText(
            (prefix + "\n\n" if prefix else "") + f"[JARVIS Coding Assistant running: {mode}...]"
        )

        self._worker = JarvisWorker(
            message=prompt,
            task="assistant_prompt",
            personality_override="CODER",
            extra={"title": mode, "prefix": prefix},
        )
        self._worker.task_completed.connect(lambda _t, body: self.output_view.setPlainText(body))
        self._worker.error_occurred.connect(lambda err: self.output_view.setPlainText(f"[ERROR] {err}"))
        self._worker.finished.connect(self._on_finished)
        self._worker.start()

    def _on_finished(self):
        w = self._worker
        self._worker = None
        self.run_btn.setEnabled(True)
        if w:
            w.deleteLater()

    def _copy_output(self):
        QApplication.clipboard().setText(self.output_view.toPlainText())

    def _clear(self):
        self.input_editor.clear()
        self.output_view.clear()

    def shutdown(self):
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)

