"""Build and EXECUTE the real-data notebooks (notebooks/real_data/src/*.py -> *.ipynb with outputs).

Cells are '# %%' blocks (same convention as scripts/build_notebooks.py). Each notebook is run top to
bottom in a fresh namespace, in order 01..05, and the captured text, tables and figures are stored in the
.ipynb so the notebooks open fully rendered for a presentation. Needs only numpy, pandas, scikit-learn,
matplotlib, openpyxl and joblib (no Jupyter install). Re-run any time the data or code changes:

    python scripts/build_real_notebooks.py
"""
from __future__ import annotations

import ast
import base64
import contextlib
import io
import json
import os
import re
import sys
import traceback
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")  # headless; the notebook itself needs no backend setting

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks" / "real_data"
SRC = NB_DIR / "src"


def parse(text: str) -> list[dict]:
    cells: list[dict] = []
    kind, buf = "code", []

    def flush() -> None:
        nonlocal buf
        src = "\n".join(buf).strip("\n")
        buf = []
        if src:
            cells.append({"kind": kind, "source": src})

    for line in text.splitlines():
        m = re.match(r"^# %%(\s*\[markdown\])?\s*$", line)
        if m:
            flush()
            kind = "markdown" if m.group(1) else "code"
            continue
        buf.append(re.sub(r"^# ?", "", line) if kind == "markdown" else line)
    flush()
    return cells


def _lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def _display_outputs(value, count: int) -> dict:
    data = {"text/plain": _lines(repr(value))}
    if hasattr(value, "to_html"):
        data["text/html"] = _lines(value.to_html(max_rows=60, max_cols=30))
    return {"output_type": "execute_result", "execution_count": count, "metadata": {}, "data": data}


def run_cell(source: str, ns: dict, count: int) -> list[dict]:
    import matplotlib.pyplot as plt

    outputs: list[dict] = []
    out, err = io.StringIO(), io.StringIO()
    tree = ast.parse(source)
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        exec(compile(tree, "<cell>", "exec"), ns)
        value = eval(compile(last, "<cell>", "eval"), ns) if last is not None else None
    if out.getvalue():
        outputs.append({"output_type": "stream", "name": "stdout", "text": _lines(out.getvalue())})
    if err.getvalue():
        outputs.append({"output_type": "stream", "name": "stderr", "text": _lines(err.getvalue())})
    if value is not None:
        outputs.append(_display_outputs(value, count))
    for num in plt.get_fignums():
        fig = plt.figure(num)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        outputs.append({"output_type": "display_data", "metadata": {},
                        "data": {"image/png": base64.b64encode(buf.getvalue()).decode("ascii"),
                                 "text/plain": ["<Figure>"]}})
        plt.close(fig)
    return outputs


def build(path: Path) -> None:
    ns: dict = {"__name__": "__main__"}
    nb_cells, count = [], 0
    for i, cell in enumerate(parse(path.read_text(encoding="utf-8")), 1):
        if cell["kind"] == "markdown":
            nb_cells.append({"cell_type": "markdown", "metadata": {}, "source": _lines(cell["source"])})
            continue
        count += 1
        try:
            outputs = run_cell(cell["source"], ns, count)
        except Exception:
            print(f"\nFAILED {path.name}, cell {i}:\n{cell['source']}\n", file=sys.stderr)
            traceback.print_exc()
            raise SystemExit(1)
        nb_cells.append({"cell_type": "code", "metadata": {}, "execution_count": count,
                         "outputs": outputs, "source": _lines(cell["source"])})
    nb = {"cells": nb_cells, "nbformat": 4, "nbformat_minor": 4,
          "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                       "language_info": {"name": "python"}}}
    target = NB_DIR / (path.stem + ".ipynb")
    target.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print("built", target.relative_to(ROOT), f"({count} code cells executed)")


if __name__ == "__main__":
    os.chdir(NB_DIR)  # notebooks are meant to be opened from here (they also work from the repo root)
    for src in sorted(SRC.glob("0*.py")):
        build(src)
