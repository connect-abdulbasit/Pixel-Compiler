"""Lower Pixel Compiler AST into simple IR instructions."""

from __future__ import annotations

from dataclasses import dataclass

from parser import BinaryOp, Canvas, Color, Loop, Number, NumericExpr, Pixel, Program, Rect, Statement, Var, VarRef


@dataclass(frozen=True)
class IRInstruction:
    """A simple IR instruction with opcode and operands."""

    opcode: str
    operands: tuple[object, ...] = ()

    def __repr__(self) -> str:
        if not self.operands:
            return self.opcode
        return f"{self.opcode} " + " ".join(str(operand) for operand in self.operands)


def generate_ir(program: Program) -> list[IRInstruction]:
    """Convert AST into a linear list of IR instructions."""
    instructions: list[IRInstruction] = []
    _lower_statements(program.statements, instructions)
    return instructions


def _lower_statements(statements: list[Statement], out: list[IRInstruction]) -> None:
    for stmt in statements:
        if isinstance(stmt, Canvas):
            out.append(IRInstruction("SET_CANVAS", (stmt.width, stmt.height)))
            continue

        if isinstance(stmt, Color):
            out.append(IRInstruction("DEFINE_COLOR", (stmt.name, stmt.hex_value)))
            continue

        if isinstance(stmt, Pixel):
            out.append(
                IRInstruction(
                    "DRAW_PIXEL",
                    (_encode_numeric(stmt.x), _encode_numeric(stmt.y), stmt.color),
                )
            )
            continue

        if isinstance(stmt, Rect):
            out.append(
                IRInstruction(
                    "DRAW_RECT",
                    (
                        _encode_numeric(stmt.x),
                        _encode_numeric(stmt.y),
                        _encode_numeric(stmt.width),
                        _encode_numeric(stmt.height),
                        stmt.color,
                    ),
                )
            )
            continue

        if isinstance(stmt, Var):
            out.append(IRInstruction("SET_VAR", (stmt.name, _encode_numeric(stmt.value))))
            continue

        if isinstance(stmt, Loop):
            out.append(IRInstruction("LOOP_BEGIN", (stmt.name, stmt.start, stmt.end)))
            _lower_statements(stmt.body, out)
            out.append(IRInstruction("LOOP_END", (stmt.name,)))
            continue


def _encode_numeric(expr: NumericExpr) -> object:
    """Encode numeric AST nodes as IR operands."""
    if isinstance(expr, Number):
        return expr.value
    if isinstance(expr, VarRef):
        return ("VAR", expr.name)
    if isinstance(expr, BinaryOp):
        if expr.operator != "+":
            raise TypeError(f"Unsupported numeric operator: {expr.operator!r}")
        return ("ADD", _encode_numeric(expr.left), _encode_numeric(expr.right))
    raise TypeError(f"Unsupported numeric expression: {expr!r}")

