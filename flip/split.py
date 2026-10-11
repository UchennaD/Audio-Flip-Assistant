"""Stem separation via the open-source Demucs model."""
import subprocess
from pathlib import Path


def split_stems(path, out_dir="stems"):
    subprocess.run(["python", "-m", "demucs", "-o", out_dir, str(path)], check=True)
    track = Path(path).stem
    stem_dir = next(Path(out_dir).glob(f"*/{track}"))
    return {p.stem: p for p in stem_dir.glob("*.wav")}
