"""BPM + key estimation and waveform peaks for an audio file."""
import librosa
import numpy as np

# Krumhansl-Schmuckler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SR = 22050
N_PEAKS = 96


def fold_bpm(bpm, lo, hi):
    """Move a tempo by whole octaves (x2 / /2) into [lo, hi) when possible."""
    for _ in range(4):
        if bpm < lo:
            bpm *= 2
        elif bpm >= hi:
            bpm /= 2
    return bpm


def estimate_bpm(y, sr, bpm_min=None, bpm_max=None):
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    if bpm <= 0:  # beat tracker found nothing; fall back to a global tempo estimate
        bpm = float(np.atleast_1d(librosa.feature.tempo(y=y, sr=sr))[0])
    if bpm_min and bpm_max:
        bpm = fold_bpm(bpm, bpm_min, bpm_max)
    beat_times = librosa.frames_to_time(beats, sr=sr)
    # Detectors often land on half/double time, so report both candidates.
    return {
        "bpm": round(bpm, 1),
        "half_time": round(bpm / 2, 1),
        "double_time": round(bpm * 2, 1),
        "first_beat": round(float(beat_times[0]), 3) if len(beat_times) else 0.0,
    }


def estimate_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    scores = []
    for i in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            score = np.corrcoef(chroma, np.roll(prof, i))[0, 1]
            scores.append((float(score), f"{NOTES[i]} {mode}"))
    scores.sort(reverse=True)
    best = scores[0]
    return {
        "key": best[1],
        "confidence": round(best[0], 2),
        "key_candidates": [{"key": k, "score": round(s, 2)} for s, k in scores[:3]],
    }


def peaks(y, n=N_PEAKS):
    """Loudness per slice, scaled 0..1, for drawing a bar waveform."""
    if len(y) == 0:
        return [0.0] * n
    chunks = np.array_split(y, n)
    rms = np.array([float(np.sqrt(np.mean(c ** 2))) if len(c) else 0.0 for c in chunks])
    top = rms.max()
    return [round(float(v / top), 3) if top > 0 else 0.0 for v in rms]


def load(path):
    return librosa.load(path, sr=SR, mono=True)


def waveform(path):
    """Cheap pass for stems: duration + peaks only."""
    y, sr = load(path)
    return {"duration": round(float(librosa.get_duration(y=y, sr=sr)), 2), "peaks": peaks(y)}


def analyze_file(path, bpm_min=None, bpm_max=None):
    y, sr = load(path)
    return {
        **estimate_bpm(y, sr, bpm_min, bpm_max),
        **estimate_key(y, sr),
        "duration": round(float(librosa.get_duration(y=y, sr=sr)), 2),
        "peaks": peaks(y),
    }
