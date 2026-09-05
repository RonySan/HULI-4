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
    expression = _replace_spoken_numbers(expression)
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
        r"^\s*(?:calcule|calcular|calcula|quanto\s+(?:e|eh|da)|qual\s+(?:e\s+)?o\s+resultado\s+de|faca\s+a\s+conta|(?:some|soma|somar|subtraia|subtrair|multiplique|multiplicar|divida|dividir)(?:\s+para\s+mim)?)\s*",
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


_SMALL_NUMBERS = {
    "zero": 0,
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
    "onze": 11,
    "doze": 12,
    "treze": 13,
    "catorze": 14,
    "quatorze": 14,
    "quinze": 15,
    "dezesseis": 16,
    "dezessete": 17,
    "dezoito": 18,
    "dezenove": 19,
    "vinte": 20,
    "trinta": 30,
    "quarenta": 40,
    "cinquenta": 50,
    "sessenta": 60,
    "setenta": 70,
    "oitenta": 80,
    "noventa": 90,
    "cem": 100,
    "cento": 100,
    "duzentos": 200,
    "duzentas": 200,
    "trezentos": 300,
    "trezentas": 300,
    "quatrocentos": 400,
    "quatrocentas": 400,
    "quinhentos": 500,
    "quinhentas": 500,
    "seiscentos": 600,
    "seiscentas": 600,
    "setecentos": 700,
    "setecentas": 700,
    "oitocentos": 800,
    "oitocentas": 800,
    "novecentos": 900,
    "novecentas": 900,
}
_SCALES = {
    "milhao": 1_000_000,
    "milhoes": 1_000_000,
    "bilhao": 1_000_000_000,
    "bilhoes": 1_000_000_000,
}


def _replace_spoken_numbers(expression: str) -> str:
    parts = re.split(r"(\*\*|[+\-*/()%])", expression)
    converted: list[str] = []
    for part in parts:
        value = part.strip()
        if not value or re.fullmatch(r"[+\-*/()%]|\*\*", value):
            converted.append(part)
            continue
        if re.fullmatch(r"\d+(?:\.\d+)?", value):
            converted.append(value)
            continue
        converted.append(str(_parse_spoken_number(value)))
    return " ".join(converted).strip()


def _parse_spoken_number(value: str) -> float:
    tokens = [token for token in value.split() if token != "e"]
    if not tokens:
        raise CalculatorError("Não consegui identificar os números da conta.")
    if tokens.count("mil") > 1 and not any(token in _SCALES for token in tokens):
        raise CalculatorError(
            "A sequência de números ficou ambígua. Repita usando 'milhão' ou faça uma parte por vez."
        )
    if "virgula" in tokens:
        position = tokens.index("virgula")
        integer = _parse_integer_tokens(tokens[:position])
        decimal_tokens = tokens[position + 1:]
        if not decimal_tokens or any(token not in _SMALL_NUMBERS or _SMALL_NUMBERS[token] > 9 for token in decimal_tokens):
            raise CalculatorError("Depois da vírgula, diga os algarismos separadamente.")
        decimal = "".join(str(_SMALL_NUMBERS[token]) for token in decimal_tokens)
        return float(f"{integer}.{decimal}")
    return float(_parse_integer_tokens(tokens))


def _parse_integer_tokens(tokens: list[str]) -> int:
    if not tokens:
        return 0
    total = 0
    group = 0
    for token in tokens:
        if token in _SMALL_NUMBERS:
            group += _SMALL_NUMBERS[token]
        elif token == "mil":
            total += (group or 1) * 1_000
            group = 0
        elif token in _SCALES:
            total += (group or 1) * _SCALES[token]
            group = 0
        else:
            raise CalculatorError(f"Não reconheci '{token}' como parte de um número.")
    return total + group


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
