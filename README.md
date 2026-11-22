# Flip Assistant

Drop in a track, get BPM, key, stems, and MIDI in one pass. Runs locally in your browser.

Built on librosa (BPM/key), Demucs (stem separation), and Basic Pitch (audio-to-MIDI),
served by FastAPI. Only processes files you provide. Clearing samples for release is your responsibility.

## Run the web app
    pip install -r requirements.txt
    uvicorn app:app --reload
    # open http://127.0.0.1:8000

Drag a file onto the unit (or hit SCAN). BPM and key show up first; stems and MIDI follow
when Demucs finishes. Stem splitting is the slow step (a few minutes per track on CPU).

## Run the CLI
    python run.py my_track.mp3 [--no-split]

## Tests
    pip install -r requirements-dev.txt
    pytest

## API
| Method | Path | What |
|---|---|---|
| POST | `/api/jobs` | multipart upload (`file`, optional `split`, `model`, `bpm_min`, `bpm_max`) -> `{id}` |
| GET | `/api/jobs/{id}` | status (`queued/analyzing/splitting/midi/done/error`) + results |
| GET | `/api/jobs/{id}/audio` | the uploaded file |
| GET | `/api/jobs/{id}/stems/{name}.wav` | one stem |
| GET | `/api/jobs/{id}/export/{stems|midi}` | zip download |

Limits: mp3/wav/flac/m4a/ogg/aiff, 100 MB, one job processed at a time, results deleted after 24 h.

## Roadmap
<<<<<<< HEAD
1. [x] CLI works end to end
2. [x] Tests for analyze.py and the API
3. [x] FastAPI backend with background jobs for the slow split step
4. [x] Web UI (upload, tempo/key, stem mixer, MIDI + stem export)
5. [ ] Browser extension that sends the current tab's audio file to this server
6. [ ] Auth and per-user storage if it ever goes public (today: local use only)
7. [ ] THREAT_MODEL.md and PRIVACY.md
8. [ ] Dockerize, deploy, put the live link on your resume
=======
1. [ ] CLI works end to end on 5 of your own tracks
2. [ ] Tests for analyze.py (use a click track at known BPM)
3. [ ] FastAPI backend + job queue for the slow split step
4. [ ] Simple web UI (upload, preview stems, download MIDI)
5. [ ] Auth, upload validation, file size/type limits, auto-delete after 24h
6. [ ] THREAT_MODEL.md and PRIVACY.md
7. [ ] Dockerize, deploy, get the live link 
>>>>>>> 167ca59afbb24f4dcc68a02d0cdafcabbef3e274
