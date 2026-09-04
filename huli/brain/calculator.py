"""Calculadora deterministica sem uso de eval."""

from __future__ import annotations

import ast
import math
import operator
import re
import unicodedata


class CalculatorError(ValueError):
    pass


_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def calculate(text: str) -> float:
    expression = _extract_expression(text)
    percent = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%\s*de\s*([+-]?\d+(?:\.\d+)?)", expression)
    if percent:
        return _validate_number(float(percent.group(1)) / 100 * float(percent.group(2)))
    expression = _replace_words(expression)
    if not expression or len(expression) > 100:
        raise CalculatorError("Informe uma conta curta, por exemplo: quanto é 15% de 850?")
    if re.search(r"[^0-9+\-*/().%\s]", expression):
        raise CalculatorError("A conta contém algo que não reconheço com segurança.")
    try:
        tree = ast.parse(expression, mode="eval")
        return _validate_number(_evaluate(tree.body, depth=0))
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise CalculatorError("Não consegui calcular essa expressão.") from exc


def format_result(value: float) -> str:
    if math.isclose(value, round(value), abs_tol=1e-10):
        return f"{int(round(value)):,}".replace(",", ".")
    rendered = f"{value:.10f}".rstrip("0").rstrip(".")
    whole, dot, decimal = rendered.partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"{grouped},{decimal}" if dot else grouped


def _extract_expression(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or "").casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"^\s*huli\s*[,;:]?\s*", "", value)
    value = re.sub(
        r"^\s*(?:calcule|calcular|calcula|quanto\s+(?:e|eh|da)|qual\s+(?:e\s+)?o\s+resultado\s+de|faca\s+a\s+conta)\s*",
        "",
        value,
    )
    return value.strip(" ?=.").replace(",", ".")


def _replace_words(expression: str) -> str:
    replacements = (
        (r"\belevado\s+a\b", "**"),
        (r"\bao\s+quadrado\b", "**2"),
        (r"\bdividido\s+por\b", "/"),
        (r"\bmultiplicado\s+por\b", "*"),
        (r"\bvezes\b", "*"),
        (r"\bmais\b", "+"),
        (r"\bmenos\b", "-"),
        (r"\bmodulo\b", "%"),
    )
    for pattern, replacement in replacements:
        expression = re.sub(pattern, replacement, expression)
    return re.sub(r"\s+x\s+", " * ", expression)


def _evaluate(node: ast.AST, *, depth: int) -> float:
    if depth > 12:
        raise CalculatorError("A conta é complexa demais.")
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return _validate_number(float(node.value))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        return _validate_number(_UNARY[type(node.op)](_evaluate(node.operand, depth=depth + 1)))
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left = _evaluate(node.left, depth=depth + 1)
        right = _evaluate(node.right, depth=depth + 1)
        if isinstance(node.op, ast.Pow) and abs(right) > 10:
            raise CalculatorError("O expoente precisa estar entre -10 e 10.")
        return _validate_number(_BINARY[type(node.op)](left, right))
    raise CalculatorError("A conta contém uma operação não permitida.")


def _validate_number(value: float) -> float:
    if not math.isfinite(value) or abs(value) > 1_000_000_000_000:
        raise CalculatorError("O resultado ficou fora do limite seguro.")
    return value
