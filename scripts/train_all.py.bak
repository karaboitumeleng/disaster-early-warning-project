"""One-command training: python scripts/train_all.py  (builds and executes notebooks 01-05)."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
subprocess.run([sys.executable, str(ROOT / "scripts" / "build_notebooks.py")], check=True)
for nb in sorted((ROOT / "notebooks").glob("0*.ipynb")):
    print("executing", nb.name)
    subprocess.run(
        [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute",
         "--inplace", str(nb)],
        check=True, cwd=ROOT / "notebooks",
    )
print("done - see models/metrics.json and models/model_card.md")
