"""Regex-based lexer for the Pixel Compiler DSL."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Language keywords supported by parser phases 1-2.
KEYWORDS = {"CANVAS", "COLOR", "PIXEL", "RECT", "VAR", "LOOP", "TO"}

TOKEN_SPEC = [
    ("NUMBER", r"\d+"),
    ("HEX", r"\#[0-9A-Fa-f]{6}"),
    ("ID", r"[a-zA-Z_][a-zA-Z0-9_]*"),
    ("PLUS", r"\+"),
    ("COMMA", r","),
    ("EQUAL", r"="),
    ("LBRACE", r"\{"),
    ("RBRACE", r"\}"),
    ("NEWLINE", r"\n"),
    ("SKIP", r"[ \t]+"),
    ("MISMATCH", r"."),
]

MASTER_PATTERN = re.compile("|".join(f"(?P<{name}>{pattern})" for name, pattern in TOKEN_SPEC))


@dataclass(frozen=True)
class Token:
    """A lexical token produced by the lexer."""

    type: str
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"{self.type}({self.value})"


def tokenize(source: str) -> list[Token]:
    """Convert source code text into a list of tokens."""
    tokens: list[Token] = []
    line_num = 1
    line_start = 0

    for match in MASTER_PATTERN.finditer(source):
        kind = match.lastgroup
        value = match.group()
        column = match.start() - line_start + 1

        if kind == "NEWLINE":
            tokens.append(Token("NEWLINE", value, line_num, column))
            line_num += 1
            line_start = match.end()
            continue

        if kind == "SKIP":
            continue

        if kind == "ID" and value.upper() in KEYWORDS:
            tokens.append(Token("KEYWORD", value.upper(), line_num, column))
            continue

        if kind == "MISMATCH":
            raise SyntaxError(f"Unexpected character {value!r} at line {line_num}, column {column}")

        tokens.append(Token(kind, value, line_num, column))

    return tokens

