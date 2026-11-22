"""Audio -> MIDI via Spotify's Basic Pitch."""
from pathlib import Path


def to_midi(audio_path, out_dir="midi"):
    from basic_pitch.inference import predict_and_save  # heavy import, load on demand

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    predict_and_save([str(audio_path)], str(out_dir), True, False, False, False)
    return Path(out_dir) / f"{Path(audio_path).stem}_basic_pitch.mid"
