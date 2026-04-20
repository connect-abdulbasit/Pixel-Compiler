"""CLI entry point for Pixel Compiler."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ir import generate_ir
from lexer import tokenize
from optimizer import optimize_ir
from parser import parse
from semantic import SemanticError, analyze


def main() -> None:
    """Run the Pixel Compiler CLI."""
    parser = _build_arg_parser()
    args = parser.parse_args()

    if args.interactive:
        _run_interactive(args.output, args.debug, args.scale)
        return

    if not args.input_file:
        parser.error("input file is required unless --interactive is used")

    source_path = Path(args.input_file)
    if not source_path.exists():
        print(f"Error: input file not found: {source_path}", file=sys.stderr)
        raise SystemExit(1)

    source = source_path.read_text(encoding="utf-8")
    success = _compile_source(source, args.output, args.debug, args.scale)
    if not success:
        raise SystemExit(1)


def _build_arg_parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description="Pixel Compiler")
    cli.add_argument("input_file", nargs="?", help="Path to .px source file")
    cli.add_argument("-o", "--output", default="output.png", help="Output image path")
    cli.add_argument("--scale", type=int, default=1, help="Output scale factor (e.g. 20 makes each pixel 20x20)")
    cli.add_argument("--debug", action="store_true", help="Print tokens, AST, and IR")
    cli.add_argument("--interactive", action="store_true", help="Start interactive mode")
    return cli


def _run_interactive(output_path: str, debug: bool, scale: int) -> None:
    print("Pixel Compiler Interactive Mode")
    print("Enter source code. Submit an empty line to compile. Type ':quit' to exit.")

    while True:
        lines: list[str] = []
        while True:
            try:
                line = input("px> " if not lines else "... ")
            except EOFError:
                print()
                return
            if line.strip() == ":quit":
                return
            if line == "":
                break
            lines.append(line)

        if not lines:
            continue

        source = "\n".join(lines) + "\n"
        _compile_source(source, output_path, debug, scale)


def _compile_source(source: str, output_path: str, debug: bool, scale: int) -> bool:
    try:
        tokens = tokenize(source)
        ast = parse(tokens)
        analyze(ast)
        ir = generate_ir(ast)
        optimized_ir = optimize_ir(ir)
    except (SyntaxError, SemanticError, ValueError) as exc:
        print(f"Compilation failed:\n{exc}", file=sys.stderr)
        return False

    if debug:
        print("=== TOKENS ===")
        print(tokens)
        print("\n=== AST ===")
        print(ast)
        print("\n=== IR ===")
        for instruction in optimized_ir:
            print(instruction)
        print()

    try:
        from codegen import generate_image
    except ModuleNotFoundError as exc:
        print("Code generation dependency missing: install Pillow (`python3 -m pip install Pillow`).", file=sys.stderr)
        _ = exc
        return False

    generated_path = generate_image(optimized_ir, output_path, scale=scale)
    print(f"Compiled successfully: {generated_path}")
    return True


if __name__ == "__main__":
    main()

