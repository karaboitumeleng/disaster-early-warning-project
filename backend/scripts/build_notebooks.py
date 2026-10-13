"""Convert notebooks/src/*.py (jupytext-style '# %%' cells) into .ipynb files, no extra deps."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "notebooks" / "src"
OUT = ROOT / "notebooks"


def parse(text: str) -> list[dict]:
    cells: list[dict] = []
    kind = "code"
    buf: list[str] = []

    def flush() -> None:
        nonlocal buf
        src = "\n".join(buf).strip("\n")
        buf = []
        if not src:
            return
        lines = src.splitlines(keepends=True)
        if kind == "markdown":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
        else:
            cells.append({"cell_type": "code", "metadata": {}, "execution_count": None,
                          "outputs": [], "source": lines})

    for line in text.splitlines():
        m = re.match(r"^# %%(\s*\[markdown\])?\s*$", line)
        if m:
            flush()
            kind = "markdown" if m.group(1) else "code"
            continue
        buf.append(re.sub(r"^# ?", "", line) if kind == "markdown" else line)
    flush()
    return cells


for src in sorted(SRC.glob("0*.py")):
    nb = {
        "cells": parse(src.read_text(encoding="utf-8")),
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }
    target = OUT / (src.stem + ".ipynb")
    target.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("built", target.relative_to(ROOT))
