"""IR optimizer passes for Pixel Compiler."""

from __future__ import annotations

from ir import IRInstruction


IROperand = object


def optimize_ir(instructions: list[IRInstruction]) -> list[IRInstruction]:
    """Run all optimization passes."""
    folded = _constant_fold(instructions)
    return _eliminate_overdraw(folded)


def _constant_fold(instructions: list[IRInstruction]) -> list[IRInstruction]:
    const_vars: dict[str, int] = {}
    folded: list[IRInstruction] = []

    for inst in instructions:
        if inst.opcode == "SET_VAR":
            name, expr = inst.operands
            value = _eval_operand(expr, const_vars)
            if value is not None:
                const_vars[str(name)] = value
                folded.append(IRInstruction("SET_VAR", (name, value)))
            else:
                const_vars.pop(str(name), None)
                folded.append(IRInstruction("SET_VAR", (name, _rewrite_operand(expr, const_vars))))
            continue

        if inst.opcode in {"DRAW_PIXEL", "DRAW_RECT"}:
            rewritten = tuple(_rewrite_operand(op, const_vars) for op in inst.operands)
            folded.append(IRInstruction(inst.opcode, rewritten))
            continue

        if inst.opcode in {"LOOP_BEGIN", "LOOP_END"}:
            const_vars.clear()
            folded.append(inst)
            continue

        folded.append(inst)

    return folded


def _eliminate_overdraw(instructions: list[IRInstruction]) -> list[IRInstruction]:
    seen_pixels: set[tuple[int, int]] = set()
    kept_reversed: list[IRInstruction] = []

    for inst in reversed(instructions):
        if inst.opcode in {"LOOP_BEGIN", "LOOP_END", "DRAW_RECT"}:
            seen_pixels.clear()
            kept_reversed.append(inst)
            continue

        if inst.opcode != "DRAW_PIXEL":
            kept_reversed.append(inst)
            continue

        x, y, _color = inst.operands
        if isinstance(x, int) and isinstance(y, int):
            coord = (x, y)
            if coord in seen_pixels:
                continue
            seen_pixels.add(coord)
        else:
            seen_pixels.clear()

        kept_reversed.append(inst)

    kept_reversed.reverse()
    return kept_reversed


def _rewrite_operand(operand: IROperand, const_vars: dict[str, int]) -> IROperand:
    value = _eval_operand(operand, const_vars)
    if value is not None:
        return value

    if isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "VAR":
        return operand

    if isinstance(operand, tuple) and len(operand) == 3 and operand[0] == "ADD":
        return ("ADD", _rewrite_operand(operand[1], const_vars), _rewrite_operand(operand[2], const_vars))

    return operand


def _eval_operand(operand: IROperand, const_vars: dict[str, int]) -> int | None:
    if isinstance(operand, int):
        return operand

    if isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "VAR":
        name = operand[1]
        if isinstance(name, str):
            return const_vars.get(name)
        return None

    if isinstance(operand, tuple) and len(operand) == 3 and operand[0] == "ADD":
        left = _eval_operand(operand[1], const_vars)
        right = _eval_operand(operand[2], const_vars)
        if left is None or right is None:
            return None
        return left + right

    return None

