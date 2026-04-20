"""Code generation from IR to PNG using Pillow."""

from __future__ import annotations

from PIL import Image

from ir import IRInstruction


def generate_image(instructions: list[IRInstruction], output_path: str = "output.png", scale: int = 1) -> str:
    """Execute IR instructions and save output image."""
    if scale < 1:
        raise ValueError("scale must be >= 1")

    width = 16
    height = 16
    colors: dict[str, tuple[int, int, int]] = {}
    variables: dict[str, int] = {}
    loops: list[tuple[str, int, int, int]] = []

    img = Image.new("RGB", (width, height), "black")
    pixels = img.load()

    ip = 0
    while ip < len(instructions):
        inst = instructions[ip]
        opcode = inst.opcode

        if opcode == "SET_CANVAS":
            width, height = int(inst.operands[0]), int(inst.operands[1])
            img = Image.new("RGB", (width, height), "black")
            pixels = img.load()
            ip += 1
            continue

        if opcode == "DEFINE_COLOR":
            name = str(inst.operands[0])
            hex_color = str(inst.operands[1])
            colors[name] = _hex_to_rgb(hex_color)
            ip += 1
            continue

        if opcode == "SET_VAR":
            name = str(inst.operands[0])
            variables[name] = _resolve_operand(inst.operands[1], variables)
            ip += 1
            continue

        if opcode == "DRAW_PIXEL":
            x = _resolve_operand(inst.operands[0], variables)
            y = _resolve_operand(inst.operands[1], variables)
            color_name = str(inst.operands[2])
            color = _resolve_color(color_name, colors)
            if 0 <= x < width and 0 <= y < height:
                pixels[x, y] = color
            ip += 1
            continue

        if opcode == "DRAW_RECT":
            x = _resolve_operand(inst.operands[0], variables)
            y = _resolve_operand(inst.operands[1], variables)
            rect_w = _resolve_operand(inst.operands[2], variables)
            rect_h = _resolve_operand(inst.operands[3], variables)
            color_name = str(inst.operands[4])
            color = _resolve_color(color_name, colors)

            for i in range(x, x + rect_w):
                for j in range(y, y + rect_h):
                    if 0 <= i < width and 0 <= j < height:
                        pixels[i, j] = color
            ip += 1
            continue

        if opcode == "LOOP_BEGIN":
            var_name = str(inst.operands[0])
            start = int(inst.operands[1])
            end = int(inst.operands[2])
            variables[var_name] = start
            loops.append((var_name, start, end, ip))
            ip += 1
            continue

        if opcode == "LOOP_END":
            if not loops:
                ip += 1
                continue
            var_name, _start, end, begin_ip = loops[-1]
            current = variables.get(var_name, end)
            if current < end:
                variables[var_name] = current + 1
                ip = begin_ip + 1
            else:
                loops.pop()
                ip += 1
            continue

        ip += 1

    if scale > 1:
        img = img.resize((width * scale, height * scale), Image.NEAREST)

    img.save(output_path)
    return output_path


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_clean = hex_color.lstrip("#")
    return (
        int(hex_clean[0:2], 16),
        int(hex_clean[2:4], 16),
        int(hex_clean[4:6], 16),
    )


def _resolve_operand(operand: object, variables: dict[str, int]) -> int:
    if isinstance(operand, int):
        return operand

    if isinstance(operand, tuple) and len(operand) == 2 and operand[0] == "VAR":
        name = operand[1]
        if not isinstance(name, str):
            raise ValueError(f"Invalid variable reference: {operand!r}")
        if name not in variables:
            raise ValueError(f"Undefined variable at codegen: {name}")
        return variables[name]

    if isinstance(operand, tuple) and len(operand) == 3 and operand[0] == "ADD":
        return _resolve_operand(operand[1], variables) + _resolve_operand(operand[2], variables)

    raise ValueError(f"Unsupported operand: {operand!r}")


def _resolve_color(color_name: str, colors: dict[str, tuple[int, int, int]]) -> tuple[int, int, int]:
    if color_name not in colors:
        raise ValueError(f"Undefined color at codegen: {color_name}")
    return colors[color_name]

