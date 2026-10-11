"""Audio -> MIDI via Spotify's Basic Pitch."""
from pathlib import Path
from basic_pitch.inference import predict_and_save


def to_midi(audio_path, out_dir="midi"):
    Path(out_dir).mkdir(exist_ok=True)
    predict_and_save([str(audio_path)], out_dir, True, False, False, False)
