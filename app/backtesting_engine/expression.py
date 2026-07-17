"""A minimal, safe evaluator for SDL rule conditions.

`app.strategy_builder.models.RuleReference.condition` is carried through
Phase 8 as opaque text -- Strategy Builder never interprets it (see
`PROJECT_IDEAS.md`, "Condition expression grammar", explicitly deferred
"until the Backtesting Engine exists"). The Backtesting Engine is the
first real consumer, so this module implements exactly enough of a
grammar to drive deterministic simulation: comparisons, boolean
combinators, and basic arithmetic over named values (indicator outputs,
detector flags, OHLCV fields) resolved from a flat namespace.

This is intentionally NOT a general-purpose expression language. It is
built on Python's `ast` module with a strict node whitelist -- no
attribute access, no subscripting, no comprehensions, and no function
calls beyond a tiny numeric whitelist -- so a condition string can never
execute arbitrary code, import anything, or reach outside its namespace.
"""

import ast
import operator
from typing import Any

from app.backtesting_engine.exceptions import BacktestExecutionError

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
}

_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}

_COMPARE_OPS = {
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
}

_ALLOWED_CALLS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
}


def evaluate_condition(condition: str, namespace: dict[str, Any]) -> bool:
    """Evaluate `condition` against `namespace`, returning a bool.

    `namespace` should contain only values already known at the current
    candle (e.g. sliced indicator/detector series up to and including the
    current index) -- this function has no awareness of "future" data
    itself; the no-look-ahead guarantee is the caller's responsibility
    (see `app.backtesting_engine.simulator.TradeSimulator`).

    Raises:
        BacktestExecutionError: if `condition` is empty, contains a
            disallowed construct, or references an unknown name.
    """
    if not condition or not condition.strip():
        raise BacktestExecutionError("Cannot evaluate an empty condition.")
    try:
        tree = ast.parse(condition, mode="eval")
    except SyntaxError as exc:
        raise BacktestExecutionError(f"Invalid condition syntax: {condition!r} ({exc})") from exc

    value = _eval_node(tree.body, namespace, condition)
    return bool(value)


def _eval_node(node: ast.AST, namespace: dict[str, Any], source: str) -> Any:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)) or node.value is None or isinstance(node.value, str):
            return node.value
        raise BacktestExecutionError(f"Disallowed constant in condition {source!r}.")

    if isinstance(node, ast.Name):
        if node.id not in namespace:
            raise BacktestExecutionError(f"Unknown name {node.id!r} in condition {source!r}.")
        return namespace[node.id]

    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        left = _eval_node(node.left, namespace, source)
        right = _eval_node(node.right, namespace, source)
        if left is None or right is None:
            return None
        return _BIN_OPS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        operand = _eval_node(node.operand, namespace, source)
        if operand is None:
            return None
        return _UNARY_OPS[type(node.op)](operand)

    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, namespace, source) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(bool(v) for v in values)
        return any(bool(v) for v in values)

    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, namespace, source)
        for op, comparator in zip(node.ops, node.comparators):
            if type(op) not in _COMPARE_OPS:
                raise BacktestExecutionError(f"Disallowed comparison operator in condition {source!r}.")
            right = _eval_node(comparator, namespace, source)
            if left is None or right is None:
                return False
            if not _COMPARE_OPS[type(op)](left, right):
                return False
            left = right
        return True

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_CALLS:
            raise BacktestExecutionError(f"Disallowed function call in condition {source!r}.")
        args = [_eval_node(a, namespace, source) for a in node.args]
        return _ALLOWED_CALLS[node.func.id](*args)

    raise BacktestExecutionError(f"Disallowed syntax in condition {source!r}: {type(node).__name__}")
