"""BPM + key estimation for an audio file."""
import librosa
import numpy as np

# Krumhansl-Schmuckler key profiles
MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def estimate_bpm(y, sr):
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    # Detectors often land on half/double time, so report both candidates.
    return {"bpm": round(bpm, 1), "half_time": round(bpm / 2, 1), "double_time": round(bpm * 2, 1)}


def estimate_key(y, sr):
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1)
    best = (-2.0, None)
    for i in range(12):
        for mode, prof in (("major", MAJOR), ("minor", MINOR)):
            score = np.corrcoef(chroma, np.roll(prof, i))[0, 1]
            if score > best[0]:
                best = (score, f"{NOTES[i]} {mode}")
    return {"key": best[1], "confidence": round(float(best[0]), 2)}


def analyze_file(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    return {**estimate_bpm(y, sr), **estimate_key(y, sr)}
