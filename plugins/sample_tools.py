"""Built-in example JARVIS Plugin Pack demonstrating the Plugin/Tool System (7.7)."""

import ast
import math
import operator
import re
import hashlib


_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval_math(node):
    if isinstance(node, ast.Expression):
        return _safe_eval_math(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval_math(node.left), _safe_eval_math(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_safe_eval_math(node.operand))
    raise ValueError("Only basic numeric math expressions are allowed.")


def tool_calc(args: str) -> str:
    expr = (args or "").strip()
    if not expr:
        return "Usage: /plugin calc <expression> (e.g. 25 * 4 + 12)"
    tree = ast.parse(expr, mode="eval")
    result = _safe_eval_math(tree)
    return f"{expr} = {result}"


def tool_hash(args: str) -> str:
    text = (args or "").strip()
    if not text:
        return "Usage: /plugin hash <text>"
    data = text.encode("utf-8")
    return (
        f"SHA-256: {hashlib.sha256(data).hexdigest()}\n"
        f"SHA-512: {hashlib.sha512(data).hexdigest()[:64]}..."
    )


def tool_password_check(args: str) -> str:
    pw = args or ""
    if not pw:
        return "Usage: /plugin pwcheck <password>"
    score = 0
    tips = []
    if len(pw) >= 12:
        score += 2
    elif len(pw) >= 8:
        score += 1
        tips.append("Use at least 12 characters.")
    else:
        tips.append("Too short — use 12+ characters.")

    for label, pat in [
        ("uppercase letter", r"[A-Z]"),
        ("lowercase letter", r"[a-z]"),
        ("number", r"[0-9]"),
        ("special symbol", r"[^A-Za-z0-9]"),
    ]:
        if re.search(pat, pw):
            score += 1
        else:
            tips.append(f"Add at least one {label}.")

    rating = "Strong" if score >= 5 else ("Moderate" if score >= 3 else "Weak")
    entropy = len(pw) * math.log2(94 if score >= 5 else 62)
    out = f"Password Strength: {rating} (Score: {score}/6, Est. Entropy: ~{entropy:.0f} bits)"
    if tips:
        out += "\nSuggestions:\n" + "\n".join(f"  - {t}" for t in tips)
    return out


def register_tools():
    return {
        "calc": {
            "description": "Safe mathematical expression evaluator",
            "usage": "/plugin calc 12 * (8 + 4)",
            "func": tool_calc,
        },
        "hash": {
            "description": "Generate SHA-256 / SHA-512 hash for text",
            "usage": "/plugin hash hello world",
            "func": tool_hash,
        },
        "pwcheck": {
            "description": "Evaluate password strength and entropy locally",
            "usage": "/plugin pwcheck MyP@ssw0rd!2026",
            "func": tool_password_check,
        },
    }

