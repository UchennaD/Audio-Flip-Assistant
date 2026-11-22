"""Stem separation via the open-source Demucs model."""
import subprocess
import sys
from pathlib import Path

MODELS = {"htdemucs": "4 stems", "htdemucs_6s": "6 stems"}


def split_stems(path, out_dir="stems", model="htdemucs"):
    if model not in MODELS:
        raise ValueError(f"unknown model: {model}")
    subprocess.run(
        [sys.executable, "-m", "demucs", "-n", model, "-o", str(out_dir), str(path)],
        check=True,
        capture_output=True,
    )
    track = Path(path).stem
    stem_dir = next(Path(out_dir).glob(f"*/{track}"))
    return {p.stem: p for p in sorted(stem_dir.glob("*.wav"))}
