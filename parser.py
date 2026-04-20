"""Recursive-descent parser for the Pixel Compiler DSL."""

from __future__ import annotations

from dataclasses import dataclass

from lexer import Token, tokenize


@dataclass(frozen=True)
class Program:
    statements: list[Statement]


@dataclass(frozen=True)
class Number:
    value: int
    line: int
    column: int


@dataclass(frozen=True)
class VarRef:
    name: str
    line: int
    column: int


@dataclass(frozen=True)
class BinaryOp:
    operator: str
    left: NumericExpr
    right: NumericExpr
    line: int
    column: int


NumericExpr = Number | VarRef | BinaryOp


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    line: int
    column: int


@dataclass(frozen=True)
class Color:
    name: str
    hex_value: str
    line: int
    column: int


@dataclass(frozen=True)
class Pixel:
    x: NumericExpr
    y: NumericExpr
    color: str
    line: int
    column: int


@dataclass(frozen=True)
class Rect:
    x: NumericExpr
    y: NumericExpr
    width: NumericExpr
    height: NumericExpr
    color: str
    line: int
    column: int


@dataclass(frozen=True)
class Var:
    name: str
    value: NumericExpr
    line: int
    column: int


@dataclass(frozen=True)
class Loop:
    name: str
    start: int
    end: int
    body: list[Statement]
    line: int
    column: int


Statement = Canvas | Color | Pixel | Rect | Var | Loop


class Parser:
    """Simple recursive-descent parser."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def parse(self) -> Program:
        statements = self._parse_statement_list(stop_on_rbrace=False)
        if self._peek() is not None:
            token = self._peek()
            raise SyntaxError(f"Unexpected token {token.value!r} at line {token.line}, column {token.column}")
        return Program(statements)

    def _parse_statement_list(self, *, stop_on_rbrace: bool) -> list[Statement]:
        statements: list[Statement] = []

        while self._peek() is not None:
            if stop_on_rbrace and self._check("RBRACE"):
                break
            if self._match("NEWLINE"):
                continue
            statements.append(self._parse_statement())
            while self._match("NEWLINE"):
                pass

        return statements

    def _parse_statement(self) -> Statement:
        keyword_token = self._expect_keyword_token(
            "CANVAS",
            "COLOR",
            "PIXEL",
            "RECT",
            "VAR",
            "LOOP",
        )
        keyword = keyword_token.value
        line = keyword_token.line
        column = keyword_token.column

        if keyword == "CANVAS":
            width = self._expect_number()
            self._expect("COMMA")
            height = self._expect_number()
            return Canvas(width, height, line, column)

        if keyword == "COLOR":
            name = self._expect("ID").value
            self._expect("EQUAL")
            hex_value = self._expect("HEX").value
            return Color(name, hex_value, line, column)

        if keyword == "PIXEL":
            x = self._parse_numeric_expr()
            self._expect("COMMA")
            y = self._parse_numeric_expr()
            self._expect("COMMA")
            color = self._expect("ID").value
            return Pixel(x, y, color, line, column)

        if keyword == "RECT":
            x = self._parse_numeric_expr()
            self._expect("COMMA")
            y = self._parse_numeric_expr()
            self._expect("COMMA")
            width = self._parse_numeric_expr()
            self._expect("COMMA")
            height = self._parse_numeric_expr()
            self._expect("COMMA")
            color = self._expect("ID").value
            return Rect(x, y, width, height, color, line, column)

        if keyword == "VAR":
            name = self._expect("ID").value
            self._expect("EQUAL")
            value = self._parse_add_expr()
            return Var(name, value, line, column)

        # LOOP ID = NUMBER TO NUMBER { <statement_list> }
        name = self._expect("ID").value
        self._expect("EQUAL")
        start = self._expect_number()
        self._expect_keyword_token("TO")
        end = self._expect_number()
        self._expect("LBRACE")
        while self._match("NEWLINE"):
            pass
        body = self._parse_statement_list(stop_on_rbrace=True)
        self._expect("RBRACE")
        return Loop(name, start, end, body, line, column)

    def _peek(self) -> Token | None:
        if self.pos >= len(self.tokens):
            return None
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        token = self.tokens[self.pos]
        self.pos += 1
        return token

    def _check(self, token_type: str) -> bool:
        token = self._peek()
        return token is not None and token.type == token_type

    def _match(self, token_type: str) -> bool:
        if self._check(token_type):
            self._advance()
            return True
        return False

    def _expect(self, token_type: str) -> Token:
        token = self._peek()
        if token is None:
            raise SyntaxError(f"Expected {token_type}, found end of input")
        if token.type != token_type:
            raise SyntaxError(
                f"Expected {token_type}, found {token.type}({token.value!r}) "
                f"at line {token.line}, column {token.column}"
            )
        return self._advance()

    def _expect_keyword_token(self, *values: str) -> Token:
        token = self._peek()
        expected_values = ", ".join(values)
        if token is None:
            raise SyntaxError(f"Expected keyword ({expected_values}), found end of input")
        if token.type != "KEYWORD" or token.value not in values:
            raise SyntaxError(
                f"Expected keyword ({expected_values}), found {token.type}({token.value!r}) "
                f"at line {token.line}, column {token.column}"
            )
        return self._advance()

    def _expect_number(self) -> int:
        return int(self._expect("NUMBER").value)

    def _parse_numeric_expr(self) -> NumericExpr:
        return self._parse_numeric_term()

    def _parse_numeric_term(self) -> NumericExpr:
        token = self._peek()
        if token is None:
            raise SyntaxError("Expected NUMBER or ID, found end of input")
        if token.type == "NUMBER":
            consumed = self._expect("NUMBER")
            return Number(int(consumed.value), consumed.line, consumed.column)
        if token.type == "ID":
            consumed = self._advance()
            return VarRef(consumed.value, consumed.line, consumed.column)
        raise SyntaxError(
            f"Expected NUMBER or ID, found {token.type}({token.value!r}) "
            f"at line {token.line}, column {token.column}"
        )

    def _parse_add_expr(self) -> NumericExpr:
        expr = self._parse_numeric_term()
        while self._match("PLUS"):
            right = self._parse_numeric_term()
            expr = BinaryOp("+", expr, right, expr.line, expr.column)
        return expr


def parse(tokens: list[Token]) -> Program:
    """Parse a token sequence into an AST."""
    return Parser(tokens).parse()


def parse_source(source: str) -> Program:
    """Convenience function: tokenize, then parse."""
    return parse(tokenize(source))

