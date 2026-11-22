import numpy as np
import soundfile as sf

from flip.analyze import SR, analyze_file, fold_bpm, peaks, waveform


def near(a, b, tol=3):
    return abs(a - b) <= tol


def test_click_track_tempo_is_found_or_is_a_half_double_candidate(click_wav):
    r = analyze_file(click_wav)
    assert any(near(v, 120) for v in (r["bpm"], r["half_time"], r["double_time"]))
    assert abs(r["double_time"] - r["bpm"] * 2) < 0.2


def test_bpm_range_folds_by_octaves(click_wav):
    r = analyze_file(click_wav, bpm_min=70, bpm_max=180)
    assert 70 <= r["bpm"] < 180


def test_fold_bpm():
    assert fold_bpm(60, 70, 180) == 120
    assert fold_bpm(240, 70, 180) == 120
    assert fold_bpm(100, 70, 180) == 100


def test_key_for_a_minor_triad(tmp_path):
    t = np.arange(int(SR * 6)) / SR
    y = sum(np.sin(2 * np.pi * f * t) for f in (220.0, 261.63, 329.63)).astype(np.float32) / 3
    path = tmp_path / "triad.wav"
    sf.write(path, y, SR)
    r = analyze_file(path)
    assert r["key"] in {"A minor", "C major"}  # relative keys share the same notes
    assert len(r["key_candidates"]) == 3


def test_peaks_are_scaled_zero_to_one():
    p = peaks(np.sin(np.linspace(0, 200, SR)).astype(np.float32), n=40)
    assert len(p) == 40 and max(p) == 1.0 and min(p) >= 0


def test_waveform_has_duration_and_peaks(click_wav):
    w = waveform(click_wav)
    assert 15.5 < w["duration"] < 16.5 and len(w["peaks"]) == 96
