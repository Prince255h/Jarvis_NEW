"""Local Folder Knowledge Base / RAG Engine (SQLite + BM25-style ranking, 100% offline)."""

import math
import re
from collections import Counter
from pathlib import Path

from core.memory import get_connection
from tools.documents import extract_document_text, TEXT_EXTENSIONS

INDEXABLE_EXTENSIONS = TEXT_EXTENSIONS | {".pdf", ".docx"}
SKIP_DIRS = {".git", "__pycache__", "venv", ".venv", "node_modules", ".idea", ".vscode", "dist", "build"}
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{2,}")


def initialize_rag():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_file ON rag_chunks(file_path)")


def _chunk_text(text: str, chunk_size: int = 900, overlap: int = 150) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    chunks = []
    start = 0
    length = len(clean)
    while start < length:
        end = min(length, start + chunk_size)
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def index_folder(folder_path: str, max_files: int = 120) -> dict:
    """Index supported PDF, DOCX, Markdown, Code, and Text files inside folder_path."""
    root = Path(folder_path)
    if not root.is_dir():
        raise FileNotFoundError(f"Folder not found: {folder_path}")

    files_indexed = 0
    chunks_added = 0
    skipped = 0

    with get_connection() as conn:
        for path in root.rglob("*"):
            if files_indexed >= max_files:
                break
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if not path.is_file() or path.suffix.lower() not in INDEXABLE_EXTENSIONS:
                continue
            if path.stat().st_size > 8_000_000:  # skip >8MB files
                skipped += 1
                continue

            try:
                meta = extract_document_text(str(path), max_chars=45000)
                chunks = _chunk_text(meta["text"])
                if not chunks:
                    skipped += 1
                    continue

                conn.execute("DELETE FROM rag_chunks WHERE file_path = ?", (str(path),))
                for idx, chunk in enumerate(chunks):
                    conn.execute(
                        "INSERT INTO rag_chunks (file_path, file_name, chunk_index, content) VALUES (?, ?, ?, ?)",
                        (str(path), path.name, idx, chunk),
                    )
                    chunks_added += 1
                files_indexed += 1
            except Exception:
                skipped += 1

    return {
        "folder": str(root),
        "files_indexed": files_indexed,
        "chunks_added": chunks_added,
        "skipped": skipped,
    }


def list_indexed_files() -> list[tuple]:
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT file_name, file_path, COUNT(id) AS chunk_count, MAX(indexed_at)
            FROM rag_chunks
            GROUP BY file_path
            ORDER BY file_name ASC
            """
        ).fetchall()


def clear_rag_index():
    with get_connection() as conn:
        conn.execute("DELETE FROM rag_chunks")


def search_rag(query: str, top_k: int = 5) -> list[dict]:
    """BM25-inspired keyword + TF-IDF ranking over local SQLite chunks."""
    q_tokens = [t.lower() for t in TOKEN_RE.findall(query or "")]
    if not q_tokens:
        return []

    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, file_path, file_name, chunk_index, content FROM rag_chunks"
        ).fetchall()

    if not rows:
        return []

    n_docs = len(rows)
    doc_freq = Counter()
    doc_tokens_list = []

    for _, _, file_name, _, content in rows:
        toks = [t.lower() for t in TOKEN_RE.findall(f"{file_name} {content}")]
        doc_tokens_list.append(toks)
        for unique_tok in set(toks):
            if unique_tok in q_tokens:
                doc_freq[unique_tok] += 1

    avg_len = sum(len(t) for t in doc_tokens_list) / max(1, n_docs)
    k1, b = 1.5, 0.75

    scored = []
    for row, toks in zip(rows, doc_tokens_list):
        if not toks:
            continue
        tf = Counter(toks)
        score = 0.0
        dl = len(toks)
        for qt in q_tokens:
            freq = tf.get(qt, 0)
            if freq == 0:
                continue
            df = doc_freq.get(qt, 0)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            score += idf * ((freq * (k1 + 1.0)) / (freq + k1 * (1.0 - b + b * (dl / max(1.0, avg_len)))))

        if score > 0:
            scored.append({
                "score": round(score, 3),
                "file_path": row[1],
                "file_name": row[2],
                "chunk_index": row[3],
                "content": row[4],
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_rag_context(query: str, top_k: int = 5) -> str:
    hits = search_rag(query, top_k=top_k)
    if not hits:
        return ""
    blocks = []
    for idx, h in enumerate(hits, 1):
        blocks.append(
            f"[Source {idx}: {h['file_name']} (chunk #{h['chunk_index']}, path: {h['file_path']})]\n"
            f"{h['content']}"
        )
    return "\n\n---\n\n".join(blocks)


initialize_rag()

