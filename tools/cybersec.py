"""Defensive Cybersecurity & Coding Analysis Utilities (5.2, 5.6, 5.8, 6.2 - 6.6)."""

import ast
import re
import socket
import subprocess
from collections import Counter
from pathlib import Path
import psutil
import requests


# ==========================================
# 5.2 LOCAL PYTHON SYNTAX CHECKER
# ==========================================

def check_python_syntax(code: str) -> str:
    try:
        ast.parse(code or "")
        return "Python Syntax Check: OK (no syntax errors detected)."
    except SyntaxError as err:
        return f"Python SyntaxError on line {err.lineno}, column {err.offset}: {err.msg}"


# ==========================================
# 5.6 SAFE READ-ONLY GIT STATUS HELPER
# ==========================================

def get_git_repo_summary(repo_dir: str = None) -> str:
    target = repo_dir or str(Path(__file__).resolve().parent.parent)
    outputs = []
    for label, cmd in [
        ("BRANCH & STATUS", ["git", "status", "-sb"]),
        ("RECENT COMMITS", ["git", "log", "-n", "5", "--oneline"]),
    ]:
        try:
            proc = subprocess.run(cmd, cwd=target, capture_output=True, text=True, timeout=8)
            out = (proc.stdout or proc.stderr or "").strip()
            outputs.append(f"=== {label} ===\n{out or '(empty)'}")
        except Exception as err:
            outputs.append(f"=== {label} ===\nUnavailable: {err}")
    return "\n\n".join(outputs)


# ==========================================
# 5.8 LOCAL STATIC CODE SECURITY HEURISTIC SCANNER
# ==========================================

CODE_SEC_RULES = [
    ("CRITICAL", "Potential hardcoded secret/API key", re.compile(r"""(?:api[_-]?key|secret|password|passwd|token)\s*=\s*['"][^'"]{8,}['"]""", re.IGNORECASE)),
    ("HIGH", "Dynamic code execution via eval()/exec()", re.compile(r"\b(?:eval|exec)\s*\(")),
    ("HIGH", "Subprocess invoked with shell=True (command injection risk)", re.compile(r"subprocess\.\w+\([^\)]*shell\s*=\s*True")),
    ("HIGH", "os.system() call (prefer subprocess list args)", re.compile(r"\bos\.system\s*\(")),
    ("HIGH", "Possible SQL query string interpolation/concatenation", re.compile(r"""(?:SELECT|INSERT|UPDATE|DELETE)\b[^\n]*(?:\+|%s|\{)""", re.IGNORECASE)),
    ("MEDIUM", "Unsafe pickle.loads / yaml.load without SafeLoader", re.compile(r"\bpickle\.loads?\s*\(|\byaml\.load\s*\((?![^\)]*SafeLoader)")),
    ("MEDIUM", "Weak cryptographic hash (MD5/SHA1)", re.compile(r"\bhashlib\.(?:md5|sha1)\s*\(")),
    ("LOW", "TLS certificate verification disabled (verify=False)", re.compile(r"verify\s*=\s*False")),
]


def scan_code_security_local(code: str) -> str:
    findings = []
    for line_no, line in enumerate((code or "").splitlines(), 1):
        for sev, desc, pattern in CODE_SEC_RULES:
            if pattern.search(line):
                findings.append(f"[{sev}] Line {line_no}: {desc}\n    > {line.strip()[:120]}")
    if not findings:
        return "Local Static Scan: No common high-risk patterns matched (proceeding with AI deep review)."
    return "Local Static Security Pre-Scan Findings:\n" + "\n".join(findings)


# ==========================================
# 6.2 SECURITY LOG ANALYZER
# ==========================================

LOG_SIGNATURES = [
    ("SQL Injection Probe", re.compile(r"(?:union\s+select|or\s+1=1|sleep\(|benchmark\(|information_schema|'--)", re.IGNORECASE)),
    ("XSS Probe", re.compile(r"(?:<script|javascript:|onerror=|onload=)", re.IGNORECASE)),
    ("Path Traversal", re.compile(r"(?:\.\./|\.\.\\|/etc/passwd|win\.ini)", re.IGNORECASE)),
    ("Auth Failure / Brute Force", re.compile(r"(?:failed password|authentication failure|invalid user|401 unauthorized|403 forbidden|login failed)", re.IGNORECASE)),
    ("Server Error (5xx)", re.compile(r"\b50[0-9]\b")),
    ("Scanner / Recon User-Agent", re.compile(r"(?:sqlmap|nikto|nmap|masscan|dirbuster|gobuster|wpscan)", re.IGNORECASE)),
]

IP_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def analyze_security_logs_local(log_text: str) -> str:
    lines = [ln for ln in (log_text or "").splitlines() if ln.strip()]
    if not lines:
        return "No log entries provided."

    category_counts = Counter()
    ip_counts = Counter()
    flagged_lines = []

    for idx, line in enumerate(lines, 1):
        for ip in IP_REGEX.findall(line):
            ip_counts[ip] += 1
        for label, pat in LOG_SIGNATURES:
            if pat.search(line):
                category_counts[label] += 1
                if len(flagged_lines) < 25:
                    flagged_lines.append(f"Line {idx} [{label}]: {line[:150]}")

    report = [
        f"=== LOCAL LOG ANALYSIS ({len(lines)} lines) ===",
        "",
        "Indicator Summary:",
    ]
    if category_counts:
        for cat, cnt in category_counts.most_common():
            report.append(f"  - {cat}: {cnt} matches")
    else:
        report.append("  - No known attack signatures detected by local heuristics.")

    if ip_counts:
        report.append("\nTop Observed IP Addresses:")
        for ip, cnt in ip_counts.most_common(8):
            report.append(f"  - {ip}: {cnt} occurrences")

    if flagged_lines:
        report.append("\nSample Flagged Entries:")
        report.extend(f"  {fl}" for fl in flagged_lines[:15])

    return "\n".join(report)


# ==========================================
# 6.3 HTTP REQUEST & RESPONSE ANALYZER
# ==========================================

RECOMMENDED_SECURITY_HEADERS = {
    "strict-transport-security": "HSTS enforces HTTPS and prevents downgrade attacks.",
    "content-security-policy": "CSP mitigates XSS and unauthorized script execution.",
    "x-content-type-options": "Prevents MIME-type sniffing (should be 'nosniff').",
    "x-frame-options": "Prevents clickjacking (DENY or SAMEORIGIN).",
    "referrer-policy": "Controls sensitive URL leakage in Referer headers.",
    "permissions-policy": "Restricts browser APIs (camera, microphone, geolocation).",
}


def analyze_http_headers_dict(headers: dict, status_line: str = "") -> str:
    lower_headers = {k.lower(): v for k, v in headers.items()}
    lines = ["=== HTTP SECURITY HEADER AUDIT ==="]
    if status_line:
        lines.append(f"Status / Request: {status_line}")

    present = []
    missing = []
    warnings = []

    for header_key, explanation in RECOMMENDED_SECURITY_HEADERS.items():
        if header_key in lower_headers:
            present.append(f"  [OK] {header_key}: {lower_headers[header_key]}")
        else:
            missing.append(f"  [MISSING] {header_key} — {explanation}")

    if "server" in lower_headers:
        warnings.append(f"  [INFO] Server header exposed: {lower_headers['server']}")
    if "x-powered-by" in lower_headers:
        warnings.append(f"  [WARN] X-Powered-By leaks tech stack: {lower_headers['x-powered-by']}")
    if lower_headers.get("access-control-allow-origin") == "*":
        warnings.append("  [WARN] Wildcard CORS (Access-Control-Allow-Origin: *) detected.")
    if "set-cookie" in lower_headers:
        cookie = lower_headers["set-cookie"].lower()
        if "httponly" not in cookie:
            warnings.append("  [WARN] Set-Cookie missing HttpOnly flag.")
        if "secure" not in cookie:
            warnings.append("  [WARN] Set-Cookie missing Secure flag.")
        if "samesite" not in cookie:
            warnings.append("  [WARN] Set-Cookie missing SameSite attribute.")

    lines.append("\nPresent Security Headers:")
    lines.extend(present or ["  (none)"])
    lines.append("\nMissing Recommended Headers:")
    lines.extend(missing or ["  (none — great coverage!)"])
    if warnings:
        lines.append("\nAdditional Findings:")
        lines.extend(warnings)

    return "\n".join(lines)


def analyze_raw_http(raw_text: str) -> str:
    lines = [ln.rstrip("\r") for ln in (raw_text or "").splitlines()]
    if not lines:
        return "Empty HTTP input."
    status_line = lines[0]
    headers = {}
    for ln in lines[1:]:
        if not ln.strip():
            break
        if ":" in ln:
            k, v = ln.split(":", 1)
            headers[k.strip()] = v.strip()
    return analyze_http_headers_dict(headers, status_line=status_line)


def fetch_and_analyze_url_headers(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    resp = requests.get(url, timeout=10, allow_redirects=True)
    header_report = analyze_http_headers_dict(
        dict(resp.headers),
        status_line=f"HTTP {resp.status_code} ({resp.url})",
    )
    return header_report


# ==========================================
# 6.4 OWASP TOP 10 REFERENCE
# ==========================================

OWASP_TOP_10 = {
    "A01: Broken Access Control": "Failure to enforce what authenticated users are allowed to do (IDOR, privilege escalation, missing authorization checks). Fix: deny by default, enforce server-side ownership checks on every object.",
    "A02: Cryptographic Failures": "Weak/missing encryption in transit or at rest, weak hashes (MD5/SHA1), hardcoded secrets. Fix: TLS 1.2+, AES-256-GCM, Argon2id/bcrypt for passwords, proper secret management.",
    "A03: Injection (SQLi / Command / LDAP)": "Untrusted input concatenated into interpreters. Fix: parameterized queries/ORM bindings, strict input validation, avoid shell=True.",
    "A04: Insecure Design": "Missing threat modeling or flawed business logic before coding. Fix: abuse-case modeling, rate limiting, defense-in-depth architecture.",
    "A05: Security Misconfiguration": "Default credentials, verbose stack traces, missing security headers, open cloud buckets. Fix: hardened baselines, minimal permissions, automated config checks.",
    "A06: Vulnerable & Outdated Components": "Known CVEs in third-party libraries/frameworks. Fix: SBOM tracking, automated dependency updates, remove unused packages.",
    "A07: Identification & Authentication Failures": "Weak passwords, missing MFA, session fixation, predictable tokens. Fix: MFA, rate limiting, secure HttpOnly/SameSite cookies, short token lifetimes.",
    "A08: Software & Data Integrity Failures": "Untrusted CI/CD pipelines, insecure deserialization (e.g. Python pickle on untrusted data). Fix: signed artifacts, safe serialization (JSON), integrity checks.",
    "A09: Security Logging & Monitoring Failures": "Missing audit logs for login failures, admin actions, or high-value transactions. Fix: structured centralized logging with alerting and tamper protection.",
    "A10: Server-Side Request Forgery (SSRF)": "Server fetches attacker-supplied URLs, reaching internal metadata/services. Fix: strict URL allowlists, block private IP ranges, disable unused redirects.",
}


# ==========================================
# 6.5 LOCAL NETWORK INFORMATION (SAFE, LOCAL ONLY)
# ==========================================

def get_local_network_info() -> str:
    lines = ["=== LOCAL NETWORK INFORMATION ==="]
    try:
        hostname = socket.gethostname()
        lines.append(f"Hostname: {hostname}")
        try:
            primary_ip = socket.gethostbyname(hostname)
            lines.append(f"Primary Host IP: {primary_ip}")
        except Exception:
            pass
    except Exception as err:
        lines.append(f"Hostname error: {err}")

    lines.append("\nNetwork Interfaces:")
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    for iface, addr_list in addrs.items():
        st = stats.get(iface)
        state = "UP" if (st and st.isup) else "DOWN"
        speed = f"{st.speed} Mbps" if (st and st.speed) else "N/A"
        ips = []
        for a in addr_list:
            if a.family == socket.AF_INET:
                ips.append(f"IPv4={a.address}")
            elif a.family == socket.AF_INET6:
                ips.append(f"IPv6={a.address.split('%')[0]}")
        if ips:
            lines.append(f"  - {iface} [{state}, {speed}]: {', '.join(ips)}")

    io = psutil.net_io_counters()
    if io:
        lines.append(
            f"\nTotal Traffic (since boot): Sent {io.bytes_sent / (1024**2):.1f} MB | "
            f"Recv {io.bytes_recv / (1024**2):.1f} MB"
        )

    lines.append("\nLocal Listening TCP Ports (up to 20):")
    try:
        conns = psutil.net_connections(kind="tcp")
        listening = sorted({
            (c.laddr.ip, c.laddr.port, c.pid)
            for c in conns
            if c.status == "LISTEN" and c.laddr
        }, key=lambda x: x[1])
        if listening:
            for ip, port, pid in listening[:20]:
                lines.append(f"  - {ip}:{port} (PID: {pid})")
        else:
            lines.append("  (none visible)")
    except psutil.AccessDenied:
        lines.append("  (elevated privileges needed to inspect all system sockets)")
    except Exception as err:
        lines.append(f"  (unavailable: {err})")

    return "\n".join(lines)


# ==========================================
# 6.6 SECURITY CHECKLIST TEMPLATES
# ==========================================

SECURITY_CHECKLISTS = {
    "Web Application": [
        "[ ] Enforce HTTPS everywhere with HSTS enabled",
        "[ ] Implement Content-Security-Policy (CSP), X-Frame-Options, X-Content-Type-Options",
        "[ ] Use parameterized SQL queries / ORM bindings (zero string concatenation)",
        "[ ] Escape/encode all untrusted output to prevent XSS",
        "[ ] Enforce server-side authorization checks on every resource endpoint (prevent IDOR)",
        "[ ] Set HttpOnly, Secure, and SameSite flags on session cookies",
        "[ ] Protect state-changing endpoints with CSRF tokens",
        "[ ] Rate-limit authentication, password reset, and sensitive endpoints",
        "[ ] Disable debug mode and verbose stack traces in production",
        "[ ] Run dependency vulnerability audits regularly",
    ],
    "REST / GraphQL API": [
        "[ ] Validate JWT signatures, issuer, audience, and expiration strictly",
        "[ ] Enforce object-level (BOLA) and function-level (BFLA) authorization",
        "[ ] Apply strict input schema validation (type, length, range, allowlists)",
        "[ ] Configure restrictive CORS allowlists (avoid wildcard with credentials)",
        "[ ] Enforce per-user and per-IP rate limiting and request size limits",
        "[ ] Return minimal error details without internal stack traces",
        "[ ] Log authentication failures and anomalous access patterns",
    ],
    "Linux / Cloud Server": [
        "[ ] Disable SSH root login and password auth; require SSH keys",
        "[ ] Enable host firewall (ufw/nftables) with default-deny inbound policy",
        "[ ] Keep OS packages and kernel patched with unattended security updates",
        "[ ] Run services under dedicated least-privilege non-root users",
        "[ ] Store secrets in environment vaults, never in git repositories",
        "[ ] Enable centralized audit logging and disk/backup encryption",
    ],
    "Authentication Flow": [
        "[ ] Hash passwords with Argon2id or bcrypt (never MD5/SHA1/SHA256 alone)",
        "[ ] Enforce minimum password length (>=12 chars) and breach-list checks",
        "[ ] Support Multi-Factor Authentication (TOTP / WebAuthn)",
        "[ ] Rotate session IDs on login and invalidate server-side on logout",
        "[ ] Use constant-time comparisons for tokens/hashes and generic login error messages",
    ],
}

