import numpy as np
import pytest
import soundfile as sf

SR = 22050


def click_track(bpm, seconds=16):
    """Kick-drum-like hits on every beat (closer to real audio than a bare click)."""
    y = np.zeros(int(SR * seconds), dtype=np.float32)
    t = 0.0
    while t < seconds - 0.3:
        i = int(t * SR)
        n = int(0.2 * SR)
        k = np.arange(n) / SR
        y[i:i + n] += np.sin(2 * np.pi * (60 + 120 * np.exp(-k * 30)) * k) * np.exp(-k * 14)
        t += 60 / bpm
    return y


@pytest.fixture
def click_wav(tmp_path):
    path = tmp_path / "click120.wav"
    sf.write(path, click_track(120), SR)
    return path
