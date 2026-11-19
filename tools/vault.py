"""Encrypted Local Secrets & Password Vault using cryptography (PBKDF2-SHA256 + Fernet)."""

import base64
import os
import secrets
import string

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.memory import get_connection


def initialize_vault():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vault_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT NOT NULL,
                username TEXT DEFAULT '',
                secret_enc TEXT NOT NULL,
                notes_enc TEXT DEFAULT '',
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)


def generate_strong_password(length: int = 20, use_symbols: bool = True) -> str:
    length = max(10, min(64, int(length)))
    alphabet = string.ascii_letters + string.digits + ("!@#$%^&*-_=+" if use_symbols else "")
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pw)
            and any(c.isupper() for c in pw)
            and any(c.isdigit() for c in pw)
            and (not use_symbols or any(c in "!@#$%^&*-_=+" for c in pw))
        ):
            return pw


def _derive_fernet(master_password: str, salt: bytes) -> Fernet:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390_000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))
    return Fernet(key)


class LocalSecretVault:
    """In-memory unlocked Fernet vault backed by SQLite."""

    def __init__(self):
        initialize_vault()
        self._fernet = None

    @property
    def is_unlocked(self) -> bool:
        return self._fernet is not None

    def is_initialized(self) -> bool:
        with get_connection() as conn:
            row = conn.execute("SELECT value FROM vault_meta WHERE key = 'salt'").fetchone()
            return row is not None

    def setup_or_unlock(self, master_password: str) -> str:
        if not master_password or len(master_password) < 6:
            raise ValueError("Master password must be at least 6 characters.")

        with get_connection() as conn:
            salt_row = conn.execute("SELECT value FROM vault_meta WHERE key = 'salt'").fetchone()
            check_row = conn.execute("SELECT value FROM vault_meta WHERE key = 'check_token'").fetchone()

            if not salt_row:
                salt = os.urandom(16)
                fernet = _derive_fernet(master_password, salt)
                check_token = fernet.encrypt(b"JARVIS_VAULT_OK").decode("ascii")
                conn.execute(
                    "INSERT OR REPLACE INTO vault_meta (key, value) VALUES ('salt', ?)",
                    (base64.b64encode(salt).decode("ascii"),),
                )
                conn.execute(
                    "INSERT OR REPLACE INTO vault_meta (key, value) VALUES ('check_token', ?)",
                    (check_token,),
                )
                self._fernet = fernet
                return "Vault created and unlocked."

            salt = base64.b64decode(salt_row[0].encode("ascii"))
            fernet = _derive_fernet(master_password, salt)
            try:
                decrypted = fernet.decrypt(check_row[0].encode("ascii"))
                if decrypted != b"JARVIS_VAULT_OK":
                    raise InvalidToken()
            except InvalidToken:
                raise ValueError("Incorrect master password.")

            self._fernet = fernet
            return "Vault unlocked."

    def lock(self):
        self._fernet = None

    def _require_unlocked(self):
        if self._fernet is None:
            raise PermissionError("Vault is locked. Unlock with your master password first.")

    def add_entry(self, service: str, username: str, secret_value: str, notes: str = "") -> int:
        self._require_unlocked()
        service = (service or "").strip()
        if not service or not secret_value:
            raise ValueError("Service name and secret value are required.")
        sec_enc = self._fernet.encrypt(secret_value.encode("utf-8")).decode("ascii")
        notes_enc = self._fernet.encrypt((notes or "").encode("utf-8")).decode("ascii") if notes else ""
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO vault_entries (service, username, secret_enc, notes_enc) VALUES (?, ?, ?, ?)",
                (service, (username or "").strip(), sec_enc, notes_enc),
            )
            return cur.lastrowid

    def list_entries(self) -> list[dict]:
        self._require_unlocked()
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT id, service, username, secret_enc, notes_enc, updated_at FROM vault_entries ORDER BY service ASC"
            ).fetchall()
        results = []
        for eid, service, username, sec_enc, notes_enc, updated_at in rows:
            secret_plain = self._fernet.decrypt(sec_enc.encode("ascii")).decode("utf-8")
            notes_plain = self._fernet.decrypt(notes_enc.encode("ascii")).decode("utf-8") if notes_enc else ""
            results.append({
                "id": eid,
                "service": service,
                "username": username,
                "secret": secret_plain,
                "notes": notes_plain,
                "updated_at": updated_at,
            })
        return results

    def delete_entry(self, entry_id: int):
        self._require_unlocked()
        with get_connection() as conn:
            conn.execute("DELETE FROM vault_entries WHERE id = ?", (entry_id,))

