"""Built-in tools for the agent loop. Each tool = JSON schema the model sees + a Python function."""
import ast
import operator
from datetime import datetime, timezone
from pathlib import Path

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("only numbers and + - * / // % ** are allowed")


def calculator(expression: str) -> str:
    """Safe arithmetic: parses to an AST and evaluates only numeric operators (no eval())."""
    return str(_eval(ast.parse(expression, mode="eval").body))


def current_time() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_file(path: str, root: Path | None = None, max_chars: int = 20_000) -> str:
    """Read a text file, confined to `root` (default: the working directory)."""
    root = (root or Path.cwd()).resolve()
    target = (root / path).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path escapes {root}")
    return target.read_text()[:max_chars]


TOOLS = {
    "calculator": {
        "fn": calculator,
        "schema": {
            "name": "calculator",
            "description": "Evaluate an arithmetic expression, e.g. '(3 + 4) * 2 ** 10'.",
            "input_schema": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    "current_time": {
        "fn": current_time,
        "schema": {
            "name": "current_time",
            "description": "Get the current UTC date and time in ISO 8601.",
            "input_schema": {"type": "object", "properties": {}},
        },
    },
    "read_file": {
        "fn": read_file,
        "schema": {
            "name": "read_file",
            "description": "Read a text file under the current working directory (relative path).",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
}


def run(name: str, args: dict) -> tuple[str, bool]:
    """Execute a tool. Returns (output, is_error); errors go back to the model, not up the stack."""
    if name not in TOOLS:
        return f"unknown tool: {name}", True
    try:
        return TOOLS[name]["fn"](**args), False
    except Exception as e:  # noqa: BLE001 — the model should see the failure and recover
        return f"{type(e).__name__}: {e}", True
