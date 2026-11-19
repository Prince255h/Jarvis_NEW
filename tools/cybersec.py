"""Defensive Cybersecurity & Coding Analysis Utilities (5.2, 5.6, 5.8, 6.2 - 6.6)."""

import ast
import re
import socket
import ssl
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
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


def run_python_snippet(code: str, timeout: int = 10) -> dict:
    """Execute a Python snippet inside a temporary isolated subprocess with timeout."""
    code = (code or "").strip()
    if not code:
        raise ValueError("No Python code provided to execute.")

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as tf:
            tf.write(code)
            tmp_path = tf.name

        proc = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    finally:
        if tmp_path:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


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


def analyze_http_headers_dict(headers: dict, status_line: str = "", set_cookies=None) -> str:
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

    cookies_to_check = list(set_cookies) if set_cookies else (
        [lower_headers["set-cookie"]] if "set-cookie" in lower_headers else []
    )
    for idx, raw_cookie in enumerate(cookies_to_check, 1):
        cookie = raw_cookie.lower()
        cookie_name = raw_cookie.split("=", 1)[0].strip() or f"#{idx}"
        if "httponly" not in cookie:
            warnings.append(f"  [WARN] Set-Cookie ({cookie_name}) missing HttpOnly flag.")
        if "secure" not in cookie:
            warnings.append(f"  [WARN] Set-Cookie ({cookie_name}) missing Secure flag.")
        if "samesite" not in cookie:
            warnings.append(f"  [WARN] Set-Cookie ({cookie_name}) missing SameSite attribute.")

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
    set_cookies = []
    for ln in lines[1:]:
        if not ln.strip():
            break
        if ":" in ln:
            k, v = ln.split(":", 1)
            key, val = k.strip(), v.strip()
            headers[key] = val
            if key.lower() == "set-cookie":
                set_cookies.append(val)
    return analyze_http_headers_dict(headers, status_line=status_line, set_cookies=set_cookies)


def fetch_and_analyze_url_headers(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    resp = requests.get(url, timeout=10, allow_redirects=True)
    set_cookies = []
    try:
        if hasattr(resp.raw, "headers") and hasattr(resp.raw.headers, "getlist"):
            set_cookies = resp.raw.headers.getlist("Set-Cookie")
    except Exception:
        pass
    header_report = analyze_http_headers_dict(
        dict(resp.headers),
        status_line=f"HTTP {resp.status_code} ({resp.url})",
        set_cookies=set_cookies or None,
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


# ==========================================
# SSL CERTIFICATE & DNS INSPECTOR
# ==========================================

def _clean_hostname(target: str) -> str:
    raw = (target or "").strip()
    raw = re.sub(r"^https?://", "", raw, flags=re.IGNORECASE)
    raw = raw.split("/", 1)[0].split(":", 1)[0].strip().lower()
    if not raw or not re.fullmatch(r"[a-z0-9.-]+", raw):
        raise ValueError(f"Invalid domain/hostname: {target}")
    return raw


def inspect_ssl_certificate(domain: str, port: int = 443) -> str:
    """Inspect TLS/SSL certificate issuer, subject, SANs, expiry, and negotiated cipher."""
    host = _clean_hostname(domain)
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=8) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            tls_version = ssock.version()
            cipher = ssock.cipher()

    subject = dict(x[0] for x in cert.get("subject", []))
    issuer = dict(x[0] for x in cert.get("issuer", []))
    not_before = cert.get("notBefore", "Unknown")
    not_after = cert.get("notAfter", "Unknown")
    days_left = "Unknown"
    try:
        exp_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = f"{(exp_dt - datetime.now(timezone.utc)).days} days"
    except Exception:
        pass

    sans = [val for typ, val in cert.get("subjectAltName", []) if typ == "DNS"][:10]
    lines = [
        f"=== TLS / SSL CERTIFICATE: {host}:{port} ===",
        f"  Subject CN  : {subject.get('commonName', 'N/A')}",
        f"  Issuer      : {issuer.get('organizationName', 'N/A')} ({issuer.get('commonName', 'N/A')})",
        f"  TLS Version : {tls_version}",
        f"  Cipher      : {cipher[0] if cipher else 'N/A'} ({cipher[2] if cipher else '?'} bits)",
        f"  Valid From  : {not_before}",
        f"  Valid Until : {not_after}  ({days_left} remaining)",
        f"  SAN Domains : {', '.join(sans) if sans else 'None'}",
    ]
    return "\n".join(lines)


def inspect_dns_records(domain: str) -> str:
    """Query A, AAAA, MX, NS, and TXT (SPF/DMARC) records via DNS-over-HTTPS JSON API."""
    host = _clean_hostname(domain)
    lines = [f"=== DNS RECORDS: {host} ==="]

    def doh_query(qname: str, qtype: str) -> list[str]:
        resp = requests.get(
            "https://cloudflare-dns.com/dns-query",
            params={"name": qname, "type": qtype},
            headers={"Accept": "application/dns-json", "User-Agent": "JARVIS-DNS/1.0"},
            timeout=8,
        )
        if not resp.ok:
            return []
        data = resp.json()
        return [ans.get("data", "") for ans in data.get("Answer", []) if ans.get("data")]

    for rtype in ("A", "AAAA", "MX", "NS", "TXT"):
        try:
            vals = doh_query(host, rtype)
            if vals:
                lines.append(f"  [{rtype}]")
                for v in vals[:8]:
                    lines.append(f"    - {v}")
            else:
                lines.append(f"  [{rtype}] (none)")
        except Exception as err:
            lines.append(f"  [{rtype}] Error: {err}")

    # DMARC check
    try:
        dmarc = doh_query(f"_dmarc.{host}", "TXT")
        lines.append("  [DMARC]")
        if dmarc:
            for v in dmarc[:3]:
                lines.append(f"    - {v}")
        else:
            lines.append("    - [WARN] No DMARC record found.")
    except Exception:
        pass

    return "\n".join(lines)


def full_domain_security_report(domain: str) -> str:
    parts = []
    try:
        parts.append(inspect_ssl_certificate(domain))
    except Exception as err:
        parts.append(f"=== TLS / SSL CERTIFICATE ===\n  Unavailable: {err}")
    try:
        parts.append(inspect_dns_records(domain))
    except Exception as err:
        parts.append(f"=== DNS RECORDS ===\n  Unavailable: {err}")
    return "\n\n".join(parts)

