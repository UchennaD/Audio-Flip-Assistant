"""Usage: python run.py path/to/track.mp3 [--no-split]"""
import json
import sys

from flip.analyze import analyze_file
from flip.midi import to_midi
from flip.split import split_stems


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    report = {"track": analyze_file(path)}
    if "--no-split" not in sys.argv:
        stems = split_stems(path)
        report["stems"] = {name: analyze_file(p) for name, p in stems.items()}
        for name in ("other", "bass"):  # melodic stems -> MIDI
            if name in stems:
                to_midi(stems[name])
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
