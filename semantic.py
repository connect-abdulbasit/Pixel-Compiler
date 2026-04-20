"""Semantic analysis for the Pixel Compiler DSL."""

from __future__ import annotations

from dataclasses import dataclass

from parser import (
    BinaryOp,
    Canvas,
    Color,
    Loop,
    Number,
    NumericExpr,
    Pixel,
    Program,
    Rect,
    Statement,
    Var,
    VarRef,
    parse_source,
)


@dataclass(frozen=True)
class ValueRange:
    min_value: int
    max_value: int


class SemanticError(Exception):
    """Raised when semantic validation fails."""


class SemanticAnalyzer:
    """Validates semantic correctness and builds symbol tables."""

    def __init__(self) -> None:
        self.canvas: tuple[int, int] | None = None
        self.symbols: dict[str, dict[str, object]] = {
            "colors": {},
            "variables": {},
        }
        self.errors: list[str] = []

    def analyze(self, program: Program) -> dict[str, dict[str, object]]:
        self._analyze_statements(program.statements)
        if self.errors:
            raise SemanticError("\n".join(self.errors))
        return self.symbols

    def _analyze_statements(self, statements: list[Statement]) -> None:
        for stmt in statements:
            if isinstance(stmt, Canvas):
                self.canvas = (stmt.width, stmt.height)
                continue

            if isinstance(stmt, Color):
                self.symbols["colors"][stmt.name] = stmt.hex_value
                continue

            if isinstance(stmt, Var):
                self.symbols["variables"][stmt.name] = self._resolve_expr(stmt.value)
                continue

            if isinstance(stmt, Pixel):
                self._require_canvas("PIXEL", stmt.line, stmt.column)
                self._require_color(stmt.color, "PIXEL", stmt.line, stmt.column)
                x_range = self._resolve_expr(stmt.x)
                y_range = self._resolve_expr(stmt.y)
                if self.canvas is not None:
                    self._check_axis_bounds(x_range, 0, self.canvas[0] - 1, "PIXEL x", stmt.line, stmt.column)
                    self._check_axis_bounds(y_range, 0, self.canvas[1] - 1, "PIXEL y", stmt.line, stmt.column)
                continue

            if isinstance(stmt, Rect):
                self._require_canvas("RECT", stmt.line, stmt.column)
                self._require_color(stmt.color, "RECT", stmt.line, stmt.column)
                x_range = self._resolve_expr(stmt.x)
                y_range = self._resolve_expr(stmt.y)
                w_range = self._resolve_expr(stmt.width)
                h_range = self._resolve_expr(stmt.height)
                self._check_positive_size(w_range, "RECT width", stmt.line, stmt.column)
                self._check_positive_size(h_range, "RECT height", stmt.line, stmt.column)
                if self.canvas is not None:
                    max_x = self.canvas[0] - 1
                    max_y = self.canvas[1] - 1
                    self._check_axis_bounds(x_range, 0, max_x, "RECT x", stmt.line, stmt.column)
                    self._check_axis_bounds(y_range, 0, max_y, "RECT y", stmt.line, stmt.column)
                    right_edge = ValueRange(
                        x_range.min_value + w_range.min_value - 1,
                        x_range.max_value + w_range.max_value - 1,
                    )
                    bottom_edge = ValueRange(
                        y_range.min_value + h_range.min_value - 1,
                        y_range.max_value + h_range.max_value - 1,
                    )
                    self._check_axis_bounds(right_edge, 0, max_x, "RECT right edge", stmt.line, stmt.column)
                    self._check_axis_bounds(bottom_edge, 0, max_y, "RECT bottom edge", stmt.line, stmt.column)
                continue

            if isinstance(stmt, Loop):
                old_value = self.symbols["variables"].get(stmt.name)
                loop_range = ValueRange(min(stmt.start, stmt.end), max(stmt.start, stmt.end))
                self.symbols["variables"][stmt.name] = loop_range
                self._analyze_statements(stmt.body)
                if old_value is None:
                    del self.symbols["variables"][stmt.name]
                else:
                    self.symbols["variables"][stmt.name] = old_value

    def _resolve_expr(self, expr: NumericExpr) -> ValueRange:
        if isinstance(expr, Number):
            return ValueRange(expr.value, expr.value)
        if isinstance(expr, BinaryOp):
            left = self._resolve_expr(expr.left)
            right = self._resolve_expr(expr.right)
            if expr.operator == "+":
                return ValueRange(left.min_value + right.min_value, left.max_value + right.max_value)
            self._error(f"Unsupported operator '{expr.operator}'", expr.line, expr.column)
            return ValueRange(0, 0)
        variable_range = self.symbols["variables"].get(expr.name)
        if variable_range is None:
            self._error(f"Undefined variable '{expr.name}'", expr.line, expr.column)
            return ValueRange(0, 0)
        return variable_range  # type: ignore[return-value]

    def _require_canvas(self, statement_name: str, line: int, column: int) -> None:
        if self.canvas is None:
            self._error(f"{statement_name} used before CANVAS definition", line, column)

    def _require_color(self, color_name: str, statement_name: str, line: int, column: int) -> None:
        if color_name not in self.symbols["colors"]:
            self._error(f"{statement_name} uses undefined color '{color_name}'", line, column)

    def _check_axis_bounds(
        self,
        value_range: ValueRange,
        min_allowed: int,
        max_allowed: int,
        label: str,
        line: int,
        column: int,
    ) -> None:
        if value_range.min_value < min_allowed or value_range.max_value > max_allowed:
            self._error(
                f"{label} out of bounds: [{value_range.min_value}, {value_range.max_value}] "
                f"not in [{min_allowed}, {max_allowed}]",
                line,
                column,
            )

    def _check_positive_size(self, value_range: ValueRange, label: str, line: int, column: int) -> None:
        if value_range.min_value <= 0:
            self._error(
                f"{label} must be > 0, found range [{value_range.min_value}, {value_range.max_value}]",
                line,
                column,
            )

    def _error(self, message: str, line: int, column: int) -> None:
        self.errors.append(f"Line {line}, col {column}: {message}")


def analyze(program: Program) -> dict[str, dict[str, object]]:
    """Analyze a parsed AST and return the symbol table."""
    return SemanticAnalyzer().analyze(program)


def analyze_source(source: str) -> dict[str, dict[str, object]]:
    """Convenience function: parse source and run semantic checks."""
    return analyze(parse_source(source))

