"""Defensive Cybersecurity & Authorized Lab Assistant Workspace (6.1 - 6.8)."""

from pathlib import Path
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QComboBox,
    QTabWidget,
    QFileDialog,
    QApplication,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QSpinBox,
)
from PySide6.QtCore import Qt

from tools.cybersec import (
    OWASP_TOP_10,
    SECURITY_CHECKLISTS,
    analyze_security_logs_local,
    analyze_raw_http,
    fetch_and_analyze_url_headers,
    get_local_network_info,
)
from tools.vault import LocalSecretVault, generate_strong_password
from tools.exporter import export_markdown, export_text_to_pdf
from interface.worker import JarvisWorker


class CybersecurityPage(QWidget):
    """Defensive Cybersecurity, Log/HTTP Analysis, OWASP Learning, Network Info, Checklists & Authorized Lab Assistant."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._vault = LocalSecretVault()

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        title = QLabel("CYBERSECURITY & DEFENSIVE LAB CENTER")
        title.setObjectName("page_title")
        subtitle = QLabel("Educational, defensive security analysis, hardening, encrypted vault, and authorized-lab assistance.")
        subtitle.setObjectName("subtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_vuln_owasp_tab(), "Vulns & OWASP")
        self.tabs.addTab(self._build_log_tab(), "Log Analyzer")
        self.tabs.addTab(self._build_http_tab(), "HTTP Analyzer")
        self.tabs.addTab(self._build_dns_ssl_tab(), "DNS & SSL")
        self.tabs.addTab(self._build_network_tab(), "Local Network")
        self.tabs.addTab(self._build_checklist_tab(), "Checklists")
        self.tabs.addTab(self._build_bounty_lab_tab(), "Bug Bounty & Labs")
        self.tabs.addTab(self._build_vault_tab(), "Secrets Vault")
        layout.addWidget(self.tabs, 1)

    def _run_ai(self, target_output: QTextEdit, prompt: str, title: str, prefix: str = ""):
        if self._worker is not None:
            return
        target_output.setPlainText((prefix + "\n\n" if prefix else "") + f"[JARVIS Cybersecurity Analyst working on: {title}...]")
        self._worker = JarvisWorker(
            message=prompt,
            task="assistant_prompt",
            personality_override="CYBERSEC",
            extra={"title": title, "prefix": prefix},
        )
        self._worker.task_completed.connect(lambda _t, text: target_output.setPlainText(text))
        self._worker.error_occurred.connect(lambda err: target_output.setPlainText(f"[ERROR] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _on_worker_done(self):
        w = self._worker
        self._worker = None
        if w:
            w.deleteLater()

    # ==========================================
    # 6.1 EXPLAIN VULNERABILITIES & 6.4 OWASP LEARNING
    # ==========================================

    def _build_vuln_owasp_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        owasp_row = QHBoxLayout()
        owasp_row.addWidget(QLabel("OWASP Top 10:"))
        self.owasp_combo = QComboBox()
        self.owasp_combo.addItems(list(OWASP_TOP_10.keys()))
        self.owasp_combo.currentTextChanged.connect(self._show_owasp_quick)
        owasp_deep_btn = QPushButton("AI DEEP DIVE & SECURE CODE")
        owasp_deep_btn.clicked.connect(self._ai_owasp_deep_dive)
        owasp_row.addWidget(self.owasp_combo, 2)
        owasp_row.addWidget(owasp_deep_btn, 1)
        layout.addLayout(owasp_row)

        vuln_row = QHBoxLayout()
        self.vuln_input = QLineEdit()
        self.vuln_input.setPlaceholderText("Ask about any vulnerability or CVE/CWE (e.g., SSRF, JWT none algorithm, CWE-89)...")
        self.vuln_input.returnPressed.connect(self._ai_explain_vuln)
        vuln_btn = QPushButton("EXPLAIN VULNERABILITY")
        vuln_btn.clicked.connect(self._ai_explain_vuln)
        vuln_row.addWidget(self.vuln_input, 3)
        vuln_row.addWidget(vuln_btn, 1)
        layout.addLayout(vuln_row)

        self.vuln_output = QTextEdit()
        self.vuln_output.setReadOnly(True)
        layout.addWidget(self.vuln_output, 1)

        self._show_owasp_quick(self.owasp_combo.currentText())
        return tab

    def _show_owasp_quick(self, topic):
        summary = OWASP_TOP_10.get(topic, "")
        self.vuln_output.setPlainText(f"=== {topic} ===\n\n{summary}\n\nClick 'AI DEEP DIVE & SECURE CODE' for full walkthrough, vulnerable vs. fixed code examples, and detection tips.")

    def _ai_owasp_deep_dive(self):
        topic = self.owasp_combo.currentText()
        prompt = (
            f"Teach me '{topic}' from the OWASP Top 10 for defensive engineering:\n"
            "1. How it happens (root cause)\n"
            "2. Real-world impact\n"
            "3. Minimal vulnerable vs. secure patched code example\n"
            "4. Detection & prevention checklist."
        )
        self._run_ai(self.vuln_output, prompt, topic)

    def _ai_explain_vuln(self):
        q = self.vuln_input.text().strip()
        if not q:
            return
        prompt = (
            f"Explain the security vulnerability '{q}' thoroughly from a defensive perspective: "
            "root cause, attack mechanics conceptually, severity/impact, detection indicators, and concrete remediation."
        )
        self._run_ai(self.vuln_output, prompt, f"Explain {q}")

    # ==========================================
    # 6.2 SECURITY LOG ANALYZER
    # ==========================================

    def _build_log_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        btns = QHBoxLayout()
        load_btn = QPushButton("LOAD LOG FILE")
        load_btn.clicked.connect(self._load_log_file)
        local_btn = QPushButton("LOCAL SCAN ONLY")
        local_btn.clicked.connect(self._scan_logs_local)
        ai_btn = QPushButton("LOCAL + AI DEEP LOG ANALYSIS")
        ai_btn.clicked.connect(self._scan_logs_ai)
        btns.addWidget(load_btn)
        btns.addWidget(local_btn)
        btns.addWidget(ai_btn)
        btns.addStretch()
        layout.addLayout(btns)

        self.log_input = QPlainTextEdit()
        self.log_input.setPlaceholderText("Paste web server, firewall, auth, or application logs here...")
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_input, 1)
        layout.addWidget(self.log_output, 1)
        return tab

    def _load_log_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Log File", "", "Logs (*.log *.txt);;All Files (*)")
        if path:
            self.log_input.setPlainText(Path(path).read_text(encoding="utf-8", errors="replace")[:25000])

    def _scan_logs_local(self):
        self.log_output.setPlainText(analyze_security_logs_local(self.log_input.toPlainText()))

    def _scan_logs_ai(self):
        raw = self.log_input.toPlainText().strip()
        if not raw:
            return
        local_report = analyze_security_logs_local(raw)
        prompt = (
            "Analyze these security logs for anomalies, suspicious patterns, false positives, "
            "and recommended defensive containment/hardening steps:\n\n"
            f"{local_report}\n\n--- RAW LOG SAMPLE ---\n{raw[:10000]}"
        )
        self._run_ai(self.log_output, prompt, "Security Log Analysis", prefix=local_report)

    # ==========================================
    # 6.3 HTTP REQUEST & RESPONSE ANALYZER
    # ==========================================

    def _build_http_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        url_row = QHBoxLayout()
        self.http_url_input = QLineEdit()
        self.http_url_input.setPlaceholderText("Inspect headers of an authorized URL (e.g. https://example.com)...")
        fetch_btn = QPushButton("AUDIT URL HEADERS")
        fetch_btn.clicked.connect(self._audit_url_headers)
        url_row.addWidget(self.http_url_input, 3)
        url_row.addWidget(fetch_btn, 1)
        layout.addLayout(url_row)

        self.http_raw_input = QPlainTextEdit()
        self.http_raw_input.setPlaceholderText("Or paste a raw HTTP request/response here (headers + body)...")

        btns = QHBoxLayout()
        raw_local_btn = QPushButton("AUDIT RAW HTTP")
        raw_local_btn.clicked.connect(self._audit_raw_http_local)
        raw_ai_btn = QPushButton("AI DEEP HTTP ANALYSIS")
        raw_ai_btn.clicked.connect(self._audit_raw_http_ai)
        btns.addWidget(raw_local_btn)
        btns.addWidget(raw_ai_btn)
        btns.addStretch()

        self.http_output = QTextEdit()
        self.http_output.setReadOnly(True)

        layout.addWidget(self.http_raw_input, 1)
        layout.addLayout(btns)
        layout.addWidget(self.http_output, 1)
        return tab

    def _audit_url_headers(self):
        if self._worker is not None:
            return
        url = self.http_url_input.text().strip()
        if not url:
            return
        self.http_output.setPlainText(f"[Auditing HTTP security headers for {url}...]")
        self._worker = JarvisWorker(message=url, task="http_audit")
        self._worker.task_completed.connect(lambda _t, report: self.http_output.setPlainText(report))
        self._worker.error_occurred.connect(lambda err: self.http_output.setPlainText(f"[HTTP Audit Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    def _audit_raw_http_local(self):
        self.http_output.setPlainText(analyze_raw_http(self.http_raw_input.toPlainText()))

    def _audit_raw_http_ai(self):
        raw = self.http_raw_input.toPlainText().strip()
        if not raw:
            return
        local_audit = analyze_raw_http(raw)
        prompt = (
            "Review this HTTP request/response for security misconfigurations (cookies, CORS, CSP, "
            "auth tokens, caching, information leakage) and recommend concrete fixes:\n\n"
            f"{raw[:10000]}"
        )
        self._run_ai(self.http_output, prompt, "HTTP Security Analysis", prefix=local_audit)

    # ==========================================
    # 6.5 LOCAL NETWORK INFORMATION
    # ==========================================

    def _build_network_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        refresh_btn = QPushButton("REFRESH LOCAL NETWORK DIAGNOSTICS")
        refresh_btn.clicked.connect(self._refresh_network)
        self.net_output = QTextEdit()
        self.net_output.setReadOnly(True)

        layout.addWidget(refresh_btn)
        layout.addWidget(self.net_output, 1)
        self._refresh_network()
        return tab

    def _refresh_network(self):
        self.net_output.setPlainText(get_local_network_info())

    # ==========================================
    # 6.6 SECURITY CHECKLIST GENERATOR
    # ==========================================

    def _build_checklist_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        self.chk_combo = QComboBox()
        self.chk_combo.addItems(list(SECURITY_CHECKLISTS.keys()))
        self.chk_combo.currentTextChanged.connect(self._load_checklist_template)
        self.chk_custom = QLineEdit()
        self.chk_custom.setPlaceholderText("Or describe your stack (e.g. FastAPI + PostgreSQL + Docker)...")
        ai_btn = QPushButton("GENERATE AI CHECKLIST")
        ai_btn.clicked.connect(self._generate_ai_checklist)
        row.addWidget(self.chk_combo, 1)
        row.addWidget(self.chk_custom, 2)
        row.addWidget(ai_btn, 1)

        self.chk_output = QTextEdit()
        layout.addLayout(row)
        layout.addWidget(self.chk_output, 1)
        self._load_checklist_template(self.chk_combo.currentText())
        return tab

    def _load_checklist_template(self, name):
        items = SECURITY_CHECKLISTS.get(name, [])
        self.chk_output.setPlainText(f"=== {name.upper()} SECURITY CHECKLIST ===\n\n" + "\n".join(items))

    def _generate_ai_checklist(self):
        target = self.chk_custom.text().strip() or self.chk_combo.currentText()
        prompt = (
            f"Generate a comprehensive, prioritized defensive security hardening checklist for: {target}.\n"
            "Format with Markdown checkboxes [ ] grouped by Authentication, Authorization, Data Protection, Infrastructure, and Monitoring."
        )
        self._run_ai(self.chk_output, prompt, f"Checklist: {target}")

    # ==========================================
    # 6.7 BUG BOUNTY REPORT DRAFTING & 6.8 LEGAL LAB TESTING
    # ==========================================

    def _build_bounty_lab_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row1 = QHBoxLayout()
        self.bb_title = QLineEdit()
        self.bb_title.setPlaceholderText("Finding Title (e.g. Stored XSS in Profile Bio on Authorized Lab)")
        self.bb_asset = QLineEdit()
        self.bb_asset.setPlaceholderText("Authorized Scope / Lab (e.g. OWASP Juice Shop / TryHackMe)")
        self.bb_severity = QComboBox()
        self.bb_severity.addItems(["Critical", "High", "Medium", "Low", "Informational"])
        self.bb_severity.setCurrentText("Medium")
        row1.addWidget(self.bb_title, 2)
        row1.addWidget(self.bb_asset, 2)
        row1.addWidget(self.bb_severity, 1)
        layout.addLayout(row1)

        self.bb_notes = QPlainTextEdit()
        self.bb_notes.setPlaceholderText(
            "Enter reproduction notes, observed impact, or your legal lab question (TryHackMe / Hack The Box / PortSwigger Labs / Juice Shop / DVWA)..."
        )

        btns = QHBoxLayout()
        draft_btn = QPushButton("DRAFT BUG BOUNTY REPORT")
        draft_btn.clicked.connect(self._draft_bounty_report)
        lab_btn = QPushButton("LEGAL LAB STUDY ASSISTANCE")
        lab_btn.clicked.connect(self._legal_lab_assist)
        copy_btn = QPushButton("COPY OUTPUT")
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(self.bb_output.toPlainText()))
        exp_md_btn = QPushButton("EXPORT .MD")
        exp_md_btn.clicked.connect(lambda: self._export_bounty("md"))
        exp_pdf_btn = QPushButton("EXPORT .PDF")
        exp_pdf_btn.clicked.connect(lambda: self._export_bounty("pdf"))
        btns.addWidget(draft_btn)
        btns.addWidget(lab_btn)
        btns.addStretch()
        btns.addWidget(exp_md_btn)
        btns.addWidget(exp_pdf_btn)
        btns.addWidget(copy_btn)

        self.bb_output = QTextEdit()
        self.bb_output.setReadOnly(True)

        layout.addWidget(self.bb_notes, 1)
        layout.addLayout(btns)
        layout.addWidget(self.bb_output, 1)
        return tab

    def _draft_bounty_report(self):
        title = self.bb_title.text().strip() or "Security Vulnerability Finding"
        asset = self.bb_asset.text().strip() or "Authorized Target"
        sev = self.bb_severity.currentText()
        notes = self.bb_notes.toPlainText().strip()
        if not notes:
            self.bb_output.setPlainText("Please enter your finding notes/steps above first.")
            return
        prompt = (
            "Draft a professional, HackerOne/Bugcrowd-ready vulnerability disclosure report in Markdown.\n"
            f"Title: {title}\nAsset/Scope: {asset}\nSuggested Severity: {sev}\nNotes:\n{notes}\n\n"
            "Include: Executive Summary, Severity & CVSS Rationale, Steps to Reproduce, Security Impact, and Concrete Remediation."
        )
        self._run_ai(self.bb_output, prompt, "Bug Bounty Report Draft")

    def _legal_lab_assist(self):
        asset = self.bb_asset.text().strip() or "Authorized Practice Lab (e.g. OWASP Juice Shop / PortSwigger)"
        notes = self.bb_notes.toPlainText().strip()
        if not notes:
            self.bb_output.setPlainText("Describe the authorized lab challenge or concept you want help understanding.")
            return
        prompt = (
            f"The user is learning defensive cybersecurity in a legal, authorized lab environment ({asset}).\n"
            f"Question/Scenario: {notes}\n\n"
            "Provide educational methodology, conceptual hints, defensive understanding, and how developers fix the root vulnerability."
        )
        self._run_ai(self.bb_output, prompt, "Legal Lab Assistance")

    def _export_bounty(self, fmt: str):
        text = self.bb_output.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "Empty Report", "Draft a report first before exporting.")
            return
        if fmt == "pdf":
            path, _ = QFileDialog.getSaveFileName(self, "Export Report to PDF", "security_report.pdf", "PDF (*.pdf)")
            if path:
                export_text_to_pdf(text, path, title="J.A.R.V.I.S Security Report")
                QMessageBox.information(self, "Exported", f"PDF saved to:\n{path}")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "Export Report to Markdown", "security_report.md", "Markdown (*.md)")
            if path:
                export_markdown(text, path)
                QMessageBox.information(self, "Exported", f"Markdown saved to:\n{path}")

    # ==========================================
    # DNS & SSL CERTIFICATE INSPECTOR
    # ==========================================

    def _build_dns_ssl_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        row = QHBoxLayout()
        self.dns_domain_input = QLineEdit()
        self.dns_domain_input.setPlaceholderText("Enter authorized domain (e.g. example.com, github.com)...")
        self.dns_domain_input.returnPressed.connect(self._run_dns_ssl_audit)
        scan_btn = QPushButton("INSPECT TLS/SSL + DNS")
        scan_btn.clicked.connect(self._run_dns_ssl_audit)
        row.addWidget(self.dns_domain_input, 3)
        row.addWidget(scan_btn, 1)

        self.dns_output = QTextEdit()
        self.dns_output.setReadOnly(True)
        self.dns_output.setPlaceholderText("SSL certificate details (issuer, SANs, expiry, cipher) and DNS records (A, AAAA, MX, NS, TXT, DMARC) appear here...")

        layout.addLayout(row)
        layout.addWidget(self.dns_output, 1)
        return tab

    def _run_dns_ssl_audit(self):
        if self._worker is not None:
            return
        domain = self.dns_domain_input.text().strip()
        if not domain:
            return
        self.dns_output.setPlainText(f"[Inspecting TLS certificate & DNS records for {domain}...]")
        self._worker = JarvisWorker(message=domain, task="dns_ssl_audit")
        self._worker.task_completed.connect(lambda _t, rep: self.dns_output.setPlainText(rep))
        self._worker.error_occurred.connect(lambda err: self.dns_output.setPlainText(f"[DNS/SSL Error] {err}"))
        self._worker.finished.connect(self._on_worker_done)
        self._worker.start()

    # ==========================================
    # ENCRYPTED LOCAL SECRETS / PASSWORD VAULT
    # ==========================================

    def _build_vault_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Unlock / Lock row
        auth_row = QHBoxLayout()
        self.vault_master_input = QLineEdit()
        self.vault_master_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.vault_master_input.setPlaceholderText(
            "Enter Master Password to unlock (or create new encrypted vault)..."
        )
        self.vault_master_input.returnPressed.connect(self._unlock_vault)

        unlock_btn = QPushButton("UNLOCK / INIT")
        unlock_btn.clicked.connect(self._unlock_vault)
        lock_btn = QPushButton("LOCK VAULT")
        lock_btn.clicked.connect(self._lock_vault)
        self.vault_status_lbl = QLabel("LOCKED")
        self.vault_status_lbl.setObjectName("status_pill")

        auth_row.addWidget(self.vault_master_input, 3)
        auth_row.addWidget(unlock_btn)
        auth_row.addWidget(lock_btn)
        auth_row.addWidget(self.vault_status_lbl)
        layout.addLayout(auth_row)

        # Password generator row
        gen_row = QHBoxLayout()
        self.pw_len_spin = QSpinBox()
        self.pw_len_spin.setRange(12, 64)
        self.pw_len_spin.setValue(20)
        self.pw_len_spin.setSuffix(" chars")
        gen_btn = QPushButton("GENERATE STRONG PASSWORD")
        gen_btn.clicked.connect(self._generate_password)
        gen_row.addWidget(QLabel("Password Generator:"))
        gen_row.addWidget(self.pw_len_spin)
        gen_row.addWidget(gen_btn)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        # Add entry form
        add_row = QHBoxLayout()
        self.v_service = QLineEdit()
        self.v_service.setPlaceholderText("Service (e.g. GitHub, AWS)")
        self.v_user = QLineEdit()
        self.v_user.setPlaceholderText("Username / Key Name")
        self.v_secret = QLineEdit()
        self.v_secret.setEchoMode(QLineEdit.EchoMode.Password)
        self.v_secret.setPlaceholderText("Password / Secret Token")
        add_btn = QPushButton("ENCRYPT & SAVE")
        add_btn.clicked.connect(self._add_vault_entry)
        add_row.addWidget(self.v_service, 2)
        add_row.addWidget(self.v_user, 2)
        add_row.addWidget(self.v_secret, 3)
        add_row.addWidget(add_btn, 1)
        layout.addLayout(add_row)

        # Vault entries list
        self.vault_list = QListWidget()
        layout.addWidget(self.vault_list, 1)

        actions = QHBoxLayout()
        copy_sec_btn = QPushButton("COPY SECRET")
        copy_sec_btn.clicked.connect(self._copy_vault_secret)
        reveal_btn = QPushButton("REVEAL SELECTED")
        reveal_btn.clicked.connect(self._reveal_vault_secret)
        del_btn = QPushButton("DELETE ENTRY")
        del_btn.setObjectName("danger_button")
        del_btn.clicked.connect(self._delete_vault_entry)
        actions.addWidget(copy_sec_btn)
        actions.addWidget(reveal_btn)
        actions.addStretch()
        actions.addWidget(del_btn)
        layout.addLayout(actions)
        return tab

    def _unlock_vault(self):
        pw = self.vault_master_input.text()
        try:
            msg = self._vault.setup_or_unlock(pw)
            self.vault_master_input.clear()
            self.vault_status_lbl.setText("UNLOCKED")
            self._refresh_vault()
            QMessageBox.information(self, "Secrets Vault", msg)
        except Exception as err:
            QMessageBox.warning(self, "Vault Error", str(err))

    def _lock_vault(self):
        self._vault.lock()
        self.vault_list.clear()
        self.vault_status_lbl.setText("LOCKED")

    def _generate_password(self):
        pw = generate_strong_password(self.pw_len_spin.value())
        self.v_secret.setText(pw)
        QApplication.clipboard().setText(pw)
        QMessageBox.information(self, "Password Generated", f"Generated & copied to clipboard:\n{pw}")

    def _add_vault_entry(self):
        try:
            self._vault.add_entry(self.v_service.text(), self.v_user.text(), self.v_secret.text())
            self.v_service.clear()
            self.v_user.clear()
            self.v_secret.clear()
            self._refresh_vault()
        except Exception as err:
            QMessageBox.warning(self, "Vault Error", str(err))

    def _refresh_vault(self):
        self.vault_list.clear()
        if not self._vault.is_unlocked:
            return
        for entry in self._vault.list_entries():
            masked = "•" * min(16, len(entry["secret"]))
            item = QListWidgetItem(f"{entry['service']}  |  {entry['username'] or '(no user)'}  |  {masked}")
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.vault_list.addItem(item)

    def _copy_vault_secret(self):
        item = self.vault_list.currentItem()
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        QApplication.clipboard().setText(entry["secret"])

    def _reveal_vault_secret(self):
        item = self.vault_list.currentItem()
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        QMessageBox.information(
            self,
            f"Secret: {entry['service']}",
            f"Username: {entry['username']}\nSecret: {entry['secret']}",
        )

    def _delete_vault_entry(self):
        item = self.vault_list.currentItem()
        if not item:
            return
        entry = item.data(Qt.ItemDataRole.UserRole)
        self._vault.delete_entry(entry["id"])
        self._refresh_vault()

    def shutdown(self):
        self._vault.lock()
        if self._worker and self._worker.isRunning():
            self._worker.quit()
            self._worker.wait(1000)

