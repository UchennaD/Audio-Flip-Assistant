# Flip Assistant

A local web app for producers who flip samples. Drop in a track and get its **BPM**, **key**, **separated stems** (vocals, drums, bass, other), and **MIDI** for the melodic parts, then audition everything in a small in-browser mixer.

I built it because I make beats and wanted one tool that answers "what tempo and key is this, and can I pull the parts apart?" without bouncing between five sites.

<!-- Add a screenshot or GIF here: docs/screenshot.png -->

## What it does

- **Tempo and key detection.** Estimates BPM and shows the half-time and double-time readings too, since detectors often land on the wrong octave. Shows the top three key matches with their scores.
- **Stem separation.** Splits a track into 4 or 6 stems with Demucs.
- **Audio to MIDI.** Converts vocals, bass, and other melodic stems to `.mid` files with Basic Pitch.
- **In-browser mixer.** Play the original or the stems together, with mute, solo, and level faders per channel, plus loop and click-to-seek on the waveform.
- **Export.** Download all stems or all MIDI files as zips.
- **Tempo range setting.** Fold results into a range you actually work in (for example 70-180) so a 60 BPM reading shows as 120.

## How it works

```
Browser (vanilla JS, Web Audio, Canvas)
   |  POST /api/jobs (upload)         GET /api/jobs/{id} (poll)
   v
FastAPI  ->  background job runner (one worker)
                |-- analyze.py : librosa -> BPM, key, waveform peaks
                |-- split.py   : Demucs  -> stems
                `-- midi.py    : Basic Pitch -> MIDI
```

BPM and key come back quickly, so the interface shows them while the slow stem split is still running. The browser polls the job and fills in stems and MIDI as they finish.

**Key detection** uses chroma features from librosa, then correlates the average pitch-class profile against the Krumhansl-Schmuckler major and minor key profiles across all 12 roots. The best three matches are returned.

## Run it

Requires Python 3.10+ and `ffmpeg` on your PATH (Demucs and some audio formats need it).

```bash
git clone <this repo>
cd flip-assistant
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```

Open http://127.0.0.1:8000 and drag a track onto the unit.

Stem splitting is the slow step. Expect a few minutes per track on CPU, much less with a GPU. If you only want tempo and key, turn off **Split stems** in the Setup tab.

There is also a CLI:

```bash
python run.py my_track.mp3            # BPM, key, stems, MIDI
python run.py my_track.mp3 --no-split # BPM and key only
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests cover tempo and key detection on generated audio (a synthetic kick pattern and a known chord), octave folding, waveform peaks, and the full API flow with the heavy models stubbed out. They also check upload validation, size limits, path traversal, and 24-hour cleanup.

## API

| Method | Path                                  | Description                                                                              |
| ------ | ------------------------------------- | ---------------------------------------------------------------------------------------- |
| POST   | `/api/jobs`                           | Upload a file (`file`, optional `split`, `model`, `bpm_min`, `bpm_max`). Returns `{id}`. |
| GET    | `/api/jobs/{id}`                      | Job status (`queued`, `analyzing`, `splitting`, `midi`, `done`, `error`) and results.    |
| GET    | `/api/jobs/{id}/audio`                | The uploaded file.                                                                       |
| GET    | `/api/jobs/{id}/stems/{name}.wav`     | A single stem.                                                                           |
| GET    | `/api/jobs/{id}/export/{stems\|midi}` | Zip download.                                                                            |

## Skills this project demonstrates

- **Backend development in Python:** a FastAPI service with multipart uploads, background job processing, and a polling API for long-running work.
- **Audio signal processing:** tempo estimation, chroma features, key profile correlation, and loudness envelopes with librosa and NumPy.
- **Working with ML models:** integrating Demucs (source separation) and Basic Pitch (transcription) behind a clean interface, and handling failures without losing the rest of a job.
- **Frontend without a framework:** vanilla JavaScript, the Canvas API for the waveform and mixer, and the Web Audio API for synchronized multi-stem playback with gain control.
- **UI and interaction design:** a hardware-sampler interface that stays usable on a phone-sized screen.
- **Testing:** pytest with generated audio fixtures, API tests with monkeypatched models, and edge cases for bad input.
- **Secure handling of untrusted input:** file type allowlist, size limits, ID validation against path traversal, per-job isolated directories, and automatic deletion after 24 hours.

## Limits and notes

- Built for **local use**. There is no authentication or per-user storage, so don't expose it to the public internet as is.
- Accepts mp3, wav, flac, m4a, ogg, and aiff up to 100 MB, one job processed at a time.
- Tempo and key are estimates. Tracks with swing, tempo changes, or heavy modulation can fool them, which is why alternate readings are shown.
- Stem and MIDI quality depends on the models and the source material. Treat MIDI as a starting point to clean up.
- Only process audio you have the rights to use. Clearing samples for release is your responsibility.

## Roadmap

- [ ] Browser extension that sends audio to this server
- [ ] Docker image
- [ ] Auth and per-user storage for a hosted version
- [ ] Threat model and privacy notes

## Built with

[FastAPI](https://fastapi.tiangolo.com/), [librosa](https://librosa.org/), [Demucs](https://github.com/facebookresearch/demucs), [Basic Pitch](https://github.com/spotify/basic-pitch), and the browser's Canvas and Web Audio APIs.
