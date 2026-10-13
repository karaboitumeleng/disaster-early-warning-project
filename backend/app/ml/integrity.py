"""Model-artefact integrity: SHA-256 manifest written at registration time, verified at load.
Stdlib only, so it works without torch installed."""
import hashlib
import hmac
import json
import logging
from collections.abc import Iterable
from pathlib import Path

log = logging.getLogger(__name__)
REQUIRED = ("ewsa_cnn_lstm.pt", "preprocessing.json", "metrics.json")
OPTIONAL = ("autoencoder.pt",)


class ModelIntegrityError(Exception):
    """Raised when artefacts are missing from, or differ from, the manifest."""


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def write_manifest(models_dir: Path, names: Iterable[str]) -> dict[str, str]:
    files = {n: sha256_file(models_dir / n) for n in names}
    (models_dir / "manifest.json").write_text(
        json.dumps({"files": files}, indent=2, sort_keys=True), encoding="utf-8"
    )
    return files


def verify_manifest(models_dir: Path, names: Iterable[str], require_manifest: bool) -> None:
    mpath = models_dir / "manifest.json"
    if not mpath.is_file():
        if require_manifest:
            raise ModelIntegrityError("models/manifest.json missing (run scripts/register_model.py)")
        log.warning("no model manifest; integrity not checked (allowed in dev only)")
        return
    try:
        expected = json.loads(mpath.read_text(encoding="utf-8"))["files"]
    except (OSError, ValueError, KeyError) as exc:
        raise ModelIntegrityError("unreadable model manifest") from exc
    for name in names:
        if name not in expected:
            raise ModelIntegrityError(f"{name} is not listed in the manifest")
        if not hmac.compare_digest(sha256_file(models_dir / name), str(expected[name])):
            raise ModelIntegrityError(f"checksum mismatch for {name}")
