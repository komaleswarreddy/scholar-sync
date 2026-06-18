"""Unit tests for markdown-math preprocess (mirrors apps/web/src/lib/markdown-math.ts)."""

from __future__ import annotations

import re


def _normalize_blank_lines(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _normalize_display_math_delimiters(text: str) -> str:
    text = re.sub(r"\\\[\s*", "\n$$\n", text)
    text = re.sub(r"\s*\\\]", "\n$$\n", text)
    text = re.sub(r"\$\$\s*\n\s*\$\$", "\n$$\n", text)
    return text


def _normalize_inline_math_delimiters(text: str) -> str:
    return re.sub(r"\\\((.+?)\\\)", lambda m: f"${m.group(1).strip()}$", text, flags=re.DOTALL)


def _normalize_math_operators(expr: str) -> str:
    expr = re.sub(r"(\d)\s*[xX×]\s*(\d)", r"\1 \\times \2", expr)
    expr = re.sub(r"(\d)\s*\\times\s*(\d)", r"\1 \\times \2", expr)
    expr = re.sub(r"\\times(\d)", r"\\times \1", expr)
    expr = re.sub(r"(\d)\\times", r"\1 \\times", expr)
    return expr


def _normalize_math_units(expr: str) -> str:
    expr = re.sub(r"(\d)\s+km/h", r"\1\\,\\text{ km/h}", expr, flags=re.IGNORECASE)
    expr = re.sub(r"(\d)\s+m/s\^2", r"\1\\,\\text{ m/s}^2", expr, flags=re.IGNORECASE)
    expr = re.sub(r"(\d)\s+m/s(?!\^)", r"\1\\,\\text{ m/s}", expr, flags=re.IGNORECASE)
    return expr


def _polish_math_expression(expr: str) -> str:
    return _normalize_math_units(_normalize_math_operators(expr.strip()))


def _normalize_math_segments(text: str) -> str:
    def repl_block(m: re.Match[str]) -> str:
        return f"$$\n{_polish_math_expression(m.group(1))}\n$$"

    out = re.sub(r"\$\$([\s\S]+?)\$\$", repl_block, text)
    out = re.sub(
        r"(?<!\$)\$([^$\n]+?)\$(?!\$)",
        lambda m: f"${_polish_math_expression(m.group(1))}$",
        out,
    )
    return out


def preprocess_markdown_math(raw: str) -> str:
    if not (raw or "").strip():
        return ""
    text = raw.replace("\r\n", "\n")
    text = (
        text.replace("\\\\[", "\\[")
        .replace("\\\\]", "\\]")
        .replace("\\\\(", "\\(")
        .replace("\\\\)", "\\)")
    )
    text = _normalize_display_math_delimiters(text)
    text = _normalize_inline_math_delimiters(text)
    text = _normalize_math_segments(text)
    text = _normalize_blank_lines(text)
    return text


def test_display_math_converts_to_double_dollar_blocks():
    raw = r"1. To find acceleration:\n\[ a = \frac{v - u}{t} \]"
    out = preprocess_markdown_math(raw)
    assert "$$" in out
    assert r"\frac{v - u}{t}" in out
    assert "\\[" not in out or "$$" in out


def test_numbered_list_and_equation_preserve_structure():
    raw = (
        "1. Convert the final velocity from km/h to m/s:\n"
        r"\[ v = 72 \text{ km/h} = 20 \text{ m/s} \]\n"
        "2. Calculate acceleration:"
    )
    out = preprocess_markdown_math(raw)
    assert "1. Convert" in out
    assert "2. Calculate" in out
    assert "$$" in out


def test_plain_text_unchanged():
    raw = "This is a simple hint without math."
    assert preprocess_markdown_math(raw) == raw


def test_inline_math_parentheses_to_dollars():
    raw = r"The value is \( x = 5 \) units."
    out = preprocess_markdown_math(raw)
    assert "$x = 5$" in out


def test_times_operator_gets_spacing():
    raw = "$$v=\\frac{72\\times1000}{3600}$$"
    out = preprocess_markdown_math(raw)
    assert r"72 \times 1000" in out


def test_bare_units_wrapped_in_text():
    raw = "$$v = 72 km/h = 20 m/s$$"
    out = preprocess_markdown_math(raw)
    assert r"\text{ km/h}" in out
    assert r"\text{ m/s}" in out


def _replace_pdf_private_use_symbols(text: str) -> str:
    out = re.sub(r"([A-Za-z0-9])\s*\uf0a2", r"\1^{\\prime}", text)
    standalone = {
        "\uf0a3": r"\leq ",
        "\uf0b1": r"\pm ",
        "\uf0b3": r"\geq ",
        "\uf0b9": r"\neq ",
        "\uf06c": r"\lambda ",
        "\uf070": r"\pi ",
        "\uf044": r"\Delta ",
    }
    for glyph, latex in standalone.items():
        out = out.replace(glyph, latex)
    out = re.sub(r"[\uf000-\uf0ff]", "", out)
    return out


def _normalize_pdf_dashes(text: str) -> str:
    return re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", text)


def test_pdf_transpose_glyph_becomes_prime():
    raw = "if A + A \uf0a2 is a symmetric matrix"
    out = _replace_pdf_private_use_symbols(raw)
    assert r"A^{\prime}" in out
    assert "\uf0a2" not in out


def test_pdf_en_dash_becomes_hyphen():
    raw = "(A \u2013 A\uf0a2) cannot be a skew symmetric matrix"
    out = _normalize_pdf_dashes(raw)
    assert "\u2013" not in out
    assert "(A - A" in out


def test_pdf_plus_minus_glyph_becomes_latex():
    raw = "(A) \uf0b1 49"
    out = _replace_pdf_private_use_symbols(raw)
    assert r"\pm" in out
