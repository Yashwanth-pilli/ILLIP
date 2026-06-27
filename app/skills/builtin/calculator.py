"""
Calculator skill — safe AST-based math evaluator (no eval()).
"""

import ast
import operator
from app.skills.base_skill import BaseSKill

_OPS = {
    ast.Add:  operator.add,
    ast.Sub:  operator.sub,
    ast.Mult: operator.mul,
    ast.Div:  operator.truediv,
    ast.Pow:  operator.pow,
    ast.Mod:  operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


class CalculatorSkill(BaseSKill):
    name = "calculator"
    description = (
        "Evaluate a math expression safely. Use for arithmetic, powers, modulo, "
        "or any calculation. Examples: '2 + 2', '2**10', '(100 / 3) * 7', '200 * 0.15'."
    )
    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Math expression to evaluate. Use ** for powers, % for modulo.",
            }
        },
        "required": ["expression"],
    }

    async def execute(self, expression: str, **_) -> str:
        try:
            expr = expression.strip().replace("^", "**")
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree.body)
            # Pretty-print: drop .0 for whole numbers
            result_str = str(int(result)) if result == int(result) else f"{result:.6g}"
            return f"{expression} = {result_str}"
        except ZeroDivisionError:
            return f"Error: division by zero in '{expression}'"
        except Exception as e:
            return f"Cannot evaluate '{expression}': {e}"
