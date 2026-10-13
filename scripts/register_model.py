"""Record SHA-256 hashes of the trained artefacts in models/manifest.json.
Run after every training run; the API refuses artefacts that do not match."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
from app.ml.integrity import OPTIONAL, REQUIRED, write_manifest  # noqa: E402

models = ROOT / "models"
missing = [n for n in REQUIRED if not (models / n).is_file()]
if missing:
    sys.exit(f"Missing artefacts in models/: {missing}. Run python scripts/train_all.py first.")
names = [n for n in (*REQUIRED, *OPTIONAL) if (models / n).is_file()]
for name, digest in write_manifest(models, names).items():
    print(f"{digest}  {name}")
kind = json.loads((models / "metrics.json").read_text(encoding="utf-8")).get("data_kind")
if kind != "real":
    print(f"\nWARNING: this model was trained on {kind.upper()} data. It will drive live alerts in "
          "APP_ENV=dev only; other environments refuse it. Do not use it for operational decisions.")
